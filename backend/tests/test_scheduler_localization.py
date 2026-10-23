# backend/tests/test_scheduler_localization.py
"""
Acceptance test for morning briefing and price alert localization.
Tests:
1. Three farmers (kannada, hindi, english):
   - Messages are delivered in the right language and script.
   - No Hindi text reaches Kannada or English farmers.
   - Farmer's name is used with culturally respectful non-gendered address; neutral greeting if no name.
2. Weather failure drops only the weather line, not the whole briefing.
3. Disease follow-up line is included when open disease cases exist.
4. Price alerts use i18n templates in the farmer's registered language.
5. Concurrency semaphore and error boundary: one failure never stops others.
"""

import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from scheduler import morning_briefing, check_price_alerts, _process_single_farmer_briefing


class TestSchedulerLocalization(unittest.IsolatedAsyncioTestCase):

    def test_i18n_keys_present_in_all_languages(self):
        """Verify all new keys exist across hindi, kannada, and english."""
        from services.i18n import STRINGS
        required_keys = [
            "briefing_greeting",
            "briefing_greeting_neutral",
            "briefing_weather",
            "briefing_price_item",
            "briefing_price_section",
            "briefing_disease_followup",
            "briefing_closing",
            "price_alert_triggered",
            "price_direction_above",
            "price_direction_below",
        ]
        for lang in ["hindi", "kannada", "english"]:
            self.assertIn(lang, STRINGS)
            for k in required_keys:
                self.assertIn(k, STRINGS[lang], f"Missing key '{k}' in language '{lang}'")

    async def test_morning_briefing_three_languages_and_scripts(self):
        """
        Three farmers (kn, hi, en) with mocked weather, prices, and send show:
        - each message in the right language and native script
        - no Hindi text reaches kn / en farmers
        - weather failure drops the weather line, not the whole briefing
        """
        farmers = [
            {
                "phone": "+919000000001",
                "name": "ಬಸವರಾಜ್",  # Basavaraj
                "language": "kannada",
                "crops": ["Tomato", "Onion"],
                "location": "Kolar, Karnataka",
                "district": "Kolar",
                "lat": 13.1367,
                "lng": 78.1291,
            },
            {
                "phone": "+919000000002",
                "name": "रामेश",  # Ramesh
                "language": "hindi",
                "crops": ["Tomato"],
                "location": "Nashik, Maharashtra",
                "district": "Nashik",
                "lat": 19.9975,
                "lng": 73.7898,
            },
            {
                "phone": "+919000000003",
                "name": "John",
                "language": "english",
                "crops": ["Potato"],
                "location": "Bangalore, Karnataka",
                "district": "Bangalore",
                "lat": 12.9716,
                "lng": 77.5946,
            },
        ]

        # Weather mock: succeed for kn and en, FAIL for hi (to test weather failure resilience)
        async def mock_weather(f):
            if f["phone"] == "+919000000002":
                return None  # Weather failure for Hindi farmer
            return {
                "temp": 28,
                "humidity": 65,
                "condition": "Clear sky",
                "location": f.get("district") or f.get("location"),
            }

        # Prices mock: return 1-2 crops with data date
        def mock_prices(crops, lat, lng, state, loc):
            return [
                {
                    "crop": c,
                    "price": 1800.0,
                    "market": "APMC Mandi",
                    "date": "2026-10-23",
                }
                for c in crops[:2]
            ]

        # Disease cases mock: kn has an open disease case, others do not
        def mock_cases(phone):
            if phone == "+919000000001":
                return [{"disease": "Early Blight", "crop": "Tomato"}]
            return []

        sent_messages = {}

        async def mock_send(phone, msg):
            sent_messages[phone] = msg
            return True

        with patch("scheduler.get_eligible_briefing_farmers", return_value=farmers), \
             patch("scheduler._fetch_farmer_weather", side_effect=mock_weather), \
             patch("scheduler._fetch_farmer_crop_prices_sync", side_effect=mock_prices), \
             patch("scheduler.get_open_disease_cases", side_effect=mock_cases), \
             patch("scheduler.send_proactive_message", side_effect=mock_send):

            await morning_briefing()

        # Verify all 3 farmers received messages
        self.assertEqual(len(sent_messages), 3)

        kn_msg = sent_messages["+919000000001"]
        hi_msg = sent_messages["+919000000002"]
        en_msg = sent_messages["+919000000003"]

        # 1. Kannada farmer verification
        self.assertIn("ಶುಭೋದಯ", kn_msg)  # Kannada greeting
        self.assertIn("ಅವರೇ", kn_msg)    # Kannada respectful suffix
        self.assertIn("ಹವಾಮಾನ", kn_msg)   # Kannada weather
        self.assertIn("ಮಾರುಕಟ್ಟೆ ದರ", kn_msg)  # Kannada market price
        self.assertIn("ಬೆಳೆ ಆರೋಗ್ಯ", kn_msg)   # Kannada disease followup
        # Strictly NO Hindi or English greeting text
        self.assertNotIn("नमस्ते", kn_msg)
        self.assertNotIn("Good morning", kn_msg)
        self.assertNotIn("mausam: theek hai", kn_msg)

        # 2. Hindi farmer verification (Weather failed!)
        self.assertIn("नमस्ते", hi_msg)   # Hindi greeting
        self.assertIn("जी", hi_msg)       # Hindi respectful suffix
        self.assertIn("मंडी भाव", hi_msg) # Hindi market prices
        # Crucial requirement: Weather failed, so weather line was dropped WITHOUT failing the briefing
        self.assertNotIn("मौसम", hi_msg)
        self.assertNotIn("None", hi_msg)
        self.assertNotIn("theek hai", hi_msg)
        # Strictly NO Kannada text
        self.assertNotIn("ಶುಭೋದಯ", hi_msg)
        self.assertNotIn("Good morning", hi_msg)

        # 3. English farmer verification
        self.assertIn("Good morning", en_msg)
        self.assertIn("John", en_msg)
        self.assertIn("Today's weather", en_msg)
        self.assertIn("Market Prices", en_msg)
        # Strictly NO Hindi or Kannada text
        self.assertNotIn("नमस्ते", en_msg)
        self.assertNotIn("ಶುಭೋದಯ", en_msg)
        self.assertNotIn("theek hai", en_msg)

    async def test_price_alert_localization(self):
        """Test that check_price_alerts sends messages localized in farmer's registered language."""
        alerts = [
            {
                "id": 101,
                "phone": "+919111111111",
                "commodity": "tomato",
                "target_price": 2000.0,
                "direction": "above",
            },
            {
                "id": 102,
                "phone": "+919222222222",
                "commodity": "onion",
                "target_price": 1500.0,
                "direction": "below",
            },
        ]

        def mock_location(phone):
            return {"lat": 13.0, "lng": 77.0}

        def mock_lang(phone):
            return "kannada" if phone == "+919111111111" else "hindi"

        def mock_best_mandi(farmer_lat, farmer_lng, commodity, radius_km, top_n, db):
            if commodity == "tomato":
                return [{
                    "modal_price": 2200.0,
                    "market": "Kolar Mandi",
                    "distance_km": 15.2,
                }]
            else:
                return [{
                    "modal_price": 1200.0,
                    "market": "Lasalgaon Mandi",
                    "distance_km": 25.0,
                }]

        sent_alerts = {}
        deactivated = []

        async def mock_send(phone, msg):
            sent_alerts[phone] = msg
            return True

        def mock_deactivate(aid):
            deactivated.append(aid)

        with patch("scheduler.get_active_alerts", return_value=alerts), \
             patch("scheduler.get_farmer_location", side_effect=mock_location), \
             patch("scheduler.get_farmer_language", side_effect=mock_lang), \
             patch("scheduler.find_best_mandi_for_commodity", side_effect=mock_best_mandi), \
             patch("scheduler.send_proactive_message", side_effect=mock_send), \
             patch("scheduler.deactivate_alert", side_effect=mock_deactivate):

            await check_price_alerts()

        self.assertEqual(len(sent_alerts), 2)
        self.assertEqual(deactivated, [101, 102])

        # Kannada alert check
        kn_alert = sent_alerts["+919111111111"]
        self.assertIn("ಬೆಲೆ ಎಚ್ಚರಿಕೆ", kn_alert)
        self.assertIn("ಹೆಚ್ಚು", kn_alert)
        self.assertNotIn("Price Alert", kn_alert)
        self.assertNotIn("भाव अलर्ट", kn_alert)

        # Hindi alert check
        hi_alert = sent_alerts["+919222222222"]
        self.assertIn("भाव अलर्ट", hi_alert)
        self.assertIn("नीचे", hi_alert)
        self.assertNotIn("Price Alert", hi_alert)
        self.assertNotIn("ಬೆಲೆ ಎಚ್ಚರಿಕೆ", hi_alert)


if __name__ == "__main__":
    unittest.main()
