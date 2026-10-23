from pathlib import Path
from functools import lru_cache
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/crops", tags=["Crop Recommendation"])
MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "crop_model.joblib"

class CropInput(BaseModel):
    N: float = Field(ge=0, le=300)
    P: float = Field(ge=0, le=300)
    K: float = Field(ge=0, le=400)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    ph: float = Field(ge=0, le=14)
    rainfall: float = Field(ge=0, le=3000)

@lru_cache(maxsize=1)
def load_artifact():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run train_model.py first."
        )
    return joblib.load(MODEL_PATH)

@router.get("/health")
def crop_model_health():
    try:
        artifact = load_artifact()
        return {"status": "ready", "crop_classes": len(artifact["classes"])}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@router.post("/recommend")
def recommend_crop(data: CropInput):
    try:
        artifact = load_artifact()
        model = artifact["model"]
        features = artifact["features"]
        row = pd.DataFrame([[getattr(data, f) for f in features]], columns=features)
        probabilities = model.predict_proba(row)[0]
        indices = probabilities.argsort()[::-1][:3]
        results = [
            {
                "crop": str(model.classes_[i]),
                "model_score": round(float(probabilities[i]) * 100, 2),
            }
            for i in indices
        ]
        return {
            "status": "success",
            "recommendations": results,
            "note": "Model scores are not yield or profit probabilities. Validate local suitability before planting."
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
