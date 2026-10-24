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

TRILINGUAL_GREETING_MENU = """🌾 कृषिमित्र में आपका स्वागत है!
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
            "1. चैट में Attachment (📎 या +) दबाएं\n"
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
        "briefing_greeting": "नमस्ते {salutation}! 🌾",
        "briefing_greeting_neutral": "नमस्ते! 🌾",
        "briefing_weather": "आज {location} में मौसम: {condition}, तापमान {temp}°C, नमी {humidity}%।",
        "briefing_price_item": "• *{crop}*: ₹{price}/क्विंटल ({market}, {date})",
        "briefing_price_section": "📊 *मंडी भाव:*\n{items}",
        "briefing_disease_followup": "🩺 *फ़सल स्वास्थ्य:* {disease} ({crop}) का कैसा हाल है? अगर समस्या बनी हुई है तो नई फ़ोटो भेजें।",
        "briefing_closing": "कोई भी सवाल हो या फ़ोटो — बेझिझक भेजें!",
        "price_alert_triggered": (
            "🔔 *भाव अलर्ट!*\n\n"
            "*{crop}* अब ₹*{price}*/क्विंटल है।\n"
            "मंडी: *{market}* ({distance_km} किमी)\n"
            "आपका लक्ष्य: ₹{target_price} से {direction}\n\n"
            "✅ बेचने का अच्छा अवसर हो सकता है! 🌾"
        ),
        "price_direction_above": "ऊपर",
        "price_direction_below": "नीचे",
        "quick_greeting": "नमस्ते! 🌾 मैं आपकी खेती और मंडी भाव में कैसे मदद कर सकता हूँ?",
        "quick_thanks": "आपका स्वागत है! खेती या भाव से जुड़ा कोई भी सवाल हो तो बेझिझक पूछें।",
        "quick_ack": "जी ठीक है! जब भी ज़रूरत हो, संदेश या पत्ते की फ़ोटो भेजें।",
        "quick_bye": "नमस्ते! आपकी फ़सल अच्छी रहे। फिर मिलेंगे!",
        "quick_help": (
            "🌾 *कृषि-मित्र सहायता:*\n"
            "• *मंडी भाव:* 'टमाटर का आज का भाव'\n"
            "• *भाव अलर्ट:* 'प्याज 2000 से ऊपर जाए तो अलर्ट करें'\n"
            "• *फ़सल डॉक्टर:* बीमार पत्ते की फ़ोटो भेजें\n"
            "• *मौसम:* 'आज का मौसम'\n"
            "• *भाषा बदलें:* 'change language' लिखें"
        ),
        "alert_confirm_ask": "क्या आप *{crop}* का भाव ₹*{price}*/क्विंटल से {direction} होने पर अलर्ट सेट करना चाहते हैं? (हाँ/नहीं)",
        "alert_created_success": "✅ *{crop}* के लिए ₹{price}/क्विंटल से {direction} का अलर्ट सेट कर दिया गया है। भाव आने पर सूचना दी जाएगी।",
        "alert_cancelled": "ठीक है, अलर्ट सेट नहीं किया गया।",
        # ── Disease diagnosis flow ──────────────────────────────────────────
        "diag_checking": "आपकी फ़सल की जाँच हो रही है, एक पल रुकें 🌿",
        "diag_ask_crop_single": "क्या यह आपके *{crop}* की फ़ोटो है? (हाँ/नहीं)",
        "diag_ask_crop_multi": "यह फ़ोटो किस फ़सल की है?\n(टमाटर / आलू / मक्का / अंगूर / शिमला मिर्च / सेब / अन्य)",
        "diag_no_leaf": "फ़ोटो में पत्ता स्पष्ट नहीं दिख रहा। कृपया *एक पत्ते* का करीबी फ़ोटो भेजें — दिन की रोशनी में, फ़ोकस साफ़ हो।",
        "diag_low_confidence": "फ़ोटो से बीमारी पहचानना मुश्किल हो रहा है। कृपया *एक पत्ते* का करीबी फ़ोटो भेजें — दिन की रोशनी में, कैमरा स्थिर रखें।",
        "diag_healthy": "आपके {crop} में मुझे वे बीमारियाँ नहीं दिख रहीं जो मैं पहचान सकता हूँ। पत्ते सामान्य दिख रहे हैं। नियमित निगरानी जारी रखें।",
        "diag_no_disease_model": "{crop} के लिए मेरे पास अभी बीमारी पहचानने का डेटा नहीं है। सामान्य सलाह: प्रभावित पत्ते हटाएँ, ऊपर से पानी न दें, और नज़दीकी कृषि विज्ञान केंद्र (KVK) से संपर्क करें।",
        "diag_wrong_crop": "यह फ़ोटो {crop} की नहीं लग रही। क्या आप सही पत्ता भेज सकते हैं?",
        "diag_unsupported_crop": "यह फ़सल अभी मेरे बीमारी-पहचान सिस्टम में नहीं है। सामान्य सलाह: प्रभावित पत्ते हटाएँ, ऊपर से पानी न दें, और नज़दीकी KVK या कृषि अधिकारी से मिलें।",
        "diag_ok_single": "🩺 आपके {crop} में *{disease}* दिख रहा है ({confidence} निश्चितता)।\nपहला कदम: {first_step}\nआपके पौधे का कितना हिस्सा प्रभावित है?\n• कुछ पत्ते\n• काफ़ी पत्ते\n• ज़्यादातर पौधा",
        "diag_ok_multi": "🩺 {total} पत्तों में से {diseased} में *{disease}* दिख रहा है ({confidence} निश्चितता)।\nपहला कदम: {first_step}\nआपके पौधे का कितना हिस्सा प्रभावित है?\n• कुछ पत्ते\n• काफ़ी पत्ते\n• ज़्यादातर पौधा",
        "diag_ok_low_conf_note": " (KVK या कृषि अधिकारी से पुष्टि करें)",
        "diag_severity_ask": "पौधे का कितना हिस्सा प्रभावित है?\n• कुछ पत्ते\n• काफ़ी पत्ते\n• ज़्यादातर पौधा",
        "diag_treatment": (
            "✅ *{disease} का उपचार ({crop})*\n\n"
            "🌿 *घरेलू/जैविक:* {organic}\n\n"
            "💊 *रासायनिक:* {chemical}\n"
            "_खुराक: अपनी कृषि दुकान या KVK से पुष्टि करें_\n\n"
            "🛡️ *सावधानी:* लेबल पढ़ें, दस्ताने और मास्क पहनें, कटाई से पहले प्रतीक्षा समय का पालन करें।\n\n"
            "📅 *बिना उपचार के अनुमान (संकेतक):*\n• 3 दिन में: {day3}\n• 7 दिन में: {day7}"
        ),
        "diag_treatment_severe_note": "\n\n⚠️ गंभीर संक्रमण — कृपया नज़दीकी KVK या कृषि अधिकारी से तुरंत मिलें।",
        "diag_dose_review_note": "खुराक: अपनी कृषि दुकान या KVK से पुष्टि करें",
        "buy_header": "🛒 ऑनलाइन कहाँ से खरीदें (सर्च लिंक):",
"buy_note": "पैक पर सक्रिय तत्व और मात्रा (%) मिलाकर देखें, लाइसेंस वाले विक्रेता से ही खरीदें और लेबल ज़रूर पढ़ें। शक हो तो अपनी स्थानीय कृषि दुकान या KVK से पूछें।",
        "diag_severity_saved": "समझ गया। उपचार की जानकारी भेज रहा हूँ।",
        "outbreak_alert_urgent": (
            "🚨 *रोग प्रकोप चेतावनी (Outbreak Alert)* 🚨\n\n"
            "आपके क्षेत्र में *{crop}* में *{disease}* का प्रकोप देखा गया है।\n"
            "📍 दूरी: लगभग *{dist_km} किमी* ({direction})\n"
            "💨 कैसे फैलता है: {spread_info}\n\n"
            "🌱 *रोकथाम के मुख्य कदम:*\n{steps}\n\n"
            "🌅 *कल सुबह का आवश्यक कदम:*\n{morning_action}\n\n"
            "सतर्क रहें और अपनी फसल की निगरानी करें! 🌾"
        ),
        "outbreak_alert_watch": (
            "⚠️ *फसल सतर्कता सूचना (Crop Health Notice)* ⚠️\n\n"
            "पास के क्षेत्र में *{disease}* का प्रकोप देखा गया है (~{dist_km} किमी, {direction})।\n"
            "यह बीमारी आपकी *{crop}* की फसल को भी प्रभावित कर सकती है।\n\n"
            "💨 कैसे फैलता है: {spread_info}\n\n"
            "🌱 *बचाव के मुख्य कदम:*\n{steps}\n\n"
            "🌅 *कल सुबह का कदम:*\n{morning_action}\n\n"
            "अपनी फसल की समय पर निगरानी करें! 🌾"
        ),
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
        "briefing_greeting": "ಶುಭೋದಯ {salutation}! 🌾",
        "briefing_greeting_neutral": "ಶುಭೋದಯ! 🌾",
        "briefing_weather": "ಇಂದು {location} ಹವಾಮಾನ: {condition}, ತಾಪಮಾನ {temp}°C, ತೇವಾಂಶ {humidity}%.",
        "briefing_price_item": "• *{crop}*: ₹{price}/ಕ್ವಿಂಟಾಲ್ ({market}, {date})",
        "briefing_price_section": "📊 *ಮಾರುಕಟ್ಟೆ ದರ:*\n{items}",
        "briefing_disease_followup": "🩺 *ಬೆಳೆ ಆರೋಗ್ಯ:* {disease} ({crop}) ಹೇಗಿದೆ? ಸಮಸ್ಯೆ ಮುಂದುವರಿದರೆ ಹೊಸ ಫೋಟೋ ಕಳುಹಿಸಿ.",
        "briefing_closing": "ಯಾವುದೇ ಪ್ರಶ್ನೆ ಅಥವಾ ಫೋಟೋ ಇದ್ದರೆ ಹಿಂಜರಿಯದೆ ಕಳುಹಿಸಿ!",
        "price_alert_triggered": (
            "🔔 *ಬೆಲೆ ಎಚ್ಚರಿಕೆ!*\n\n"
            "*{crop}* ಈಗ ₹*{price}*/ಕ್ವಿಂಟಾಲ್ ಆಗಿದೆ.\n"
            "ಮಾರುಕಟ್ಟೆ: *{market}* ({distance_km} ಕಿ.ಮೀ)\n"
            "ನಿಮ್ಮ ಗುರಿ: ₹{target_price} ಗಿಂತ {direction}\n\n"
            "✅ ಮಾರಾಟ ಮಾಡಲು ಇದು ಉತ್ತಮ ಸಮಯವಾಗಿರಬಹುದು! 🌾"
        ),
        "price_direction_above": "ಹೆಚ್ಚು",
        "price_direction_below": "ಕಡಿಮೆ",
        "quick_greeting": "ನಮಸ್ಕಾರ! 🌾 ಕೃಷಿ ಅಥವಾ ಮಾರುಕಟ್ಟೆ ದರದ ಬಗ್ಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
        "quick_thanks": "ನಿಮಗೆ ಸ್ವಾಗತ! ಯಾವುದೇ ಕೃಷಿ ಮಾಹಿತಿ ಅಥವಾ ದರದ ಅಗತ್ಯವಿದ್ದಾಗ ಕೇಳಿ.",
        "quick_ack": "ಸರಿ! ಅಗತ್ಯವಿದ್ದಾಗ ಸಂದೇಶ ಅಥವಾ ಎಲೆಯ ಫೋಟೋ ಕಳುಹಿಸಿ.",
        "quick_bye": "ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಬೆಳೆ ಸಮೃದ್ಧವಾಗಿರಲಿ.",
        "quick_help": (
            "🌾 *ಕೃಷಿಮಿತ್ರ ಸಹಾಯ:*\n"
            "• *ಮಾರುಕಟ್ಟೆ ದರ:* 'ಇಂದಿನ ಟೊಮೆಟೊ ಬೆಲೆ'\n"
            "• *ಬೆಲೆ ಎಚ್ಚರಿಕೆ:* 'ಈರುಳ್ಳಿ 2000 ಕ್ಕಿಂತ ಹೆಚ್ಚಾದಾಗ ತಿಳಿಸಿ'\n"
            "• *ಬೆಳೆ ರೋಗ ತಪಾಸಣೆ:* ರೋಗಗ್ರಸ್ತ ಎಲೆಯ ಫೋಟೋ ಕಳುಹಿಸಿ\n"
            "• *ಹವಾಮಾನ:* 'ಇಂದಿನ ಹವಾಮಾನ'\n"
            "• *ಭಾಷೆ ಬದಲಾವಣೆ:* 'change language' ಎಂದು ಕಳುಹಿಸಿ"
        ),
        "alert_confirm_ask": "*{crop}* ಬೆಲೆ ₹*{price}*/ಕ್ವಿಂಟಾಲ್ ಗಿಂತ {direction} ಆದಾಗ ಎಚ್ಚರಿಕೆ ನೀಡಬೇಕೇ? (ಹೌದು/ಇಲ್ಲ)",
        "alert_created_success": "✅ *{crop}* ಬೆಲೆ ₹{price}/ಕ್ವಿಂಟಾಲ್ ಗಿಂತ {direction} ಆದಾಗ ಎಚ್ಚರಿಕೆ ನೀಡುವಂತೆ ಹೊಂದಿಸಲಾಗಿದೆ.",
        "alert_cancelled": "ಸರಿ, ಬೆಲೆ ಎಚ್ಚರಿಕೆಯನ್ನು ಹೊಂದಿಸಲಾಗಿಲ್ಲ.",
        # ── Disease diagnosis flow ──────────────────────────────────────────
        "diag_checking": "ನಿಮ್ಮ ಬೆಳೆ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ, ಒಂದು ಕ್ಷಣ 🌿",
        "diag_ask_crop_single": "ಇದು ನಿಮ್ಮ *{crop}* ಬೆಳೆಯೇ? (ಹೌದು/ಇಲ್ಲ)",
        "diag_ask_crop_multi": "ಇದು ಯಾವ ಬೆಳೆಯ ಫೋಟೋ?\n(ಟೊಮೆಟೊ / ಆಲೂಗಡ್ಡೆ / ಮೆಕ್ಕೆಜೋಳ / ದ್ರಾಕ್ಷಿ / ಕ್ಯಾಪ್ಸಿಕಂ / ಸೇಬು / ಇತರ)",
        "diag_no_leaf": "ಫೋಟೋದಲ್ಲಿ ಎಲೆ ಸ್ಪಷ್ಟವಾಗಿ ಕಾಣಿಸುತ್ತಿಲ್ಲ. ದಯವಿಟ್ಟು ದಿನದ ಬೆಳಕಿನಲ್ಲಿ, ಸ್ಪಷ್ಟವಾಗಿ ಕಾಣುವಂತೆ *ಒಂದು ಎಲೆಯ* ಹತ್ತಿರದ ಫೋಟೋ ಕಳುಹಿಸಿ.",
        "diag_low_confidence": "ರೋಗವನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಗುರುತಿಸಲು ಸಾಧ್ಯವಾಗುತ್ತಿಲ್ಲ. ದಯವಿಟ್ಟು ದಿನದ ಬೆಳಕಿನಲ್ಲಿ, ಕ್ಯಾಮೆರಾ ಸ್ಥಿರವಾಗಿಟ್ಟು *ಒಂದು ಎಲೆಯ* ಹತ್ತಿರದ ಫೋಟೋ ಕಳುಹಿಸಿ.",
        "diag_healthy": "ನಿಮ್ಮ {crop} ಬೆಳೆಯಲ್ಲಿ ನಾನು ಗುರುತಿಸಬಹುದಾದ ಯಾವುದೇ ರೋಗದ ಲಕ್ಷಣಗಳು ಕಾಣಿಸುತ್ತಿಲ್ಲ. ಎಲೆಗಳು ಸಹಜವಾಗಿವೆ. ನಿಯಮಿತ ನಿಗಾ ಇರಿಸಿ.",
        "diag_no_disease_model": "{crop} ಬೆಳೆಗೆ ರೋಗ ಪತ್ತೆಹಚ್ಚುವ ಮಾಹಿತಿ ಸದ್ಯಕ್ಕೆ ಲಭ್ಯವಿಲ್ಲ. ಸಾಮಾನ್ಯ ಸಲಹೆ: ಬಾಧಿತ ಎಲೆಗಳನ್ನು ತೆಗೆದುಹಾಕಿ, ಮೇಲಿನಿಂದ ನೀರು ಹಾಯಿಸಬೇಡಿ, ಮತ್ತು ಸ್ಥಳೀಯ ಕೆವಿಕೆ (KVK) ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "diag_wrong_crop": "ಇದು {crop} ಎಲೆಯಂತೆ ಕಾಣುತ್ತಿಲ್ಲ, ದಯವಿಟ್ಟು ಫೋಟೋವನ್ನು ಒಮ್ಮೆ ಪರಿಶೀಲಿಸುವಿರಾ?",
        "diag_unsupported_crop": "ಈ ಬೆಳೆ ಸದ್ಯಕ್ಕೆ ರೋಗ ಪತ್ತೆಹಚ್ಚುವ ವ್ಯವಸ್ಥೆಯಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ. ಸಾಮಾನ್ಯ ಸಲಹೆ: ಬಾಧಿತ ಎಲೆಗಳನ್ನು ತೆಗೆದುಹಾಕಿ, ಮೇಲಿನಿಂದ ನೀರು ಹಾಯಿಸಬೇಡಿ, ಮತ್ತು ಹತ್ತಿರದ ಕೆವಿಕೆ ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "diag_ok_single": (
            "🩺 ನಿಮ್ಮ {crop} ಬೆಳೆಯಲ್ಲಿ ಹೆಚ್ಚಾಗಿ *{disease}* ಇರುವ ಸಾಧ್ಯತೆಯಿದೆ ({confidence} ಖಚಿತತೆ){low_conf_note}.\n\n"
            "ಮೊದಲ ತುರ್ತು ಕ್ರಮ: {first_step}\n\n"
            "ಗಿಡದ ಎಷ್ಟು ಭಾಗ ಬಾಧಿತವಾಗಿದೆ?\n"
            "• ಕೆಲವು ಎಲೆಗಳು\n"
            "• ಸಾಕಷ್ಟು ಎಲೆಗಳು\n"
            "• ಬಹುತೇಕ ಗಿಡ"
        ),
        "diag_ok_multi": (
            "🩺 {total} ಎಲೆಗಳಲ್ಲಿ {diseased} ಎಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚಾಗಿ *{disease}* ಇರುವ ಸಾಧ್ಯತೆಯಿದೆ ({confidence} ಖಚಿತತೆ){low_conf_note}.\n\n"
            "ಮೊದಲ ತುರ್ತು ಕ್ರಮ: {first_step}\n\n"
            "ಗಿಡದ ಎಷ್ಟು ಭಾಗ ಬಾಧಿತವಾಗಿದೆ?\n"
            "• ಕೆಲವು ಎಲೆಗಳು\n"
            "• ಸಾಕಷ್ಟು ಎಲೆಗಳು\n"
            "• ಬಹುತೇಕ ಗಿಡ"
        ),
        "diag_ok_low_conf_note": " (ದಯವಿಟ್ಟು ಕೆವಿಕೆ ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯೊಂದಿಗೆ ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ)",
        "diag_severity_ask": "ಗಿಡದ ಎಷ್ಟು ಭಾಗ ಬಾಧಿತವಾಗಿದೆ?\n• ಕೆಲವು ಎಲೆಗಳು\n• ಸಾಕಷ್ಟು ಎಲೆಗಳು\n• ಬಹುತೇಕ ಗಿಡ",
        "diag_treatment": (
            "✅ *{disease} ಚಿಕಿತ್ಸೆ ({crop})*\n\n"
            "🌿 *ಸಾವಯವ / ಮನೆಮದ್ದು:* {organic}\n\n"
            "💊 *ರಾಸಾಯನಿಕ:* {chemical}\n"
            "_{dose_note}_\n\n"
            "🛡️ *ಸುರಕ್ಷತಾ ಕ್ರಮ:* ಲೇಬಲ್ ಸೂಚನೆಗಳನ್ನು ಓದಿ, ಕೈಗವಸು ಮತ್ತು ಮಾಸ್ಕ್ ಧರಿಸಿ, ಕಟಾವಿಗೆ ಮುನ್ನ ಕಾಯುವ ಅವಧಿ ಪಾಲಿಸಿ.\n\n"
            "📅 *ಚಿಕಿತ್ಸೆ ನೀಡದಿದ್ದರೆ ಹರಡುವಿಕೆ (ಅಂದಾಜು):*\n"
            "• 3 ದಿನಗಳಲ್ಲಿ: {day3}\n"
            "• 7 ದಿನಗಳಲ್ಲಿ: {day7}{severe_note}"
        ),
        "diag_treatment_severe_note": "\n\n⚠️ ತೀವ್ರತರವಾದ ಸೋಂಕು — ದಯವಿಟ್ಟು ತಕ್ಷಣವೇ ನಿಮ್ಮ ಹತ್ತಿರದ ಕೆವಿಕೆ ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "diag_dose_review_note": "ಪ್ರಮಾಣವನ್ನು ನಿಮ್ಮ ಕೃಷಿ ಅಂಗಡಿ ಅಥವಾ KVK ಯೊಂದಿಗೆ ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ",
        "buy_header": "🛒 ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ಎಲ್ಲಿ ಖರೀದಿಸಬಹುದು (ಹುಡುಕಾಟ ಲಿಂಕ್‌ಗಳು):",
        "buy_note": "ಪ್ಯಾಕ್‌ನಲ್ಲಿರುವ ಸಕ್ರಿಯ ಘಟಕ ಮತ್ತು ಪ್ರಮಾಣ (%) ಹೊಂದುತ್ತದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸಿ, ಪರವಾನಗಿ ಇರುವ ಮಾರಾಟಗಾರರಿಂದ ಮಾತ್ರ ಖರೀದಿಸಿ, ಲೇಬಲ್ ಓದಿ. ಸಂದೇಹವಿದ್ದರೆ ಸ್ಥಳೀಯ ಕೃಷಿ ಅಂಗಡಿ ಅಥವಾ KVK ಕೇಳಿ.",
        "diag_severity_saved": "ತಿಳಿಯಿತು. ಚಿಕಿತ್ಸಾ ವಿಧಾನ ಹೀಗಿದೆ:",
        "outbreak_alert_urgent": (
            "🚨 *ರೋಗ ಹರಡುವಿಕೆ ಎಚ್ಚರಿಕೆ (Outbreak Alert)* 🚨\n\n"
            "ನಿಮ್ಮ ಸಮೀಪದಲ್ಲಿ *{crop}* ಬೆಳೆಗೆ *{disease}* ರೋಗ ಕಂಡುಬಂದಿದೆ.\n"
            "📍 ಅಂತರ: ಸುಮಾರು *{dist_km} ಕಿ.ಮೀ* ({direction})\n"
            "💨 ಹರಡುವ ವಿಧಾನ: {spread_info}\n\n"
            "🌱 *ಮುನ್ನೆಚ್ಚರಿಕಾ ಕ್ರಮಗಳು:*\n{steps}\n\n"
            "🌅 *ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಮಾಡಬೇಕಾದ ಕೆಲಸ:*\n{morning_action}\n\n"
            "ಜಾಗರೂಕರಾಗಿರಿ ಮತ್ತು ಬೆಳೆಯ ಮೇಲೆ ನಿಗಾ ಇರಿಸಿ! 🌾"
        ),
        "outbreak_alert_watch": (
            "⚠️ *ಬೆಳೆ ಜಾಗರೂಕತೆ ಸೂಚನೆ (Crop Notice)* ⚠️\n\n"
            "ಸಮೀಪದಲ್ಲಿ *{disease}* ರೋಗ ಕಂಡುಬಂದಿದೆ (~{dist_km} ಕಿ.ಮೀ, {direction}).\n"
            "ಈ ರೋಗವು ನಿಮ್ಮ *{crop}* ಬೆಳೆಗೂ ಹರಡುವ ಸಾಧ್ಯತೆಯಿದೆ.\n\n"
            "💨 ಹರಡುವ ವಿಧಾನ: {spread_info}\n\n"
            "🌱 *ಮುನ್ನೆಚ್ಚರಿಕಾ ಕ್ರಮಗಳು:*\n{steps}\n\n"
            "🌅 *ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಮಾಡಬೇಕಾದ ಕೆಲಸ:*\n{morning_action}\n\n"
            "ನಿಮ್ಮ ಬೆಳೆಯನ್ನು ಜಾಗರೂಕತೆಯಿಂದ ಪರಿಶೀಲಿಸಿ! 🌾"
        ),
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
        "briefing_greeting": "Good morning, {salutation}! 🌾",
        "briefing_greeting_neutral": "Good morning! 🌾",
        "briefing_weather": "Today's weather in {location}: {condition}, temp {temp}°C, humidity {humidity}%.",
        "briefing_price_item": "• *{crop}*: ₹{price}/quintal ({market}, {date})",
        "briefing_price_section": "📊 *Market Prices:*\n{items}",
        "briefing_disease_followup": "🩺 *Crop Health:* How is your {crop} ({disease}) doing? If issues persist, please send a fresh photo.",
        "briefing_closing": "Feel free to send a photo or message if you have any questions!",
        "price_alert_triggered": (
            "🔔 *Price Alert!*\n\n"
            "*{crop}* is now ₹*{price}*/quintal.\n"
            "Market: *{market}* ({distance_km} km)\n"
            "Your target was: {direction} ₹{target_price}\n\n"
            "✅ Good time to consider selling! 🌾"
        ),
        "price_direction_above": "above",
        "price_direction_below": "below",
        "quick_greeting": "Hello! 🌾 How can I help with your farming or mandi prices today?",
        "quick_thanks": "You're welcome! Feel free to ask anytime about crops, prices, or farm practices.",
        "quick_ack": "Understood! Send a message or photo whenever you need support.",
        "quick_bye": "Goodbye! Wishing you a bountiful harvest. See you soon!",
        "quick_help": (
            "🌾 *KrishiMitra Help:*\n"
            "• *Mandi Prices:* 'tomato price today'\n"
            "• *Price Alerts:* 'alert me when onion goes above 2000'\n"
            "• *Crop Doctor:* Send a photo of an affected leaf\n"
            "• *Weather:* 'today weather'\n"
            "• *Language:* Send 'change language' anytime"
        ),
        "alert_confirm_ask": "Shall I set an alert when *{crop}* goes {direction} ₹*{price}*/quintal? (yes/no)",
        "alert_created_success": "✅ Alert set for *{crop}* when price goes {direction} ₹{price}/quintal at nearby mandis.",
        "alert_cancelled": "Alright, no alert was set.",
        # ── Disease diagnosis flow ──────────────────────────────────────────
        "diag_checking": "Checking your crop, one moment 🌿",
        "diag_ask_crop_single": "Is this your *{crop}* plant? (yes/no)",
        "diag_ask_crop_multi": "Which crop is this?\n(tomato / potato / maize / grape / capsicum / apple / other)",
        "diag_no_leaf": "I couldn't clearly see a leaf in the photo. Please send a close-up of *one leaf* in daylight, in focus.",
        "diag_low_confidence": "I couldn't tell clearly. Please send a close-up photo of one leaf in daylight, keeping the camera steady.",
        "diag_healthy": "I don't see signs of the diseases I can recognize on your {crop}. Leaves appear normal. Continue regular monitoring.",
        "diag_no_disease_model": "I don't have disease recognition data for {crop} yet. General advice: remove affected leaves, avoid overhead watering, and consult your local KVK or agriculture officer.",
        "diag_wrong_crop": "This doesn't look like a {crop} leaf to me, could you check the photo?",
        "diag_unsupported_crop": "This crop is not currently covered in my disease doctor. General advice: remove affected leaves, avoid overhead watering, and visit your nearest KVK or agriculture officer.",
        "diag_ok_single": (
            "🩺 Most likely *{disease}* on your {crop} ({confidence} confidence){low_conf_note}.\n\n"
            "Immediate first step: {first_step}\n\n"
            "How much of the plant is affected?\n"
            "• a few leaves\n"
            "• many leaves\n"
            "• most of the plant"
        ),
        "diag_ok_multi": (
            "🩺 Out of {total} leaves, {diseased} show most likely *{disease}* ({confidence} confidence){low_conf_note}.\n\n"
            "Immediate first step: {first_step}\n\n"
            "How much of the plant is affected?\n"
            "• a few leaves\n"
            "• many leaves\n"
            "• most of the plant"
        ),
        "diag_ok_low_conf_note": " (please confirm with your KVK or agriculture officer)",
        "diag_severity_ask": "How much of the plant is affected?\n• a few leaves\n• many leaves\n• most of the plant",
        "diag_treatment": (
            "✅ *{disease} Treatment ({crop})*\n\n"
            "🌿 *Organic / Home:* {organic}\n\n"
            "💊 *Chemical:* {chemical}\n"
            "_{dose_note}_\n\n"
            "🛡️ *Safety:* Always read label instructions, wear gloves and a mask, and follow pre-harvest interval before picking.\n\n"
            "📅 *Untreated outlook (illustrative):*\n"
            "• In 3 days: {day3}\n"
            "• In 7 days: {day7}{severe_note}"
        ),
        "diag_treatment_severe_note": "\n\n⚠️ Severe infection — please contact your nearest KVK or agriculture officer immediately.",
        "diag_dose_review_note": "Confirm the dose with your agri shop or KVK",
        # inside the "english" block
        "buy_header": "🛒 Where to buy online (search links):",
        "buy_note": "Check that the active ingredient and strength on the pack match, buy from a licensed seller, and read the label. Ask your local agri shop or KVK if unsure.",


        "diag_severity_saved": "Got it. Here is the treatment plan:",
        "outbreak_alert_urgent": (
            "🚨 *Outbreak Alert!* 🚨\n\n"
            "An outbreak of *{disease}* in *{crop}* has been reported in your area.\n"
            "📍 Distance: ~*{dist_km} km* ({direction})\n"
            "💨 How it spreads: {spread_info}\n\n"
            "🌱 *Preventive Steps:*\n{steps}\n\n"
            "🌅 *Tomorrow Morning Action:*\n{morning_action}\n\n"
            "Stay alert and monitor your crop! 🌾"
        ),
        "outbreak_alert_watch": (
            "⚠️ *Crop Health Notice* ⚠️\n\n"
            "*{disease}* has been reported nearby (~{dist_km} km, {direction}).\n"
            "This disease can also affect your *{crop}* crop.\n\n"
            "💨 How it spreads: {spread_info}\n\n"
            "🌱 *Preventive Steps:*\n{steps}\n\n"
            "🌅 *Tomorrow Morning Action:*\n{morning_action}\n\n"
            "Stay alert and inspect your crop! 🌾"
        ),
    },
}

# ── Compass Directions ────────────────────────────────────────────────────────
COMPASS_DIRECTIONS = {
    "hindi": {
        "North": "उत्तर", "North-East": "उत्तर-पूर्व", "East": "पूर्व", "South-East": "दक्षिण-पूर्व",
        "South": "दक्षिण", "South-West": "दक्षिण-पश्चिम", "West": "पश्चिम", "North-West": "उत्तर-पश्चिम"
    },
    "kannada": {
        "North": "ಉತ್ತರ", "North-East": "ಈಶಾನ್ಯ", "East": "ಪೂರ್ವ", "South-East": "ಆಗ್ನೇಯ",
        "South": "ದಕ್ಷಿಣ", "South-West": "ನೈಋತ್ಯ", "West": "ಪಶ್ಚಿಮ", "North-West": "ವಾಯುವ್ಯ"
    },
    "english": {
        "North": "North", "North-East": "North-East", "East": "East", "South-East": "South-East",
        "South": "South", "South-West": "South-West", "West": "West", "North-West": "North-West"
    }
}

def get_compass_direction(direction: str, lang: str | None = "english") -> str:
    l = (lang or "english").lower()
    return COMPASS_DIRECTIONS.get(l, COMPASS_DIRECTIONS["english"]).get(direction, direction)


# ── Spread Mode Descriptions ──────────────────────────────────────────────────
SPREAD_DESCRIPTIONS = {
    "hindi": {
        "air": "हवा और बारिश के छींटों से फैलता है",
        "insect": "कीटों और रस चूसक मक्खियों से फैलता है",
        "water": "पानी के बहाव और बारिश की बूंदों से फैलता है",
        "soil": "संक्रमित मिट्टी और पुरानी पत्तियों से फैलता है",
        "contact": "हाथों और औजारों के संपर्क से फैलता है",
    },
    "kannada": {
        "air": "ಗಾಳಿ ಮತ್ತು ಮಳೆಯ ಹನಿಗಳ ಮೂಲಕ ಹರಡುತ್ತದೆ",
        "insect": "ಕೀಟಗಳು ಮತ್ತು ನೊಣಗಳ ಮೂಲಕ ಹರಡುತ್ತದೆ",
        "water": "ನೀರು ಮತ್ತು ಮಳೆ ಸಿಂಚನದ ಮೂಲಕ ಹರಡುತ್ತದೆ",
        "soil": "ಸೋಂಕಿತ ಮಣ್ಣು ಮತ್ತು ಉಳಿಕೆಗಳಿಂದ ಹರಡುತ್ತದೆ",
        "contact": "ಸಂಪರ್ಕ ಮತ್ತು ಕೃಷಿ ಉಪಕರಣಗಳಿಂದ ಹರಡುತ್ತದೆ",
    },
    "english": {
        "air": "Wind-borne spores and rain splash",
        "insect": "Insect vectors and whiteflies",
        "water": "Water splash and surface run-off",
        "soil": "Infected soil debris",
        "contact": "Contaminated hands, tools and contact",
    }
}

def get_spread_description(modes: list[str], lang: str | None = "english") -> str:
    l = (lang or "english").lower()
    mapping = SPREAD_DESCRIPTIONS.get(l, SPREAD_DESCRIPTIONS["english"])
    descs = [mapping[m] for m in modes if m in mapping]
    if descs:
        return ", ".join(descs)
    return mapping.get("air", "Wind-borne spores")


# ── Tomorrow Morning Concrete Actions ─────────────────────────────────────────
MORNING_ACTIONS = {
    "hindi": "कल सुबह जल्दी अपने खेत का निरीक्षण करें और किसी भी रोगग्रस्त पत्ते को तुरंत तोड़कर नष्ट कर दें।",
    "kannada": "ನಾಳೆ ಬೆಳಿಗ್ಗೆ ನಿಮ್ಮ ಜಮೀನನ್ನು ಪರಿಶೀಲಿಸಿ, ರೋಗದ ಲಕ್ಷಣವಿರುವ ಎಲೆಗಳನ್ನು ತಕ್ಷಣ ಕತ್ತರಿಸಿ ನಾಶಪಡಿಸಿ.",
    "english": "Inspect your plants tomorrow morning and remove any diseased leaves immediately."
}

def get_morning_action(lang: str | None = "english") -> str:
    l = (lang or "english").lower()
    return MORNING_ACTIONS.get(l, MORNING_ACTIONS["english"])


# ── Preventive Steps ──────────────────────────────────────────────────────────
PREVENTIVE_STEPS = {
    "kannada": {
        "blight": [
            "ಗಿಡಗಳ ಬುಡಕ್ಕೆ ನೀರು ಹಾಕಿ, ಎಲೆಗಳ ಮೇಲೆ ನೀರು ಚಿಮುಕಿಸಬೇಡಿ",
            "ಬಾಧಿತ ಎಲೆಗಳನ್ನು ತಕ್ಷಣ ಕಿತ್ತು ಜಮೀನಿನಿಂದ ದೂರ ನಾಶಪಡಿಸಿ",
            "ಗಿಡಗಳ ನಡುವೆ ಸರಿಯಾದ ಅಂತರ ಮತ್ತು ಗಾಳಿಯಾಡುವಿಕೆ ಇರಲಿ",
            "ಮುಂಜಾನೆ ಬೇವಿನ ಎಣ್ಣೆ (Neem oil) ಅಥವಾ ಶಿಲೀಂಧ್ರನಾಶಕ ಸಿಂಪಡಿಸಿ"
        ],
        "spot": [
            "ಸೋಂಕಿತ ಎಲೆಗಳನ್ನು ಕಿತ್ತು ನಾಶಮಾಡಿ",
            "ಕೃಷಿ ಉಪಕರಣಗಳನ್ನು ತೊಳೆದು ಬಳಸಿ",
            "ಗಿಡದ ಬುಡಕ್ಕೆ ಮಾತ್ರ ನೀರು ಹಾಯಿಸಿ",
            "ತಾಮ್ರ ಆಧಾರಿತ ಶಿಲೀಂಧ್ರನಾಶಕ ಸಿಂಪಡಿಸಿ"
        ],
        "rust": [
            "ಮುಂಜಾನೆ ಶಿಲೀಂಧ್ರನಾಶಕ ಸಿಂಪಡಿಸಿ",
            "ಹೆಚ್ಚು ಸಾರಜನಕ (Nitrogen) ಗೊಬ್ಬರ ಹಾಕುವುದನ್ನು ತಪ್ಪಿಸಿ",
            "ಪ್ರತಿದಿನ ಎಲೆಗಳ ಕೆಳಭಾಗವನ್ನು ಪರಿಶೀಲಿಸಿ"
        ],
        "mildew": [
            "ಬಾಧಿತ ಭಾಗಗಳನ್ನು ತಕ್ಷಣ ಕತ್ತರಿಸಿ ತೆಗೆಯಿರಿ",
            "ಸಾಕಷ್ಟು ಬಿಸಿಲು ಮತ್ತು ಗಾಳಿಯಾಡುವಂತೆ ನೋಡಿಕೊಳ್ಳಿ",
            "ಬೇವಿನ ಎಣ್ಣೆ ಅಥವಾ ಶಿಲೀಂಧ್ರನಾಶಕ ಸಿಂಪಡಿಸಿ"
        ],
        "default": [
            "ಗಿಡಗಳ ಬುಡಕ್ಕೆ ನೀರು ಹಾಯಿಸಿ, ಎಲೆಗಳ ಮೇಲೆ ನೀರು ಹಾಕಬೇಡಿ",
            "ಬಾಧಿತ ಎಲೆಗಳನ್ನು ತಕ್ಷಣ ಕಿತ್ತು ನಾಶಪಡಿಸಿ",
            "ಗಿಡಗಳ ನಡುವೆ ಉತ್ತಮ ಗಾಳಿಯಾಡುವಿಕೆ ಕಾಯ್ದುಕೊಳ್ಳಿ",
            "ಮುಂಜಾನೆ ಬೇವಿನ ಎಣ್ಣೆ ಸಿಂಪಡಿಸಿ"
        ]
    },
    "hindi": {
        "blight": [
            "पौधों की जड़ों में पानी दें, पत्तियों पर छिड़काव न करें",
            "प्रभावित पत्तियों को तुरंत हटाकर नष्ट कर दें",
            "पौधों के बीच उचित दूरी और हवा का प्रवाह रखें",
            "सुबह के समय नीम के तेल या कॉपर फंगीसाइड का छिड़काव करें"
        ],
        "spot": [
            "संक्रमित पत्तियों को तुरंत हटाकर नष्ट करें",
            "औजारों को साफ करके ही इस्तेमाल करें",
            "पत्तियों पर पानी का जमाव न होने दें",
            "कॉपर आधारित फफूंदनाशक का छिड़काव करें"
        ],
        "rust": [
            "सुबह के समय कवकनाशी (फंगीसाइड) का छिड़काव करें",
            "अत्यधिक नाइट्रोजन खाद के उपयोग से बचें",
            "प्रतिदिन पत्तियों की निचली सतह की जांच करें"
        ],
        "mildew": [
            "प्रभावित पत्तियों और टहनियों को तुरंत काट दें",
            "पौधों में पर्याप्त धूप और हवा सुनिश्चित करें",
            "नीम का तेल या अनुशंसित फंगीसाइड छिड़कें"
        ],
        "default": [
            "पौधों की जड़ों में पानी दें, पत्तियों को सूखा रखें",
            "रोगग्रस्त पत्तियों को तुरंत हटा दें",
            "पौधों के बीच अच्छी हवा का संचार बनाए रखें",
            "नीम के तेल का हल्का छिड़काव करें"
        ]
    },
    "english": {
        "blight": [
            "Avoid overhead irrigation — water at soil level",
            "Remove and destroy infected leaves immediately",
            "Ensure proper spacing between plants for airflow",
            "Apply copper-based fungicide or neem oil early morning"
        ],
        "spot": [
            "Remove affected leaves promptly and destroy them",
            "Disinfect pruning tools and hands between plants",
            "Keep foliage dry and water at the base",
            "Apply copper bactericide or neem spray"
        ],
        "rust": [
            "Spray recommended fungicide early in the morning",
            "Avoid excess nitrogen fertilizer",
            "Monitor undersides of leaves daily"
        ],
        "mildew": [
            "Prune infected parts immediately and discard",
            "Ensure adequate sunlight and air circulation",
            "Apply neem oil or sulfur-based spray"
        ],
        "default": [
            "Avoid overhead irrigation — water at soil level",
            "Remove and destroy infected leaves immediately",
            "Ensure proper spacing between plants for airflow",
            "Apply protective neem oil spray"
        ]
    }
}

def get_preventive_steps(disease_name: str, lang: str | None = "english", fallback_steps: list[str] | None = None) -> list[str]:
    l = (lang or "english").lower()
    dn = (disease_name or "").lower()
    mapping = PREVENTIVE_STEPS.get(l, PREVENTIVE_STEPS["english"])

    if "blight" in dn:
        return mapping["blight"]
    if "spot" in dn or "scab" in dn:
        return mapping["spot"]
    if "rust" in dn:
        return mapping["rust"]
    if "mildew" in dn or "mold" in dn:
        return mapping["mildew"]

    if l == "english" and fallback_steps:
        return fallback_steps[:4]
    return mapping["default"]



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
