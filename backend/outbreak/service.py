import asyncio
import logging
import os
import uuid
from typing import Any

from services.db import SessionLocal
from outbreak.db_queries import (
    distance_km,
    get_direction,
    get_case_by_id,
    get_eligible_outbreak_recipients,
    count_farmer_recent_outbreak_alerts,
    try_claim_outbreak_alert,
    delete_outbreak_alert_sent,
    mark_case_outbreak_evaluated,
)
from services.whatsapp_service import send_proactive_message
from farmer_store import normalize_phone, is_test_phone
from agent.diagnose import normalize_crop_text, DISEASE_DB
from services.i18n import (
    get_string,
    get_compass_direction,
    get_spread_description,
    get_morning_action,
    get_preventive_steps,
)

logger = logging.getLogger(__name__)

# Radius defaults in km by spread mode
DEFAULT_RADIUS_BY_MODE = {
    "air": float(os.getenv("OUTBREAK_RADIUS_AIR", "15")),
    "insect": float(os.getenv("OUTBREAK_RADIUS_INSECT", "10")),
    "water": float(os.getenv("OUTBREAK_RADIUS_WATER", "5")),
    "soil": float(os.getenv("OUTBREAK_RADIUS_SOIL", "3")),
    "contact": float(os.getenv("OUTBREAK_RADIUS_CONTACT", "3")),
}


def find_disease_db_entry(disease_name: str, crop: str | None = None) -> tuple[str | None, dict | None]:
    """Find matching entry in DISEASE_DB by key or display_name, prioritizing crop match."""
    if not disease_name:
        return None, None
    dn_clean = disease_name.lower().strip()

    # 1. Exact key match
    if disease_name in DISEASE_DB:
        return disease_name, DISEASE_DB[disease_name]

    # 2. Match with crop if provided
    if crop:
        c_norm = normalize_crop_text(crop) or crop.lower()
        for k, v in DISEASE_DB.items():
            entry_crop = normalize_crop_text(v.get("crop", "")) or v.get("crop", "").lower()
            if entry_crop == c_norm:
                disp = (v.get("display_name") or "").lower()
                if dn_clean == k.lower() or dn_clean == disp or dn_clean in disp or disp in dn_clean:
                    return k, v

    # 3. Match display_name or substring across entire db
    for k, v in DISEASE_DB.items():
        disp = (v.get("display_name") or "").lower()
        if dn_clean == disp or dn_clean == k.lower():
            return k, v
        if dn_clean in k.lower() or dn_clean in disp or disp in dn_clean:
            return k, v

    return None, None


def extract_spread_modes(entry: dict | None) -> list[str]:
    """Extract canonical spread modes (air, water, insect, soil, contact) from disease entry."""
    if not entry or entry.get("status") == "healthy":
        return []
    if entry.get("spread_modes"):
        return [m.lower().strip() for m in entry["spread_modes"]]

    text = (entry.get("spread") or "").lower()
    if not text:
        return []

    modes = set()
    if any(w in text for w in ["wind", "air", "spore", "airborne"]):
        modes.add("air")
    if any(w in text for w in ["rain", "splash", "water"]):
        modes.add("water")
    if any(w in text for w in ["insect", "whitefly", "aphid", "mite", "vector", "fly"]):
        modes.add("insect")
    if any(w in text for w in ["soil", "debris"]):
        modes.add("soil")
    if any(w in text for w in ["contact", "tool", "hand", "cloth", "seed"]):
        modes.add("contact")

    return list(modes)


def get_susceptible_crops_for_disease(disease_name: str, primary_crop: str) -> set[str]:
    """
    Return set of canonical crops susceptible to this disease.
    Same-crop is always included. Other crops are included if the disease/pathogen affects them.
    """
    susceptible = set()
    norm_primary = normalize_crop_text(primary_crop)
    if norm_primary:
        susceptible.add(norm_primary)

    _, target_entry = find_disease_db_entry(disease_name, primary_crop)
    target_display = (target_entry.get("display_name") if target_entry else disease_name).lower().replace("leaf", "").strip()
    target_pathogen = (target_entry.get("pathogen") if target_entry else "").split("(")[0].strip().lower()

    for k, v in DISEASE_DB.items():
        if v.get("status") == "healthy":
            continue
        c = normalize_crop_text(v.get("crop", ""))
        if not c:
            continue
        v_disp = (v.get("display_name") or "").lower().replace("leaf", "").strip()
        v_path = (v.get("pathogen") or "").split("(")[0].strip().lower()

        # Match by display name stem or pathogen
        if target_display and (target_display == v_disp or target_display in v_disp or v_disp in target_display):
            susceptible.add(c)
        elif target_pathogen and v_path and (target_pathogen in v_path or v_path in target_pathogen):
            susceptible.add(c)

    return susceptible


def calculate_outbreak_radius(modes: list[str]) -> float:
    """Calculate maximum radius in km across all active spread modes."""
    if not modes:
        return 0.0
    return max(DEFAULT_RADIUS_BY_MODE.get(m, 3.0) for m in modes)


async def evaluate_case(case_id: str | uuid.UUID, dry_run: bool | None = None) -> dict[str, Any]:
    """
    Evaluate an open disease case for outbreak notification to nearby farmers.
    Idempotent: sets outbreak_evaluated_at at the end; running twice sends nothing.
    """
    case_str = str(case_id)
    is_dry_run = dry_run if dry_run is not None else (os.getenv("OUTBREAK_DRY_RUN", "false").lower() in ("true", "1"))

    # 1. Fetch case from database
    def _fetch_case():
        with SessionLocal() as db:
            return get_case_by_id(db, case_str)

    case = await asyncio.to_thread(_fetch_case)
    if not case:
        logger.warning(f"[Outbreak] Case {case_str} not found")
        return {"status": "case_not_found", "case_id": case_str}

    # 2. Check if already evaluated (Requirement 2.e)
    if case.get("outbreak_evaluated_at") is not None:
        logger.info(f"[Outbreak] Case {case_str} already evaluated at {case['outbreak_evaluated_at']}")
        return {"status": "already_evaluated", "case_id": case_str, "evaluated_at": str(case["outbreak_evaluated_at"])}

    # 3. Check case status (open or worsening)
    c_status = (case.get("status") or "").lower()
    if c_status not in ("open", "worsening"):
        logger.info(f"[Outbreak] Case {case_str} status '{c_status}' is not open/worsening")
        return {"status": "case_not_open", "case_status": c_status}

    # 4. Check reporter coordinates
    rep_lat = case.get("lat")
    rep_lng = case.get("lng")
    if rep_lat is None or rep_lng is None:
        logger.info(f"[Outbreak] Case {case_str} has no lat/lng coordinates")
        return {"status": "missing_coordinates"}

    # 5. Check detector confidence >= DISEASE_OUTBREAK_MIN_CONF (default 0.70)
    min_conf = float(os.getenv("DISEASE_OUTBREAK_MIN_CONF", "0.70"))
    case_conf = case.get("confidence")
    if case_conf is None or float(case_conf) < min_conf:
        logger.info(f"[Outbreak] Case {case_str} confidence {case_conf} below threshold {min_conf}")
        return {"status": "confidence_below_threshold", "confidence": case_conf, "min_conf": min_conf}

    # 6. Check severity condition (farmer-reported >= Moderate, or OUTBREAK_DEMO_MODE=true)
    demo_mode = os.getenv("OUTBREAK_DEMO_MODE", "false").lower() in ("true", "1")
    if not demo_mode:
        sev_source = case.get("severity_source")
        sev_level = (case.get("severity_level") or "").title()
        if sev_source != "farmer_reported" or sev_level not in ("Moderate", "Severe"):
            logger.info(f"[Outbreak] Case {case_str} severity condition not met: source={sev_source}, level={sev_level}")
            return {
                "status": "severity_condition_unmet",
                "severity_source": sev_source,
                "severity_level": sev_level,
            }

    # 7. Check disease entry and contagious spread modes
    disease_name = case.get("disease", "")
    crop_name = case.get("crop", "")
    db_key, db_entry = find_disease_db_entry(disease_name, crop_name)

    if not db_entry or db_entry.get("status") == "healthy":
        # Non-contagious or healthy — mark evaluated and stop
        def _mark_done():
            with SessionLocal() as db:
                mark_case_outbreak_evaluated(db, case_str)
        if not is_dry_run:
            await asyncio.to_thread(_mark_done)
        logger.info(f"[Outbreak] Disease '{disease_name}' has no contagious entry in disease_db")
        return {"status": "not_contagious", "disease": disease_name}

    modes = extract_spread_modes(db_entry)
    # Merge any spread modes saved on the case itself
    if case.get("spread_modes"):
        modes = list(set(modes + [m.lower().strip() for m in case["spread_modes"]]))

    if not modes:
        def _mark_done():
            with SessionLocal() as db:
                mark_case_outbreak_evaluated(db, case_str)
        if not is_dry_run:
            await asyncio.to_thread(_mark_done)
        logger.info(f"[Outbreak] Disease '{disease_name}' has no active spread modes (not contagious)")
        return {"status": "not_contagious", "disease": disease_name}

    # 8. Radius by spread mode
    radius_km = calculate_outbreak_radius(modes)
    logger.info(f"[Outbreak] Case {case_str} ({disease_name}): modes={modes}, radius={radius_km} km")

    # 9. Query eligible recipients
    def _fetch_recipients():
        with SessionLocal() as db:
            return get_eligible_outbreak_recipients(db, case["phone"])

    recipients = await asyncio.to_thread(_fetch_recipients)

    # Allowlist filter if BROADCAST_ALLOWLIST is configured
    allowlist_raw = os.getenv("BROADCAST_ALLOWLIST")
    if allowlist_raw and allowlist_raw.strip():
        allowlist = {normalize_phone(p.strip()) for p in allowlist_raw.split(",") if p.strip()}
        recipients = [r for r in recipients if normalize_phone(r["phone"]) in allowlist]

    case_crop_norm = normalize_crop_text(crop_name) or crop_name.lower()
    susceptible_crops = get_susceptible_crops_for_disease(disease_name, crop_name)

    evaluated_candidates = []
    alerts_sent = 0
    alerts_skipped = 0

    for farmer in recipients:
        f_phone = normalize_phone(farmer["phone"])
        dist = distance_km(rep_lat, rep_lng, farmer["lat"], farmer["lng"])
        if dist > radius_km:
            continue

        farmer_crops = [str(c) for c in (farmer.get("crops") or [])]
        farmer_crops_norm = {normalize_crop_text(c) or c.lower() for c in farmer_crops}

        is_same_crop = (case_crop_norm in farmer_crops_norm)
        is_other_susceptible = any(c in susceptible_crops for c in farmer_crops_norm)

        if not is_same_crop and not is_other_susceptible:
            # Farmer does not grow a susceptible crop
            continue

        # 10. Max 2 outbreak alerts per farmer per 24h
        def _count_alerts(p=f_phone):
            with SessionLocal() as db:
                return count_farmer_recent_outbreak_alerts(db, p, hours=24)

        recent_count = await asyncio.to_thread(_count_alerts)
        if recent_count >= 2:
            logger.info(f"[Outbreak] Farmer {f_phone} reached 24h cap ({recent_count} alerts)")
            alerts_skipped += 1
            continue

        # 11. Compose message
        lang = (farmer.get("language") or "english").lower()
        dist_rounded = round(dist)
        direction_eng = get_direction(farmer["lat"], farmer["lng"], rep_lat, rep_lng)
        direction_loc = get_compass_direction(direction_eng, lang)
        spread_info = get_spread_description(modes, lang)
        morning_action = get_morning_action(lang)
        fallback_steps = (db_entry.get("remedies") or {}).get("prevention") or []
        preventive_steps = get_preventive_steps(disease_name, lang, fallback_steps)
        steps_text = "\n".join([f"• {s}" for s in preventive_steps[:4]])

        disp_disease = db_entry.get("display_name") or disease_name
        disp_crop = (farmer_crops[0] if farmer_crops else crop_name).title()

        if is_same_crop:
            msg = get_string(
                "outbreak_alert_urgent",
                lang,
                disease=disp_disease,
                crop=crop_name.title(),
                dist_km=dist_rounded,
                direction=direction_loc,
                spread_info=spread_info,
                steps=steps_text,
                morning_action=morning_action,
            )
        else:
            msg = get_string(
                "outbreak_alert_watch",
                lang,
                disease=disp_disease,
                crop=disp_crop,
                dist_km=dist_rounded,
                direction=direction_loc,
                spread_info=spread_info,
                steps=steps_text,
                morning_action=morning_action,
            )

        candidate_info = {
            "phone": f_phone,
            "language": lang,
            "distance_km": dist_rounded,
            "direction": direction_eng,
            "direction_localized": direction_loc,
            "match_type": "same_crop" if is_same_crop else "other_susceptible",
            "message": msg,
        }
        evaluated_candidates.append(candidate_info)

        # 12. Send or Dry Run
        if is_dry_run:
            print(f"[Outbreak DRY_RUN] Recipient: {f_phone} ({lang}) | {dist_rounded} km {direction_loc} | {candidate_info['match_type']}")
            print(f"[Outbreak DRY_RUN] Message Preview:\n{msg}\n" + "-" * 50)
            alerts_sent += 1
        else:
            # Claim deduplication row
            def _claim(p=f_phone):
                with SessionLocal() as db:
                    return try_claim_outbreak_alert(db, case_str, p)

            claimed = await asyncio.to_thread(_claim)
            if not claimed:
                logger.info(f"[Outbreak] Alert already claimed for case {case_str} -> {f_phone}")
                continue

            # Send via proactive message path
            success = await send_proactive_message(f_phone, msg)
            if not success:
                logger.warning(f"[Outbreak] Send failed for {f_phone}. Deleting claim to allow retry.")
                def _rollback(p=f_phone):
                    with SessionLocal() as db:
                        delete_outbreak_alert_sent(db, case_str, p)
                await asyncio.to_thread(_rollback)
            else:
                alerts_sent += 1

    # 13. Mark case evaluated at the end
    if not is_dry_run:
        def _mark_done():
            with SessionLocal() as db:
                mark_case_outbreak_evaluated(db, case_str)
        await asyncio.to_thread(_mark_done)

    return {
        "status": "completed",
        "case_id": case_str,
        "disease": disease_name,
        "spread_modes": modes,
        "radius_km": radius_km,
        "dry_run": is_dry_run,
        "alerts_sent": alerts_sent,
        "alerts_skipped": alerts_skipped,
        "candidates": evaluated_candidates,
    }


def schedule_outbreak_evaluation(case_id: str | uuid.UUID) -> None:
    """
    Fire-and-forget background task to evaluate case for outbreak alerts.
    Never raises an exception into the caller.
    """
    async def _safe_run():
        try:
            res = await evaluate_case(case_id)
            print(f"[Outbreak] Background evaluation result for {case_id}: {res}")
        except Exception as e:
            print(f"[Outbreak] Background evaluation failed for case {case_id}: {e}")
            logger.error(f"[Outbreak] Background evaluation failed for case {case_id}: {e}", exc_info=True)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_safe_run())
    except RuntimeError:
        # No running event loop in current thread
        try:
            asyncio.run(_safe_run())
        except Exception as e:
            logger.error(f"[Outbreak] schedule_outbreak_evaluation error: {e}")
    except Exception as e:
        logger.error(f"[Outbreak] schedule_outbreak_evaluation error: {e}")