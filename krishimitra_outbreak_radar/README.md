# KrishiMitra Outbreak Radar — Quick Integration

This starter adds:
- PostgreSQL table for geolocated disease observations
- FastAPI endpoints to record observations and return aggregated outbreak signals
- React + Leaflet map component for the admin dashboard

This is a rule-based outbreak signal, not a trained model. It flags clusters of recent detections for human review.

## 1. Install backend dependency

In the existing backend environment:
```bash
pip install asyncpg
```

Set `DATABASE_URL` in `.env` to your Supabase PostgreSQL connection string. For asyncpg, use a standard PostgreSQL URL such as:
`postgresql://USER:PASSWORD@HOST:5432/postgres`
If your current URL begins `postgresql+asyncpg://`, remove `+asyncpg` for this module.

## 2. Create the table
Run `backend/outbreak_schema.sql` in the Supabase SQL Editor.

## 3. Add the API
Copy `backend/outbreak_api.py` into your backend. In existing `main.py`, add:
```python
from outbreak_api import router as outbreak_router, initialize_outbreak_pool, close_outbreak_pool

app.include_router(outbreak_router)

@app.on_event("startup")
async def startup_outbreak_radar():
    await initialize_outbreak_pool()

@app.on_event("shutdown")
async def shutdown_outbreak_radar():
    await close_outbreak_pool()
```
If your app already uses startup/shutdown hooks, add these calls to the existing hooks instead of defining duplicate handlers. Adjust the import path if you place the file in a package.

## 4. Connect your disease detection pipeline
After the existing disease model returns a diagnosis, call `POST /api/outbreaks/observations` only when the farmer has shared coordinates (or has previously saved coordinates). Example payload:
```json
{
  "farmer_id": "internal-farmer-id",
  "disease": "Tomato Early Blight",
  "crop": "Tomato",
  "confidence": 0.87,
  "severity": "Moderate",
  "latitude": 12.9716,
  "longitude": 77.5946
}
```
Use a stable internal farmer identifier, not a publicly displayed phone number. The schema stores this identifier for unique-farmer counting; do not expose it in API responses. In production, protect this write endpoint with authentication or an internal service token.

## 5. Frontend
Install in your React frontend:
```bash
npm install leaflet react-leaflet
```
Import Leaflet CSS once in your app entry file:
```js
import "leaflet/dist/leaflet.css";
```
Copy `frontend/OutbreakRadar.jsx` into your React project and render:
```jsx
import OutbreakRadar from "./OutbreakRadar";
export default function OutbreaksPage() {
  return <OutbreakRadar />;
}
```
Set `VITE_API_BASE_URL` to your backend URL if it is not `http://127.0.0.1:8000`.

## API
- `GET /api/outbreaks/health`
- `POST /api/outbreaks/observations`
- `GET /api/outbreaks?days=7`

The map endpoint groups observations into approximate ~5 km grid cells and returns cells with at least 3 unique farmers in the selected window. This is a lightweight MVP approximation; grid width varies by latitude. The underlying observation table can be used for more robust PostGIS clustering later.

## Important
- Only observations with valid GPS coordinates can appear on the map.
- This detects clusters of submitted model diagnoses, not confirmed disease transmission.
- Avoid exposing farmer identifiers, phone numbers, exact household locations, or unaggregated observations in the public dashboard.
- Verify the disease label, location and timestamp quality before interpreting a signal.
