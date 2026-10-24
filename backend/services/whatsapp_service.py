# services/whatsapp_service.py
"""
services/whatsapp_service.py
Unified WhatsApp message handler and outbound sender.
"""

import asyncio
import os
import re
import uuid
import tempfile
from pathlib import Path
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

from config import GROQ_MODEL
from agent.agent import process_message
from agent.diagnose import (
    diagnose_image,
    SUPPORTED_CROPS,
    normalize_crop_text,
    DISEASE_DB,
)
from agent.guardrails import check_message, check_image, check_crisis
from services.location_state import _pending_location
from services.geocode_service import reverse_geocode, geocode_location
from services.i18n import get_string, get_salutation, TRILINGUAL_GREETING_MENU
from services.db import SessionLocal

from farmer_store import (
    get_or_create_farmer,
    get_farmer,
    normalize_phone,
    get_farmer_location,
    save_farmer_location,
    update_farmer_profile,
    set_farmer_language,
    set_onboarding_step,
    get_state,
    set_state,
    clear_state,
    add_chat,
    create_case,
    update_case,
)

from services.language_onboarding import handle_language_selection
from services.name_onboarding import handle_name_submission
from services.market_service import find_nearest_from_json, find_best_mandi_for_commodity

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)
TEMP_DIR  = tempfile.gettempdir()


def format_for_whatsapp(text: str) -> str:
    """
    Format message text cleanly for WhatsApp:
    - **bold** -> *bold*
    - # header -> *header*
    - markdown tables -> "• col1: col2" lines (dropping separator rows)
    - strip code fences (```)
    - collapse 3+ consecutive blank lines into 2
    """
    if not text:
        return ""

    s = text

    # 1. Strip code fences
    s = re.sub(r"```[a-zA-Z]*\n?", "", s)
    s = s.replace("```", "")

    # 2. Markdown tables -> bullet lines
    lines = s.split("\n")
    cleaned_lines = []
    in_table = False
    table_headers = []

    for line in lines:
        stripped = line.strip()
        # Check if table separator row: |---|---|
        if re.match(r"^\|?[\s\-:]+(\|[\s\-:]+)+\|?$", stripped):
            in_table = True
            continue
        # Check if table row: | a | b |
        if stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:-1]:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # Clean formatting in cells
            cells = [re.sub(r"\*\*([^*]+)\*\*", r"\1", c).strip("*") for c in cells]
            if not in_table and not table_headers:
                table_headers = cells
                in_table = True
                continue
            elif table_headers and len(cells) == len(table_headers):
                # Format as "• Market: Kolar | Modal Price: ₹860"
                items_str = ", ".join(f"{h}: {v}" for h, v in zip(table_headers, cells) if v)
                cleaned_lines.append(f"• {items_str}")
            else:
                cleaned_lines.append("• " + " | ".join(cells))
            continue
        else:
            in_table = False
            table_headers = []

        # 3. Headings: "# Header" or "## Header" -> "*Header*"
        line_clean = re.sub(r"^#{1,6}\s+(.*)$", r"*\1*", line)
        cleaned_lines.append(line_clean)

    s = "\n".join(cleaned_lines)

    # 4. Convert **bold** -> *bold*
    s = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", s)

    # 5. Collapse excessive blank lines
    s = re.sub(r"\n{3,}", "\n\n", s)

    return s.strip()


def parse_price_alert_intent(text: str) -> dict | None:
    """
    Extract crop, direction, and target price from price alert request.
    If market isn't given, defaults to None (treated as all nearby mandis).
    """
    if not text:
        return None
    s = text.strip().lower()

    alert_keywords = ["alert", "notify", "notification", "सूचना", "अलर्ट", "ತಿಳಿಸಿ", "ಎಚ್ಚರಿಕೆ"]
    if not any(k in s for k in alert_keywords):
        return None

    # Number for target price
    num_match = re.search(r"(?:rs\.?|₹|\b)?\s*([0-9]{2,6}(?:,[0-9]{3})*)\b", s)
    if not num_match:
        return None
    try:
        price_val = float(num_match.group(1).replace(",", ""))
    except Exception:
        return None

    # Direction
    direction = "above"
    if any(w in s for w in ["below", "under", "less", "नीचे", "कम", "ಕಡಿಮೆ"]):
        direction = "below"
    elif any(w in s for w in ["above", "more", "over", "ऊपर", "ज्यादा", "ಹೆಚ್ಚು"]):
        direction = "above"

    # Crop
    crop = None
    crop_aliases = {
        "onion": ["onion", "onions", "pyaj", "pyaaz", "प्याज", "ಈರುಳ್ಳಿ"],
        "tomato": ["tomato", "tomatoes", "tamatar", "टमाटर", "ಟೊಮೆಟೊ", "ಟೊಮೇಟೊ"],
        "potato": ["potato", "potatoes", "aloo", "आलू", "ಆಲೂಗಡ್ಡೆ", "ಆಲೂ"],
        "wheat": ["wheat", "gehun", "गेहूं", "ಗೋಧಿ"],
        "rice": ["rice", "paddy", "chawal", "चावल", "ಅಕ್ಕಿ", "ಭತ್ತ"],
        "chilli": ["chilli", "chili", "mirchi", "मिर्च", "ಮೆಣಸಿನಕಾಯಿ"],
        "garlic": ["garlic", "lahsun", "लहसुन", "ಬೆಳ್ಳುಳ್ಳಿ"],
    }
    for canon, aliases in crop_aliases.items():
        if any(a in s for a in aliases):
            crop = canon
            break

    if not crop:
        # Fallback to alphanumeric words
        for w in re.findall(r"[a-zA-Z]+", s):
            if w not in ("alert", "me", "when", "goes", "above", "below", "over", "under", "price", "is", "at", "to"):
                crop = w
                break

    if crop and price_val:
        return {
            "crop": crop,
            "target_price": price_val,
            "direction": direction,
            "market": None,
        }
    return None


def check_deterministic_reply(body: str, lang: str | None) -> str | None:
    """
    BUG 8: Fast deterministic handlers (no LLM, no tools) checked before the agent:
    - greetings / 'thanks' / 'ok' / 'bye' -> one short warm line.
    - 'help' / 'menu' -> short list of capabilities with examples.
    """
    clean = (body or "").strip().lower()
    clean_words = set(re.findall(r"[\w']+", clean))

    # 1. Greetings
    if clean in ("hi", "hello", "hey", "namaste", "namaskara", "namaskar", "start"):
        return get_string("quick_greeting", lang)

    # 2. Thanks / Gratitude
    if clean in ("thanks", "thank you", "dhanyavaad", "dhanyavada", "dhanyavadagalu", "shukriya") or \
       clean_words.issubset({"thanks", "thank", "you", "a", "lot", "very", "much"}):
        return get_string("quick_thanks", lang)

    # 3. Acknowledgment / OK
    if clean in ("ok", "okay", "accha", "theek hai", "sari", "ha", "haan", "ho"):
        return get_string("quick_ack", lang)

    # 4. Farewell / Bye
    if clean in ("bye", "goodbye", "alvida"):
        return get_string("quick_bye", lang)

    # 5. Help / Menu
    if clean in ("help", "menu", "madad", "sahayate", "commands"):
        return get_string("quick_help", lang)

    return None


def _split_message(text: str, max_len: int = 1500) -> list[str]:
    """Split message on paragraph boundaries without breaking mid-word."""
    text = (text or "").strip()
    if len(text) <= max_len:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for p in paragraphs:
        if not current_chunk:
            if len(p) <= max_len:
                current_chunk = p
            else:
                # Fallback to single line splitting
                lines = p.split("\n")
                for line in lines:
                    if len(current_chunk) + len(line) + 1 <= max_len:
                        current_chunk = f"{current_chunk}\n{line}" if current_chunk else line
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = line
        elif len(current_chunk) + len(p) + 2 <= max_len:
            current_chunk = f"{current_chunk}\n\n{p}"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = p

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


async def send_message(phone: str, text: str, retries: int = 3) -> bool:
    """
    Unified outbound reply path via Twilio REST.
    Applies format_for_whatsapp().
    Splits messages >1500 chars on paragraph boundaries with small delays.
    Retries with exponential backoff.
    """
    if not text or not text.strip():
        return False

    formatted_text = format_for_whatsapp(text)
    if not formatted_text:
        formatted_text = text.strip()

    clean_phone = normalize_phone(phone)

    # GUARD: Never call Twilio for a reserved test number
    from farmer_store import is_test_phone
    if is_test_phone(clean_phone):
        print(f"[WhatsApp] [TEST_GUARD] Simulated send to test phone {clean_phone}: {formatted_text[:80]}...")
        try:
            await asyncio.to_thread(add_chat, clean_phone, "assistant", formatted_text)
        except Exception as e:
            print(f"[WhatsApp] Failed to record outbound test chat: {e}")
        return True

    to_addr = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone
    from_addr = FROM_NUMBER if FROM_NUMBER.startswith("whatsapp:") else f"whatsapp:{FROM_NUMBER}"

    chunks = _split_message(formatted_text, max_len=1500)

    for chunk in chunks:
        sent = False
        for attempt in range(retries):
            try:
                await asyncio.to_thread(
                    twilio_client.messages.create,
                    from_=from_addr,
                    to=to_addr,
                    body=chunk,
                )
                sent = True
                break
            except Exception as e:
                wait_time = 0.5 * (2 ** attempt)
                print(f"[WhatsApp] Send error to {to_addr} (attempt {attempt + 1}): {e}")
                await asyncio.sleep(wait_time)

        if not sent:
            print(f"❌ [WhatsApp] Failed to send message to {to_addr} after {retries} retries.")
            return False

        if len(chunks) > 1:
            await asyncio.sleep(0.6)

    # Persist outbound bot message to chat history
    try:
        await asyncio.to_thread(add_chat, clean_phone, "assistant", formatted_text)
    except Exception as e:
        print(f"[WhatsApp] Failed to record outbound chat: {e}")

    return True


async def send_proactive_message(phone: str, message: str) -> bool:
    """Wrapper using the unified send_message path with BROADCAST_ALLOWLIST guard."""
    clean_phone = normalize_phone(phone)
    allowlist_raw = os.getenv("BROADCAST_ALLOWLIST")
    if allowlist_raw and allowlist_raw.strip():
        allowed_numbers = {
            normalize_phone(num.strip())
            for num in allowlist_raw.split(",")
            if num.strip()
        }
        if clean_phone not in allowed_numbers:
            print(f"[WhatsApp] [ALLOWLIST_SKIP] Phone {clean_phone} is not in BROADCAST_ALLOWLIST. Skipping proactive send.")
            return False

    return await send_message(clean_phone, message)


def _state_expired(updated_at, max_minutes: int = 30) -> bool:
    """True if conversation_state is older than max_minutes."""
    if not updated_at:
        return False
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return (now - updated_at).total_seconds() > max_minutes * 60


async def _handle_incoming_photo(phone: str, media_url: str, content_type: str, lang: str, farmer: dict) -> None:
    """Handle incoming plant leaf photo for diagnosis with crop gate."""
    if farmer.get("onboarding_step") != "done":
        await send_message(phone, get_string("photo_during_onboarding", lang))
        return

    img_check = check_image(content_type, lang)
    if not img_check.allowed:
        await send_message(phone, img_check.reply)
        return

    # Immediate acknowledgement
    await send_message(phone, get_string("diag_checking", lang))

    try:
        image_path = await _download_image(media_url, content_type)
    except Exception as e:
        print(f"[WhatsApp] Photo download error: {e}")
        await send_message(phone, get_string("diag_no_leaf", lang))
        return

    # Crop confirmation gate
    farmer_crops = farmer.get("crops") or []
    supported_matches = []
    for c in farmer_crops:
        norm = normalize_crop_text(str(c))
        if norm and norm in SUPPORTED_CROPS:
            supported_matches.append(norm)

    if len(supported_matches) == 1:
        suggested = supported_matches[0]
        ask_msg = get_string("diag_ask_crop_single", lang, crop=suggested.title())
        await asyncio.to_thread(
            set_state,
            phone,
            flow="disease_crop",
            step="confirm_single",
            data={
                "image_path": image_path,
                "suggested_crop": suggested,
                "single_crop": True,
            },
        )
        await send_message(phone, ask_msg)
    else:
        ask_msg = get_string("diag_ask_crop_multi", lang)
        await asyncio.to_thread(
            set_state,
            phone,
            flow="disease_crop",
            step="ask_which",
            data={
                "image_path": image_path,
                "single_crop": False,
            },
        )
        await send_message(phone, ask_msg)


async def _handle_disease_crop_reply(phone: str, body: str, lang: str, farmer: dict, state: dict) -> bool:
    """
    Handle response to crop confirmation. If message is unrelated, answer via agent and keep flow.
    """
    data = state.get("data") or {}
    image_path = data.get("image_path")
    step = state.get("step")

    quick_reply = check_deterministic_reply(body, lang)
    if quick_reply:
        await send_message(phone, quick_reply)
        return True

    affirmatives = {
        "yes", "y", "yeah", "yep", "sure", "ok", "okay",
        "haan", "ha", "bilkul", "sahi", "houdu", "haudu", "sari",
        "ಹೌದು", "ಹಾ", "ಸರಿ", "हाँ", "हाँ सेट करें", "सेट करो"
    }
    negatives = {
        "no", "n", "nope", "nahi", "illa", "bedi", "ಇಲ್ಲ", "ಬೇಡ", "नहीं", "मत करो"
    }

    clean_body = body.strip().lower()
    confirmed_crop = None

    if step == "confirm_single":
        if clean_body in affirmatives or any(clean_body == a for a in affirmatives):
            confirmed_crop = data.get("suggested_crop")
        elif clean_body in negatives or any(clean_body == n for n in negatives):
            data["single_crop"] = False
            await asyncio.to_thread(set_state, phone, flow="disease_crop", step="ask_which", data=data)
            await send_message(phone, get_string("diag_ask_crop_multi", lang))
            return True
        else:
            norm = normalize_crop_text(body)
            if norm:
                confirmed_crop = norm
            elif any(w in clean_body for w in ["other", "अन्य", "ಇತರ", "ಬೇರೆ"]):
                confirmed_crop = "other"
            else:
                reply = await process_message(farmer_id=phone, message=body)
                await send_message(phone, reply)
                return True
    else:  # ask_which
        norm = normalize_crop_text(body)
        if norm:
            confirmed_crop = norm
        elif any(w in clean_body for w in ["other", "अन्य", "ಇತರ", "ಬೇರೆ"]):
            confirmed_crop = "other"
        else:
            reply = await process_message(farmer_id=phone, message=body)
            await send_message(phone, reply)
            return True

    if not image_path or not os.path.exists(image_path):
        await asyncio.to_thread(clear_state, phone)
        await send_message(phone, get_string("diag_no_leaf", lang))
        return True

    if confirmed_crop == "other" or confirmed_crop not in SUPPORTED_CROPS:
        await asyncio.to_thread(clear_state, phone)
        try:
            os.remove(image_path)
        except Exception:
            pass
        await send_message(phone, get_string("diag_unsupported_crop", lang))
        return True

    # Run diagnosis with CROP FILTER
    from agent.tools import active_farmer_phone
    token = active_farmer_phone.set(phone)
    try:
        diag_res = await asyncio.to_thread(
            diagnose_image,
            image_path=image_path,
            confirmed_crop=confirmed_crop,
            phone=phone,
        )
    finally:
        active_farmer_phone.reset(token)
        try:
            os.remove(image_path)
        except Exception:
            pass

    status = diag_res.get("status")

    if status == "no_leaf":
        await asyncio.to_thread(clear_state, phone)
        await send_message(phone, get_string("diag_no_leaf", lang))
        return True
    elif status == "wrong_crop":
        await asyncio.to_thread(clear_state, phone)
        await send_message(phone, get_string("diag_wrong_crop", lang, crop=confirmed_crop.title()))
        return True
    elif status == "low_confidence":
        await asyncio.to_thread(clear_state, phone)
        await send_message(phone, get_string("diag_low_confidence", lang))
        return True
    elif status == "healthy":
        await asyncio.to_thread(clear_state, phone)
        await send_message(phone, get_string("diag_healthy", lang, crop=confirmed_crop.title()))
        return True
    elif status == "no_disease_model":
        await asyncio.to_thread(clear_state, phone)
        await send_message(phone, get_string("diag_no_disease_model", lang, crop=confirmed_crop.title()))
        return True
    elif status == "ok":
        from datetime import datetime, time, timedelta, timezone
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist)
        next_followup = datetime.combine(now_ist.date() + timedelta(days=1), time(9, 0), tzinfo=ist)

        display_name = diag_res.get("display_name", diag_res.get("disease", ""))
        conf_num = diag_res.get("confidence_num", 0.0)
        conf_pct = diag_res.get("confidence", "0%")
        db_key = diag_res.get("db_key", "")
        db_entry = diag_res.get("db_entry", {})
        spread_modes = diag_res.get("spread_modes", [])

        case_id = await asyncio.to_thread(
            create_case,
            phone=phone,
            crop=confirmed_crop,
            disease=display_name,
            confidence=conf_num,
            severity_level="Unknown",
            severity_score=0,
            severity_source="unknown",
            lat=farmer.get("lat"),
            lng=farmer.get("lng"),
            spread_modes=spread_modes,
            next_followup_at=next_followup,
        )

        try:
            from outbreak.service import schedule_outbreak_evaluation
            schedule_outbreak_evaluation(case_id)
        except (ImportError, AttributeError, Exception) as e:
            pass

        org_rems = db_entry.get("remedies", {}).get("organic", [])
        first_step = org_rems[0] if org_rems else (
            "प्रभावित पत्ते हटाएँ" if lang == "hindi" else
            "ಬಾಧಿತ ಎಲೆಗಳನ್ನು ತೆಗೆದುಹಾಕಿ" if lang == "kannada" else
            "Remove and destroy affected leaves immediately"
        )
        low_conf_note = get_string("diag_ok_low_conf_note", lang) if conf_num < 0.70 else ""

        total_leaves = diag_res.get("total_leaves", 1)
        diseased_leaves = diag_res.get("diseased_leaves", 1)

        if total_leaves > 1:
            msg = get_string(
                "diag_ok_multi",
                lang,
                total=total_leaves,
                diseased=diseased_leaves,
                disease=display_name,
                confidence=conf_pct,
                low_conf_note=low_conf_note,
                first_step=first_step,
            )
        else:
            msg = get_string(
                "diag_ok_single",
                lang,
                crop=confirmed_crop.title(),
                disease=display_name,
                confidence=conf_pct,
                low_conf_note=low_conf_note,
                first_step=first_step,
            )

        await asyncio.to_thread(
            set_state,
            phone,
            flow="disease_severity",
            step="ask_severity",
            data={
                "case_id": str(case_id),
                "crop": confirmed_crop,
                "db_key": db_key,
                "display_name": display_name,
            },
        )
        await send_message(phone, msg)
        return True

    return False


async def _handle_disease_severity_reply(phone: str, body: str, lang: str, farmer: dict, state: dict) -> bool:
    """
    Handle severity answer: save farmer_reported severity and send treatment plan.
    """
    data = state.get("data") or {}
    case_id = data.get("case_id")
    db_key = data.get("db_key")
    crop = data.get("crop", "")
    display_name = data.get("display_name", "")

    quick_reply = check_deterministic_reply(body, lang)
    if quick_reply:
        await send_message(phone, quick_reply)
        return True

    sb = body.strip().lower()
    parsed_level = None
    if any(k in sb for k in ["few", "1", "kuch", "kelavu", "mild", "कम", "कुछ", "ಕೆಲವು"]):
        parsed_level = "Mild"
    elif any(k in sb for k in ["most", "3", "zyada", "zyadatar", "bahut", "bahutek", "severe", "ज़्यादा", "ಬಹುತೇಕ", "ತೀವ್ರ"]):
        parsed_level = "Severe"
    elif any(k in sb for k in ["many", "2", "kafi", "sakashthu", "moderate", "काफ़ी", "ಸಾಕಷ್ಟು", "ಮಧ್ಯಮ"]):
        parsed_level = "Moderate"

    if not parsed_level:
        reply = await process_message(farmer_id=phone, message=body)
        await send_message(phone, reply)
        return True

    await asyncio.to_thread(
        update_case,
        case_id,
        severity_level=parsed_level,
        severity_source="farmer_reported",
    )
    try:
        from outbreak.service import schedule_outbreak_evaluation
        schedule_outbreak_evaluation(case_id)
    except Exception as e:
        print(f"[WhatsApp] Failed to schedule outbreak evaluation after severity reply: {e}")
    await asyncio.to_thread(clear_state, phone)

    db_entry = DISEASE_DB.get(db_key, {})
    remedies = db_entry.get("remedies", {})
    org_list = remedies.get("organic", [])
    chem_list = remedies.get("chemical", [])

    org_text = "\n• ".join([""] + org_list).strip() if org_list else "None specified"
    chem_text = "\n• ".join([""] + chem_list).strip() if chem_list else "None specified"
    dose_note = get_string("diag_dose_review_note", lang)

    

    prog_vals = {
        "Mild": ("10%", "15%"),
        "Moderate": ("30%", "50%"),
        "Severe": ("60%", "85%"),
    }.get(parsed_level, ("30%", "50%"))

    severe_note = get_string("diag_treatment_severe_note", lang) if parsed_level == "Severe" else ""

    treatment_msg = get_string(
        "diag_treatment",
        lang,
        crop=crop.title(),
        disease=display_name,
        organic=org_text,
        chemical=chem_text,
        dose_note=dose_note,
        day3=prog_vals[0],
        day7=prog_vals[1],
        severe_note=severe_note,
    )

    ack_msg = get_string("diag_severity_saved", lang)
    await send_message(phone, f"{ack_msg}\n\n{treatment_msg}")

    # Where to buy online (search links), sent as a separate short message
    try:
        from services.buy_links import products_from_remedies, format_buy_message
        products = products_from_remedies(remedies)
        if products:
            await send_message(
                phone,
                format_buy_message(
                    products,
                    get_string("buy_header", lang),
                    get_string("buy_note", lang),
                ),
            )
    except Exception as e:
        print(f"[WhatsApp] Buy-links failed (non-fatal): {e}")
    return True


async def handle_incoming_message(form_data: dict) -> None:
    """
    Main background worker for all incoming messages.
    Does not return TwiML XML bodies — all replies dispatch via send_message.
    """
    phone = form_data.get("From", "").replace("whatsapp:", "").strip()
    body = (form_data.get("Body") or "").strip()
    num_media = int(form_data.get("NumMedia", 0))
    media_url = form_data.get("MediaUrl0")
    content_type = form_data.get("MediaContentType0")
    latitude = form_data.get("Latitude")
    longitude = form_data.get("Longitude")
    profile_name = form_data.get("ProfileName")

    # Record incoming chat
    if body:
        try:
            await asyncio.to_thread(add_chat, phone, "user", body)
        except Exception:
            pass

    # ── 1. SAFETY FIRST: Crisis Check at top of router ─────────────────────────
    crisis_res = check_crisis(body)
    if crisis_res:
        farmer = await asyncio.to_thread(get_farmer, phone)
        lang = farmer.get("language")
        # Localized helpline reply
        if lang:
            crisis_res = check_crisis(body, lang)
        await send_message(phone, crisis_res.reply)
        return

    # ── 2. Farmer resolution & timestamp ──────────────────────────────────────
    farmer = await asyncio.to_thread(get_or_create_farmer, phone)
    # Treat legacy 'Kisan bhai' as unset name
    farmer_name = farmer.get("name")
    if farmer_name and farmer_name.strip().lower() == "kisan bhai":
        farmer_name = None

    onboarding_step = farmer.get("onboarding_step") or "new"
    lang = farmer.get("language")

    # ── 3. ONBOARDING STATE MACHINE (if onboarding_step != 'done') ─────────────
    if onboarding_step != "done":
        # If photo sent before completing onboarding
        if num_media > 0:
            notice = get_string("photo_during_onboarding", lang or "english")
            # Also re-prompt current onboarding question
            if onboarding_step in ("new", "ask_language"):
                notice = f"{notice}\n\n{TRILINGUAL_GREETING_MENU}"
            elif onboarding_step == "ask_name":
                notice = f"{notice}\n\n{get_string('ask_name', lang)}"
            elif onboarding_step == "ask_location":
                sal = get_salutation(farmer_name, lang)
                notice = f"{notice}\n\n{get_string('name_saved_ask_location', lang, salutation=sal)}"
            await send_message(phone, notice)
            return

        # Step 1: Language selection (or ANY initial message)
        if onboarding_step in ("new", "ask_language"):
            reply, advanced = handle_language_selection(phone, body, profile_name)
            await send_message(phone, reply)
            return

        # Step 2: Name submission
        if onboarding_step == "ask_name":
            reply, advanced = handle_name_submission(phone, body, lang)
            await send_message(phone, reply)
            return

        # Step 3: Location submission
        if onboarding_step == "ask_location":
            sal = get_salutation(farmer_name, lang)
            # A. Shared location pin
            if latitude and longitude:
                lat = float(latitude)
                lng = float(longitude)
                await asyncio.to_thread(save_farmer_location, phone, lat, lng)
                geo = await asyncio.to_thread(reverse_geocode, lat, lng)
                district = geo.get("district")
                state = geo.get("state")
                disp = geo.get("display_name") or f"{lat:.2f}, {lng:.2f}"
                await asyncio.to_thread(
                    update_farmer_profile,
                    phone,
                    location=disp,
                    district=district,
                    state=state,
                    onboarding_step="done",
                )
                confirm_txt = get_string("location_confirm_geocoded", lang, salutation=sal, place=disp)
                welcome_txt = get_string("welcome_capabilities", lang, salutation=sal)
                await send_message(phone, f"{confirm_txt}\n\n{welcome_txt}")
                return

            # B. Typed 'skip'
            if body.lower() in ("skip", "chhod do", "biddubidi", "illa", "nahi"):
                await asyncio.to_thread(set_onboarding_step, phone, "done")
                skip_txt = get_string("location_skip", lang, salutation=sal)
                welcome_txt = get_string("welcome_capabilities", lang, salutation=sal)
                await send_message(phone, f"{skip_txt}\n\n{welcome_txt}")
                return

            # C. Typed place name
            geo = await asyncio.to_thread(geocode_location, body)
            if geo and geo.get("lat"):
                lat = geo["lat"]
                lng = geo["lng"]
                disp = geo.get("display_name", body)
                await asyncio.to_thread(save_farmer_location, phone, lat, lng)
                await asyncio.to_thread(
                    update_farmer_profile,
                    phone,
                    location=disp,
                    district=geo.get("district"),
                    state=geo.get("state"),
                    onboarding_step="done",
                )
                confirm_txt = get_string("location_confirm_geocoded", lang, salutation=sal, place=disp)
                welcome_txt = get_string("welcome_capabilities", lang, salutation=sal)
                await send_message(phone, f"{confirm_txt}\n\n{welcome_txt}")
                return
            else:
                # Re-ask gently
                reask = get_string("name_saved_ask_location", lang, salutation=sal)
                await send_message(phone, reask)
                return

    # ── 4. LOCATION SHARE POST-ONBOARDING ──────────────────────────────────────
    if latitude and longitude:
        lat = float(latitude)
        lng = float(longitude)
        await asyncio.to_thread(save_farmer_location, phone, lat, lng)
        geo = await asyncio.to_thread(reverse_geocode, lat, lng)
        disp = geo.get("display_name") or f"{lat:.2f}, {lng:.2f}"
        await asyncio.to_thread(
            update_farmer_profile,
            phone,
            location=disp,
            district=geo.get("district"),
            state=geo.get("state"),
        )

        # Check if an active flow was waiting for location
        state_entry = await asyncio.to_thread(get_state, phone)
        if state_entry and state_entry.get("flow") == "mandi" and state_entry.get("step") == "ask_location":
            context = state_entry.get("data") or {}
            await asyncio.to_thread(clear_state, phone)
            commodity = context.get("commodity")
            state_filter = context.get("state_filter")
            reply = await handle_location_for_mandi(
                phone=phone,
                lat=lat,
                lng=lng,
                commodity=commodity,
                state_filter=state_filter,
            )
            await send_message(phone, reply)
            return

        # Warm confirmation
        sal = get_salutation(farmer_name, lang)
        confirm_loc = get_string("location_updated", lang, place=disp)
        await send_message(phone, confirm_loc)
        return

    # ── 4B. ACTIVE CONVERSATION FLOWS (Disease Crop / Severity / Price Alert) ──
    if not (num_media > 0 and media_url) and body:
        pending_state = await asyncio.to_thread(get_state, phone)
        if pending_state:
            # 30-minute timeout for mid-flow state
            if _state_expired(pending_state.get("updated_at"), max_minutes=30):
                await asyncio.to_thread(clear_state, phone)
            else:
                flow = pending_state.get("flow")
                if flow == "disease_crop":
                    handled = await _handle_disease_crop_reply(phone, body, lang, farmer, pending_state)
                    if handled:
                        return
                elif flow == "disease_severity":
                    handled = await _handle_disease_severity_reply(phone, body, lang, farmer, pending_state)
                    if handled:
                        return
                elif flow == "price_alert_confirm":
                    data = pending_state.get("data") or {}
                    clean_body = body.strip().lower()
                    affirmatives = {
                        "yes", "y", "yeah", "yep", "sure", "ok", "okay",
                        "haan", "ha", "bilkul", "sahi", "houdu", "haudu", "sari",
                        "ಹೌದು", "ಹಾ", "ಸರಿ", "हाँ", "हाँ सेट करें", "सेट करो"
                    }
                    negatives = {
                        "no", "n", "nope", "nahi", "illa", "bedi", "ಇಲ್ಲ", "ಬೇಡ", "नहीं", "मत करो"
                    }

                    if clean_body in affirmatives or any(clean_body == a for a in affirmatives):
                        await asyncio.to_thread(clear_state, phone)
                        crop = data.get("crop", "crop")
                        target_price = float(data.get("target_price", 0))
                        direction = data.get("direction", "above")
                        market = data.get("market")

                        from agent.tools import create_price_alert, active_farmer_phone
                        token = active_farmer_phone.set(phone)
                        try:
                            tool_res = await asyncio.to_thread(
                                create_price_alert.invoke,
                                {
                                    "crop": crop,
                                    "target_price": target_price,
                                    "direction": direction,
                                    "market": market,
                                },
                            )
                        finally:
                            active_farmer_phone.reset(token)

                        if isinstance(tool_res, dict) and tool_res.get("status") == "created":
                            dir_key = "price_direction_above" if direction == "above" else "price_direction_below"
                            direction_word = get_string(dir_key, lang)
                            success_msg = get_string(
                                "alert_created_success",
                                lang,
                                crop=crop.title(),
                                price=int(target_price),
                                direction=direction_word,
                            )
                            await send_message(phone, success_msg)
                            return
                        else:
                            err_msg = (tool_res.get("message") if isinstance(tool_res, dict) else None) or "Unable to set alert at this time."
                            await send_message(phone, f"Could not set alert: {err_msg}")
                            return

                    elif clean_body in negatives or any(clean_body == n for n in negatives):
                        await asyncio.to_thread(clear_state, phone)
                        cancel_msg = get_string("alert_cancelled", lang)
                        await send_message(phone, cancel_msg)
                        return
                    else:
                        await asyncio.to_thread(clear_state, phone)

        # B. Price alert intent detection
        alert_intent = parse_price_alert_intent(body)
        if alert_intent:
            await asyncio.to_thread(
                set_state,
                phone,
                flow="price_alert_confirm",
                step="ask_confirm",
                data=alert_intent,
            )
            dir_key = "price_direction_above" if alert_intent["direction"] == "above" else "price_direction_below"
            direction_word = get_string(dir_key, lang)
            ask_msg = get_string(
                "alert_confirm_ask",
                lang,
                crop=alert_intent["crop"].title(),
                price=int(alert_intent["target_price"]),
                direction=direction_word,
            )
            await send_message(phone, ask_msg)
            return

        # C. Fast deterministic handlers (greetings / thanks / ok / bye / help / menu)
        quick_reply = check_deterministic_reply(body, lang)
        if quick_reply:
            await send_message(phone, quick_reply)
            return

    # ── 5. IMAGE MESSAGE (Disease Diagnosis Flow) ──────────────────────────────
    if num_media > 0 and media_url:
        await _handle_incoming_photo(phone, media_url, content_type, lang, farmer)
        return

    # ── 6. GUARDRAIL CHECK ─────────────────────────────────────────────────────
    msg_check = check_message(body, lang)
    if not msg_check.allowed:
        await send_message(phone, msg_check.reply)
        return

    # ── 7. AGENT REASONING ─────────────────────────────────────────────────────
    reply = await process_message(
        farmer_id=phone,
        message=body or "Hello",
    )
    await send_message(phone, reply)


async def handle_location_for_mandi(
    phone: str,
    lat: float,
    lng: float,
    commodity: str | None,
    state_filter: str | None = None,
) -> str:
    """Mandi price resolver based on farmer location coordinates."""
    if not commodity:
        nearest = find_nearest_from_json(lat, lng, top_n=5, state=state_filter)
        if not nearest:
            st = f" *{state_filter}* mein" if state_filter else ""
            return f"500km ke andar koi mandi nahi mili{st}."

        reply = "*Aapke sabse nazdeek mandis:*\n\n"
        for m in nearest:
            reply += f"• *{m['market']}*, {m['district']} ({m['state']}) — {m['distance_km']} km\n"
        reply += "\nKisi fasal ka bhav janne ke liye fasal ka naam likhein (jaise 'Tamatar ka bhav')."
        return reply

    with SessionLocal() as db:
        results = find_best_mandi_for_commodity(
            farmer_lat=lat,
            farmer_lng=lng,
            commodity=commodity,
            radius_km=500,
            top_n=3,
            state=state_filter,
            db=db,
        )

    if not results:
        st = f" *{state_filter}* mein" if state_filter else ""
        return (
            f"*{commodity.title()}* ke liye{st} 500km mein koi mandi nahi mili.\n"
            f"Doosre state ke liye message mein state ka naam likhein, phir location bhejein."
        )

    best = results[0]
    reply = (
        f"*{commodity.title()} ke liye sabse acchi mandi:*\n\n"
        f"*{best['market']}*, {best['district']}, {best['state']}\n"
        f"Modal Rate : Rs.{best['modal_price']}/quintal\n"
        f"Doori      : {best['distance_km']} km\n"
        f"Transport  : Rs.{best['transport_cost']}\n"
        f"*Net Price : Rs.{best['net_price']}/quintal* ✅\n"
    )
    if len(results) > 1:
        reply += "\n*Doosre options:*\n"
        for m in results[1:]:
            reply += f"  • {m['market']} — Rs.{m['net_price']}/q ({m['distance_km']}km)\n"

    return reply

async def _download_image(media_url: str, content_type: str) -> str:
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg":  ".jpg",
        "image/png":  ".png",
        "image/webp": ".webp",
    }
    ext = ext_map.get(content_type, ".jpg")
    filepath = os.path.join(TEMP_DIR, f"kisan_{uuid.uuid4().hex}{ext}")

    if os.path.exists(media_url):
        import shutil
        await asyncio.to_thread(shutil.copyfile, media_url, filepath)
        return filepath

    from services.twilio_media_download import download_twilio_media_sync

    data = await asyncio.to_thread(download_twilio_media_sync, media_url)
    with open(filepath, "wb") as f:
        f.write(data)

    print(f"[WhatsApp] Image saved to {filepath}")
    return filepath