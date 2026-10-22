# services/name_onboarding.py
"""
Name collection for WhatsApp onboarding state machine.
Driven by farmer onboarding_step == 'ask_name'.
"""

from __future__ import annotations
import re

from farmer_store import (
    normalize_phone,
    update_farmer_profile,
    set_onboarding_step,
    get_farmer,
)
from services.i18n import get_string, get_salutation

_NAME_TOO_LONG = 80

GREETING_WORDS = frozenset({
    "hi", "hello", "hey", "namaste", "namaskar", "hlo", "hii", "helo",
    "ನಮಸ್ಕಾರ", "नमस्ते", "good morning", "good evening",
})


def handle_name_submission(phone: str, body: str, lang: str | None = "english") -> tuple[str, bool]:
    """
    Validates and stores the farmer's name.
    Advances onboarding_step to 'ask_location'.
    Returns (reply_message, advanced).
    """
    pid = normalize_phone(phone)
    raw = (body or "").strip()

    if not raw:
        return get_string("ask_name", lang), False

    if raw.lower() in GREETING_WORDS:
        return get_string("ask_name", lang), False

    if len(raw) > _NAME_TOO_LONG:
        return get_string("invalid_name", lang), False

    # Must contain at least one letter across Latin, Devanagari, or Kannada scripts
    if not re.search(r"[a-zA-Z\u0900-\u0FFF\u0C80-\u0CFF]", raw, re.UNICODE):
        return get_string("invalid_name", lang), False

    # Check if user accepted profile name prompt ("yes", "haan", "ha", "yes please", "ಹೌದು")
    accept_words = {"yes", "haan", "ha", "y", "sahi hai", "theek hai", "ಹೌದು", "ಸರಿ", "ok"}
    clean_name = raw
    if raw.lower() in accept_words:
        # Check if there is an existing name in profile or we keep asking
        f = get_farmer(pid)
        if f.get("name"):
            clean_name = f["name"]

    clean = re.sub(r"\s+", " ", clean_name).strip()
    update_farmer_profile(pid, name=clean)
    set_onboarding_step(pid, "ask_location")

    salutation = get_salutation(clean, lang)
    reply = get_string("name_saved_ask_location", lang, salutation=salutation)
    return reply, True
