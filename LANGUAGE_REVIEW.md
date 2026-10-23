# KrishiMitra Language Review (Native Speaker Checklist)

This document catalogs newly added internationalized strings in `services/i18n.py` across **Kannada**, **Hindi**, and **English** for native speaker verification, cultural nuance, and respectful agricultural address.

---

## 1. Morning Briefing Keys

### `briefing_greeting`
- **Context**: Personalized salutation when farmer's name is known.
- **Hindi**: `"नमस्ते {salutation}! 🌾"` *(e.g. नमस्ते सुरेश जी! 🌾)*
- **Kannada**: `"ಶುಭೋದಯ {salutation}! 🌾"` *(e.g. ಶುಭೋದಯ ಸುರೇಶ್ ಅವರೇ! 🌾)*
- **English**: `"Good morning, {salutation}! 🌾"` *(e.g. Good morning, Suresh! 🌾)*

### `briefing_greeting_neutral`
- **Context**: Greeting when farmer has not provided a name.
- **Hindi**: `"नमस्ते! 🌾"`
- **Kannada**: `"ಶುಭೋದಯ! 🌾"`
- **English**: `"Good morning! 🌾"`

### `briefing_weather`
- **Context**: Real local weather line in the morning briefing.
- **Hindi**: `"आज {location} में मौसम: {condition}, तापमान {temp}°C, नमी {humidity}%।"`
- **Kannada**: `"ಇಂದು {location} ಹವಾಮಾನ: {condition}, ತಾಪಮಾನ {temp}°C, ತೇವಾಂಶ {humidity}%."`
- **English**: `"Today's weather in {location}: {condition}, temp {temp}°C, humidity {humidity}%."`

### `briefing_price_item`
- **Context**: Per-crop line item for nearby mandi price.
- **Hindi**: `"• *{crop}*: ₹{price}/क्विंटल ({market}, {date})"`
- **Kannada**: `"• *{crop}*: ₹{price}/ಕ್ವಿಂಟಾಲ್ ({market}, {date})"`
- **English**: `"• *{crop}*: ₹{price}/quintal ({market}, {date})"`

### `briefing_price_section`
- **Context**: Market price section container.
- **Hindi**: `"📊 *मंडी भाव:*\n{items}"`
- **Kannada**: `"📊 *ಮಾರುಕಟ್ಟೆ ದರ:*\n{items}"`
- **English**: `"📊 *Market Prices:*\n{items}"`

### `briefing_disease_followup`
- **Context**: One-line follow-up for an open crop disease case.
- **Hindi**: `"🩺 *फ़सल स्वास्थ्य:* {disease} ({crop}) का कैसा हाल है? अगर समस्या बनी हुई है तो नई फ़ोटो भेजें।"`
- **Kannada**: `"🩺 *ಬೆಳೆ ಆರೋಗ್ಯ:* {disease} ({crop}) ಹೇಗಿದೆ? ಸಮಸ್ಯೆ ಮುಂದುವರಿದರೆ ಹೊಸ ಫೋಟೋ ಕಳುಹಿಸಿ."`
- **English**: `"🩺 *Crop Health:* How is your {crop} ({disease}) doing? If issues persist, please send a fresh photo."`

### `briefing_closing`
- **Context**: Encouraging, non-intrusive closing for the daily briefing.
- **Hindi**: `"कोई भी सवाल हो या फ़ोटो — बेझिझक भेजें!"`
- **Kannada**: `"ಯಾವುದೇ ಪ್ರಶ್ನೆ ಅಥವಾ ಫೋಟೋ ಇದ್ದರೆ ಹಿಂಜರಿಯದೆ ಕಳುಹಿಸಿ!"`
- **English**: `"Feel free to send a photo or message if you have any questions!"`

---

## 2. Price Alert Keys

### `price_alert_triggered`
- **Context**: Proactive alert when nearest mandi price crosses farmer's target.
- **Hindi**:
```text
🔔 *भाव अलर्ट!*

*{crop}* अब ₹*{price}*/क्विंटल है।
मंडी: *{market}* ({distance_km} किमी)
आपका लक्ष्य: ₹{target_price} से {direction}

✅ बेचने का अच्छा अवसर हो सकता है! 🌾
```
- **Kannada**:
```text
🔔 *ಬೆಲೆ ಎಚ್ಚರಿಕೆ!*

*{crop}* ಈಗ ₹*{price}*/ಕ್ವಿಂಟಾಲ್ ಆಗಿದೆ.
ಮಾರುಕಟ್ಟೆ: *{market}* ({distance_km} ಕಿ.ಮೀ)
ನಿಮ್ಮ ಗುರಿ: ₹{target_price} ಗಿಂತ {direction}

✅ ಮಾರಾಟ ಮಾಡಲು ಇದು ಉತ್ತಮ ಸಮಯವಾಗಿರಬಹುದು! 🌾
```
- **English**:
```text
🔔 *Price Alert!*

*{crop}* is now ₹*{price}*/quintal.
Market: *{market}* ({distance_km} km)
Your target was: {direction} ₹{target_price}

✅ Good time to consider selling! 🌾
```

### `price_direction_above`
- **Hindi**: `"ऊपर"`
- **Kannada**: `"ಹೆಚ್ಚು"`
- **English**: `"above"`

### `price_direction_below`
- **Hindi**: `"नीचे"`
- **Kannada**: `"ಕಡಿಮೆ"`
- **English**: `"below"`

---

## Notes for Native Reviewers
1. Respectful honorifics: Uses Kannada `{name} ಅವರೇ` / `ರೈತ ಮಿತ್ರರೇ` and Hindi `{name} जी` / `किसान साथी`. No gendered terms (such as "bhai").
2. Scripts: Hindi is strictly in Devanagari script, Kannada in Kannada script, and English in Latin script.
3. Units: Metric units (`km`, `°C`, `%`, `quintal`/`क्विंटल`/`ಕ್ವಿಂಟಾಲ್`) and standard Rupee symbol `₹`.
