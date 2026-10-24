"""
tests/test_acceptance_demo.py

Acceptance tests for TASK DEMO-O:
1. simulate_outbreak.py on a real case from DEMO-D lists the recipients and prints a Kannada message.
2. With two WhatsApp numbers on the allowlist, a photo from phone A produces an alert on phone B.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db import SessionLocal
from farmer_store import create_case, get_farmer, update_farmer_profile, normalize_phone
from outbreak.service import evaluate_case
from services.whatsapp_service import handle_incoming_message

PHONE_A = "+910000000000"  # Reporter
PHONE_B = "+910000000001"  # Recipient (Kannada farmer)

SAMPLE_IMG = str(BACKEND_DIR / "test_images" / "a849a1cf-b06a-4900-bf59-417da8b1d860___GHLB2 Leaf 56.JPG")


def setup_acceptance_farmers():
    """Seed Phone A and Phone B in the database."""
    with SessionLocal() as db:
        db.execute(text("DELETE FROM outbreak_alerts_sent WHERE recipient_phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM disease_cases WHERE phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM conversation_state WHERE phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM chat_history WHERE phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM farmers WHERE phone LIKE '+91000000%'"))

        # Phone A: Tomato farmer in Bengaluru
        db.execute(
            text("""
                INSERT INTO farmers (phone, name, language, lat, lng, location, state, district, crops, onboarding_step, proactive_opt_in)
                VALUES (:phone, 'Kishan A', 'english', 13.0000, 77.5000, 'Bengaluru', 'Karnataka', 'Bengaluru Urban', ARRAY['tomato'], 'done', true)
            """),
            {"phone": PHONE_A},
        )

        # Phone B: Kannada tomato farmer 4.5 km away in Bengaluru
        db.execute(
            text("""
                INSERT INTO farmers (phone, name, language, lat, lng, location, state, district, crops, onboarding_step, proactive_opt_in)
                VALUES (:phone, 'Basavaraj B', 'kannada', 13.0400, 77.5000, 'Yelahanka', 'Karnataka', 'Bengaluru Urban', ARRAY['tomato'], 'done', true)
            """),
            {"phone": PHONE_B},
        )
        db.commit()


def test_acceptance_simulate_outbreak_kannada_message():
    """
    ACCEPTANCE PART 1:
    simulate_outbreak.py on a real case from DEMO-D lists the recipients and prints a Kannada message.
    """
    setup_acceptance_farmers()

    # Create real case as from DEMO-D
    case_id = create_case(
        phone=PHONE_A,
        crop="tomato",
        disease="Early Blight",
        confidence=0.88,
        severity_level="Moderate",
        severity_source="farmer_reported",
        lat=13.0000,
        lng=77.5000,
    )

    cmd = [
        sys.executable,
        str(BACKEND_DIR / "scripts" / "simulate_outbreak.py"),
        "--case",
        str(case_id),
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["OUTBREAK_DEMO_MODE"] = "true"

    proc = subprocess.run(cmd, cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"simulate_outbreak failed: {proc.stderr}"

    output = proc.stdout

    # Verify recipient is listed and Kannada message is printed
    assert "Basavaraj" in output or "Recipient:" in output
    assert "KANNADA" in output
    assert "ರೋಗ ಹರಡುವಿಕೆ ಎಚ್ಚರಿಕೆ" in output or "ಮುನ್ನೆಚ್ಚರಿಕಾ ಕ್ರಮಗಳು" in output
    assert "ಕಿ.ಮೀ" in output


def test_acceptance_photo_flow_triggers_outbreak_to_phone_b():
    """
    ACCEPTANCE PART 2:
    With two WhatsApp numbers on the allowlist (PHONE_A, PHONE_B),
    a photo from Phone A produces an alert on Phone B.
    """
    setup_acceptance_farmers()

    # Set allowlist and demo mode
    os.environ["BROADCAST_ALLOWLIST"] = f"{PHONE_A},{PHONE_B}"
    os.environ["OUTBREAK_DEMO_MODE"] = "true"

    sent_to_phone_b = []
    all_sent = []

    async def mock_send(phone, message):
        clean = normalize_phone(phone)
        all_sent.append((clean, message))
        if clean == PHONE_B:
            sent_to_phone_b.append(message)
        return True

    async def _run_photo_flow():
        with patch("services.whatsapp_service._download_image", return_value=SAMPLE_IMG), \
             patch("services.whatsapp_service.send_message", side_effect=mock_send), \
             patch("outbreak.service.send_proactive_message", side_effect=mock_send):

            # Turn 1: Phone A sends plant photo
            await handle_incoming_message({
                "From": f"whatsapp:{PHONE_A}",
                "Body": "",
                "NumMedia": "1",
                "MediaUrl0": "https://example.com/fake_leaf.jpg",
                "MediaContentType0": "image/jpeg",
                "MessageSid": "SM_ACCEPTANCE_TEST_001",
            })

            # Turn 2: Phone A confirms crop ("yes")
            await handle_incoming_message({
                "From": f"whatsapp:{PHONE_A}",
                "Body": "yes",
                "NumMedia": "0",
                "MessageSid": "SM_ACCEPTANCE_TEST_002",
            })

            # Give background evaluation task enough time for remote Supabase DB queries
            await asyncio.sleep(3.5)

    asyncio.run(_run_photo_flow())

    assert len(sent_to_phone_b) >= 1, f"Expected Phone B to receive an outbreak alert! All sent: {all_sent}"
    b_msg = sent_to_phone_b[0]

    # Check alert content on Phone B
    assert "ರೋಗ ಹರಡುವಿಕೆ ಎಚ್ಚರಿಕೆ" in b_msg or "ಮುನ್ನೆಚ್ಚರಿಕಾ ಕ್ರಮಗಳು" in b_msg
    assert "ಕಿ.ಮೀ" in b_msg
    assert PHONE_A not in b_msg
    assert "Kishan A" not in b_msg

