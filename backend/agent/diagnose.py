# backend/agent/diagnose.py
"""
YOLOv8 detect-based crop disease diagnosis.

Model: weights/best.onnx (preferred) | weights/best.pt (fallback)
  - 29 classes: 18 disease + 11 healthy-leaf
  - imgsz 640, conf threshold configurable via DISEASE_MIN_CONF env var (default 0.50, UNTUNED)
  - Class names are read from the model metadata at runtime — never from a hardcoded list.

Statuses returned:
  ok              — a disease class >= DISEASE_MIN_CONF and clearly ahead of runner-up
  healthy         — only the crop's healthy-leaf class detected (careful wording)
  no_disease_model— crop is Blueberry/Cherry/Peach/Raspberry/Soybean/Strawberry (healthy-only)
  low_confidence  — detections below threshold or ambiguous
  no_leaf         — zero detections above conf=0.25

Crop gate:
  Before diagnosis the farmer confirms the crop (from profile or explicit answer).
  Detections for *other* crops are discarded. Status is decided from filtered detections only.

Severity:
  Severity is NOT computed from bbox — only the farmer's verbal answer sets it.
  Until the farmer answers, severity_level = 'Unknown'.
  Progression uses illustrative level-based values (Mild=10%, Moderate=30%, Severe=60%) clearly
  labelled as illustrative.

Diagnosis log: every call is appended to backend/logs/diagnosis.jsonl (masked phone).
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

print("[Diagnose] module loaded from", __file__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_BACKEND = Path(__file__).parent.parent
ROOT = _BACKEND.parent
DISEASE_DB_PATH = _BACKEND / "data" / "disease_db.json"
PROG_DB_PATH = _BACKEND / "data" / "progression_db.json"
ONNX_PATH = _BACKEND / "weights" / "best.onnx"
PT_PATH = _BACKEND / "weights" / "best.pt"
LOG_DIR = _BACKEND / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DIAG_LOG = LOG_DIR / "diagnosis.jsonl"

# ── Load static data ──────────────────────────────────────────────────────────
DISEASE_DB: dict = json.loads(DISEASE_DB_PATH.read_text(encoding="utf-8")) if DISEASE_DB_PATH.exists() else {}
PROGRESSION_DB: dict = json.loads(PROG_DB_PATH.read_text(encoding="utf-8")) if PROG_DB_PATH.exists() else {}

# ── Threshold (UNTUNED — adjust after field validation) ───────────────────────
DISEASE_MIN_CONF: float = float(os.getenv("DISEASE_MIN_CONF", "0.50"))  # UNTUNED

# ── Crops that have only a healthy-leaf class, no disease classes in this model ──
NO_DISEASE_MODEL_CROPS = frozenset(
    {"blueberry", "cherry", "peach", "raspberry", "soybean", "soyabean", "strawberry"}
)

# ── Supported crops (has at least one class in the model) ─────────────────────
SUPPORTED_CROPS = frozenset(
    {"apple", "blueberry", "cherry", "corn", "maize", "grape", "orange",
     "peach", "pepper", "capsicum", "potato", "raspberry", "soybean", "soyabean",
     "squash", "strawberry", "tomato"}
)

# ── Crop alias normalisation (WhatsApp messages in kn/hi/en) ─────────────────
CROP_ALIASES: dict[str, str] = {
    # English
    "tomato": "tomato", "tamatar": "tomato", "tomatoes": "tomato",
    "potato": "potato", "aloo": "potato", "potatoes": "potato",
    "maize": "corn", "corn": "corn", "makka": "corn",
    "grape": "grape", "grapes": "grape", "angur": "grape",
    "capsicum": "pepper", "bell pepper": "pepper", "pepper": "pepper",
    "mirchi": "pepper", "shimla mirchi": "pepper",
    "apple": "apple", "seb": "apple",
    "squash": "squash",
    "strawberry": "strawberry",
    "blueberry": "blueberry",
    "cherry": "cherry",
    "peach": "peach",
    "raspberry": "raspberry",
    "soybean": "soybean", "soyabean": "soybean",
    # Kannada
    "ಟೊಮೆಟೊ": "tomato", "ಟೊಮೇಟೊ": "tomato",
    "ಆಲೂಗಡ್ಡೆ": "potato", "ಆಲೂ": "potato",
    "ಮೆಕ್ಕೆಜೋಳ": "corn",
    "ದ್ರಾಕ್ಷಿ": "grape",
    "ಮೆಣಸಿನಕಾಯಿ": "pepper", "ಕ್ಯಾಪ್ಸಿಕಂ": "pepper",
    "ಸೇಬು": "apple",
    # Hindi
    "टमाटर": "tomato",
    "आलू": "potato",
    "मक्का": "corn",
    "अंगूर": "grape",
    "शिमला मिर्च": "pepper", "मिर्च": "pepper",
    "सेब": "apple",
    "other": None,  # unsupported
    "अन्य": None,
    "ಇತರ": None,
    "ಬೇರೆ": None,
}


def normalize_crop_text(text: str) -> Optional[str]:
    """
    Map farmer's typed crop to a canonical crop name used in class_to_crop mapping.
    Returns None if unsupported / 'other'.
    """
    t = text.strip().lower()
    if t in CROP_ALIASES:
        return CROP_ALIASES[t]
    # Token-level fallback: try each alias as substring
    for alias, canon in CROP_ALIASES.items():
        if alias and alias in t:
            return canon
    return None

# ── Healthy leaf classes (the 11 healthy classes in YOLOv8 29-class model) ────
HEALTHY_CLASSES: frozenset[str] = frozenset({
    "apple leaf", "bell_pepper leaf", "blueberry leaf", "cherry leaf",
    "peach leaf", "potato leaf", "raspberry leaf", "soyabean leaf",
    "strawberry leaf", "tomato leaf", "grape leaf"
})


def _is_healthy(class_name: str) -> bool:
    cn = class_name.lower().strip()
    return cn in HEALTHY_CLASSES or "healthy" in cn


# ── Lazy YOLO singleton ───────────────────────────────────────────────────────
_yolo_model = None
_yolo_model_path: str = ""
_class_names: list[str] = []


def _load_yolo() -> tuple:
    """
    Load YOLO model once. Configured path from config.DISEASE_MODEL_PATH (default weights/best.onnx),
    falling back to weights/best.pt if missing or failing.
    Returns (model, class_names, model_path_str).
    """
    global _yolo_model, _class_names, _yolo_model_path
    if _yolo_model is not None:
        return _yolo_model, _class_names, _yolo_model_path

    from ultralytics import YOLO

    try:
        from config import DISEASE_MODEL_PATH
    except ImportError:
        DISEASE_MODEL_PATH = "weights/best.onnx"

    primary_path = Path(DISEASE_MODEL_PATH)
    if not primary_path.is_absolute():
        primary_path = _BACKEND / primary_path

    fallback_path = _BACKEND / "weights" / "best.pt"

    candidates = [primary_path]
    if fallback_path != primary_path and fallback_path.exists():
        candidates.append(fallback_path)

    for p in candidates:
        if not p.exists():
            continue
        try:
            model = YOLO(str(p), task="detect")
            names: dict = model.names  # {0: "Apple Scab Leaf", ...}
            class_names = [names[i] for i in sorted(names.keys())]
            _yolo_model = model
            _class_names = class_names
            _yolo_model_path = str(p)
            logger.info(f"[Diagnose] Active model: {p} ({len(class_names)} classes)")
            print(f"[Diagnose] ✅ Active model: {p} ({len(class_names)} classes)")
            return model, class_names, str(p)
        except Exception as e:
            logger.warning(f"[Diagnose] Failed to load {p}: {e}")

    raise RuntimeError(f"No YOLO model found (tried {[str(c) for c in candidates]})")


# ── Class-to-crop map ─────────────────────────────────────────────────────────
def _build_class_to_crop(class_names: list[str]) -> dict[str, str]:
    """
    Map each YOLO class name (e.g. 'Apple Scab Leaf', 'Tomato leaf late blight',
    'Bell_pepper leaf spot', 'Tomato___Late_blight') to canonical crop name.
    """
    mapping = {}
    for name in class_names:
        if "___" in name:
            crop_raw = name.split("___")[0].replace("_", " ").strip().lower()
        else:
            nl = name.lower()
            if nl.startswith("bell_pepper") or nl.startswith("pepper") or nl.startswith("capsicum"):
                crop_raw = "pepper"
            elif nl.startswith("soyabean") or nl.startswith("soybean"):
                crop_raw = "soybean"
            elif nl.startswith("corn") or nl.startswith("maize"):
                crop_raw = "corn"
            elif nl.startswith("grape"):
                crop_raw = "grape"
            elif nl.startswith("apple"):
                crop_raw = "apple"
            elif nl.startswith("blueberry"):
                crop_raw = "blueberry"
            elif nl.startswith("cherry"):
                crop_raw = "cherry"
            elif nl.startswith("peach"):
                crop_raw = "peach"
            elif nl.startswith("potato"):
                crop_raw = "potato"
            elif nl.startswith("raspberry"):
                crop_raw = "raspberry"
            elif nl.startswith("squash"):
                crop_raw = "squash"
            elif nl.startswith("strawberry"):
                crop_raw = "strawberry"
            elif nl.startswith("tomato"):
                crop_raw = "tomato"
            else:
                crop_raw = nl.split()[0].replace("_", " ").strip()
        mapping[name] = crop_raw
    return mapping


# ── disease_db.json key matching ─────────────────────────────────────────────
def _norm(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for fuzzy matching."""
    s = unicodedata.normalize("NFKD", s).lower()
    s = re.sub(r"[_\-.]", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


# Build model-class → disease_db_key mapping at module load time
def _build_class_to_db_key(class_names: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    For each YOLO class (non-healthy), find the matching disease_db.json key.
    Returns (class_to_db, unmapped_list).
    """
    db_keys_norm = {_norm(k): k for k in DISEASE_DB.keys()}
    result: dict[str, str] = {}
    unmapped: list[str] = []

    for cls in class_names:
        if _is_healthy(cls):
            continue  # healthy classes don't need a disease db entry
        norm_cls = _norm(cls)
        # 1. Exact match
        if norm_cls in db_keys_norm:
            result[cls] = db_keys_norm[norm_cls]
            continue
        # 2. Token-set overlap (≥ 2 shared significant tokens)
        cls_tokens = set(norm_cls.split()) - {"leaf", "the", "a", "of"}
        best_match, best_score = None, 0
        for nk, orig_k in db_keys_norm.items():
            k_tokens = set(nk.split()) - {"leaf", "the", "a", "of"}
            overlap = len(cls_tokens & k_tokens)
            if overlap >= 2 and overlap > best_score:
                best_score = overlap
                best_match = orig_k
        if best_match:
            result[cls] = best_match
        else:
            unmapped.append(cls)
            logger.warning(f"[Diagnose] Unmapped disease class: {cls}")

    return result, unmapped


# ── Progression illustrative values ──────────────────────────────────────────
_PROG_ILLUSTRATIVE = {
    "Mild":     {"day_3_pct": 10, "day_7_pct": 15, "label": "illustrative"},
    "Moderate": {"day_3_pct": 30, "day_7_pct": 50, "label": "illustrative"},
    "Severe":   {"day_3_pct": 60, "day_7_pct": 85, "label": "illustrative"},
}

# Also use the progression_db for untreated notes if available
def _get_progression(db_key: str, severity_level: str) -> dict:
    illus = _PROG_ILLUSTRATIVE.get(severity_level, _PROG_ILLUSTRATIVE["Moderate"])
    prog = PROGRESSION_DB.get(db_key, {})
    note = prog.get("untreated_note", "")
    return {
        "day_3_spread": f"~{illus['day_3_pct']}% of plant",
        "day_7_spread": f"~{illus['day_7_pct']}% of plant",
        "label": "illustrative",
        "warning": note,
    }


# ── Diagnosis log ─────────────────────────────────────────────────────────────
def _log_diagnosis(masked_phone: str, confirmed_crop: str, raw_top3: list, final_status: str) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "phone": masked_phone,
        "crop": confirmed_crop,
        "top3": raw_top3,
        "status": final_status,
    }
    try:
        with open(DIAG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[Diagnose] Failed to write diagnosis log: {e}")


def _mask_phone(phone: str) -> str:
    p = str(phone or "")
    return p[:4] + "***" + p[-3:] if len(p) >= 7 else "***"

def _finish_classifier_result(c: dict, crop: str) -> dict:
    """Shape a classifier result like the detector's ok/healthy result so the rest of the flow is unchanged."""
    if c["status"] == "healthy":
        return {**_status_result("healthy", crop), "total_leaves": 1, "diseased_leaves": 0}

    db_key = c.get("db_key") or ""
    db_entry = DISEASE_DB.get(db_key, {})
    disease_label = c["raw_name"].split("___")[-1].replace("_", " ").strip()
    display_name = db_entry.get("display_name", disease_label)
    remedies = db_entry.get("remedies") or {
        "organic": ["Remove and destroy affected leaves immediately",
                    "Avoid overhead irrigation — water at soil level"],
        "chemical": ["Consult your local KVK or agricultural officer for recommended treatments in your area"],
        "prevention": ["Maintain proper plant spacing", "Monitor crop regularly"],
    }
    spread_flag = bool(PROGRESSION_DB.get(db_key, {}).get("daily_spread_rate", 0) > 0)
    spread_modes = list(db_entry.get("spread", "").split(". ")) if db_entry.get("spread") else []
    conf = c["confidence_num"]
    crop_name = crop.title()
    return {
        "status": "ok",
        "disease": f"{crop_name} {display_name}",
        "display_name": display_name,
        "raw_name": c["raw_name"],
        "crop": crop_name,
        "confidence": f"{conf:.0%}",
        "confidence_num": conf,
        "severity": {"level": "Unknown", "description": "Severity not yet reported by farmer."},
        "severity_score": 0,
        "spread": spread_flag,
        "spread_modes": spread_modes,
        "urgency": db_entry.get("urgency", ""),
        "pathogen": db_entry.get("pathogen", ""),
        "symptoms": db_entry.get("symptoms", ""),
        "remedies": remedies,
        "progression": _get_progression(db_key, "Mild") if db_key else {},
        "primary": {"class": c["raw_name"], "crop": crop_name, "confidence": conf},
        "diseased_leaves": 1,
        "total_leaves": 1,
        "db_key": db_key,
        "db_entry": db_entry,
        "error": False,
    }

# ── Main diagnosis function ───────────────────────────────────────────────────
def diagnose_image(
    image_path: str,
    confirmed_crop: Optional[str] = None,
    phone: Optional[str] = None,
    # Legacy kwargs accepted silently so old call sites don't crash
    classifier_path: Optional[str] = None,
    detector_path: Optional[str] = None,
) -> dict:
    """
    Run YOLO detection on image_path.

    confirmed_crop: canonical crop name (e.g. 'tomato') already confirmed by the farmer.
                    If None, returns raw results without crop filtering.

    Returns a dict with keys:
        status, disease, raw_name, crop, confidence, confidence_num,
        severity, severity_score, spread, urgency, pathogen, symptoms,
        remedies, progression, primary, diseased_leaves, total_leaves, error
    """
    try:
        # Crop-conditioned classifier for tomato / potato / capsicum (the 29-class detector is weak on these)
        print(f"[Diagnose] called: crop={confirmed_crop!r} image={image_path}")
        _cc = (confirmed_crop or "").lower()
        if _cc in ("tomato", "potato", "capsicum", "pepper"):
            _cc = "capsicum" if _cc == "pepper" else _cc
            try:
                from services.crop_diagnosis import diagnose_with_classifier
                _cres = diagnose_with_classifier(image_path, _cc)
            except Exception as e:
                logger.warning(f"[Diagnose] classifier path failed, using detector: {e}")
                print(f"[Diagnose] classifier path failed: {e!r}")
                _cres = None
            if _cres is not None:
                _top = [{"class": _cres["raw_name"], "crop": _cc,
                         "confidence": _cres["confidence_num"], "is_healthy": _cres["status"] == "healthy"}]
                if _cres["status"] in ("ok", "healthy"):
                    _log_diagnosis(_mask_phone(phone), _cc, _top, _cres["status"])
                    return _finish_classifier_result(_cres, _cc)
                # tentative / low_confidence: don't fall through to the weak detector
                _log_diagnosis(_mask_phone(phone), _cc, _top, "low_confidence")
                return _status_result("low_confidence", _cc)
        model, class_names, model_path = _load_yolo()
        class_to_crop = _build_class_to_crop(class_names)
        class_to_db, unmapped = _build_class_to_db_key(class_names)

        # Ensure image has a recognized extension for ultralytics
        actual_path = Path(image_path)
        temp_renamed = None
        if actual_path.exists() and actual_path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            import shutil, tempfile
            temp_renamed = Path(tempfile.gettempdir()) / f"diag_temp_{actual_path.name}.jpg"
            shutil.copyfile(actual_path, temp_renamed)
            pred_source = str(temp_renamed)
        else:
            pred_source = str(image_path)

        # Run inference
        try:
            results_list = model.predict(
                pred_source,
                conf=0.25,
                imgsz=640,
                verbose=False,
            )
        finally:
            if temp_renamed and temp_renamed.exists():
                try:
                    temp_renamed.unlink()
                except Exception:
                    pass

        result = results_list[0] if results_list else None

        # Collect raw detections
        raw_detections: list[dict] = []
        if result is not None and result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id < len(class_names):
                    cname = class_names[cls_id]
                    raw_detections.append({
                        "class": cname,
                        "crop": class_to_crop.get(cname, ""),
                        "confidence": round(float(box.conf[0]), 4),
                        "is_healthy": _is_healthy(cname),
                    })

        # Top-3 for logging
        raw_sorted = sorted(raw_detections, key=lambda x: x["confidence"], reverse=True)
        raw_top3 = raw_sorted[:3]

        # ── no_leaf ───────────────────────────────────────────────────────────
        if not raw_detections:
            _log_diagnosis(_mask_phone(phone), confirmed_crop or "unknown", [], "no_leaf")
            return _status_result("no_leaf", confirmed_crop)

        # ── Crop filtering ────────────────────────────────────────────────────
        if confirmed_crop:
            cc = confirmed_crop.lower()
            # Remap aliases
            if cc in ("maize",):
                cc = "corn"
            if cc in ("capsicum",):
                cc = "pepper"
            if cc in ("soyabean",):
                cc = "soybean"

            filtered = [d for d in raw_detections if d["crop"] == cc]

            # no_disease_model crops
            if cc in NO_DISEASE_MODEL_CROPS:
                _log_diagnosis(_mask_phone(phone), cc, raw_top3, "no_disease_model")
                return _status_result("no_disease_model", cc)

            if not filtered:
                top_other = raw_sorted[0] if raw_sorted else None
    
                # 1. Check if the top detection is a disease that affects the confirmed crop too
                # (e.g., Late Blight detected as Tomato, but confirmed crop is Potato)
                if top_other:
                    other_class = top_other["class"]
                    # Extract disease part after '___' (e.g., 'Late_blight')
                    parts = other_class.split("___")
                    disease_type = parts[1] if len(parts) > 1 else ""
                    # Try to map the detected disease to the confirmed crop
                    cross_crop_key = f"{cc}_{disease_type}".lower()
                    
                    if cross_crop_key in DISEASE_DB or top_other["confidence"] >= 0.25:
                        # Re-key detection to the confirmed crop
                        remapped_detection = {
                            "class": f"{cc}___{disease_type}",
                            "crop": cc,
                            "confidence": top_other["confidence"],
                            "is_healthy": False
                        }
                        filtered = [remapped_detection]
                # 2. If still not filtered, handle wrong_crop vs low_confidence
                if not filtered:
                    if top_other and top_other["confidence"] >= 0.60:
                        _log_diagnosis(_mask_phone(phone), cc, raw_top3, "wrong_crop")
                        return _status_result("wrong_crop", cc, other_crop=top_other["crop"])
                    
                    _log_diagnosis(_mask_phone(phone), cc, raw_top3, "low_confidence")
                    return _status_result("low_confidence", cc)
        else:
            filtered = raw_detections

        # Sort filtered by confidence
        filtered_sorted = sorted(filtered, key=lambda x: x["confidence"], reverse=True)
        top = filtered_sorted[0]

        # Count leaf types
        total_leaves = len(filtered)
        diseased_leaves = sum(1 for d in filtered if not d["is_healthy"])
        healthy_leaves = total_leaves - diseased_leaves

        # ── healthy ───────────────────────────────────────────────────────────
        if top["is_healthy"]:
            _log_diagnosis(_mask_phone(phone), confirmed_crop or "unknown", raw_top3, "healthy")
            return {
                **_status_result("healthy", top["crop"]),
                "total_leaves": total_leaves,
                "diseased_leaves": 0,
            }

        # ── ok / low_confidence ───────────────────────────────────────────────
        top_conf = top["confidence"]
        runner_up_conf = filtered_sorted[1]["confidence"] if len(filtered_sorted) > 1 else 0.0
        gap = top_conf - runner_up_conf

        runner_up_is_disease = (len(filtered_sorted) > 1 and not filtered_sorted[1]["is_healthy"])
        is_clear_lead = (gap >= 0.05) if runner_up_is_disease else True

        if top_conf >= DISEASE_MIN_CONF and is_clear_lead:
            status = "ok"
        else:
            _log_diagnosis(_mask_phone(phone), confirmed_crop or "unknown", raw_top3, "low_confidence")
            return {
                **_status_result("low_confidence", top.get("crop")),
                "total_leaves": total_leaves,
                "diseased_leaves": diseased_leaves,
            }

        # ── Build ok result ───────────────────────────────────────────────────
        cls_name = top["class"]
        crop_name = top["crop"].title()
        parts = cls_name.split("___")
        disease_label = parts[1].replace("_", " ") if len(parts) > 1 else cls_name

        db_key = class_to_db.get(cls_name, "")
        db_entry = DISEASE_DB.get(db_key, {})
        remedies = db_entry.get("remedies", {})
        if not remedies:
            # Fallback general advice for unmapped diseases (no doses, remedies-free)
            remedies = {
                "organic": ["Remove and destroy affected leaves immediately", "Avoid overhead irrigation — water at soil level"],
                "chemical": ["Consult your local KVK or agricultural officer for recommended treatments in your area"],
                "prevention": ["Maintain proper plant spacing", "Monitor crop regularly"]
            }
        urgency = db_entry.get("urgency", "")
        pathogen = db_entry.get("pathogen", "")
        symptoms = db_entry.get("symptoms", "")
        display_name = db_entry.get("display_name", disease_label)
        spread_flag = bool(PROGRESSION_DB.get(db_key, {}).get("daily_spread_rate", 0) > 0)
        spread_modes = list(db_entry.get("spread", "").split(". ")) if db_entry.get("spread") else []

        progression = _get_progression(db_key, "Mild")  # default until farmer reports severity

        _log_diagnosis(_mask_phone(phone), confirmed_crop or "unknown", raw_top3, "ok")

        return {
            "status": "ok",
            "disease": f"{crop_name} {display_name}",
            "display_name": display_name,
            "raw_name": cls_name,
            "crop": crop_name,
            "confidence": f"{top_conf:.0%}",
            "confidence_num": top_conf,
            "severity": {"level": "Unknown", "description": "Severity not yet reported by farmer."},
            "severity_score": 0,
            "spread": spread_flag,
            "spread_modes": spread_modes,
            "urgency": urgency,
            "pathogen": pathogen,
            "symptoms": symptoms,
            "remedies": remedies,
            "progression": progression,
            "primary": {
                "class": cls_name,
                "crop": crop_name,
                "confidence": top_conf,
            },
            "diseased_leaves": diseased_leaves,
            "total_leaves": total_leaves,
            "db_key": db_key,
            "db_entry": db_entry,
            "error": False,
        }

    except Exception as e:
        logger.exception(f"[Diagnose] Error: {e}")
        return {"error": True, "status": "error", "disease": "Could not analyze", "confidence": "0%"}


def _status_result(status: str, crop: Optional[str] = None, **kwargs) -> dict:
    """Build a minimal result dict for non-ok statuses."""
    base = {
        "status": status,
        "disease": "",
        "raw_name": "",
        "crop": (crop or "").title(),
        "confidence": "0%",
        "confidence_num": 0.0,
        "severity": {"level": "Unknown", "description": ""},
        "severity_score": 0,
        "spread": False,
        "spread_modes": [],
        "urgency": "",
        "pathogen": "",
        "symptoms": "",
        "remedies": {},
        "progression": {},
        "primary": None,
        "diseased_leaves": 0,
        "total_leaves": 0,
        "error": False,
    }
    base.update(kwargs)
    return base


# ── Public helpers ────────────────────────────────────────────────────────────
def get_model_class_names() -> list[str]:
    """Return the model's class names (used by tests)."""
    _, class_names, _ = _load_yolo()
    return class_names


def get_unmapped_classes() -> list[str]:
    """Return disease classes that have no disease_db.json entry."""
    _, class_names, _ = _load_yolo()
    _, unmapped = _build_class_to_db_key(class_names)
    return unmapped


async def async_diagnose_image(
    image_path: str,
    confirmed_crop: Optional[str] = None,
    phone: Optional[str] = None,
    **kwargs,
) -> dict:
    """Run diagnose_image asynchronously in a worker thread via asyncio.to_thread."""
    import asyncio
    return await asyncio.to_thread(
        diagnose_image,
        image_path,
        confirmed_crop=confirmed_crop,
        phone=phone,
        **kwargs,
    )
