import json
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import text
from services.db import SessionLocal


TEST_PHONE_PREFIX = "+91000000"


def normalize_phone(phone: str) -> str:
    return (phone or "").replace("whatsapp:", "").strip()


def is_test_phone(phone: str) -> bool:
    """Returns True if the normalized phone starts with the reserved test prefix."""
    pid = normalize_phone(phone)
    return pid.startswith(TEST_PHONE_PREFIX)


def delete_farmer_records(phone: str) -> None:
    """
    Deletes all records across tables for a test farmer:
    farmers, conversation_state, chat_history, processed_messages, disease_cases, case_updates, price_alerts.
    """
    pid = normalize_phone(phone)
    if not pid:
        return

    with SessionLocal() as db:
        # 1. case_updates (via disease_cases or directly)
        db.execute(
            text("""
                DELETE FROM case_updates
                WHERE case_id IN (SELECT id FROM disease_cases WHERE phone = :phone)
            """),
            {"phone": pid},
        )
        # 2. outbreak_alerts_sent
        db.execute(
            text("DELETE FROM outbreak_alerts_sent WHERE recipient_phone = :phone"),
            {"phone": pid},
        )
        # 3. disease_cases
        db.execute(
            text("DELETE FROM disease_cases WHERE phone = :phone"),
            {"phone": pid},
        )
        # 4. price_alerts
        db.execute(
            text("DELETE FROM price_alerts WHERE phone = :phone"),
            {"phone": pid},
        )
        # 5. chat_history
        db.execute(
            text("DELETE FROM chat_history WHERE phone = :phone"),
            {"phone": pid},
        )
        # 6. conversation_state
        db.execute(
            text("DELETE FROM conversation_state WHERE phone = :phone"),
            {"phone": pid},
        )
        # 7. detections
        db.execute(
            text("DELETE FROM detections WHERE phone = :phone"),
            {"phone": pid},
        )
        # 8. farmers
        db.execute(
            text("DELETE FROM farmers WHERE phone = :phone"),
            {"phone": pid},
        )
        db.commit()


def get_farmer_language(phone: str) -> str | None:
    """Returns stored language code (hindi/kannada/english) or None if unset."""
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT language FROM farmers WHERE phone = :phone"),
            {"phone": pid},
        ).fetchone()
    if not row or row[0] is None:
        return None
    s = str(row[0]).strip()
    return s if s else None


def set_farmer_language(phone: str, language: str) -> None:
    """Persist language on farmers row (upserts phone row if missing)."""
    pid = normalize_phone(phone)
    lang = (language or "").strip().lower()
    if not lang:
        return
    with SessionLocal() as db:
        db.execute(
            text(
                """
                INSERT INTO farmers (phone, language, last_seen)
                VALUES (:phone, :language, NOW())
                ON CONFLICT (phone) DO UPDATE
                SET language = EXCLUDED.language, last_seen = NOW()
                """
            ),
            {"phone": pid, "language": lang},
        )
        db.commit()


def get_farmer(phone: str) -> dict:
    """
    Returns farmer dict.
    Returns real None for missing name, location, soil_type, and language (no hardcoded fallbacks).
    """
    phone = normalize_phone(phone)
    with SessionLocal() as db:
        result = db.execute(
            text(
                "SELECT phone, name, crops, location, soil_type, history, messages, language, "
                "lat, lng, onboarding_step, water_source, state, district, farm_size_acres "
                "FROM farmers WHERE phone = :phone"
            ),
            {"phone": phone},
        ).fetchone()

        if not result:
            db.execute(
                text("INSERT INTO farmers (phone) VALUES (:phone) ON CONFLICT DO NOTHING"),
                {"phone": phone},
            )
            db.commit()
            result = db.execute(
                text(
                    "SELECT phone, name, crops, location, soil_type, history, messages, language, "
                    "lat, lng, onboarding_step, water_source, state, district, farm_size_acres "
                    "FROM farmers WHERE phone = :phone"
                ),
                {"phone": phone},
            ).fetchone()

    return {
        "phone":           result[0],
        "name":            result[1] if result[1] else None,
        "crops":           result[2] or [],
        "location":        result[3] if result[3] else None,
        "soil_type":       result[4] if result[4] and result[4] != "unknown" else None,
        "history":         result[5] or [],
        "messages":        result[6] or [],
        "language":        result[7] if result[7] else None,
        "lat":             result[8] if len(result) > 8 else None,
        "lng":             result[9] if len(result) > 9 else None,
        "onboarding_step": result[10] if len(result) > 10 else None,
        "water_source":    result[11] if len(result) > 11 else None,
        "state":           result[12] if len(result) > 12 else None,
        "district":        result[13] if len(result) > 13 else None,
        "farm_size_acres": float(result[14]) if len(result) > 14 and result[14] is not None else None,
    }


def get_or_create_farmer(phone: str) -> dict:
    return get_farmer(phone)


def set_onboarding_step(phone: str, step: str) -> None:
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        db.execute(
            text("UPDATE farmers SET onboarding_step = :step, last_seen = NOW() WHERE phone = :phone"),
            {"phone": pid, "step": step},
        )
        db.commit()


# ── Conversation State Helpers ────────────────────────────────────────────────

def get_state(phone: str) -> dict | None:
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT flow, step, data, updated_at FROM conversation_state WHERE phone = :phone"),
            {"phone": pid},
        ).fetchone()
    if not row:
        return None
    data = row[2] if isinstance(row[2], dict) else {}
    return {
        "flow": row[0],
        "step": row[1],
        "data": data,
        "updated_at": row[3],
    }


def set_state(phone: str, flow: str, step: str, data: dict = None) -> None:
    pid = normalize_phone(phone)
    payload_json = json.dumps(data or {})
    with SessionLocal() as db:
        db.execute(
            text("""
                INSERT INTO conversation_state (phone, flow, step, data, updated_at)
                VALUES (:phone, :flow, :step, cast(:data as jsonb), NOW())
                ON CONFLICT (phone) DO UPDATE
                SET flow = EXCLUDED.flow,
                    step = EXCLUDED.step,
                    data = EXCLUDED.data,
                    updated_at = NOW()
            """),
            {"phone": pid, "flow": flow, "step": step, "data": payload_json},
        )
        db.commit()


def clear_state(phone: str) -> None:
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM conversation_state WHERE phone = :phone"),
            {"phone": pid},
        )
        db.commit()


# ── Chat History Helpers ──────────────────────────────────────────────────────

def add_chat(phone: str, role: str, content: str) -> None:
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        db.execute(
            text("""
                INSERT INTO chat_history (phone, role, content, created_at)
                VALUES (:phone, :role, :content, NOW())
            """),
            {"phone": pid, "role": role, "content": content},
        )
        db.execute(
            text("UPDATE farmers SET last_message_at = NOW(), last_seen = NOW() WHERE phone = :phone"),
            {"phone": pid},
        )
        db.commit()


def get_chat_history(phone: str, limit: int = 10) -> list[dict]:
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT role, content
                FROM chat_history
                WHERE phone = :phone
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
            """),
            {"phone": pid, "limit": limit},
        ).fetchall()
    # Reverse to return in chronological order
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def save_message(phone: str, user_msg: str, bot_msg: str):
    """
    Persist chat to chat_history table (discontinues unbounded JSON growth in farmers.messages).
    """
    pid = normalize_phone(phone)
    add_chat(pid, "user", user_msg)
    add_chat(pid, "assistant", bot_msg)


# ── Message Deduplication Helper ──────────────────────────────────────────────

def mark_message_processed(message_sid: str) -> bool:
    """
    Returns True if message_sid was newly inserted (first time seen),
    or False if message_sid was already processed.
    """
    if not message_sid:
        return True
    with SessionLocal() as db:
        res = db.execute(
            text("""
                INSERT INTO processed_messages (message_sid, created_at)
                VALUES (:sid, NOW())
                ON CONFLICT (message_sid) DO NOTHING
            """),
            {"sid": message_sid},
        )
        db.commit()
        return res.rowcount > 0


# ── Profile & Farmer Location Updates ────────────────────────────────────────

def update_farmer_profile(phone: str, **kwargs):
    phone = normalize_phone(phone)
    # Ensure row exists
    get_farmer(phone)

    allowed = {
        "name", "crops", "location", "soil_type", "water_source",
        "state", "district", "farm_size_acres", "onboarding_step", "language"
    }
    fields, values = [], {"phone": phone}

    for key, val in kwargs.items():
        if key in allowed and val is not None:
            fields.append(f"{key} = :{key}")
            values[key] = val

    if not fields:
        return

    fields.append("last_seen = NOW()")
    with SessionLocal() as db:
        db.execute(
            text(f"UPDATE farmers SET {', '.join(fields)} WHERE phone = :phone"),
            values,
        )
        db.commit()


def add_to_history(phone: str, issue: str, treatment: str):
    phone = normalize_phone(phone)
    event = json.dumps([{
        "date":      str(date.today()),
        "issue":     issue,
        "treatment": treatment,
    }])
    with SessionLocal() as db:
        db.execute(
            text("""
                UPDATE farmers
                SET history = COALESCE(history, '[]'::jsonb) || cast(:event as jsonb)
                WHERE phone = :phone
            """),
            {"event": event, "phone": phone},
        )
        db.commit()


def _parse_last_detection_row(raw) -> dict | None:
    """Support jsonb object, JSON string, or legacy 'bbox|severity' text."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        d = dict(raw)
        b = d.get("bbox_pct")
        if b is not None:
            try:
                d["affected_pct"] = float(b)
            except (TypeError, ValueError):
                pass
        return d
    if isinstance(raw, str):
        raw_s = raw.strip()
        if raw_s.startswith("{"):
            try:
                data = json.loads(raw_s)
                b = data.get("bbox_pct")
                if b is not None:
                    try:
                        data["affected_pct"] = float(b)
                    except (TypeError, ValueError):
                        pass
                return data
            except Exception:
                pass
        parts = raw_s.split("|")
        try:
            pct = float(parts[0])
            sev = parts[1] if len(parts) > 1 else "unknown"
            return {
                "affected_pct": pct,
                "bbox_pct":     pct,
                "severity":     sev,
                "disease":      "Crop disease",
            }
        except (ValueError, IndexError):
            pass
    return None


def get_last_detection(phone: str) -> dict | None:
    """Last crop diagnosis: returns real None if nothing is stored (no fake 20%)."""
    phone = normalize_phone(phone)
    try:
        with SessionLocal() as db:
            result = db.execute(
                text("SELECT last_detection FROM farmers WHERE phone = :phone"),
                {"phone": phone},
            ).fetchone()
        if result and result[0] is not None:
            return _parse_last_detection_row(result[0])
    except Exception as e:
        print(f"[FarmerStore] get_last_detection error: {e}")

    return None


def get_farmer_location(phone: str) -> dict | None:
    """Returns saved lat/lng or None if not set yet."""
    phone = normalize_phone(phone)
    with SessionLocal() as db:
        result = db.execute(
            text("SELECT lat, lng FROM farmers WHERE phone = :phone"),
            {"phone": phone},
        ).fetchone()

    if result and result[0] is not None and result[1] is not None:
        return {"lat": result[0], "lng": result[1]}
    return None


def save_farmer_location(phone: str, lat: float, lng: float):
    phone = normalize_phone(phone)
    with SessionLocal() as db:
        db.execute(
            text("""
                INSERT INTO farmers (phone, lat, lng)
                VALUES (:phone, :lat, :lng)
                ON CONFLICT (phone) DO UPDATE
                SET lat = :lat, lng = :lng, last_seen = NOW()
            """),
            {"phone": phone, "lat": lat, "lng": lng},
        )
        db.commit()
    print(f"[FarmerStore] Saved location for {phone}: {lat}, {lng}")


def save_price_alert(phone: str, commodity: str, target_price: float, direction: str, market: str = None):
    phone = normalize_phone(phone)
    with SessionLocal() as db:
        db.execute(
            text("""
                INSERT INTO price_alerts (phone, commodity, target_price, direction, market)
                VALUES (:phone, :commodity, :target_price, :direction, :market)
            """),
            {
                "phone": phone,
                "commodity": commodity,
                "target_price": target_price,
                "direction": direction,
                "market": market,
            },
        )
        db.commit()
    print(f"[Alert] Saved: {phone} wants {commodity} {direction} Rs.{target_price}")


def get_active_alerts() -> list:
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT id, phone, commodity, target_price, direction, market
                FROM price_alerts
                WHERE active = TRUE
                  AND phone NOT LIKE :test_prefix
            """),
            {"test_prefix": f"{TEST_PHONE_PREFIX}%"},
        ).fetchall()
    return [
        {
            "id": r[0],
            "phone": r[1],
            "commodity": r[2],
            "target_price": float(r[3]),
            "direction": r[4],
            "market": r[5] if len(r) > 5 else None,
        }
        for r in rows
    ]


def deactivate_alert(alert_id: int):
    with SessionLocal() as db:
        db.execute(
            text("UPDATE price_alerts SET active = FALSE WHERE id = :id"),
            {"id": alert_id},
        )
        db.commit()


def get_farmer_alerts(phone: str) -> list[dict]:
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT id, commodity, target_price, direction, market, created_at
                FROM price_alerts
                WHERE phone = :phone AND active = TRUE
                ORDER BY created_at DESC
            """),
            {"phone": pid},
        ).fetchall()
    return [
        {
            "id": r[0],
            "commodity": r[1],
            "target_price": float(r[2]),
            "direction": r[3],
            "market": r[4] if len(r) > 4 else None,
            "created_at": r[5].isoformat() if len(r) > 5 and r[5] else None,
        }
        for r in rows
    ]


def get_open_disease_cases(phone: str) -> list[dict]:
    pid = normalize_phone(phone)
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT id, crop, disease, severity_level, severity_score, created_at
                FROM disease_cases
                WHERE phone = :phone AND status = 'open'
                ORDER BY created_at DESC
            """),
            {"phone": pid},
        ).fetchall()
    return [
        {
            "id": str(r[0]),
            "crop": r[1],
            "disease": r[2],
            "severity_level": r[3],
            "severity_score": r[4],
            "created_at": r[5].isoformat() if len(r) > 5 and r[5] else None,
        }
        for r in rows
    ]


def add_farmer_crop(phone: str, crop: str):
    if not crop:
        return
    phone = normalize_phone(phone)
    crop = crop.strip().lower()
    farmer = get_farmer(phone)
    crops = farmer.get("crops") or []
    if isinstance(crops, list):
        if crop not in [c.lower() for c in crops]:
            crops.append(crop)
            update_farmer_profile(phone, crops=crops)


def record_detection_if_outbreak(phone: str, disease_result: dict) -> None:
    """Legacy detection recorder — writing to detections table is stopped per requirement."""
    return


def save_farmer_diagnosis(phone: str, disease_result: dict, user_message: str) -> None:
    if not disease_result or disease_result.get("error"):
        return
    raw = (disease_result.get("raw_name") or "").lower()
    if "healthy" in raw:
        return

    pid = normalize_phone(phone)
    get_farmer(pid)

    sev = disease_result.get("severity") or {}
    prog = disease_result.get("progression") or {}
    payload = {
        "disease": disease_result.get("disease"),
        "crop_model": disease_result.get("crop"),
        "crop_from_message": (user_message or "").strip()[:200] or None,
        "severity_level": sev.get("level"),
        "severity_description": sev.get("description"),
        "severity_score": disease_result.get("severity_score"),
        "spread": disease_result.get("spread"),
        "confidence": disease_result.get("confidence"),
        "bbox_pct": disease_result.get("bbox_pct"),
        "progression": prog,
        "urgency": disease_result.get("urgency"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    issue = str(disease_result.get("disease") or "Crop disease")
    treatment = (
        f"Severity {sev.get('level', '?')} (score {disease_result.get('severity_score', '?')}); "
        f"urgency: {disease_result.get('urgency') or '—'}"
    )

    with SessionLocal() as db:
        db.execute(
            text("""
                UPDATE farmers
                SET last_detection = cast(:payload as jsonb),
                    last_seen = NOW()
                WHERE phone = :phone
            """),
            {"payload": payload_json, "phone": pid},
        )
        db.commit()

    add_to_history(pid, issue, treatment)


# ── Disease Case Management Helpers ───────────────────────────────────────────

def create_case(
    phone: str,
    crop: str,
    disease: str,
    confidence: float = None,
    severity_level: str = None,
    severity_score: int = None,
    severity_source: str = "unknown",
    lat: float = None,
    lng: float = None,
    spread_modes: list[str] = None,
    image_url: str = None,
    next_followup_at = None,
) -> uuid.UUID:
    pid = normalize_phone(phone)
    case_id = uuid.uuid4()
    with SessionLocal() as db:
        db.execute(
            text("""
                INSERT INTO disease_cases (
                    id, phone, crop, disease, status, confidence,
                    severity_level, severity_score, severity_source,
                    lat, lng, spread_modes, image_url, next_followup_at, created_at
                ) VALUES (
                    :id, :phone, :crop, :disease, 'open', :confidence,
                    :severity_level, :severity_score, :severity_source,
                    :lat, :lng, :spread_modes, :image_url, :next_followup_at, NOW()
                )
            """),
            {
                "id": case_id,
                "phone": pid,
                "crop": crop,
                "disease": disease,
                "confidence": confidence,
                "severity_level": severity_level,
                "severity_score": severity_score,
                "severity_source": severity_source,
                "lat": lat,
                "lng": lng,
                "spread_modes": spread_modes or [],
                "image_url": image_url,
                "next_followup_at": next_followup_at,
            },
        )
        db.commit()
    return case_id


def update_case(case_id: uuid.UUID | str, **kwargs) -> None:
    allowed = {
        "status", "severity_level", "severity_score", "severity_source",
        "last_followup_at", "next_followup_at", "followup_count", "resolved_at"
    }
    fields, values = [], {"id": str(case_id)}
    for key, val in kwargs.items():
        if key in allowed and val is not None:
            fields.append(f"{key} = :{key}")
            values[key] = val

    if not fields:
        return

    with SessionLocal() as db:
        db.execute(
            text(f"UPDATE disease_cases SET {', '.join(fields)} WHERE id = :id"),
            values,
        )
        db.commit()


def due_followup_cases() -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT id, phone, crop, disease, status, next_followup_at, followup_count
                FROM disease_cases
                WHERE status = 'open'
                  AND next_followup_at IS NOT NULL
                  AND next_followup_at <= NOW()
                  AND phone NOT LIKE :test_prefix
            """),
            {"test_prefix": f"{TEST_PHONE_PREFIX}%"},
        ).fetchall()
    return [
        {
            "id": r[0],
            "phone": r[1],
            "crop": r[2],
            "disease": r[3],
            "status": r[4],
            "next_followup_at": r[5],
            "followup_count": r[6],
        }
        for r in rows
    ]


def get_eligible_briefing_farmers() -> list[dict]:
    """
    Returns farmers eligible for proactive morning briefing:
    - onboarding_step = 'done'
    - proactive_opt_in is true (if column exists)
    - Has at least crops or a location (lat/lng or location string)
    - Skips reserved test numbers
    """
    with SessionLocal() as db:
        # Check if proactive_opt_in column exists in farmers table
        has_opt_in_col = db.execute(
            text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'farmers' AND column_name = 'proactive_opt_in'
            """)
        ).scalar()

        if has_opt_in_col:
            query = """
                SELECT phone, name, crops, location, lat, lng, language, district, state, proactive_opt_in
                FROM farmers
                WHERE onboarding_step = 'done'
                  AND (proactive_opt_in IS TRUE OR proactive_opt_in IS NULL)
                  AND phone NOT LIKE :test_prefix
            """
        else:
            query = """
                SELECT phone, name, crops, location, lat, lng, language, district, state, NULL as proactive_opt_in
                FROM farmers
                WHERE onboarding_step = 'done'
                  AND phone NOT LIKE :test_prefix
            """

        rows = db.execute(text(query), {"test_prefix": f"{TEST_PHONE_PREFIX}%"}).fetchall()

    farmers = []
    for r in rows:
        phone = r[0]
        name = r[1] if r[1] else None
        crops = r[2] or []
        location = r[3] if r[3] else None
        lat = r[4]
        lng = r[5]
        language = r[6] or "english"
        district = r[7] if r[7] else None
        state = r[8] if r[8] else None

        has_location = (lat is not None and lng is not None) or bool(location) or bool(district)
        has_crops = bool(crops and len(crops) > 0)

        # Requirement: If the farmer has neither crops nor location, skip them.
        if not has_location and not has_crops:
            continue

        farmers.append({
            "phone": phone,
            "name": name,
            "crops": crops,
            "location": location,
            "lat": lat,
            "lng": lng,
            "language": language,
            "district": district,
            "state": state,
        })

    return farmers