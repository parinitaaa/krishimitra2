# services/language_onboarding.py
"""
First-contact language selection for WhatsApp.
Driven by farmer onboarding_step, accepting 1/2/3 or language names in any script.
"""

from __future__ import annotations
import re

from farmer_store import (
    normalize_phone,
    set_farmer_language,
    set_onboarding_step,
    update_farmer_profile,
)
from services.i18n import (
    TRILINGUAL_GREETING_MENU,
    get_string,
    get_salutation,
)


def parse_language_choice(text: str) -> str | None:
    t = (text or "").strip().lower()
    if not t:
        return None

    # Number mapping
    digit_only = "".join(c for c in t if c.isdigit())
    if len(digit_only) == 1 and digit_only in "123":
        return {"1": "hindi", "2": "kannada", "3": "english"}[digit_only]

    # Name mapping in multiple scripts
    if "hindi" in t or "हिंदी" in t or "हिन्दी" in t:
        return "hindi"
    if "kannada" in t or "ಕನ್ನಡ" in t or "kanada" in t:
        return "kannada"
    if "english" in t or "इंग्लिश" in t or "ಇಂಗ್ಲಿಷ್" in t or "angrezi" in t or "eng" in t:
        return "english"

    return None


def handle_language_selection(phone: str, body: str, profile_name: str | None = None) -> tuple[str, bool]:
    """
    Handles language selection step.
    Returns (reply_message, advanced_to_next_step).
    """
    pid = normalize_phone(phone)
    lang_choice = parse_language_choice(body)

    if lang_choice:
        set_farmer_language(pid, lang_choice)
        set_onboarding_step(pid, "ask_name")

        confirm_msg = get_string("lang_confirm", lang_choice)
        if profile_name and profile_name.strip():
            # Offer profile name
            name_msg = get_string("name_offer_profile", lang_choice, profile_name=profile_name.strip())
        else:
            name_msg = get_string("ask_name", lang_choice)

        reply = f"{confirm_msg}\n\n{name_msg}"
        return reply, True

    # If message is not recognized as a language choice, return the trilingual menu
    return TRILINGUAL_GREETING_MENU, False