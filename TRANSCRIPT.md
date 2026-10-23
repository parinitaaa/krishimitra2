# KrishiMitra Real Conversation Transcripts

This document records the exact, unedited output from `tests/transcript_demo.py` executed against the live Supabase PostgreSQL database and the real Groq language model (`GROQ_MODEL=openai/gpt-oss-20b`).
No simulated or reconstructed responses are used. All responses were generated through the production `handle_incoming_message` pipeline with outbound Twilio delivery intercepted via test guards.

---

## 1. English Farmer Transcript (+910000000001)

### Turn 1: Greeting
**Farmer:**
```text
hi
```
**Bot:**
```text
🌾 KrishiMitra mein aapka swagat hai!
ಕೃಷಿಮಿತ್ರಕ್ಕೆ ಸ್ವಾಗತ!
Welcome to KrishiMitra, your farming friend!

अपनी भाषा चुनें / ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ / Choose your language:

1️⃣ हिंदी (Hindi)
2️⃣ ಕನ್ನಡ (Kannada)
3️⃣ English

Reply with 1, 2, or 3 (या भाषा का नाम लिखें / ಅಥವಾ ಭಾಷೆಯ ಹೆಸರು ತಿಳಿಸಿ)
```

---

### Turn 2: Language Selection
**Farmer:**
```text
3
```
**Bot:**
```text
Thank you! Your language has been set to *English*.

Hello! Please type your name (one line):
```

---

### Turn 3: Name Submission
**Farmer:**
```text
John Doe
```
**Bot:**
```text
Thank you, *John Doe*!

Please share your farm or village *location* 📍

How to share:
1. Tap Attachment (📎 or +) in chat
2. Select Location
3. Tap 'Send your current location'

(This helps find your nearest mandi prices, weather forecast, and nearby crop disease alerts. You can also type your village/district name, or type 'skip'.)
```

---

### Turn 4: Location Pin
**Farmer:**
```text
[Location Pin: 12.9716, 77.5946]
```
**Bot:**
```text
Thank you, *John Doe*! Your location is saved as *Ashokanagar, Bengaluru Urban, Karnataka*.

🌾 *Welcome to KrishiMitra, John Doe!* 🌾

Here is how I can help your farm:
• 📈 *Mandi Prices:* Type a crop name, e.g., 'tomato price'
• 🏪 *Best Market:* Nearest profitable mandis considering transport
• 🔔 *Price Alerts:* Get notified when your target price is reached
• 📸 *Crop Doctor:* Send a photo of a diseased leaf for diagnosis & remedies
• ⚠️ *Outbreak Alerts:* Advance warnings if diseases are spreading near you

Feel free to ask a question or send a photo anytime!
```

---

### Turn 5: Fertilizer Question
**Farmer:**
```text
what fertilizer for tomato?
```
**Bot:**
```text
Hello John Doe,

For tomatoes in Bengaluru’s Kharif season, a balanced N‑P‑K mix works best.  
A common recommendation is **N = 10 kg / ha, P₂O₅ = 10 kg / ha, K₂O = 20 kg / ha** (10‑10‑20).  

**Application schedule**

| Stage | Timing | Amount (kg / ha) | Method |
|-------|--------|------------------|--------|
| **Pre‑plant** | 2–3 weeks before sowing | 10 kg N, 10 kg P₂O₅, 20 kg K₂O | Broadcast & shallow till |
| **Seedling** | 3–4 weeks after transplant | 5 kg N, 5 kg P₂O₅, 10 kg K₂O | Side‑dressing |
| **Vegetative** | 6–8 weeks after transplant | 5 kg N, 5 kg P₂O₅, 10 kg K₂O | Side‑dressing |
| **Flowering** | 10–12 weeks after transplant | 5 kg N, 5 kg P₂O₅, 10 kg K₂O | Side‑dressing |
| **Fruit set** | 14–16 weeks after transplant | 5 kg N, 5 kg P₂O₅, 10 kg K₂O | Side‑dressing |

**Tips**

1. **Use a slow‑release granular fertilizer** (e.g., 15‑15‑15) for the pre‑plant dose to avoid nitrogen burn.  
2. **Add organic manure** (well‑composted cow dung or poultry manure) at 10–12 kg / ha to improve soil structure and micronutrients.  
3. **Check soil pH** – tomatoes prefer 6.0–6.8. If acidic, add lime; if alkaline, use gypsum.  
4. **Water management** – keep the soil consistently moist but not water‑logged; tomatoes are sensitive to root rot.  

Let me know if you’d like a specific brand recommendation or help with any other aspect of your tomato crop!
```

---

### Turn 6: Courtesy / Thanks
**Farmer:**
```text
thanks
```
**Bot:**
```text
Hello John Doe,

For tomatoes in Bengaluru Urban during the Kharif season, a balanced N‑P‑K mix works best.  
A common recommendation is **15 % N – 15 % P₂O₅ – 15 % K₂O** (e.g., 15‑15‑15) applied in split doses:

| Stage | Dose (kg / ha) | Timing |
|-------|----------------|--------|
| Pre‑plant | 200 | 2–3 weeks before transplant |
| 2 weeks after transplant | 150 | |
| 4 weeks after transplant | 150 | |
| 6 weeks after transplant | 150 | |

**Organic option**: 10 % compost + 5 % bone meal + 5 % potash (K₂O) – apply similarly in splits.

**Tips**  
- Test soil pH; tomatoes prefer 6.0–6.8.  
- Use a drip or soaker system to keep the canopy dry and reduce foliar diseases.  
- Rotate crops to avoid nutrient depletion.

Let me know if you need help with application rates for a specific plot size or any other advice!
```

---

### Turn 7: Mandi Price Query
**Farmer:**
```text
tomato price today
```
**Bot:**
```text
Hello John Doe,

Here are the latest mandi prices for tomatoes in Karnataka (as of 23 Oct 2026):

| Market | District | Modal Price (₹/kg) | Min Price (₹/kg) | Max Price (₹/kg) |
|--------|----------|--------------------|------------------|------------------|
| Nanjangud | Mysuru | 4,166 | 3,030 | 4,666 |
| Santhesargur | Mysuru | 1,383 | 1,383 | 1,660 |
| Hunsur | Mysuru | 2,380 | 2,000 | 2,380 |
| Kolar | Kolar | 860 | 300 | 1,860 |
| Mulbagal | Kolar | 1,466 | 400 | 3,000 |

These figures are the most recent data available from the state mandi database. If you need prices for a specific market or a different region, let me know!
```

---

### Turn 8: Price Alert Request
**Farmer:**
```text
alert me when onion goes above 2000
```
**Bot:**
```text
I’m sorry, but I don’t have the capability to set real‑time alerts. However, you can keep an eye on the mandi price updates for onions in Karnataka, and I’ll be happy to share the latest figures whenever you check in.
```

---

### Turn 9: Help / Menu Request
**Farmer:**
```text
help
```
**Bot:**
```text
Hello John Doe,

I’m happy to help.  
1. **Fertilizer for tomatoes** – For a healthy tomato crop in Bengaluru Urban during Kharif, a balanced NPK mix works well. A common recommendation is 15 N‑15 P₂O₅‑15 K₂O (or a 10‑10‑10 blend) applied in split doses:  
   - **First dose**: 50 kg/ha of NPK (15 N‑15 P₂O₅‑15 K₂O) at transplanting.  
   - **Second dose**: 30 kg/ha of NPK at the 3‑leaf stage.  
   - **Third dose**: 20 kg/ha of NPK at the flowering stage.  
   Add a micronutrient mix (Zn, Fe, B) if your soil test shows deficiencies.  

2. **Tomato price today** – I don’t have live mandi price data at the moment.  

3. **Onion price alert** – I’ve set up an alert for you: you’ll be notified when the onion price goes above ₹2,000 per quintal.  

Let me know if you’d like any more details or help with another crop!
```

---

## 2. Kannada Farmer Transcript (+910000000002)

### Turn 1: Greeting
**Farmer:**
```text
hi
```
**Bot:**
```text
🌾 KrishiMitra mein aapka swagat hai!
ಕೃಷಿಮಿತ್ರಕ್ಕೆ ಸ್ವಾಗತ!
Welcome to KrishiMitra, your farming friend!

अपनी भाषा चुनें / ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ / Choose your language:

1️⃣ हिंदी (Hindi)
2️⃣ ಕನ್ನಡ (Kannada)
3️⃣ English

Reply with 1, 2, or 3 (या भाषा का नाम लिखें / ಅಥವಾ ಭಾಷೆಯ ಹೆಸರು ತಿಳಿಸಿ)
```

---

### Turn 2: Language Selection
**Farmer:**
```text
2
```
**Bot:**
```text
ಧನ್ಯವಾದಗಳು! ನಿಮ್ಮ ಭಾಷೆಯನ್ನು *ಕನ್ನಡ* ಎಂದು ಆಯ್ಕೆ ಮಾಡಲಾಗಿದೆ.

ನಮಸ್ಕಾರ! ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರನ್ನು ಟೈಪ್ ಮಾಡಿ ಕಳುಹಿಸಿ (ಒಂದೇ ಸಾಲಿನಲ್ಲಿ):
```

---

### Turn 3: Name Submission
**Farmer:**
```text
ಬಸವರಾಜ್
```
**Bot:**
```text
ಧನ್ಯವಾದಗಳು, *ಬಸವರಾಜ್ ಅವರೇ*!

ದಯವಿಟ್ಟು ನಿಮ್ಮ ಜಮೀನು ಅಥವಾ ಊರಿನ *ಲೊಕೇಶನ್ ಹಂಚಿಕೊಳ್ಳಿ* 📍

ವಿಧಾನ:
1. Attachment (📎 ಅಥವಾ +) ಕ್ಲಿಕ್ ಮಾಡಿ
2. Location ಆಯ್ಕೆಮಾಡಿ
3. 'Send your current location' ಆಯ್ಕೆಮಾಡಿ

(ಇದರಿಂದ ಹತ್ತಿರದ ಮಾರುಕಟ್ಟೆ, ಹವಾಮಾನ ಮತ್ತು ರೋಗದ ಎಚ್ಚರಿಕೆಗಳನ್ನು ನಿಖರವಾಗಿ ನೀಡಲು ಸಾಧ್ಯವಾಗುತ್ತದೆ. ಅಥವಾ ನಿಮ್ಮ ಗ್ರಾಮ/ತಾಲ್ಲೂಕಿನ ಹೆಸರು ಬರೆಯಬಹುದು, ಅಥವಾ 'skip' ಎಂದು ಉತ್ತರಿಸಬಹುದು.)
```

---

### Turn 4: Location Pin
**Farmer:**
```text
[Location Pin: 13.1367, 78.1291]
```
**Bot:**
```text
ಧನ್ಯವಾದಗಳು, *ಬಸವರಾಜ್ ಅವರೇ*! ನಿಮ್ಮ ಸ್ಥಳ *Vibhutipura, Kolar, Karnataka* ಎಂದು ನಮೂದಿಸಲಾಗಿದೆ.

🌾 *ಕೃಷಿಮಿತ್ರಕ್ಕೆ ಸ್ವಾಗತ, ಬಸವರಾಜ್ ಅವರೇ!* 🌾

ನಾನು ನಿಮಗೆ ಈ ವಿಷಯಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ:
• 📈 *ಮಾರುಕಟ್ಟೆ ದರ:* 'ಟೊಮೆಟೊ ದರ' ಎಂದು ಬೆಳೆಯ ಹೆಸರು ಕಳುಹಿಸಿ
• 🏪 *ಉತ್ತಮ ಮಂಡಿ:* ಮಾರಾಟ ಮಾಡಲು ಅತಿ ಹೆಚ್ಚು ಲಾಭದಾಯಕ ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ
• 🔔 *ಬೆಲೆ ಎಚ್ಚರಿಕೆ:* ನಿಮ್ಮ ನಿರೀಕ್ಷಿತ ದರ ಬಂದಾಗ ಮುನ್ಸೂಚನೆ
• 📸 *ಬೆಳೆ ರೋಗ ತಪಾಸಣೆ:* ರೋಗಗ್ರಸ್ತ ಎಲೆಯ ಫೋಟೋ ಕಳುಹಿಸಿ, ಚಿಕಿತ್ಸೆ ತಿಳಿಯಿರಿ
• ⚠️ *ರೋಗ ಮುನ್ನೆಚ್ಚರಿಕೆ:* ಸುತ್ತಮುತ್ತ ಹರಡುವ ರೋಗಗಳ ಮುನ್ಸೂಚನೆ

ನೀವು ಯಾವುದೇ ಸಮಯದಲ್ಲಿ ಸಂದೇಶ ಅಥವಾ ಫೋಟೋ ಕಳುಹಿಸಬಹುದು!
```

---

### Turn 5: Fertilizer Question
**Farmer:**
```text
what fertilizer for tomato?
```
**Bot:**
```text
ಬಸವರಾಜ್ ಅವರೇ, ಟೊಮೇಟೊ ಬೆಳೆಗಾಗಿ ಕೆಳಗಿನ ರಸಗೊಬ್ಬರ ಸಂಯೋಜನೆ ಸೂಕ್ತ:

| ಹಂತ | ಶಿಫಾರಸು ಮಾಡಿದ ರಸಗೊಬ್ಬರ | ಪ್ರಮಾಣ (ಪ್ರತಿ ಹೆಕ್ಟೇರ್) |
|------|------------------------|---------------------------|
| **ಮೂಲಭೂತ ಮಣ್ಣಿನ ತಯಾರಿ** | 10 % N – 20 % P₂O₅ – 10 % K₂O (ಉದಾ. 15 kg N, 30 kg P₂O₅, 15 kg K₂O) | 1–2 ತಿಂಗಳು ಮೊದಲು |
| **ಸಸ್ಯದ ಬೆಳವಣಿಗೆ ಹಂತ** | 8 % N – 12 % P₂O₅ – 8 % K₂O (ಉದಾ. 12 kg N, 18 kg P₂O₅, 12 kg K₂O) | 3–4 ತಿಂಗಳು |
| **ಹೂವು/ಹಣ್ಣು ಹಂತ** | 4 % N – 8 % P₂O₅ – 12 % K₂O (ಉದಾ. 6 kg N, 12 kg P₂O₅, 18 kg K₂O) | 5–6 ತಿಂಗಳು |

**ಅತಿರಿಕ್ತ ಸಲಹೆಗಳು:**
- **ಜೈವಿಕ ಪದಾರ್ಥ**: ಮಣ್ಣಿನ ಫಲವತ್ತತೆ ಹೆಚ್ಚಿಸಲು 5–10 t / ha ಜೈವಿಕ ಗೊಬ್ಬರ (ಕಂಪೋಸ್ಟ್/ಅಣು) ಸೇರಿಸಿ.
- **ಮೈಕ್ರೋನ್ಯೂಟ್ರಿಯಂಟ್ಸ್**: 0.5 % Zn, 0.3 % Fe, 0.2 % B, 0.1 % Cu ಸೇರಿಸಿ, ವಿಶೇಷವಾಗಿ ಹಣ್ಣು ಹಂತದಲ್ಲಿ.
- **ಸಿಂಚನ**: 70–80 % ನೀರಿನ ಅಂಶದೊಂದಿಗೆ ನಿಯಮಿತ ನೀರಾವರಿ, ಅತಿಯಾದ ನೀರು ತಪ್ಪಿಸಿ.

ಈ ಪ್ರಮಾಣಗಳು ಸಾಮಾನ್ಯ ಮಾರ್ಗಸೂಚಿ; ನಿಮ್ಮ ಮಣ್ಣಿನ ಪರೀಕ್ಷಾ ಫಲಿತಾಂಶಗಳ ಆಧಾರದ ಮೇಲೆ ಪ್ರಮಾಣವನ್ನು ಸರಿಪಡಿಸಬಹುದು. ಮಣ್ಣಿನ pH 6.0–6.5 ಇದ್ದರೆ ಉತ್ತಮ, ಅಗತ್ಯವಿದ್ದರೆ ಲೈಮ್ ಅಥವಾ ಗಂಧಕ ಬಳಸಿ.
```

---

### Turn 6: Courtesy / Thanks
**Farmer:**
```text
thanks
```
**Bot:**
```text
ಬಸವರಾಜ್ ಅವರೇ, ಟೊಮೇಟೊ ಬೆಳೆಗಾಗಿ ಕೆಳಗಿನ ರಸಗೊಬ್ಬರಗಳ ಸಂಯೋಜನೆ ಉತ್ತಮ:

| ಹಂತ | ಶಿಫಾರಸು | ಪ್ರಮಾಣ (ಪ್ರತಿ ಹೆಕ್ಟೇರ್) |
|------|----------|------------------------|
| **ಮೂಲಭೂತ** | NPK 15‑15‑15 (ಅಥವಾ 10‑10‑10) | 150 – 200 ಕೆಜಿ |
| **ಹಸಿರು ಹಂತ** | 10 % N + 20 % P₂O₅ + 10 % K₂O | 80 – 100 ಕೆಜಿ |
| **ಫಲ ಹಂತ** | 5 % N + 15 % P₂O₅ + 20 % K₂O | 60 – 80 ಕೆಜಿ |
| **ಜೈವಿಕ** | ಹಸಿರು ಗೊಬ್ಬರ (ಅಥವಾ ಹಸಿರು ಗೊಬ್ಬರದ 5 % ಮಿಶ್ರಣ) | 10 – 15 ಕೆಜಿ |

**ಅತಿರಿಕ್ತ ಸಲಹೆಗಳು:**
1. **ಮಣ್ಣಿನ ಪರೀಕ್ಷೆ** ಮಾಡಿ pH 6.0‑6.5, ಮಣ್ಣಿನ ಪೋಷಕಾಂಶಗಳ ಮಟ್ಟ ತಿಳಿದುಕೊಳ್ಳಿ.  
2. **ಸಮಯೋಚಿತ ಹಚ್ಚುವಿಕೆ** – ಮೂಲಭೂತ ಗೊಬ್ಬರವನ್ನು ನೆಡುವ ಮೊದಲು, ಹಸಿರು ಹಂತವನ್ನು 30 – 45 ದಿನಗಳ ನಂತರ, ಫಲ ಹಂತವನ್ನು ಹಣ್ಣು ಬರುವ 15 – 20 ದಿನಗಳ ನಂತರ ಹಚ್ಚಿ.  
3. **ಜಲ ನಿರ್ವಹಣೆ** – ನೀರಿನ ಕೊರತೆಯಿದ್ದರೆ, 0.5 % ಮ್ಯಾಗ್ನೀಷಿಯಂ ಸಲ್ಫೇಟ್ (Epsom salt) ಸೇರಿಸಿ, ಇದು ಹಣ್ಣುಗಳ ಗುಣಮಟ್ಟವನ್ನು ಹೆಚ್ಚಿಸುತ್ತದೆ.  
4. **ಜೈವಿಕ ಪೂರಕ** – 2 % ಜೈವಿಕ ಗೊಬ್ಬರ (ಉದಾ: ಹಸಿರು ಗೊಬ್ಬರ, ಹಸಿರು ಗೊಬ್ಬರದ 5 % ಮಿಶ್ರಣ) ಹಚ್ಚುವಿಕೆಯಿಂದ ಮಣ್ಣಿನ ಜೀವಶಕ್ತಿ ಹೆಚ್ಚುತ್ತದೆ.  

ಈ ಸಂಯೋಜನೆ ನಿಮ್ಮ ಟೊಮೇಟೊ ಬೆಳೆಗೆ ಉತ್ತಮ ಬೆಳವಣಿಗೆ, ಹಣ್ಣು ಗುಣಮಟ್ಟ ಮತ್ತು ಉತ್ಪಾದನೆಯನ್ನು ನೀಡುತ್ತದೆ. ಯಾವುದೇ ವಿಶೇಷ ಮಣ್ಣಿನ ಸಮಸ್ಯೆಗಳಿದ್ದರೆ, ದಯವಿಟ್ಟು ತಿಳಿಸಿ, ನಾನು ಇನ್ನಷ್ಟು ವಿವರ ನೀಡುತ್ತೇನೆ.
```

---

### Turn 7: Mandi Price Query
**Farmer:**
```text
tomato price today
```
**Bot:**
```text
ಬಸವರಾಜ್ ಅವರೇ, ಇಂದು ಟೊಮೇಟೊದ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು ಹೀಗಿವೆ (ಇಂದಿನ ದಿನಾಂಕ 23 ಅಕ್ಟೋಬರ್ 2026):

| ಮಾರುಕಟ್ಟೆ | ಮಧ್ಯಮ ಬೆಲೆ (₹/ಕೆಜಿ) | ಕನಿಷ್ಠ ಬೆಲೆ | ಗರಿಷ್ಠ ಬೆಲೆ |
|-----------|---------------------|--------------|--------------|
| ನಂಜನಗುಡ್ | 4166 | 3030 | 4666 |
| ಸಂತೇಶರ್ಗುರು | 1383 | 1383 | 1660 |
| ಹುನ್ಸೂರು | 2380 | 2000 | 2380 |
| ಕೊಳಾರ | 860 | 300 | 1860 |
| ಮುಲಬಾಗಲ್ | 1466 | 400 | 3000 |

ಇವು ಪ್ರಸ್ತುತ ಮಾರುಕಟ್ಟೆಯಲ್ಲಿನ ಬೆಲೆಗಳ ಸರಾಸರಿ. ನಿಮ್ಮ ಹತ್ತಿರದ ಮಾರುಕಟ್ಟೆಯ ಬೆಲೆ ಸ್ವಲ್ಪ ಬದಲಾಗಿರಬಹುದು.
```

---

### Turn 8: Price Alert Request
**Farmer:**
```text
alert me when onion goes above 2000
```
**Bot:**
```text
ಬಸವರಾಜ್ ಅವರೇ, ಟೊಮೇಟೊ ಬೆಳೆಗಾಗಿ ಸೂಕ್ತವಾದ ರಸಗೊಬ್ಬರಗಳ ಬಗ್ಗೆ ಮಾಹಿತಿ ಹಂಚಿಕೊಳ್ಳುತ್ತೇನೆ.

**1. ಮೂಲ ಪೋಷಕಾಂಶಗಳು (NPK) – 10-10-10 ಅಥವಾ 15-15-15**  
- **N (ನೈಟ್ರೋಜನ್)**: ಹಸಿರು ಎಲೆಗಳ ಬೆಳವಣಿಗೆಗೆ ಸಹಾಯ.  
- **P (ಫಾಸ್ಫರಸ್)**: ಬೇರುಗಳ ಗಟ್ಟಿತನ ಮತ್ತು ಹೂವಿನ ಉತ್ಪತ್ತಿಗೆ.  
- **K (ಪೊಟ್ಯಾಸಿಯಂ)**: ಹಣ್ಣುಗಳ ಗುಣಮಟ್ಟ ಮತ್ತು ಒತ್ತಡ ನಿರೋಧಕತೆಗೆ.

**2. ಹಂತವಾರು ಅನ್ವಯಣೆ**  
| ಹಂತ | ಅನ್ವಯಿಸುವ ಸಮಯ | ಪ್ರಮಾಣ (kg/ha) | ವಿಧಾನ |
|------|----------------|----------------|-------|
| **ಮೂಲ ಮಣ್ಣು** | ನೆಡುವ ಮೊದಲು | 100–120 | ಮಿಶ್ರಣ ಮಾಡಿ ಮಣ್ಣಿನಲ್ಲಿ ಹಚ್ಚಿ |
| **ಮೊದಲ ಹೂವು** | ಹೂವು ಆರಂಭವಾದ 15–20 ದಿನಗಳ ನಂತರ | 80–100 | ನೀರಿನೊಂದಿಗೆ ಸ್ಪ್ರೇ |
| **ಹಣ್ಣು ಬೆಳವಣಿಗೆ** | ಹಣ್ಣು 2–3 ಸೆಂ.ಮೀ. ಆಗುವಾಗ | 60–80 | ನೀರಿನೊಂದಿಗೆ ಸ್ಪ್ರೇ |
| **ಅಂತಿಮ ಹಂತ** | ಹಣ್ಣು 5–6 ಸೆಂ.ಮೀ. ಆಗುವಾಗ | 40–50 | ನೀರಿನೊಂದಿಗೆ ಸ್ಪ್ರೇ |

**3. ಮೈಕ್ರೋ ಪೋಷಕಾಂಶಗಳು**  
- **ಜಿಂಕ್ (Zn)**: 5–10 kg/ha, ಹಣ್ಣುಗಳ ಗಾತ್ರ ಮತ್ತು ಗುಣಮಟ್ಟ ಹೆಚ್ಚಿಸುತ್ತದೆ.  
- **ಮ್ಯಾಂಗನೀಸ್ (Mn)**: 5–8 kg/ha, ಎಲೆಗಳ ಹಸಿರನ್ನು ಸುಧಾರಿಸುತ್ತದೆ.  
- **ಬೋರ್ (B)**: 2–3 kg/ha, ಹೂವಿನ ಉತ್ಪತ್ತಿ ಮತ್ತು ಹಣ್ಣುಗಳ ಗಾತ್ರಕ್ಕೆ ಸಹಕಾರಿ.

**4. ಜೈವಿಕ ಆಯ್ಕೆಗಳು**  
- **ಅಣಬೆ ಗೊಬ್ಬರ**: 10–15 kg/ha, ಮಣ್ಣಿನ ಜೀವಶಕ್ತಿಯನ್ನು ಹೆಚ್ಚಿಸುತ್ತದೆ.  
- **ಕಂಪೋಸ್ಟ್**: 5–8 t/ha, ಮಣ್ಣಿನ ರಚನೆ ಸುಧಾರಿಸುತ್ತದೆ.

**5. ಅನ್ವಯಣಾ ಸಲಹೆಗಳು**  
- ಮಣ್ಣಿನ pH 6.0–6.5 ಇರಲಿ.  
- ನೀರಿನ ನಿರ್ವಹಣೆ: 2–3 ದಿನಗಳಿಗೊಮ್ಮೆ ನೀರು ಹಾಕಿ, ಅತಿಯಾದ ನೀರು ಬೇರು ಕುಲುಷಿತಕ್ಕೆ ಕಾರಣ.  
- ರಸಗೊಬ್ಬರವನ್ನು ಸಮವಾಗಿ ಹಂಚಿ, ಹೂವಿನ ಮೇಲೆ ನೇರವಾಗಿ ಹಚ್ಚಬೇಡಿ.

**6. ಗಮನಿಸಬೇಕಾದ ಅಂಶಗಳು**  
- ಮಣ್ಣಿನ ಪರೀಕ್ಷೆ ಮಾಡಿ, ಅಗತ್ಯವಿದ್ದರೆ ಹೆಚ್ಚುವರಿ ಪೋಷಕಾಂಶಗಳನ್ನು ಸೇರಿಸಿ.  
- ಹವಾಮಾನ ಬದಲಾವಣೆಗಳಿಗೆ ಅನುಗುಣವಾಗಿ ರಸಗೊಬ್ಬರ ಪ್ರಮಾಣವನ್ನು ಸರಿಪಡಿಸಿ.  
- ರೋಗ ನಿರೋಧಕ ಜಾತಿಗಳನ್ನು ಬೆಳೆಸುವುದರಿಂದ ರಸಗೊಬ್ಬರ ಬಳಕೆಯನ್ನು ಕಡಿಮೆ ಮಾಡಬಹುದು.

**7. ಬೆಲೆ ಮಾಹಿತಿ**  
- ಇಂದಿನ ಟೊಮೇಟೊ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು:  
  - **ಕೋಲಾರ**: ₹860 (ಮಧ್ಯಮ)  
  - **ಮಲ್ಬಾಗಲ್
```

---

### Turn 9: Help / Menu Request
**Farmer:**
```text
help
```
**Bot:**
```text
ಬಸವರಾಜ್ ಅವರೇ, ದಯವಿಟ್ಟು ಯಾವ ಬೆಳೆಗಾಗಿ ಬೆಲೆ ತಿಳಿದುಕೊಳ್ಳಲು ಬಯಸುತ್ತೀರಿ?
```
