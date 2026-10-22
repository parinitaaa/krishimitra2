# agent/guardrails.py
"""
Guardrails for incoming WhatsApp messages and media.
Provides native-script replies via services/i18n.py without gendered address ("bhai").
"""

import re
from dataclasses import dataclass
from services.i18n import get_string, CRISIS_HELPLINES, TRILINGUAL_CRISIS


@dataclass
class GuardrailResult:
    allowed: bool
    reply: str = ""
    warning: str = ""
    is_crisis: bool = False


BLOCKED_PATTERNS = [
    (r"\b(suicide|khud ko maarna|zindagi khatam|mar jaana|mar jaunga|mar jau|zeher|pesticide peena|zeher peena|zeher khaana)\b", "mental_health"),
    (r"\b(end my life|kill myself|want to die|kill me)\b", "mental_health"),
    (r"\b(ಆತ್ಮಹತ್ಯೆ|ಸಾಯಬೇಕು|ಜೀವ ಕಳೆದುಕೊಳ್ಳಲು|ವಿಷ ಕುಡಿಯುವುದು)\b", "mental_health"),
]

OUT_OF_SCOPE = [
    "cricket",
    "ipl",
    "bollywood",
    "movie",
    "film",
    "cinema",
    "politics",
    "election",
    "vote",
    "share market",
    "sensex",
    "nifty",
    "stock",
    "crypto",
    "bitcoin",
]

FARMING_KEYWORDS = [
    "crop", "plant", "leaf", "soil", "disease", "spray", "mandi",
    "price", "rain", "fertilizer", "pest", "harvest", "seed", "farm",
    "field", "khet", "irrigation", "yield", "sowing",
    "fasal", "paudha", "patta", "mitti", "bimari", "khad", "kida",
    "katai", "beej", "bhav", "barish", "gehu", "chawal", "pyaz",
    "tamatar", "aloo", "kapas", "ganna", "arhar", "moong", "bajra",
    "tomato", "onion", "wheat", "rice", "potato", "cotton",
    "sugarcane", "maize", "soybean", "mustard", "groundnut",
    "brinjal", "cabbage", "cauliflower", "chilli", "garlic", "ginger",
    # Kannada agricultural keywords
    "ಬೆಳೆ", "ಎಲೆ", "ರೋಗ", "ಮಾರುಕಟ್ಟೆ", "ಬೆಲೆ", "ಮಳೆ", "ಗೊಬ್ಬರ", "ಕೀಟ", "ಬೀಜ",
]


def check_crisis(message: str, lang: str | None = None) -> GuardrailResult | None:
    """Run crisis check. If matched, returns GuardrailResult with compassionate helpline reply."""
    msg_lower = (message or "").strip().lower()
    if not msg_lower:
        return None

    for pattern, category in BLOCKED_PATTERNS:
        if re.search(pattern, msg_lower, re.UNICODE):
            if lang and lang.lower() in CRISIS_HELPLINES:
                reply = CRISIS_HELPLINES[lang.lower()]
            else:
                reply = TRILINGUAL_CRISIS
            return GuardrailResult(
                allowed=False,
                reply=reply,
                warning=f"BLOCKED: {category}",
                is_crisis=True,
            )
    return None


def check_message(message: str, lang: str | None = None) -> GuardrailResult:
    msg_lower = (message or "").strip().lower()

    # 1. Crisis check first
    crisis_res = check_crisis(message, lang)
    if crisis_res:
        return crisis_res

    # 2. Farming keywords pass immediately
    if any(kw in msg_lower for kw in FARMING_KEYWORDS):
        return GuardrailResult(allowed=True)

    # 3. Out-of-scope check
    for kw in OUT_OF_SCOPE:
        if kw in msg_lower:
            reply = get_string("out_of_scope", lang or "english")
            return GuardrailResult(
                allowed=False,
                reply=reply,
                warning=f"OUT_OF_SCOPE: {kw}",
                is_crisis=False,
            )

    return GuardrailResult(allowed=True)


def check_image(content_type: str, lang: str | None = None) -> GuardrailResult:
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if content_type and content_type.lower() in allowed:
        return GuardrailResult(allowed=True)

    reply = get_string("unsupported_media", lang or "english")
    return GuardrailResult(
        allowed=False,
        reply=reply,
        warning=f"UNSUPPORTED_MEDIA: {content_type}",
        is_crisis=False,
    )
