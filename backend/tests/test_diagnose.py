# backend/tests/test_diagnose.py
"""
Unit and integration tests for YOLOv8 crop disease diagnosis (TASK DEMO-D).

Covers:
  1. Class names loaded dynamically from model metadata (29 classes, not 38).
  2. All 18 disease classes map to disease_db.json (0 unmapped).
  3. Crop gate failure reproduction:
     (a) farmer says potato, model returns Apple Scab 0.71 -> NOT ok (wrong_crop)
     (b) farmer says tomato, model returns Potato early blight 0.51 -> NOT ok (low_confidence)
     (c) farmer says potato, model returns Potato early blight 0.60 -> ok
  4. Unit tests for each status in kn / hi / en (ok, healthy, no_disease_model, low_confidence, no_leaf, wrong_crop).
  5. Severity update & treatment plan composition from disease_db.json (no hallucinated doses).
  6. End-to-end WhatsApp flow through handle_incoming_message (Kannada tomato leaf photo, hand/soil photo).
  7. Verification: no conf*40 or 38-class list remains; no writes to detections table.
  8. Test images table evaluation.
"""

import asyncio
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.diagnose import (
    diagnose_image,
    get_model_class_names,
    get_unmapped_classes,
    normalize_crop_text,
    SUPPORTED_CROPS,
    NO_DISEASE_MODEL_CROPS,
    DISEASE_DB,
    _load_yolo,
    _build_class_to_crop,
    _build_class_to_db_key,
    _is_healthy,
)
from services.i18n import get_string
from farmer_store import (
    get_or_create_farmer,
    get_farmer,
    set_onboarding_step,
    set_farmer_language,
    update_farmer_profile,
    clear_state,
    get_state,
    delete_farmer_records,
)
from services.db import SessionLocal
from sqlalchemy import text

SAMPLE_IMG = str(BACKEND_DIR / "test_images" / "tomato late blight.jpg")


def _create_mock_box(cls_id: int, conf: float):
    box = MagicMock()
    box.cls = [cls_id]
    box.conf = [conf]
    return box


def _create_mock_result(boxes_data: list[tuple[int, float]]):
    res = MagicMock()
    res.boxes = [_create_mock_box(cid, conf) for cid, conf in boxes_data]
    return res


class TestYoloDiagnosis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.model, cls.class_names, cls.model_path = _load_yolo()

    def test_class_names_read_from_model(self):
        """1. Class names come from the active model metadata, not a hardcoded list."""
        names = get_model_class_names()
        self.assertEqual(len(names), 29, f"Expected 29 classes, got {len(names)}: {names}")
        healthy_classes = [c for c in names if _is_healthy(c)]
        self.assertEqual(len(healthy_classes), 11, f"Expected 11 healthy classes, got {len(healthy_classes)}")
        disease_classes = [c for c in names if not _is_healthy(c)]
        self.assertEqual(len(disease_classes), 18, f"Expected 18 disease classes, got {len(disease_classes)}")

    def test_mapping_all_18_resolve(self):
        """2. All 18 disease classes resolve to disease_db.json keys."""
        unmapped = get_unmapped_classes()
        self.assertEqual(unmapped, [], f"Expected 0 unmapped disease classes, but found: {unmapped}")
        mapping, _ = _build_class_to_db_key(self.class_names)
        for cls_name, db_key in mapping.items():
            self.assertIn(db_key, DISEASE_DB, f"Mapped key '{db_key}' for class '{cls_name}' not in disease_db.json")

    def test_crop_gate_case_a(self):
        """(a) Farmer says potato, model returns Apple Scab 0.71 -> NOT ok (wrong_crop)."""
        apple_scab_idx = self.class_names.index("Apple Scab Leaf")
        mock_res = _create_mock_result([(apple_scab_idx, 0.71)])

        with patch.object(self.model, "predict", return_value=[mock_res]):
            result = diagnose_image(SAMPLE_IMG, confirmed_crop="potato")
            self.assertNotEqual(result["status"], "ok", "Should not be ok when crop does not match")
            self.assertEqual(result["status"], "wrong_crop", f"Expected wrong_crop, got {result['status']}")

    def test_crop_gate_case_b(self):
        """(b) Farmer says tomato, model returns Potato early blight 0.51 -> NOT ok (low_confidence)."""
        potato_eb_idx = self.class_names.index("Potato leaf early blight")
        mock_res = _create_mock_result([(potato_eb_idx, 0.51)])

        with patch.object(self.model, "predict", return_value=[mock_res]):
            result = diagnose_image(SAMPLE_IMG, confirmed_crop="tomato")
            self.assertNotEqual(result["status"], "ok", "Should not be ok when crop does not match")
            self.assertEqual(result["status"], "low_confidence", f"Expected low_confidence, got {result['status']}")

    def test_crop_gate_case_c(self):
        """(c) Farmer says potato, model returns Potato early blight 0.60 -> ok."""
        potato_eb_idx = self.class_names.index("Potato leaf early blight")
        mock_res = _create_mock_result([(potato_eb_idx, 0.60)])

        with patch.object(self.model, "predict", return_value=[mock_res]):
            result = diagnose_image(SAMPLE_IMG, confirmed_crop="potato")
            self.assertEqual(result["status"], "ok", f"Expected ok status, got {result['status']}")
            self.assertEqual(result["crop"], "Potato")
            self.assertIn("Early Blight", result["disease"])
            self.assertEqual(result["severity"]["level"], "Unknown")

    def test_status_healthy(self):
        """Healthy leaf returns status 'healthy'."""
        tomato_healthy_idx = self.class_names.index("Tomato leaf")
        mock_res = _create_mock_result([(tomato_healthy_idx, 0.75)])

        with patch.object(self.model, "predict", return_value=[mock_res]):
            result = diagnose_image(SAMPLE_IMG, confirmed_crop="tomato")
            self.assertEqual(result["status"], "healthy")
            self.assertEqual(result["diseased_leaves"], 0)

    def test_status_no_disease_model(self):
        """Crop with only healthy class returns 'no_disease_model'."""
        sb_idx = self.class_names.index("Strawberry leaf")
        mock_res = _create_mock_result([(sb_idx, 0.80)])
        with patch.object(self.model, "predict", return_value=[mock_res]):
            result = diagnose_image(SAMPLE_IMG, confirmed_crop="strawberry")
            self.assertEqual(result["status"], "no_disease_model")

    def test_status_no_leaf(self):
        """Zero detections above threshold returns 'no_leaf'."""
        mock_res = _create_mock_result([])
        with patch.object(self.model, "predict", return_value=[mock_res]):
            result = diagnose_image(SAMPLE_IMG, confirmed_crop="tomato")
            self.assertEqual(result["status"], "no_leaf")

    def test_i18n_strings_for_all_statuses_kn_hi_en(self):
        """Ensure all required diagnosis strings exist in kn, hi, en."""
        keys = [
            "diag_checking",
            "diag_ask_crop_single",
            "diag_ask_crop_multi",
            "diag_no_leaf",
            "diag_low_confidence",
            "diag_healthy",
            "diag_no_disease_model",
            "diag_wrong_crop",
            "diag_unsupported_crop",
            "diag_ok_single",
            "diag_ok_multi",
            "diag_treatment",
            "diag_dose_review_note",
            "diag_treatment_severe_note",
            "diag_severity_saved",
        ]
        for lang in ("kannada", "hindi", "english"):
            for k in keys:
                s = get_string(k, lang, crop="Tomato", disease="Early Blight", confidence="80%",
                               first_step="Remove leaves", total=1, diseased=1, low_conf_note="",
                               organic="Neem oil", chemical="Mancozeb", dose_note="check dose",
                               day3="10%", day7="15%", severe_note="")
                self.assertTrue(len(s) > 0, f"String '{k}' missing or empty for language '{lang}'")

    def test_no_conf_times_40_or_38_names(self):
        """Verify codebase has no trace of conf*40 or 38-class PlantVillage list."""
        py_files = [p for p in BACKEND_DIR.rglob("*.py") if "legacy" not in p.parts and "test_diagnose.py" not in p.name]
        for p in py_files:
            text = p.read_text(encoding="utf-8", errors="ignore")
            self.assertFalse(
                re.search(r"conf\s*\*\s*40", text),
                f"Forbidden 'conf * 40' found in {p}"
            )
            self.assertFalse(
                "Apple___Apple_scab" in text,
                f"Forbidden 38-class PlantVillage list found in {p}"
            )


class TestWhatsAppDiseaseFlow(unittest.IsolatedAsyncioTestCase):
    """Integration test of handle_incoming_message for the photo diagnosis flow."""

    TEST_PHONE = "+910000000088"

    async def asyncSetUp(self):
        delete_farmer_records(self.TEST_PHONE)

        get_or_create_farmer(self.TEST_PHONE)
        set_farmer_language(self.TEST_PHONE, "kannada")
        set_onboarding_step(self.TEST_PHONE, "done")
        update_farmer_profile(self.TEST_PHONE, name="ರಮೇಶ್", crops=["tomato"], location="Kolar")

    async def asyncTearDown(self):
        delete_farmer_records(self.TEST_PHONE)

    async def test_kannada_tomato_leaf_flow(self):
        """
        Acceptance test: A real tomato-leaf photo sent through handle_incoming_message:
          1. Photo message -> receives 'Checking...' and 'Is this your tomato plant?'
          2. Reply 'ಹೌದು' -> diagnosed as Tomato disease, creates disease_case row, asks severity
          3. Reply 'ಕೆಲವು ಎಲೆಗಳು' -> receives treatment options, case severity updated to Mild.
        """
        from services.whatsapp_service import handle_incoming_message

        outbound = []

        async def mock_send(phone, msg):
            outbound.append(msg)
            return True

        tomato_img_path = str(BACKEND_DIR / "test_images" / "a849a1cf-b06a-4900-bf59-417da8b1d860___GHLB2 Leaf 56.JPG")
        self.assertTrue(os.path.exists(tomato_img_path), f"Missing {tomato_img_path}")

        with patch("services.whatsapp_service.send_message", side_effect=mock_send):
            # Step 1: Send Photo
            outbound.clear()
            await handle_incoming_message({
                "From": f"whatsapp:{self.TEST_PHONE}",
                "Body": "",
                "NumMedia": "1",
                "MediaUrl0": tomato_img_path,
                "MediaContentType0": "image/jpeg",
            })

            self.assertEqual(len(outbound), 2, f"Expected 2 outbound messages, got {len(outbound)}: {outbound}")
            self.assertIn("ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ", outbound[0])
            self.assertIn("Tomato", outbound[1])

            st = get_state(self.TEST_PHONE)
            self.assertIsNotNone(st)
            self.assertEqual(st.get("flow"), "disease_crop")

            # Step 2: Farmer confirms crop with "ಹೌದು" (yes)
            outbound.clear()
            await handle_incoming_message({
                "From": f"whatsapp:{self.TEST_PHONE}",
                "Body": "ಹೌದು",
                "NumMedia": "0",
            })

            self.assertEqual(len(outbound), 1, f"Expected 1 outbound message, got {len(outbound)}: {outbound}")
            diag_msg = outbound[0]
            print("\n" + "="*60)
            print("STEP 2: [Kannada Bot Diagnosis Reply]:")
            print("="*60)
            print(diag_msg)
            self.assertIn("🩺", diag_msg)
            self.assertIn("ಬಾಧಿತವಾಗಿದೆ", diag_msg)

            with SessionLocal() as db:
                case_row = db.execute(
                    text("SELECT id, crop, disease, severity_level, status FROM disease_cases WHERE phone = :p"),
                    {"p": self.TEST_PHONE},
                ).fetchone()
                self.assertIsNotNone(case_row, "disease_cases row should exist for status ok")
                self.assertEqual(case_row[1], "tomato")
                self.assertEqual(case_row[3], "Unknown")
                self.assertEqual(case_row[4], "open")

            st = get_state(self.TEST_PHONE)
            self.assertIsNotNone(st)
            self.assertEqual(st.get("flow"), "disease_severity")

            # Step 3: Farmer reports severity "ಕೆಲವು ಎಲೆಗಳು" (a few leaves)
            outbound.clear()
            await handle_incoming_message({
                "From": f"whatsapp:{self.TEST_PHONE}",
                "Body": "ಕೆಲವು ಎಲೆಗಳು",
                "NumMedia": "0",
            })

            self.assertEqual(len(outbound), 1)
            treatment_msg = outbound[0]
            print("\n" + "="*60)
            print("STEP 3: [Kannada Bot Treatment Reply]:")
            print("="*60)
            print(treatment_msg)
            self.assertIn("ಚಿಕಿತ್ಸೆ", treatment_msg)
            self.assertIn("ಸಾವಯವ", treatment_msg)
            self.assertIn("ರಾಸಾಯನಿಕ", treatment_msg)
            self.assertIn("ಸುರಕ್ಷತಾ", treatment_msg)

            with SessionLocal() as db:
                updated_case = db.execute(
                    text("SELECT severity_level, severity_source FROM disease_cases WHERE phone = :p"),
                    {"p": self.TEST_PHONE},
                ).fetchone()
                self.assertEqual(updated_case[0], "Mild")
                self.assertEqual(updated_case[1], "farmer_reported")

            self.assertIsNone(get_state(self.TEST_PHONE))

            with SessionLocal() as db:
                det_count = db.execute(
                    text("SELECT count(*) FROM detections WHERE phone = :p"),
                    {"p": self.TEST_PHONE},
                ).scalar()
                self.assertEqual(det_count, 0, "No records should ever be written to detections table!")

    async def test_hand_soil_photo_produces_retry_message(self):
        """A hand or non-leaf photo (mocked no_leaf / low_confidence) produces the retry message."""
        from services.whatsapp_service import handle_incoming_message

        outbound = []

        async def mock_send(phone, msg):
            outbound.append(msg)
            return True

        soil_img_path = str(BACKEND_DIR / "test_images" / "apple healthy.jpg")

        # Mock diagnose_image returning no_leaf
        with patch("services.whatsapp_service.send_message", side_effect=mock_send):
            # Send photo
            await handle_incoming_message({
                "From": f"whatsapp:{self.TEST_PHONE}",
                "Body": "",
                "NumMedia": "1",
                "MediaUrl0": soil_img_path,
                "MediaContentType0": "image/jpeg",
            })
            outbound.clear()

            # Confirm crop, but diagnosis detects no leaf
            with patch("services.whatsapp_service.diagnose_image", return_value={"status": "no_leaf", "crop": "Tomato"}):
                await handle_incoming_message({
                    "From": f"whatsapp:{self.TEST_PHONE}",
                    "Body": "yes",
                    "NumMedia": "0",
                })
                self.assertEqual(len(outbound), 1)
                retry_msg = outbound[0]
                print("\n[Retry Message for non-leaf photo]:", retry_msg)
                self.assertIn("ಎಲೆ ಸ್ಪಷ್ಟವಾಗಿ ಕಾಣಿಸುತ್ತಿಲ್ಲ", retry_msg)

                # Ensure NO disease_cases row was created
                with SessionLocal() as db:
                    cnt = db.execute(
                        text("SELECT count(*) FROM disease_cases WHERE phone = :p"),
                        {"p": self.TEST_PHONE},
                    ).scalar()
                    self.assertEqual(cnt, 0, "No disease case should be created for no_leaf!")


def run_test_images_evaluation():
    """
    Run every named test image in backend/test_images through the real model
    with confirmed crop taken from the filename, and print evaluation table.
    """
    print("\n" + "="*80)
    print("REAL MODEL EVALUATION ON backend/test_images (Crop Gate & Crop Filter)")
    print("="*80)

    test_imgs_dir = BACKEND_DIR / "test_images"
    named_files = [
        "apple black rot.jpg",
        "apple healthy.jpg",
        "apple scab.jpg",
        "healthy potato leaf.jpg",
        "healthy tomato leaf",
        "potato early blight.jpg",
        "potato late blight.jpg",
        "tomato late blight.jpg",
    ]

    header = f"{'Image':26} | {'Confirmed Crop':14} | {'Final Status':14} | {'Top Detection':30}"
    print(header)
    print("-" * len(header))

    for fname in named_files:
        fpath = test_imgs_dir / fname
        if not fpath.exists():
            continue

        # Extract confirmed crop from filename
        fn_lower = fname.lower()
        if "apple" in fn_lower:
            crop = "apple"
        elif "potato" in fn_lower:
            crop = "potato"
        elif "tomato" in fn_lower:
            crop = "tomato"
        else:
            crop = "tomato"

        res = diagnose_image(str(fpath), confirmed_crop=crop)
        status = res.get("status", "unknown")
        disease_or_name = res.get("disease") or res.get("crop") or ""
        conf = res.get("confidence", "")
        top_str = f"{disease_or_name} ({conf})" if conf else disease_or_name

        print(f"{fname:26} | {crop:14} | {status:14} | {top_str:30}")

    print("="*80 + "\n")


if __name__ == "__main__":
    run_test_images_evaluation()
    unittest.main()
