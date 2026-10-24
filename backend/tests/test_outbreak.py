"""
tests/test_outbreak.py

Comprehensive tests for outbreak alerts from disease_cases:
1. 5 test farmers at known coordinates with different crops, languages, and opt-in states.
2. Only the right farmers get the right messages (Kannada urgent for same-crop, Hindi watch for susceptible-crop, 0 for unrelated crop, 0 for out-of-radius, 0 for opt-out).
3. Low-confidence case sends nothing.
4. Non-contagious case sends nothing.
5. Second run sends nothing (idempotency).
6. Failed send cleans up claim so retry works without duplicating successful sends.
7. Reporter privacy: reporter's phone, name, or coordinates never appear in any message.
"""

import asyncio
import os
import uuid
import pytest
from unittest.mock import patch
from sqlalchemy import text

from services.db import SessionLocal
from outbreak.service import evaluate_case
from farmer_store import create_case, update_case, normalize_phone

# Reserved test numbers
REPORTER_PHONE = "+910000000000"
FARMER_SAME_CROP_KN = "+910000000001"
FARMER_OTHER_CROP_HI = "+910000000002"
FARMER_UNRELATED_CROP = "+910000000003"
FARMER_OUT_OF_RADIUS = "+910000000004"
FARMER_OPT_OUT = "+910000000005"

ALL_TEST_PHONES = [
    REPORTER_PHONE,
    FARMER_SAME_CROP_KN,
    FARMER_OTHER_CROP_HI,
    FARMER_UNRELATED_CROP,
    FARMER_OUT_OF_RADIUS,
    FARMER_OPT_OUT,
]


def clean_test_data():
    """Wipe all test records before and after testing using prefix match."""
    with SessionLocal() as db:
        db.execute(text("DELETE FROM outbreak_alerts_sent WHERE recipient_phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM disease_cases WHERE phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM conversation_state WHERE phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM chat_history WHERE phone LIKE '+91000000%'"))
        db.execute(text("DELETE FROM farmers WHERE phone LIKE '+91000000%'"))
        db.commit()


@pytest.fixture(autouse=True)
def setup_teardown():
    clean_test_data()
    # Populate the 5 test farmers in a single multi-row insert
    with SessionLocal() as db:
        db.execute(text("""
            INSERT INTO farmers (phone, name, language, lat, lng, crops, onboarding_step, proactive_opt_in)
            VALUES
                ('+910000000000', 'Reporter Rao', 'english', 13.0000, 77.5000, ARRAY['tomato'], 'done', true),
                ('+910000000001', 'Basavaraj', 'kannada', 13.0400, 77.5000, ARRAY['tomato'], 'done', true),
                ('+910000000002', 'Ramesh', 'hindi', 13.0000, 77.5500, ARRAY['potato'], 'done', true),
                ('+910000000003', 'Kumar', 'english', 13.0300, 77.5200, ARRAY['corn'], 'done', true),
                ('+910000000004', 'Suresh', 'english', 13.3500, 77.5000, ARRAY['tomato'], 'done', true),
                ('+910000000005', 'Manjunath', 'english', 13.0200, 77.5000, ARRAY['tomato'], 'done', false)
        """))
        db.commit()

    yield
    clean_test_data()


def test_outbreak_5_farmer_matrix():
    """
    Test that across the 5 farmers:
    - Farmer 1 (same-crop, within radius, Kannada) gets URGENT message in Kannada.
    - Farmer 2 (potato, susceptible, within radius, Hindi) gets WATCH message in Hindi.
    - Farmer 3 (corn, unrelated, within radius) gets NOTHING.
    - Farmer 4 (tomato, outside radius) gets NOTHING.
    - Farmer 5 (tomato, within radius, opt-out) gets NOTHING.
    - Reporter never receives a message.
    - Privacy: Reporter phone/name never appears in message text.
    """
    case_id = create_case(
        phone=REPORTER_PHONE,
        crop="tomato",
        disease="Early Blight",
        confidence=0.88,
        severity_level="Moderate",
        severity_source="farmer_reported",
        lat=13.0000,
        lng=77.5000,
    )

    sent_messages = {}

    async def fake_send(phone, message):
        sent_messages[phone] = message
        return True

    async def _run():
        with patch("outbreak.service.send_proactive_message", side_effect=fake_send):
            return await evaluate_case(case_id, dry_run=False)

    result = asyncio.run(_run())

    assert result["status"] == "completed"
    assert result["alerts_sent"] == 2

    # Verify recipients
    assert FARMER_SAME_CROP_KN in sent_messages
    assert FARMER_OTHER_CROP_HI in sent_messages
    assert FARMER_UNRELATED_CROP not in sent_messages
    assert FARMER_OUT_OF_RADIUS not in sent_messages
    assert FARMER_OPT_OUT not in sent_messages
    assert REPORTER_PHONE not in sent_messages

    # Check Kannada message content
    kn_msg = sent_messages[FARMER_SAME_CROP_KN]
    assert "ರೋಗ ಹರಡುವಿಕೆ ಎಚ್ಚರಿಕೆ" in kn_msg or "ಮುನ್ನೆಚ್ಚರಿಕಾ ಕ್ರಮಗಳು" in kn_msg
    assert "ಕಿ.ಮೀ" in kn_msg
    assert "ನಾಳೆ ಬೆಳಿಗ್ಗೆ" in kn_msg
    assert REPORTER_PHONE not in kn_msg
    assert "Reporter Rao" not in kn_msg

    # Check Hindi message content
    hi_msg = sent_messages[FARMER_OTHER_CROP_HI]
    assert "सतर्कता" in hi_msg or "रोकथाम" in hi_msg
    assert "किमी" in hi_msg
    assert "कल सुबह" in hi_msg
    assert REPORTER_PHONE not in hi_msg
    assert "Reporter Rao" not in hi_msg


def test_low_confidence_case_sends_nothing():
    """Case with detector confidence < 0.70 sends nothing."""
    case_id = create_case(
        phone=REPORTER_PHONE,
        crop="tomato",
        disease="Early Blight",
        confidence=0.55,  # below 0.70 threshold
        severity_level="Moderate",
        severity_source="farmer_reported",
        lat=13.0000,
        lng=77.5000,
    )

    sent_messages = {}
    async def fake_send(phone, message):
        sent_messages[phone] = message
        return True

    async def _run():
        with patch("outbreak.service.send_proactive_message", side_effect=fake_send):
            return await evaluate_case(case_id, dry_run=False)

    result = asyncio.run(_run())

    assert result["status"] == "confidence_below_threshold"
    assert len(sent_messages) == 0


def test_non_contagious_case_sends_nothing():
    """Healthy class or unknown disease is treated as NOT contagious and sends nothing."""
    case_id = create_case(
        phone=REPORTER_PHONE,
        crop="tomato",
        disease="Healthy Tomato",
        confidence=0.92,
        severity_level="Moderate",
        severity_source="farmer_reported",
        lat=13.0000,
        lng=77.5000,
    )

    sent_messages = {}
    async def fake_send(phone, message):
        sent_messages[phone] = message
        return True

    async def _run():
        with patch("outbreak.service.send_proactive_message", side_effect=fake_send):
            return await evaluate_case(case_id, dry_run=False)

    result = asyncio.run(_run())

    assert result["status"] == "not_contagious"
    assert len(sent_messages) == 0


def test_second_run_sends_nothing():
    """Idempotency: evaluating the same case a second time sends nothing."""
    case_id = create_case(
        phone=REPORTER_PHONE,
        crop="tomato",
        disease="Early Blight",
        confidence=0.88,
        severity_level="Moderate",
        severity_source="farmer_reported",
        lat=13.0000,
        lng=77.5000,
    )

    sent_messages = {}
    async def fake_send(phone, message):
        sent_messages[phone] = message
        return True

    async def _run():
        with patch("outbreak.service.send_proactive_message", side_effect=fake_send):
            res1 = await evaluate_case(case_id, dry_run=False)
            sent_messages.clear()
            res2 = await evaluate_case(case_id, dry_run=False)
            return res1, res2

    res1, res2 = asyncio.run(_run())
    assert res1["status"] == "completed"
    assert res2["status"] == "already_evaluated"
    assert len(sent_messages) == 0


def test_failed_send_retries_without_duplicates():
    """
    If send fails for one recipient, its claim is deleted so retry can succeed
    without sending duplicate alerts to previously successful recipients.
    """
    case_id = create_case(
        phone=REPORTER_PHONE,
        crop="tomato",
        disease="Early Blight",
        confidence=0.88,
        severity_level="Moderate",
        severity_source="farmer_reported",
        lat=13.0000,
        lng=77.5000,
    )

    call_counts = {FARMER_SAME_CROP_KN: 0, FARMER_OTHER_CROP_HI: 0}

    async def flaky_send(phone, message):
        call_counts[phone] = call_counts.get(phone, 0) + 1
        # Fail for FARMER_SAME_CROP_KN on first attempt
        if phone == FARMER_SAME_CROP_KN and call_counts[phone] == 1:
            return False
        return True

    async def _run():
        with patch("outbreak.service.send_proactive_message", side_effect=flaky_send):
            # Run 1: Farmer 1 fails, Farmer 2 succeeds
            res1 = await evaluate_case(case_id, dry_run=False)
            assert res1["alerts_sent"] == 1  # Only Farmer 2 succeeded

            # Reset evaluated_at so we can simulate retry of the case
            with SessionLocal() as db:
                db.execute(text("UPDATE disease_cases SET outbreak_evaluated_at = NULL WHERE id = :id"), {"id": str(case_id)})
                db.commit()

            # Run 2: Retry evaluation
            res2 = await evaluate_case(case_id, dry_run=False)
            return res1, res2

    res1, res2 = asyncio.run(_run())

    # Farmer 2 was already claimed and inserted, so only Farmer 1 is sent on retry!
    assert call_counts[FARMER_SAME_CROP_KN] == 2  # Retried and succeeded
    assert call_counts[FARMER_OTHER_CROP_HI] == 1  # NOT called again (deduped!)


def test_outbreak_routes_require_admin_token_and_mask_phones():
    """
    Requirement 6:
    - outbreak/routes.py requires env ADMIN_TOKEN or returns 404 (not 401/403).
    - Never returns phone numbers in responses.
    """
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    os.environ["ADMIN_TOKEN"] = "test_secret_token_123"

    # 1. Without ADMIN_TOKEN -> 404
    r1 = client.post("/outbreak/new-detection", json={"case_id": "dummy"})
    assert r1.status_code == 404

    # 2. With invalid token -> 404
    r2 = client.post("/outbreak/new-detection", json={"case_id": "dummy"}, headers={"X-Admin-Token": "wrong"})
    assert r2.status_code == 404

    # 3. With valid token -> 200 and no phone numbers
    r3 = client.post("/outbreak/new-detection", json={"case_id": "nonexistent"}, headers={"X-Admin-Token": "test_secret_token_123"})
    assert r3.status_code == 200
    res_str = str(r3.json()).lower()
    assert "phone" not in res_str
    assert "+91" not in res_str
