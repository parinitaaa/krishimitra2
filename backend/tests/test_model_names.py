# tests/test_model_names.py
import unittest
import json
from pathlib import Path
from ultralytics import YOLO

class TestModelNames(unittest.TestCase):
    def test_model_names_match_snapshot(self):
        backend_dir = Path(__file__).resolve().parent.parent
        snapshot_path = backend_dir / "agent" / "model" / "class_names.json"
        self.assertTrue(snapshot_path.exists(), f"Snapshot not found at {snapshot_path}")

        with open(snapshot_path, "r", encoding="utf-8") as f:
            snapshot_names = json.load(f)

        # Convert keys to int
        snapshot_names = {int(k): v for k, v in snapshot_names.items()}

        model_path = backend_dir / "best1.pt"
        self.assertTrue(model_path.exists(), f"Model not found at {model_path}")

        model = YOLO(str(model_path))
        model_names = model.names

        self.assertEqual(len(model_names), 29, f"Expected 29 classes, got {len(model_names)}")
        self.assertEqual(model_names, snapshot_names, f"Model names mismatch: {model_names} vs {snapshot_names}")

if __name__ == "__main__":
    unittest.main()
