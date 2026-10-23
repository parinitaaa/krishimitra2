# KrishiMitra Crop Recommendation — Quick Integration

This starter adds a Random Forest crop recommendation model and a React form for testing it.

## 1. Dataset
Download `Crop_recommendation.csv` from:
https://www.kaggle.com/datasets/siddharthss/crop-recommendation-dataset

Put it here:
`backend/crop_recommendation/Crop_recommendation.csv`

Expected columns:
`N,P,K,temperature,humidity,ph,rainfall,label`

## 2. Backend setup
From your existing backend virtual environment:

```bash
pip install -r backend/requirements.txt
python backend/crop_recommendation/train_model.py
```

This creates:
`backend/crop_recommendation/artifacts/crop_model.joblib`

Then copy `backend/crop_recommendation/crop_api.py` and its package folder into your existing backend. In your existing FastAPI app (`main.py`), add:

```python
from crop_recommendation.crop_api import router as crop_router
app.include_router(crop_router)
```

If your existing backend has a different package structure, adjust the import path accordingly. Do not create a second FastAPI `app`.

Run your existing server, e.g.:
```bash
uvicorn main:app --reload --port 8000
```

Check `http://127.0.0.1:8000/docs` and test `POST /api/crops/recommend`.

## 3. Frontend setup
Copy `frontend/src/components/CropRecommendation.jsx` into your React project.
Render it on a page:
```jsx
import CropRecommendation from "./components/CropRecommendation";

export default function CropPage() {
  return <CropRecommendation />;
}
```

By default it calls `http://127.0.0.1:8000/api/crops/recommend`.
If your API is deployed elsewhere, set `VITE_API_BASE_URL` in your frontend `.env`, for example:
`VITE_API_BASE_URL=http://localhost:8000`

For a Create React App project, replace `import.meta.env.VITE_API_BASE_URL` with `process.env.REACT_APP_API_BASE_URL`.

## Notes
- Train locally or in Colab; no GPU is needed.
- The CSV dataset's values are a prototype baseline, not a guarantee of suitability for a real farm.
- The form asks for all seven features. Don't silently invent missing soil values.
- Model scores are classifier scores, not yield probabilities.
