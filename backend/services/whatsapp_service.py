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
from agent.diagnose import diagnose_image
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
    record_detection_if_outbreak,
    save_farmer_diagnosis,
    update_farmer_profile,
    set_farmer_language,
    set_onboarding_step,
    get_state,
    clear_state,
    add_chat,
)

from services.language_onboarding import handle_language_selection
from services.name_onboarding import handle_name_submission
from services.market_service import find_nearest_from_json, find_best_mandi_for_commodity

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)
TEMP_DIR  = tempfile.gettempdir()

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
_MODEL_DIR = AGENT_DIR / "model"
if not (_MODEL_DIR / "classifier.onnx").exists():
    _MODEL_DIR = AGENT_DIR / "models"
CLASSIFIER_PATH = str(_MODEL_DIR / "classifier.onnx")
DETECTOR_PATH   = str(_MODEL_DIR / "detector.onnx")


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
    Splits messages >1500 chars on paragraph boundaries with small delays.
    Retries with exponential backoff.
    """
    if not text or not text.strip():
        return False

    clean_phone = normalize_phone(phone)
    to_addr = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone
    from_addr = FROM_NUMBER if FROM_NUMBER.startswith("whatsapp:") else f"whatsapp:{FROM_NUMBER}"

    chunks = _split_message(text, max_len=1500)

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
        await asyncio.to_thread(add_chat, clean_phone, "assistant", text)
    except Exception as e:
        print(f"[WhatsApp] Failed to record outbound chat: {e}")

    return True


async def send_proactive_message(phone: str, message: str) -> bool:
    """Wrapper using the unified send_message path."""
    return await send_message(phone, message)


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

    # ── 5. IMAGE MESSAGE (Disease Flow) ────────────────────────────────────────
    image_path = None
    if num_media > 0 and media_url:
        img_check = check_image(content_type, lang)
        if not img_check.allowed:
            await send_message(phone, img_check.reply)
            return
        try:
            image_path = await _download_image(media_url, content_type)
        except Exception as e:
            print(f"[WhatsApp] Image download failed: {e}")

    # ── 6. GUARDRAIL CHECK ─────────────────────────────────────────────────────
    msg_check = check_message(body, lang)
    if not msg_check.allowed:
        await send_message(phone, msg_check.reply)
        return

    # ── 7. DISEASE DIAGNOSIS OR AGENT REASONING ────────────────────────────────
    disease_result = None
    if image_path and os.path.exists(CLASSIFIER_PATH):
        disease_result = await asyncio.to_thread(
            diagnose_image,
            image_path=image_path,
            classifier_path=CLASSIFIER_PATH,
            detector_path=DETECTOR_PATH if os.path.exists(DETECTOR_PATH) else None,
        )
    elif image_path:
        print(f"[WhatsApp] Missing classifier at {CLASSIFIER_PATH}")

    if disease_result:
        await asyncio.to_thread(save_farmer_diagnosis, phone, disease_result, body)
        await asyncio.to_thread(record_detection_if_outbreak, phone, disease_result)

    # Note: extract_farmer_data is completely removed to prevent LLM touching identity.

    reply = await process_message(
        farmer_id=phone,
        message=body or "Hello",
        disease_result=disease_result,
    )

    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception:
            pass

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
            state_filter=state_filter,
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
    from services.twilio_media_download import download_twilio_media_sync

    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg":  ".jpg",
        "image/png":  ".png",
        "image/webp": ".webp",
    }
    ext = ext_map.get(content_type, ".jpg")
    filepath = os.path.join(TEMP_DIR, f"kisan_{uuid.uuid4().hex}{ext}")

    data = await asyncio.to_thread(download_twilio_media_sync, media_url)
    with open(filepath, "wb") as f:
        f.write(data)

    print(f"[WhatsApp] Image saved to {filepath}")
    return filepath