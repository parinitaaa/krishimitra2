# services/i18n.py
"""
Internationalization for KrishiMitra.
Provides native-script strings for Hindi (Devanagari), Kannada (Kannada script), and English.
No gendered address; addresses farmers with "{name} ji" (Hindi), "{name} ಅವರೇ" (Kannada), or "{name}" (English).
"""

# Crisis message (Tele-MANAS & Kisan Call Centre)
CRISIS_HELPLINES = {
    "hindi": (
        "आप अकेले नहीं हैं। यदि आप किसी कठिन समय या मानसिक तनाव से गुज़र रहे हैं, "
        "तो कृपया भारत सरकार की निःशुल्क हेल्पलाइन पर संपर्क करें:\n\n"
        "📞 टेली-मानस (Tele-MANAS): 14416 या 1800-891-4416 (24x7 निःशुल्क)\n"
        "🌾 किसान कॉल सेंटर (Kisan Call Centre): 1800-180-1551 (सुबह 6 से रात 10 बजे)\n\n"
        "कृपया तुरंत बात करें, सहायता उपलब्ध है।"
    ),
    "kannada": (
        "ನೀವು ಒಂಟಿಯಲ್ಲ. ನೀವು ಕಷ್ಟದ ಪರಿಸ್ಥಿತಿಯಲ್ಲಿದ್ದರೆ ಅಥವಾ ಮಾನಸಿಕ ಒತ್ತಡ ಅನುಭವಿಸುತ್ತಿದ್ದರೆ, "
        "ದಯವಿಟ್ಟು ಭಾರತ ಸರ್ಕಾರದ ಉಚಿತ ಸಹಾಯವಾಣಿಗೆ ಕರೆ ಮಾಡಿ:\n\n"
        "📞 ಟೆಲಿ-ಮಾನಸ್ (Tele-MANAS): 14416 ಅಥವಾ 1800-891-4416 (24x7 ಉಚಿತ)\n"
        "🌾 ಕಿಸಾನ್ ಕಾಲ್ ಸೆಂಟರ್ (Kisan Call Centre): 1800-180-1551 (ಬೆಳಿಗ್ಗೆ 6 ರಿಂದ ರಾತ್ರಿ 10)\n\n"
        "ದಯವಿಟ್ಟು ಈಗಲೇ ಮಾತನಾಡಿ, ಸಹಾಯ ಲಭ್ಯವಿದೆ."
    ),
    "english": (
        "You are not alone. If you are going through a difficult time or emotional distress, "
        "please reach out to these free national helplines:\n\n"
        "📞 Tele-MANAS: 14416 or 1800-891-4416 (24x7 toll-free)\n"
        "🌾 Kisan Call Centre: 1800-180-1551 (6 AM – 10 PM toll-free)\n\n"
        "Please talk to someone, support is always available."
    ),
}

TRILINGUAL_CRISIS = (
    "आप अकेले नहीं हैं / ನೀವು ಒಂಟಿಯಲ್ಲ / You are not alone.\n\n"
    "📞 Tele-MANAS (24x7): 14416 / 1800-891-4416\n"
    "🌾 Kisan Call Centre: 1800-180-1551\n\n"
    "कृपया तुरंत सहायता प्राप्त करें / ದಯವಿಟ್ಟು ನೆರವು ಪಡೆಯಿರಿ / Please reach out for help."
)

TRILINGUAL_GREETING_MENU = """🌾 KrishiMitra mein aapka swagat hai!
ಕೃಷಿಮಿತ್ರಕ್ಕೆ ಸ್ವಾಗತ!
Welcome to KrishiMitra, your farming friend!

अपनी भाषा चुनें / ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ / Choose your language:

1️⃣ हिंदी (Hindi)
2️⃣ ಕನ್ನಡ (Kannada)
3️⃣ English

Reply with 1, 2, or 3 (या भाषा का नाम लिखें / ಅಥವಾ ಭಾಷೆಯ ಹೆಸರು ತಿಳಿಸಿ)"""

STRINGS = {
    "hindi": {
        "lang_confirm": "धन्यवाद! आपकी भाषा *हिंदी* सेट कर दी गई है।",
        "name_offer_profile": "नमस्ते! क्या मैं आपको *{profile_name}* कहकर बुला सकता हूँ, या आप कोई दूसरा नाम बताना चाहेंगे?",
        "ask_name": "नमस्ते! कृपया अपना शुभ नाम लिखकर भेजें (एक पंक्ति में):",
        "invalid_name": "कृपया सही नाम लिखें (कम से कम एक अक्षर होना चाहिए, केवल संख्या नहीं):",
        "name_saved_ask_location": (
            "धन्यवाद, *{salutation}*!\n\n"
            "कृपया अपनी खेत या गाँव की *लोकेशन शेयर करें* 📍\n\n"
            "तरीका:\n"
            "1. चैट में Attachment (📎 বা +) दबाएं\n"
            "2. Location चुनें\n"
            "3. 'Send your current location' पर टैप करें\n\n"
            "(लोकेशन से आपको सबसे नज़दीकी मंडी, स्थानीय मौसम और बीमारी के प्रकोप की चेतावनी समय पर मिलेगी। "
            "आप चाहें तो अपने गाँव या ज़िले का नाम भी लिख सकते हैं, या 'skip' लिख सकते हैं।)"
        ),
        "location_confirm_geocoded": "धन्यवाद, *{salutation}*! आपकी लोकेशन *{place}* सेट हो गई है।",
        "location_skip": "ठीक है, *{salutation}*! हमने अभी लोकेशन छोड़ दी है। ज़रूरत पड़ने पर आप कभी भी लोकेशन भेज सकते हैं।",
        "welcome_capabilities": (
            "🌾 *कृषि-मित्र में आपका स्वागत है, {salutation}!* 🌾\n\n"
            "मैं आपकी खेती में इन चीज़ों में मदद कर सकता हूँ:\n"
            "• 📈 *मंडी भाव:* अपनी फसल का नाम लिखकर पूछें, जैसे 'टमाटर का भाव'\n"
            "• 🏪 *सर्वश्रेष्ठ मंडी:* फसल बेचने के लिए सबसे मुनाफ़े वाली नज़दीकी मंडी\n"
            "• 🔔 *भाव अलर्ट:* जब आपकी मनपसंद क़ीमत आए तो चेतावनी पाएं\n"
            "• 📸 *फ़सल डॉक्टर:* बीमार पत्ते की फ़ोटो भेजें और तुरंत उपचार जानें\n"
            "• ⚠️ *रोग चेतावनी:* आपके क्षेत्र में फैलने वाली बीमारियों की पूर्व सूचना\n\n"
            "आप कभी भी सवाल पूछ सकते हैं या फ़ोटो भेज सकते हैं!"
        ),
        "photo_during_onboarding": (
            "हमें आपकी फ़ोटो मिल गई है! पहले आपका परिचय पूरा कर लेते हैं ताकि सही जानकारी दे सकें। "
            "सेटअप पूरा होने के बाद कृपया यह फ़ोटो दोबारा भेजें।"
        ),
        "out_of_scope": (
            "मैं केवल खेती-किसानी से जुड़े विषयों में सहायता कर सकता हूँ। "
            "कृपया फसल, मंडी भाव, मौसम, या फसल की बीमारी के बारे में पूछें।"
        ),
        "unsupported_media": (
            "कृपया केवल फ़ोटो भेजें (JPG, PNG, WEBP)। "
            "ऑडियो संदेश और वीडियो अभी समर्थित नहीं हैं।"
        ),
        "location_updated": "आपकी लोकेशन अपडेट कर दी गई है: *{place}* ✅",
    },
    "kannada": {
        "lang_confirm": "ಧನ್ಯವಾದಗಳು! ನಿಮ್ಮ ಭಾಷೆಯನ್ನು *ಕನ್ನಡ* ಎಂದು ಆಯ್ಕೆ ಮಾಡಲಾಗಿದೆ.",
        "name_offer_profile": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮನ್ನು *{profile_name}* ಎಂದು ಕರೆಯಬಹುದೇ, ಅಥವಾ ನಿಮ್ಮ ಬೇರೆ ಹೆಸರು ತಿಳಿಸುತ್ತೀರಾ?",
        "ask_name": "ನಮಸ್ಕಾರ! ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರನ್ನು ಟೈಪ್ ಮಾಡಿ ಕಳುಹಿಸಿ (ಒಂದೇ ಸಾಲಿನಲ್ಲಿ):",
        "invalid_name": "ದಯವಿಟ್ಟು ಸರಿಯಾದ ಹೆಸರನ್ನು ನಮೂದಿಸಿ (ಕನಿಷ್ಠ ಒಂದು ಅಕ್ಷರ ಇರಬೇಕು):",
        "name_saved_ask_location": (
            "ಧನ್ಯವಾದಗಳು, *{salutation}*!\n\n"
            "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಜಮೀನು ಅಥವಾ ಊರಿನ *ಲೊಕೇಶನ್ ಹಂಚಿಕೊಳ್ಳಿ* 📍\n\n"
            "ವಿಧಾನ:\n"
            "1. Attachment (📎 ಅಥವಾ +) ಕ್ಲಿಕ್ ಮಾಡಿ\n"
            "2. Location ಆಯ್ಕೆಮಾಡಿ\n"
            "3. 'Send your current location' ಆಯ್ಕೆಮಾಡಿ\n\n"
            "(ಇದರಿಂದ ಹತ್ತಿರದ ಮಾರುಕಟ್ಟೆ, ಹವಾಮಾನ ಮತ್ತು ರೋಗದ ಎಚ್ಚರಿಕೆಗಳನ್ನು ನಿಖರವಾಗಿ ನೀಡಲು ಸಾಧ್ಯವಾಗುತ್ತದೆ. "
            "ಅಥವಾ ನಿಮ್ಮ ಗ್ರಾಮ/ತಾಲ್ಲೂಕಿನ ಹೆಸರು ಬರೆಯಬಹುದು, ಅಥವಾ 'skip' ಎಂದು ಉತ್ತರಿಸಬಹುದು.)"
        ),
        "location_confirm_geocoded": "ಧನ್ಯವಾದಗಳು, *{salutation}*! ನಿಮ್ಮ ಸ್ಥಳ *{place}* ಎಂದು ನಮೂದಿಸಲಾಗಿದೆ.",
        "location_skip": "ಸರಿ, *{salutation}*! ಸ್ಥಳ ನಮೂದಿಸುವುದನ್ನು ಸದ್ಯಕ್ಕೆ ಬಿಟ್ಟುಬಿಡಲಾಗಿದೆ. ಅಗತ್ಯವಿದ್ದಾಗ ನೀವು ಹಂಚಿಕೊಳ್ಳಬಹುದು.",
        "welcome_capabilities": (
            "🌾 *ಕೃಷಿಮಿತ್ರಕ್ಕೆ ಸ್ವಾಗತ, {salutation}!* 🌾\n\n"
            "ನಾನು ನಿಮಗೆ ಈ ವಿಷಯಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ:\n"
            "• 📈 *ಮಾರುಕಟ್ಟೆ ದರ:* 'ಟೊಮೆಟೊ ದರ' ಎಂದು ಬೆಳೆಯ ಹೆಸರು ಕಳುಹಿಸಿ\n"
            "• 🏪 *ಉತ್ತಮ ಮಂಡಿ:* ಮಾರಾಟ ಮಾಡಲು ಅತಿ ಹೆಚ್ಚು ಲಾಭದಾಯಕ ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ\n"
            "• 🔔 *ಬೆಲೆ ಎಚ್ಚರಿಕೆ:* ನಿಮ್ಮ ನಿರೀಕ್ಷಿತ ದರ ಬಂದಾಗ ಮುನ್ಸೂಚನೆ\n"
            "• 📸 *ಬೆಳೆ ರೋಗ ತಪಾಸಣೆ:* ರೋಗಗ್ರಸ್ತ ಎಲೆಯ ಫೋಟೋ ಕಳುಹಿಸಿ, ಚಿಕಿತ್ಸೆ ತಿಳಿಯಿರಿ\n"
            "• ⚠️ *ರೋಗ ಮುನ್ನೆಚ್ಚರಿಕೆ:* ಸುತ್ತಮುತ್ತ ಹರಡುವ ರೋಗಗಳ ಮುನ್ಸೂಚನೆ\n\n"
            "ನೀವು ಯಾವುದೇ ಸಮಯದಲ್ಲಿ ಸಂದೇಶ ಅಥವಾ ಫೋಟೋ ಕಳುಹಿಸಬಹುದು!"
        ),
        "photo_during_onboarding": (
            "ನಿಮ್ಮ ಫೋಟೋ ತಲುಪಿದೆ! ಸರಿಯಾದ ಮಾಹಿತಿ ನೀಡಲು ಮೊದಲು ಪರಿಚಯ ಪೂರ್ಣಗೊಳಿಸೋಣ. "
            "ನೋಂದಣಿ ಮುಗಿದ ನಂತರ ದಯವಿಟ್ಟು ಈ ಫೋಟೋವನ್ನು ಮತ್ತೊಮ್ಮೆ ಕಳುಹಿಸಿ."
        ),
        "out_of_scope": (
            "ನಾನು ಕೃಷಿ ಸಂಬಂಧಿತ ವಿಷಯಗಳಿಗೆ ಮಾತ್ರ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ. "
            "ದಯವಿಟ್ಟು ಬೆಳೆ, ಮಾರುಕಟ್ಟೆ ಬೆಲೆ, ಹವಾಮಾನ ಅಥವಾ ರೋಗಗಳ ಬಗ್ಗೆ ಕೇಳಿ."
        ),
        "unsupported_media": (
            "ದಯವಿಟ್ಟು ಕೇವಲ ಫೋಟೋ ಕಳುಹಿಸಿ (JPG, PNG, WEBP). "
            "ಆಡಿಯೋ ಮತ್ತು ವಿಡಿಯೋ ಸದ್ಯಕ್ಕೆ ಲಭ್ಯವಿಲ್ಲ."
        ),
        "location_updated": "ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ನವೀಕರಿಸಲಾಗಿದೆ: *{place}* ✅",
    },
    "english": {
        "lang_confirm": "Thank you! Your language has been set to *English*.",
        "name_offer_profile": "Hello! Should I call you *{profile_name}*, or would you prefer another name?",
        "ask_name": "Hello! Please type your name (one line):",
        "invalid_name": "Please enter a valid name with at least one letter:",
        "name_saved_ask_location": (
            "Thank you, *{salutation}*!\n\n"
            "Please share your farm or village *location* 📍\n\n"
            "How to share:\n"
            "1. Tap Attachment (📎 or +) in chat\n"
            "2. Select Location\n"
            "3. Tap 'Send your current location'\n\n"
            "(This helps find your nearest mandi prices, weather forecast, and nearby crop disease alerts. "
            "You can also type your village/district name, or type 'skip'.)"
        ),
        "location_confirm_geocoded": "Thank you, *{salutation}*! Your location is saved as *{place}*.",
        "location_skip": "Understood, *{salutation}*! We skipped location for now. You can share it anytime later.",
        "welcome_capabilities": (
            "🌾 *Welcome to KrishiMitra, {salutation}!* 🌾\n\n"
            "Here is how I can help your farm:\n"
            "• 📈 *Mandi Prices:* Type a crop name, e.g., 'tomato price'\n"
            "• 🏪 *Best Market:* Nearest profitable mandis considering transport\n"
            "• 🔔 *Price Alerts:* Get notified when your target price is reached\n"
            "• 📸 *Crop Doctor:* Send a photo of a diseased leaf for diagnosis & remedies\n"
            "• ⚠️ *Outbreak Alerts:* Advance warnings if diseases are spreading near you\n\n"
            "Feel free to ask a question or send a photo anytime!"
        ),
        "photo_during_onboarding": (
            "We received your photo! Let's finish your quick setup first so I can give accurate recommendations. "
            "Please resend your photo right after setup."
        ),
        "out_of_scope": (
            "I can only help with farming and agriculture topics. "
            "Please ask about crops, mandi prices, weather, or plant diseases."
        ),
        "unsupported_media": (
            "Please send images only (JPG, PNG, WEBP). "
            "Audio notes and videos are not supported yet."
        ),
        "location_updated": "Your location has been updated to: *{place}* ✅",
    },
}


def get_salutation(name: str | None, lang: str | None) -> str:
    """Format name with culturally respectful, non-gendered honorific."""
    clean_name = (name or "").strip()
    if not clean_name or clean_name.lower() == "kisan bhai":
        if lang == "hindi":
            return "किसान साथी"
        if lang == "kannada":
            return "ರೈತ ಮಿತ್ರರೇ"
        return "Farmer Friend"

    l = (lang or "english").lower()
    if l == "hindi":
        return f"{clean_name} जी"
    if l == "kannada":
        return f"{clean_name} ಅವರೇ"
    return clean_name


def get_string(key: str, lang: str | None = "english", **kwargs) -> str:
    l = (lang or "english").lower()
    if l not in STRINGS:
        l = "english"
    template = STRINGS[l].get(key, STRINGS["english"].get(key, ""))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
