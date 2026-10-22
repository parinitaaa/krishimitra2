import unittest
import uuid
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from farmer_store import (
    normalize_phone,
    get_farmer,
    get_or_create_farmer,
    set_onboarding_step,
    set_state,
    get_state,
    clear_state,
    add_chat,
    get_chat_history,
    mark_message_processed,
    save_price_alert,
    get_active_alerts,
    deactivate_alert,
    create_case,
    update_case,
    due_followup_cases,
    update_farmer_profile,
    get_last_detection,
)


class TestDBConsolidation(unittest.TestCase):
    def setUp(self):
        self.test_phone = f"+9199999{uuid.uuid4().hex[:5]}"
        self.norm_phone = normalize_phone(self.test_phone)

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("whatsapp:+919876543210"), "+919876543210")
        self.assertEqual(normalize_phone("+919876543210"), "+919876543210")
        self.assertEqual(normalize_phone("  +919876543210  "), "+919876543210")

    def test_new_farmer_has_none_defaults(self):
        farmer = get_farmer(self.test_phone)
        self.assertEqual(farmer["phone"], self.norm_phone)
        self.assertIsNone(farmer["name"])
        self.assertIsNone(farmer["location"])
        self.assertIsNone(farmer["soil_type"])
        self.assertIsNone(farmer["language"])
        self.assertEqual(farmer["crops"], [])

    def test_conversation_state_lifecycle(self):
        # Initial is None
        self.assertIsNone(get_state(self.test_phone))

        # Set state
        set_state(self.test_phone, flow="onboarding", step="ask_name", data={"intent": "greeting"})
        st = get_state(self.test_phone)
        self.assertIsNotNone(st)
        self.assertEqual(st["flow"], "onboarding")
        self.assertEqual(st["step"], "ask_name")
        self.assertEqual(st["data"].get("intent"), "greeting")

        # Update state
        set_state(self.test_phone, flow="mandi", step="ask_location", data={"commodity": "tomato"})
        st2 = get_state(self.test_phone)
        self.assertEqual(st2["flow"], "mandi")
        self.assertEqual(st2["step"], "ask_location")
        self.assertEqual(st2["data"].get("commodity"), "tomato")

        # Clear state
        clear_state(self.test_phone)
        self.assertIsNone(get_state(self.test_phone))

    def test_chat_history_and_last_message_at(self):
        add_chat(self.test_phone, "user", "Namaste!")
        add_chat(self.test_phone, "assistant", "Namaste! Kaise madad kar sakta hoon?")

        history = get_chat_history(self.test_phone, limit=5)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Namaste!")
        self.assertEqual(history[1]["role"], "assistant")

    def test_mark_message_processed_deduplication(self):
        test_sid = f"SM{uuid.uuid4().hex}"
        # First attempt -> True
        self.assertTrue(mark_message_processed(test_sid))
        # Second attempt (duplicate webhook) -> False
        self.assertFalse(mark_message_processed(test_sid))

    def test_price_alert_crud(self):
        save_price_alert(self.test_phone, "Tomato", 1500.0, "above", market="Kolar")
        alerts = [a for a in get_active_alerts() if a["phone"] == self.norm_phone]
        self.assertTrue(len(alerts) >= 1)
        target_alert = alerts[0]
        self.assertEqual(target_alert["commodity"], "Tomato")
        self.assertEqual(target_alert["target_price"], 1500.0)
        self.assertEqual(target_alert["market"], "Kolar")

        # Deactivate
        deactivate_alert(target_alert["id"])
        remaining = [a for a in get_active_alerts() if a["id"] == target_alert["id"]]
        self.assertEqual(len(remaining), 0)

    def test_disease_case_and_last_detection(self):
        # get_last_detection returns None when nothing stored
        self.assertIsNone(get_last_detection(self.test_phone))

        # create case
        case_id = create_case(
            phone=self.test_phone,
            crop="Tomato",
            disease="Tomato Early blight leaf",
            confidence=0.88,
            severity_level="Moderate",
            severity_score=6,
            severity_source="estimated",
            lat=13.123,
            lng=77.456,
            spread_modes=["air", "water"],
        )
        self.assertIsNotNone(case_id)

        # update case
        update_case(case_id, status="resolved", severity_score=2)

    def test_update_farmer_profile_extended_fields(self):
        update_farmer_profile(
            self.test_phone,
            name="Ramesh Kumar",
            state="Karnataka",
            district="Bangalore Rural",
            farm_size_acres=3.5,
            water_source="borewell",
            onboarding_step="done",
        )
        farmer = get_farmer(self.test_phone)
        self.assertEqual(farmer["name"], "Ramesh Kumar")
        self.assertEqual(farmer["state"], "Karnataka")
        self.assertEqual(farmer["district"], "Bangalore Rural")
        self.assertEqual(farmer["farm_size_acres"], 3.5)
        self.assertEqual(farmer["water_source"], "borewell")
        self.assertEqual(farmer["onboarding_step"], "done")


if __name__ == "__main__":
    unittest.main()
