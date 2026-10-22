# AUDIT.md — Read-Only Verification Audit

This document contains the read-only verification findings across all 12 requested audit points, along with code facts, architectural discrepancies, and a prioritized fix list.

---

## 1. Live Supabase Schema
The database was queried directly via `services/db.py` (`SessionLocal()`) against the Postgres `information_schema`.
A snapshot file was written to [`migrations/000_baseline.sql`](file:///c:/Krishi-Mitra/migrations/000_baseline.sql).

### Key Schema Findings:
- **`farmers.crops`**: Defined as **PostgreSQL native array `text[]`** (`ARRAY`, udt `_text`), **NOT** JSONB.
- **`farmers.location`**: `text`, nullable (stores free-text district/state).
- **`farmers.name`**: `text` with default `'Kisan bhai'::text`.
- **`farmers.history` & `farmers.messages`**: `jsonb` with default `'[]'::jsonb`.
- **`farmers.last_detection`**: `jsonb`, nullable.
- **`farmers.lat` & `farmers.lng`**: `double precision` (`float8`), nullable.
- **`farmers.language`**: `varchar`, nullable.
- **`price_alerts`**: PK `id` (`serial`), `phone text`, `commodity text`, `target_price numeric`, `direction text`, `active boolean DEFAULT true`, `last_triggered_price numeric`.
- **`detections`**: PK `id` (`uuid DEFAULT gen_random_uuid()`), `phone text`, `disease_name text`, `crop_type text`, `severity int4`, `lat float8`, `lng float8`, `created_at timestamptz DEFAULT now()`, `spread bool DEFAULT false`, `processed bool DEFAULT false`.
- **`mandi_prices`**: PK `id` (`serial`), `state varchar`, `district varchar`, `market varchar`, `commodity varchar`, `variety varchar`, `min_price float8`, `max_price float8`, `modal_price float8`, `arrival_date date`, `fetched_at timestamp`.
  - Unique Constraint: `uq_market_commodity_date` on `(market, commodity, variety, arrival_date)`.
  - Indexes: B-tree indexes on `commodity`, `id`, `market`, `state`.

---

## 2. Twilio Webhook Handler (`routes/whatsapp.py`)
- **Signature Validation**: **None**. There is no Twilio request validator (`RequestValidator` from `twilio.request_validator` is NOT called or imported).
- **Logic**: Extracts form parameters (`From`, `Body`, `NumMedia`, `MediaUrl0`, `MediaContentType0`, `Latitude`, `Longitude`, `Address`), bundles them into `form_data`, and calls `await handle_incoming_message(form_data)` from `services/whatsapp_service.py`.
- **Response**: Awaits the full response synchronously and returns `Response(content=twiml_xml, media_type="text/xml")`.
- **Violation of Design Rule**: Twilio expects a response within 15 seconds. Heavy operations (YOLO/ONNX inference, Groq LLM completions, DB queries) run directly inside the webhook HTTP handler instead of immediately returning an empty `<Response/>` and processing the message asynchronously via background task + `send_proactive_message` / Twilio REST client.

---

## 3. Onboarding & State Modules
- **`services/language_onboarding.py`**:
  - Checks completion via `get_farmer_language(pid)`.
  - Returns `None` (done) if `farmers.language` has a non-empty string in the DB.
  - Intercepts simple greetings (`hi`, `hello`, `namaste`) or digits `1, 2, 3`.
  - When option 1, 2, or 3 is selected, updates DB via `set_farmer_language` and marks in-memory `mark_pending_name(pid)`.
  - **Vulnerability**: If the server restarts after language selection, the pending-name state is lost because it is kept in memory.
- **`services/name_onboarding.py`**:
  - Checks if step is active via `is_pending_name(pid)`.
  - If active, accepts any string containing at least one unicode letter and <= 80 characters.
  - Updates DB via `update_farmer_profile(pid, name=clean)` and calls `clear_pending_name(pid)`.
  - **Bug with default name**: If a farmer record was already created with the DB default name `'Kisan bhai'` (or Python fallback `name or "Kisan bhai"`), neither module checks `farmers.name` to determine whether name onboarding has completed. It depends entirely on transient in-memory `_pending_name`.
- **`services/profile_state.py`**:
  - Storage: **In-Memory dictionary** `_pending_name: dict[str, bool] = {}`.
  - Does **NOT** persist to the database. Process restarts wipe state.
- **`services/location_state.py`**:
  - Storage: **In-Memory dictionary** `_pending_location: dict = {}`.
  - Does **NOT** persist to the database. Process restarts lose pending commodity context for location requests.

---

## 4. Disease Diagnostics: `agent/diagnose.py` (ONNX) vs `services/yolo_service.py` (best.pt)
- **Which one WhatsApp calls**:
  - WhatsApp flow in [`services/whatsapp_service.py`](file:///c:/Krishi-Mitra/backend/services/whatsapp_service.py#L159-L164) calls **`diagnose_image(...)` in `agent/diagnose.py`** using ONNX runtime (`classifier.onnx` and `detector.onnx`).
  - WhatsApp **NEVER** calls `services/yolo_service.py` or `best.pt`.
- **Keys returned by `diagnose_image`**:
  `"disease"`, `"raw_name"`, `"crop"`, `"bbox_pct"`, `"confidence"`, `"confidence_num"`, `"severity"`, `"severity_score"`, `"spread"`, `"boxes_found"`, `"urgency"`, `"pathogen"`, `"symptoms"`, `"remedies"`, `"progression"`, `"error"`.
- **Is `best.pt` used?**:
  - In WhatsApp: **NO**.
  - In REST endpoints: Only used in HTTP routes [`routes/detect.py`](file:///c:/Krishi-Mitra/backend/routes/detect.py) and [`routes/diagnose.py`](file:///c:/Krishi-Mitra/backend/routes/diagnose.py).

---

## 5. Tool Imports & Model Names
- **How `from agent.tools import ...` resolves**:
  - In `agent/agent.py`, the import is now `from agent.tools import (...)`.
  - Because `uvicorn main:app` is run from `c:\Krishi-Mitra\backend`, `backend` is the top-level directory in `sys.path`. Python resolves `agent` as a package (containing `__init__.py`) and loads `agent.tools`.
- **List of all tools in `agent/tools.py`**:
  1. `get_weather(location: str) -> str`: Calls OpenWeather API, derives fungal risk.
  2. `get_mandi_price(crop: str) -> str`: Calls data.gov.in AGMARKNET API with hardcoded mock price fallback.
  3. `get_treatment(disease: str) -> str`: Multi-word matching against `disease_db.json`.
  4. `get_disease_progression(disease: str) -> str`: Lookups daily spread rate from `progression_db.json`.
  5. `get_nearby_mandis(location: str) -> str`: Searches `mandi_coordinates.json` by name, falls back to OpenStreetMap Nominatim geocoding.
  6. `get_govt_schemes(state: str) -> str`: Returns static hardcoded schemes (PM Fasal Bima, PM Kisan, KCC, Soil Health Card).
- **Grep for model strings**:
  - `GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")` in:
    - `agent/agent.py`
    - `services/whatsapp_service.py`
    - `services/disease_service.py`
    - `outbreak/service.py`
    - `legacy/agent_scheduler.py`
  - In `routes/soil.py` (line 86): Hardcoded vision model `meta-llama/llama-4-scout-17b-16e-instruct`.

---

## 6. Mandi Prices & Ingestion Jobs
- **Price Sources**:
  1. `data.gov.in` AGMARKNET API (resource `9ef84268-d588-465a-a308-a864a43d0070`).
  2. NaPanta website scraper (`https://www.napanta.com/market-price/karnataka/...`).
- **Difference between the two scheduled ingestion jobs**:
  1. **`daily_price_fetch` (00:00 UTC/Midnight via `backend/scheduler.py`)**:
     - Calls `services.price_fetcher.run_daily_fetch()`.
     - Iterates through 20 core commodities, queries `data.gov.in` with limit 500 per commodity.
     - Checks if Karnataka rows exist for each commodity; if not, triggers the fallback `scrape_napanta_karnataka()`.
  2. **`daily_karnataka_scrape` (10:20 IST via `backend/scheduler.py`)**:
     - Runs `scripts.scrape_karnataka_napanta.run()`.
     - Scrapes specific Karnataka markets from NaPanta (`bangalore`, `bellary`, `kustagi`, etc.) with pagination, crawling up to 10 pages and parsing HTML tables.
- **Freshness of `mandi_prices` in live DB**:
  - For top commodities (`Onion`, `Tomato`, `Brinjal`, `Potato`, `Carrot`, `Cabbage`, `Beans`, `Cauliflower`, `Pumpkin`, `Maize`, `Groundnut`, `Rice`, `Wheat`, `Cotton`, `Soyabean`): Max date is **today (2026-10-21)**.
  - For regional commodities ingested primarily via old test runs or specific scrapers (e.g., `Banana - Green`, `Ginger(Green)`, `Sweet Potato`, `Garlic`, `Arecanut`): Max dates date back to **2026-04-02 / 2026-04-03**.

---

## 7. Logic Inside `routes/*.py` That WhatsApp Should Reuse
1. **`routes/diagnose.py` & `routes/severity.py`**:
   - `services/severity_service.py` (`calculate_severity`, `get_overall_severity`): Calculates exact diseased leaf percentage from bounding boxes and thresholds.
2. **`routes/treatment.py`**:
   - `services/disease_service.py` (`lookup_static`, `lookup_claude` / Groq): Fallback AI lookup if disease is not found in static `disease_db.json`.
3. **`routes/progression.py`**:
   - `services/progression_service.py` (`predict_progression`): Calculates day-to-day spread estimates based on `progression_db.json`.
4. **`routes/market.py`**:
   - `services/market_service.py` (`find_nearby_mandis`, `get_latest_prices`): Calculates transport cost, distance from farmer lat/lng, and net price per quintal.
   - `services/prediction_service.py` (`predict_prices`): 7-day price forecasting based on historical trends.
5. **`routes/soil.py`**:
   - Multimodal soil/nutrient deficiency inspection via vision model.

---

## 8. Status of the Four Features
| Feature | Status | Notes |
|---|---|---|
| **Onboarding** | **Partial** | Multi-lingual language selection (Hindi, Kannada, English) works; name prompt works; but state is stored in memory (`_pending_name`), so server reboots drop in-progress sessions. Missing location onboarding step (only triggered on mandi price request). Database default name `'Kisan bhai'` causes false positives. |
| **Mandi Discovery & Alerts** | **Complete** | Mandi price queries, location-based transport calculation, net price sorting, daily official price ingestion (`data.gov.in`), Karnataka fallback scraping, and proactive price alert threshold triggers are fully implemented. |
| **Disease Diagnosis** | **Partial** | Image validation and disease inference run via ONNX, but there is a major class and model mismatch (detailed in #9 and #12). Bounding box calculations are mocked (`bbox_pct = conf * 40`) rather than parsed from detector. |
| **Outbreak Monitoring** | **Complete** | Periodic job checks `detections` for severity > 5 and spread = true, calculates distance and compass bearing to nearby farmers within 20km, generates AI preventive tips via Groq, and sends WhatsApp alert notifications. |

---

## 9. Model Verification: `best.pt`, `classifier.onnx`, and `detector.onnx`

### A. Ultralytics `best.pt`:
- **Task**: `detect` (Object Detection, YOLOv8n)
- **Names**: `{0: 'leaf'}` (1 class: detects leaf region)
- **Input size (`imgsz`)**: `640`
- **Output**: Single class leaf detection bounding boxes.

### B. `agent/model/classifier.onnx`:
- **Model Description**: `Ultralytics YOLOv8l-cls model trained on /content/plantvillage_yolo`
- **Task**: `classify`
- **Classes**: **15 classes only**, NOT 38:
  ```json
  {
    0: 'Pepper__bell___Bacterial_spot', 1: 'Pepper__bell___healthy',
    2: 'Potato___Early_blight', 3: 'Potato___Late_blight', 4: 'Potato___healthy',
    5: 'Tomato_Bacterial_spot', 6: 'Tomato_Early_blight', 7: 'Tomato_Late_blight',
    8: 'Tomato_Leaf_Mold', 9: 'Tomato_Septoria_leaf_spot',
    10: 'Tomato_Spider_mites_Two_spotted_spider_mite', 11: 'Tomato__Target_Spot',
    12: 'Tomato__Tomato_YellowLeaf__Curl_Virus', 13: 'Tomato__Tomato_mosaic_virus',
    14: 'Tomato_healthy'
  }
  ```
- **Inputs**: `[1, 3, 224, 224]`
- **Outputs**: `[1, 15]`
- **Probabilities**: **Already Softmaxed** (sum across output row equals 1.0).
- **CRITICAL BUG in `agent/diagnose.py`**:
  `CLASS_NAMES` in `agent/diagnose.py` has **38 classes** (starting with `Apple___Apple_scab`). But `classifier.onnx` has **15 classes** (starting with `Pepper__bell___Bacterial_spot`).
  Because `diagnose.py` indexes `CLASS_NAMES[top]`, index 0 (`Pepper__bell___Bacterial_spot`) gets mapped to `Apple___Apple_scab`! Every diagnosis prediction is mislabeled.

### C. `agent/model/detector.onnx`:
- **Model Description**: `Ultralytics detector_best model trained on /content/plantdoc/data.yaml`
- **Task**: `detect`
- **Classes**: `{0: 'leaf'}`
- **Inputs**: `[1, 3, 640, 640]`
- **Outputs**: `[1, 5, 8400]` (Raw YOLOv8 detection tensor: `[x, y, w, h, class_conf]` across 8400 candidate anchor boxes).
- **Export Relationship**:
  - `detector.onnx` was exported from `detector_best` (YOLO detection on plantdoc).
  - `best.pt` has identical task (`detect`) and classes (`{0: 'leaf'}`).
- **Detector Output Parsing Bug**:
  In `agent/diagnose.py` lines 202-205:
  ```python
  det_out = det.run(None, {det.get_inputs()[0].name: det_arr})
  if det_out and len(det_out[0]) > 0:
      boxes = len(det_out[0]) # len(det_out[0]) is always 1 (batch dimension)!
  ```
  `det_out[0]` has shape `(1, 5, 8400)`. It is **never decoded with NMS or thresholding**. Furthermore, `bbox_pct` is faked as `bbox_pct = conf * 40` rather than computed from bounding boxes.

---

## 10. `services/profile_state.py` State Location
- **Location**: In-memory Python dictionary `_pending_name = {}`.
- Does **NOT** live in the DB.

---

## 11. Guardrails (`agent/guardrails.py`)
- **Greetings like "hi"**:
  - `check_message("hi")` evaluates `FARMING_KEYWORDS` and `OUT_OF_SCOPE`. Since "hi" is not in `OUT_OF_SCOPE`, it falls through to line 78:
    ```python
    return GuardrailResult(allowed=True)
    ```
  - It does **not block** greetings.
- **Language Assumptions**:
  - **Yes, it assumes Hindi/Hinglish**:
    - Crisis hotline reply is hardcoded in Romanized Hindi ("Bhai, lagta hai aap mushkil waqt se guzar rahe hain...").
    - Out of scope reply is hardcoded in Romanized Hindi ("Bhai, main sirf kheti mein help kar sakta hoon...").
    - Unsupported media reply is hardcoded in Romanized Hindi ("Bhai, sirf photo bhejo...").
    - It uses gendered address ("Bhai") on all blocked messages.

---

## 12. Mapping Analysis for the 38 `CLASS_NAMES`
- Total classes defined in `agent/diagnose.py`: **38**
- Total classes mapped in `CLASSIFIER_TO_DB`: **20**
- Total unmapped classes (**18**):
  - Healthy classes (11): `'Apple___healthy'`, `'Blueberry___healthy'`, `'Cherry___healthy'`, `'Corn___healthy'`, `'Grape___healthy'`, `'Peach___healthy'`, `'Pepper___healthy'`, `'Potato___healthy'`, `'Raspberry___healthy'`, `'Soybean___healthy'`, `'Strawberry___healthy'`, `'Tomato___healthy'`
  - Diseased classes with no mapping (7):
    1. `'Apple___Black_rot'`
    2. `'Grape___Esca'`
    3. `'Grape___Leaf_blight'`
    4. `'Orange___Haunglongbing'`
    5. `'Peach___Bacterial_spot'`
    6. `'Tomato___Target_Spot'`
- Database key mismatch:
  - `'Tomato___Late_blight'` maps to `'Tomato late blight leaf'`, but `data/disease_db.json` has capital `'Tomato Late blight leaf'`. Because dictionary lookup is case-sensitive, this lookup returns empty `{}`.

---

## Prioritized Fix List (Awaiting Approval)

### Priority 1: Critical Correctness & Stability
1. **Fix ONNX Classifier Indexing**:
   - Replace the 38-item `CLASS_NAMES` in `agent/diagnose.py` with the actual 15 classes from `classifier.onnx`, or export a model matching the full 38 PlantVillage classes.
   - Fix `'Tomato late blight leaf'` casing in `CLASSIFIER_TO_DB` to match `disease_db.json`.
2. **Move Onboarding State to Database**:
   - Persist onboarding state (`onboarding_step`: e.g. `'LANGUAGE'`, `'NAME'`, `'LOCATION'`, `'COMPLETE'`) directly onto the `farmers` table using `ALTER TABLE farmers ADD COLUMN IF NOT EXISTS onboarding_step text;`.
   - Eliminate volatile in-memory dicts (`_pending_name`, `_pending_location`).
3. **Decouple Twilio Webhook from Synchronous Inference**:
   - Update `routes/whatsapp.py` to immediately return an empty TwiML `<Response/>`.
   - Dispatch background tasks for image processing, ONNX, and Groq LLM inference, replying via `send_proactive_message` to prevent Twilio 15-second timeouts.

### Priority 2: Real Measurements & Detector Integration
4. **Implement Real YOLO Bounding Box Parsing & Severity Calculation**:
   - Replace fake `bbox_pct = conf * 40` with real inference using `best.pt` via `services/yolo_service.py` (which already loads `best.pt` and extracts `xyxy` and `conf`), or parse the raw `(1, 5, 8400)` tensor from `detector.onnx`.
   - Connect detections directly to `services/severity_service.py` instead of guessing.

### Priority 3: Communication & Localization Quality
5. **Enforce Language & Identity Constraints**:
   - Strip all hardcoded `"bhai"` strings across `guardrails.py`, `language_onboarding.py`, `name_onboarding.py`, and `scheduler.py`.
   - Format messages in native scripts (Devanagari for Hindi, Kannada script for Kannada) based on `farmers.language`.
   - Remove fixed closing lines (`"Koi aur madad chahiye? 🌾"`).
   - Ensure the LLM never overrides identity fields (`name`, `language`, `location`).

---
*Awaiting your approval before making any code modifications.*
