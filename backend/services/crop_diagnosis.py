"""Crop-conditioned PlantVillage classifier for tomato / potato / capsicum."""
import json
import re
from functools import lru_cache
from pathlib import Path

from ultralytics import YOLO

_BACKEND = Path(__file__).resolve().parent.parent
MODEL = _BACKEND / "agent" / "model" / "classifier.onnx"
DATA = _BACKEND / "data"
PREFIX = {"tomato": "tomato", "potato": "potato", "capsicum": "pepper"}
OK_CONF, OK_MASS = 0.70, 0.50        # UNTUNED
TENT_CONF, TENT_MASS = 0.40, 0.30    # UNTUNED

DISEASE_DB = json.loads((DATA / "disease_db.json").read_text(encoding="utf-8"))
PROGRESSION_DB = json.loads((DATA / "progression_db.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _model():
    return YOLO(str(MODEL), task="classify")


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower().replace("leaf", " ")))


def match_db_key(label: str):
    lt, best, best_score = _tokens(label), None, (0, 0)
    for key in DISEASE_DB:
        kt = _tokens(key)
        score = (len(lt & kt), -len(kt - lt))
        if score[0] >= 2 and score > best_score:
            best, best_score = key, score
    return best


def diagnose_with_classifier(image_path: str, crop: str):
    """Blocking. Returns a diagnose_image-shaped dict, or None if this model doesn't cover the crop."""
    prefix = PREFIX.get((crop or "").lower())
    if not prefix or not MODEL.exists():
        return None
    r = _model().predict(image_path, imgsz=224, verbose=False)[0]
    probs = r.probs.data.tolist()
    ranked = [(r.names[i], probs[i]) for i in range(len(probs)) if r.names[i].lower().startswith(prefix)]
    mass = sum(p for _, p in ranked)
    ranked = sorted(((n, p / (mass or 1.0)) for n, p in ranked), key=lambda x: -x[1])
    label, conf = ranked[0]
    healthy = "healthy" in label.lower()

    if healthy and conf >= TENT_CONF and mass >= TENT_MASS:
        status = "healthy"
    elif not healthy and conf >= OK_CONF and mass >= OK_MASS:
        status = "ok"
    elif not healthy and conf >= TENT_CONF and mass >= TENT_MASS:
        status = "tentative"
    else:
        status = "low_confidence"

    key = None if healthy else match_db_key(label)
    entry = DISEASE_DB.get(key, {}) if key else {}
    prog = PROGRESSION_DB.get(key, {}) if key else {}
    print(f"[Classifier] crop={crop} label={label} conf={conf:.2f} mass={mass:.2f} status={status} db_key={key}")
    return {
        "status": status, "error": False, "source": "classifier",
        "disease": key or label.replace("_", " ").strip(), "raw_name": label,
        "crop": crop.title(), "confidence": f"{conf:.1%}", "confidence_num": conf,
        "primary": {"class": label, "crop": crop, "confidence": conf, "mass": round(mass, 3)},
        "diseased_leaves": 0 if healthy else 1, "total_leaves": 1,
        "remedies": entry.get("remedies", {}), "urgency": entry.get("urgency", ""),
        "pathogen": entry.get("pathogen", ""), "symptoms": entry.get("symptoms", ""),
        "spread": (prog.get("daily_spread_rate", 0) or 0) > 0, "progression": {}, "db_key": key,
    }