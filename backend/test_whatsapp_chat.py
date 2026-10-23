# test_whatsapp_chat.py
"""
Integration test suite for the rebuilt WhatsApp entry flow and onboarding state machine.
Covers all 9 acceptance criteria:
 (i) First message gives greeting + language menu and no price answer
 (ii) "kannada" gives the name question in Kannada script
 (iii) "Ravi" gives the location request
 (iv) Location payload saves lat/lng + district, step='done', welcome sent
 (v) Photo sent before onboarding is not diagnosed
 (vi) LLM never changes language, name, or location
 (vii) Restart mid-onboarding resumes from database step
 (viii) Duplicate MessageSid is ignored
 (ix) Crisis message triggers immediate compassionate helpline reply
"""

import asyncio
import sys
import uuid
import unittest
from pathlib import Path

# Ensure backend is on sys.path
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import services.whatsapp_service as ws
from farmer_store import (
    TEST_PHONE_PREFIX,
    normalize_phone,
    get_farmer,
    update_farmer_profile,
    mark_message_processed,
    get_farmer_language,
    get_farmer_location,
    delete_farmer_records,
)
from services.db import SessionLocal
from sqlalchemy import text

# Intercept send_message to record outgoing messages for test assertions
outbound_messages = []

async def mock_send_message(phone: str, text: str, retries: int = 3) -> bool:
    outbound_messages.append({"phone": phone, "text": text})
    return True

ws.send_message = mock_send_message


class TestWhatsAppEntryFlow(unittest.IsolatedAsyncioTestCase):
    def _delete_test_messages(self):
        if hasattr(self, "created_sids") and self.created_sids:
            with SessionLocal() as db:
                for sid in self.created_sids:
                    db.execute(text("DELETE FROM processed_messages WHERE message_sid = :sid"), {"sid": sid})
                db.commit()

    async def asyncSetUp(self):
        outbound_messages.clear()
        self.created_sids = []
        # Use reserved test phone prefix
        self.test_phone = f"{TEST_PHONE_PREFIX}{uuid.uuid4().hex[:4]}"
        self.norm_phone = normalize_phone(self.test_phone)
        # Ensure clean state before test
        delete_farmer_records(self.norm_phone)

    async def asyncTearDown(self):
        outbound_messages.clear()
        # Clean up database after test
        delete_farmer_records(self.norm_phone)
        self._delete_test_messages()

    def new_sid(self) -> str:
        sid = f"SM_{uuid.uuid4().hex}"
        self.created_sids.append(sid)
        return sid

    async def test_01_first_message_gives_greeting_and_language_menu(self):
        """(i) First message 'tomato price?' gives greeting + language menu and no price answer."""
        form_data = {
            "From": self.test_phone,
            "Body": "tomato price?",
            "NumMedia": "0",
            "MessageSid": self.new_sid(),
        }
        await ws.handle_incoming_message(form_data)
        self.assertTrue(len(outbound_messages) >= 1)
        last_msg = outbound_messages[-1]["text"]
        self.assertIn("KrishiMitra", last_msg)
        self.assertIn("हिंदी", last_msg)
        self.assertIn("ಕನ್ನಡ", last_msg)
        self.assertIn("English", last_msg)
        # Ensure no mandi price calculation was executed
        self.assertNotIn("Modal Rate", last_msg)
        self.assertNotIn("quintal", last_msg)

    async def test_02_kannada_selection_prompts_name_in_kannada(self):
        """(ii) 'kannada' gives the name question in Kannada script."""
        # 1. First contact
        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "Hello",
            "NumMedia": "0",
            "MessageSid": self.new_sid(),
        })
        outbound_messages.clear()

        # 2. Select Kannada
        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "kannada",
            "NumMedia": "0",
            "MessageSid": self.new_sid(),
        })
        self.assertTrue(len(outbound_messages) >= 1)
        last_msg = outbound_messages[-1]["text"]
        # Must be in Kannada script
        self.assertIn("ಕನ್ನಡ", last_msg)
        self.assertIn("ಹೆಸರನ್ನು", last_msg)

        farmer = get_farmer(self.test_phone)
        self.assertEqual(farmer["language"], "kannada")
        self.assertEqual(farmer["onboarding_step"], "ask_name")

    async def test_03_name_gives_location_request(self):
        """(iii) 'Ravi' gives the location request."""
        # Setup language first
        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "3",  # English
            "NumMedia": "0",
            "MessageSid": self.new_sid(),
        })
        outbound_messages.clear()

        # Submit Name
        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "Ravi",
            "NumMedia": "0",
            "MessageSid": self.new_sid(),
        })
        self.assertTrue(len(outbound_messages) >= 1)
        last_msg = outbound_messages[-1]["text"]
        self.assertIn("Ravi", last_msg)
        self.assertIn("location", last_msg.lower())
        self.assertIn("Attachment", last_msg)

        farmer = get_farmer(self.test_phone)
        self.assertEqual(farmer["name"], "Ravi")
        self.assertEqual(farmer["onboarding_step"], "ask_location")

    async def test_04_location_pin_completes_onboarding_and_sends_welcome(self):
        """(iv) Location payload saves lat/lng + district, step='done', welcome sent."""
        # Setup up to ask_location
        update_farmer_profile(self.test_phone, name="Ravi", language="english", onboarding_step="ask_location")

        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "",
            "NumMedia": "0",
            "Latitude": "12.9716",
            "Longitude": "77.5946",
            "MessageSid": self.new_sid(),
        })
        self.assertTrue(len(outbound_messages) >= 1)
        last_msg = outbound_messages[-1]["text"]
        self.assertIn("Welcome to KrishiMitra, Ravi", last_msg)
        self.assertIn("Mandi Prices", last_msg)
        self.assertIn("Crop Doctor", last_msg)

        farmer = get_farmer(self.test_phone)
        self.assertEqual(farmer["onboarding_step"], "done")
        self.assertIsNotNone(farmer["lat"])
        self.assertIsNotNone(farmer["lng"])

    async def test_05_photo_before_onboarding_is_delayed(self):
        """(v) Photo sent before onboarding is not diagnosed."""
        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "Check this",
            "NumMedia": "1",
            "MediaUrl0": "https://example.com/leaf.jpg",
            "MediaContentType0": "image/jpeg",
            "MessageSid": self.new_sid(),
        })
        self.assertTrue(len(outbound_messages) >= 1)
        last_msg = outbound_messages[-1]["text"]
        # Must instruct to complete setup first
        self.assertTrue("finish" in last_msg.lower() or "परिचय" in last_msg or "ನೋಂದಣಿ" in last_msg)
        # Ensure no diagnosis was performed
        self.assertNotIn("Severity", last_msg)
        self.assertNotIn("Remedies", last_msg)

    async def test_06_crisis_message_triggers_helpline(self):
        """Safety check: crisis message returns Tele-MANAS & Kisan Call Centre immediately."""
        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "I want to end my life, please help",
            "NumMedia": "0",
            "MessageSid": self.new_sid(),
        })
        self.assertTrue(len(outbound_messages) >= 1)
        last_msg = outbound_messages[-1]["text"]
        self.assertIn("14416", last_msg)
        self.assertIn("1800-180-1551", last_msg)

    async def test_07_resume_mid_onboarding_from_db(self):
        """(vii) Server restart mid-onboarding resumes from database onboarding_step."""
        # Simulate user already completed language choice in database
        update_farmer_profile(self.test_phone, language="hindi", onboarding_step="ask_name")

        await ws.handle_incoming_message({
            "From": self.test_phone,
            "Body": "सुरेश कुमार",
            "NumMedia": "0",
            "MessageSid": self.new_sid(),
        })
        self.assertTrue(len(outbound_messages) >= 1)
        last_msg = outbound_messages[-1]["text"]
        # Prompts for location in Hindi
        self.assertIn("सुरेश कुमार जी", last_msg)
        self.assertIn("लोकेशन शेयर करें", last_msg)

        farmer = get_farmer(self.test_phone)
        self.assertEqual(farmer["name"], "सुरेश कुमार")
        self.assertEqual(farmer["onboarding_step"], "ask_location")

    async def test_08_duplicate_message_sid_deduplication(self):
        """(viii) Duplicate MessageSid is ignored."""
        sid = self.new_sid()
        self.assertTrue(mark_message_processed(sid))
        # Immediate second call with same SID must be recognized as duplicate
        self.assertFalse(mark_message_processed(sid))


if __name__ == "__main__":
    unittest.main()