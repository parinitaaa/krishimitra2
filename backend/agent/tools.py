# backend/agent/tools.py
"""
Typed LangChain tools for KrishiMitra.
All tools have pydantic input schemas, rich descriptions, and return structured dictionaries.
No mock price fallback is used.
"""

from __future__ import annotations

import os
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextvars import ContextVar
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Context variable for the currently active farmer phone in the session
active_farmer_phone: ContextVar[Optional[str]] = ContextVar("active_farmer_phone", default=None)

ROOT = Path(__file__).parent.parent.parent
DISEASE_DB_PATH = ROOT / "backend" / "data" / "disease_db.json"
PROG_DB_PATH = ROOT / "backend" / "data" / "progression_db.json"
MANDI_COORDS_PATH = ROOT / "backend" / "data" / "mandi_coordinates.json"

DISEASE_DB = json.loads(DISEASE_DB_PATH.read_text(encoding="utf-8")) if DISEASE_DB_PATH.exists() else {}
PROGRESSION_DB = json.loads(PROG_DB_PATH.read_text(encoding="utf-8")) if PROG_DB_PATH.exists() else {}
MANDI_COORDS = json.loads(MANDI_COORDS_PATH.read_text(encoding="utf-8")) if MANDI_COORDS_PATH.exists() else {}


def _get_active_farmer_profile() -> dict:
    phone = active_farmer_phone.get()
    if not phone:
        return {}
    try:
        from farmer_store import get_farmer
        return get_farmer(phone)
    except Exception:
        return {}


# ── 1. Weather Tool ───────────────────────────────────────────────────────────

class WeatherInput(BaseModel):
    location: Optional[str] = Field(None, description="City, district, or village name to fetch weather for. If omitted, uses farmer's saved location.")


@tool("get_weather", args_schema=WeatherInput)
def get_weather(location: Optional[str] = None) -> dict:
    """Get current weather, humidity, temperature, and disease/fungal risk for a farm location."""
    loc = location
    if not loc or not loc.strip():
        f = _get_active_farmer_profile()
        loc = f.get("district") or f.get("location") or "India"

    try:
        key = os.getenv("OPENWEATHER_API_KEY")
        if not key:
            return {"location": loc, "error": "OpenWeather API key not configured"}

        res = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": f"{loc}, India", "appid": key, "units": "metric"},
            timeout=6,
        )
        if res.status_code != 200:
            return {"location": loc, "error": f"Weather service returned status {res.status_code}"}

        data = res.json()
        temp = data.get("main", {}).get("temp")
        humidity = data.get("main", {}).get("humidity")
        condition = data.get("weather", [{}])[0].get("description", "clear")

        risk = "LOW"
        spray_advice = "Good conditions for spraying"
        if humidity is not None and temp is not None:
            if humidity > 80 and 20 <= temp <= 30:
                risk = "HIGH"
                spray_advice = "High fungal disease risk — avoid spraying today as rain/high humidity washes off sprays"
            elif humidity > 60:
                risk = "MEDIUM"
                spray_advice = "Moderate risk — monitor crop closely"

        return {
            "location": loc,
            "temperature_c": temp,
            "humidity_pct": humidity,
            "condition": condition,
            "fungal_risk": risk,
            "spray_advice": spray_advice,
        }
    except Exception as e:
        return {"location": loc, "error": f"Failed to retrieve weather: {str(e)}"}


# ── 2. Mandi Price Tool (uses teammate's fetcher; no mock fallback) ───────────

class MandiPriceInput(BaseModel):
    crop: str = Field(description="Name of the agricultural commodity or crop, e.g. tomato, potato, onion, wheat")
    state: Optional[str] = Field(None, description="Optional Indian state name to filter prices")


@tool("get_mandi_price", args_schema=MandiPriceInput)
def get_mandi_price(crop: str, state: Optional[str] = None) -> dict:
    """Get current mandi prices for a crop. Returns error: no_data if nothing real is found."""
    if not crop or not crop.strip():
        return {"missing": ["crop"]}

    clean_crop = crop.strip().lower()
    target_state = state.strip() if state else None
    if not target_state:
        f = _get_active_farmer_profile()
        target_state = f.get("state")

    try:
        from services.db import SessionLocal
        from services.price_fetcher import ensure_commodity_prices_fresh
        from services.market_service import get_latest_prices, get_all_latest_prices

        with SessionLocal() as db:
            try:
                # Fetches from the API / Karnataka scraper if today's data is missing
                ensure_commodity_prices_fresh(clean_crop, db)
            except Exception as e:
                print(f"[get_mandi_price] fresh-fetch failed for {clean_crop}: {e}")

            if target_state:
                rows = get_latest_prices(clean_crop, target_state, db)
            else:
                rows = get_all_latest_prices(clean_crop, db)

            if rows:
                return {
                    "crop": clean_crop,
                    "state": target_state,
                    "source": "mandi_database",
                    "prices": [
                        {
                            "market": r.get("market"),
                            "district": r.get("district"),
                            "state": r.get("state"),
                            "modal_price": r.get("modal_price"),
                            "min_price": r.get("min_price"),
                            "max_price": r.get("max_price"),
                            "date":  str(r.get("date") or r.get("arrival_date") or ""),
                        }
                        for r in rows[:5]
                    ],
                }
    except Exception as e:
        print(f"[get_mandi_price] error for {clean_crop}: {e}")

    # No real data: say so honestly (never invent a price)
    return {
        "error": "no_data",
        "crop": clean_crop,
        "state": target_state,
        "message": f"No current mandi prices found for {clean_crop}.",
    }


# ── 3. Treatment & Diagnosis Tools ────────────────────────────────────────────

class TreatmentInput(BaseModel):
    disease: str = Field(description="Name of the plant disease or pest condition")
    crop: Optional[str] = Field(None, description="Optional crop name to refine treatment")


@tool("get_treatment", args_schema=TreatmentInput)
def get_treatment(disease: str, crop: Optional[str] = None) -> dict:
    """Get detailed organic and chemical remedies, pathogen information, and urgency for a crop disease."""
    if not disease or not disease.strip():
        return {"missing": ["disease"]}

    d_lower = disease.strip().lower()
    match = None

    for key, val in DISEASE_DB.items():
        k_lower = key.lower()
        if d_lower in k_lower or k_lower in d_lower:
            match = val
            break
        d_words = set(d_lower.split())
        k_words = set(k_lower.split())
        if len(d_words & k_words) >= 2:
            match = val
            break

    if match:
        remedies = match.get("remedies", {})
        return {
            "disease": match.get("display_name", disease),
            "crop": match.get("crop", crop or "Unknown"),
            "pathogen": match.get("pathogen", ""),
            "symptoms": match.get("symptoms", ""),
            "urgency": match.get("urgency", ""),
            "organic_remedies": remedies.get("organic", []),
            "chemical_remedies": remedies.get("chemical", []),
            "prevention": remedies.get("prevention", []),
        }

    return {
        "disease": disease,
        "crop": crop,
        "found": False,
        "advice": f"No specific entry found for '{disease}'. Consult your local Krishi Vigyan Kendra or agricultural extension officer.",
    }


@tool("get_treatment_options", args_schema=TreatmentInput)
def get_treatment_options(disease: str, crop: Optional[str] = None) -> dict:
    """Detailed treatment options categorized into organic, chemical, and preventive practices."""
    return get_treatment.func(disease=disease, crop=crop)


# ── 4. Disease Progression Tool ───────────────────────────────────────────────

class DiseaseProgressionInput(BaseModel):
    disease: str = Field(description="Name of the crop disease")


@tool("get_disease_progression", args_schema=DiseaseProgressionInput)
def get_disease_progression(disease: str) -> dict:
    """Get the estimated rate at which a disease spreads if untreated over 7 days."""
    if not disease or not disease.strip():
        return {"missing": ["disease"]}

    d_lower = disease.strip().lower()
    for key, val in PROGRESSION_DB.items():
        if d_lower in key.lower() or key.lower() in d_lower:
            rate = float(val.get("daily_spread_rate", 0))
            note = val.get("untreated_note", "")
            day7 = min(100.0, rate * 7 * 100)
            return {
                "disease": key,
                "daily_spread_rate_pct": round(rate * 100, 1),
                "day_7_spread_pct": round(day7, 1),
                "warning": note,
            }

    return {
        "disease": disease,
        "found": False,
        "message": f"Spread progression model not available for '{disease}'. Prompt treatment is advised.",
    }


# ── 5. Nearby Mandis & Best Market ───────────────────────────────────────────

class NearbyMandisInput(BaseModel):
    location: Optional[str] = Field(None, description="City, district, or town name")
    lat: Optional[float] = Field(None, description="Optional latitude coordinate")
    lng: Optional[float] = Field(None, description="Optional longitude coordinate")


@tool("get_nearby_mandis", args_schema=NearbyMandisInput)
def get_nearby_mandis(
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict:
    """Find the closest agricultural mandis based on coordinates or place name."""
    f_lat, f_lng = lat, lng

    if f_lat is None or f_lng is None:
        f = _get_active_farmer_profile()
        f_lat = f.get("lat")
        f_lng = f.get("lng")

    if (f_lat is None or f_lng is None) and location:
        from services.geocode_service import geocode_location
        geo = geocode_location(location)
        if geo:
            f_lat, f_lng = geo["lat"], geo["lng"]

    if f_lat is None or f_lng is None:
        return {"missing": ["location"], "message": "Location coordinates needed to find nearest mandis."}

    from services.market_service import find_nearest_from_json
    mandis = find_nearest_from_json(f_lat, f_lng, top_n=5)
    return {
        "reference_lat": f_lat,
        "reference_lng": f_lng,
        "nearby_mandis": mandis,
    }


class BestMarketInput(BaseModel):
    crop: str = Field(description="Crop commodity to sell, e.g. tomato, onion")
    lat: Optional[float] = Field(None, description="Farmer latitude coordinate")
    lng: Optional[float] = Field(None, description="Farmer longitude coordinate")
    state: Optional[str] = Field(None, description="Optional state filter")


@tool("find_best_market", args_schema=BestMarketInput)
def find_best_market(
    crop: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    state: Optional[str] = None,
) -> dict:
    """Find the most profitable mandi to sell a crop, factoring in modal price and transport costs."""
    if not crop or not crop.strip():
        return {"missing": ["crop"]}

    f_lat, f_lng = lat, lng
    f_state = state

    if f_lat is None or f_lng is None:
        f = _get_active_farmer_profile()
        f_lat = f.get("lat")
        f_lng = f.get("lng")
        if not f_state:
            f_state = f.get("state")

    if f_lat is None or f_lng is None:
        return {"missing": ["location"], "message": "Need location coordinates to compute transport costs and best mandi."}

    from services.db import SessionLocal
    from services.market_service import find_best_mandi_for_commodity

    with SessionLocal() as db:
        results = find_best_mandi_for_commodity(
            farmer_lat=f_lat,
            farmer_lng=f_lng,
            commodity=crop.strip().lower(),
            radius_km=500,
            top_n=3,
            db=db,
            state=f_state,
        )

    if not results:
        return {
            "crop": crop,
            "error": "no_mandis_found",
            "message": f"No mandis found for {crop} within 500km.",
        }

    return {
        "crop": crop,
        "best_mandi": results[0],
        "alternatives": results[1:],
    }


# ── 6. Price Prediction Tool ──────────────────────────────────────────────────

class PredictPriceInput(BaseModel):
    crop: str = Field(description="Name of the crop to forecast prices for")
    market: Optional[str] = Field(None, description="Optional specific market name")


@tool("predict_price", args_schema=PredictPriceInput)
def predict_price(crop: str, market: Optional[str] = None) -> dict:
    """Forecast future mandi price trend for a crop 7 days ahead with seasonal & trend models."""
    if not crop or not crop.strip():
        return {"missing": ["crop"]}

    clean_crop = crop.strip().lower()
    from services.db import SessionLocal
    from services.prediction_service import predict_prices
    from services.market_service import find_best_mandi_for_commodity

    target_market = market or "General"
    f = _get_active_farmer_profile()
    f_lat = f.get("lat")
    f_lng = f.get("lng")

    with SessionLocal() as db:
        if not market and f_lat and f_lng:
            best = find_best_mandi_for_commodity(f_lat, f_lng, clean_crop, 500, 1, db)
            if best:
                target_market = best[0]["market"]

        pred = predict_prices(clean_crop, target_market, db)

    if pred.get("error"):
        return {"crop": clean_crop, "market": target_market, "error": pred["error"]}

    return {
        "crop": clean_crop,
        "market": pred.get("market"),
        "current_price": pred.get("current_price"),
        "predicted_7_day_price": pred.get("day_7_price"),
        "change_pct": pred.get("change_pct"),
        "trend": pred.get("trend"),
        "advice": pred.get("advice"),
    }


# ── 7. Price Alerts Tools ─────────────────────────────────────────────────────

class CreatePriceAlertInput(BaseModel):
    crop: str = Field(description="Crop commodity to monitor, e.g. tomato")
    target_price: float = Field(description="Target price per quintal in Rupees")
    direction: str = Field("above", description="Condition: 'above' (when price rises) or 'below' (when price drops)")
    market: Optional[str] = Field(None, description="Optional specific mandi market name")


@tool("create_price_alert", args_schema=CreatePriceAlertInput)
def create_price_alert(
    crop: str,
    target_price: float,
    direction: str = "above",
    market: Optional[str] = None,
) -> dict:
    """Set an automated price alert that notifies the farmer when crop rate crosses target threshold."""
    if not crop or not crop.strip():
        return {"missing": ["crop"]}
    if target_price <= 0:
        return {"missing": ["target_price"], "message": "Target price must be a positive number."}

    phone = active_farmer_phone.get()
    if not phone:
        return {"error": "no_active_farmer", "message": "No active farmer session found."}

    farmer = _get_active_farmer_profile()
    f_lat = farmer.get("lat")
    f_lng = farmer.get("lng")
    if f_lat is None or f_lng is None:
        return {
            "missing": ["location"],
            "message": "Farmer location (latitude/longitude) is needed to check alerts at nearby mandis. Please share your location.",
        }

    dir_clean = "below" if direction.lower() in ("below", "neeche", "less", "under") else "above"
    from farmer_store import save_price_alert

    save_price_alert(
        phone=phone,
        commodity=crop.strip().lower(),
        target_price=target_price,
        direction=dir_clean,
        market=market,
    )
    return {
        "status": "created",
        "crop": crop.strip().title(),
        "target_price": target_price,
        "direction": dir_clean,
        "market": market or "All nearby mandis",
    }


class ListPriceAlertsInput(BaseModel):
    pass


@tool("list_price_alerts", args_schema=ListPriceAlertsInput)
def list_price_alerts() -> dict:
    """List all currently active price alert subscriptions for the farmer."""
    phone = active_farmer_phone.get()
    if not phone:
        return {"alerts": []}

    from farmer_store import get_farmer_alerts
    alerts = get_farmer_alerts(phone)
    return {"alerts": alerts, "total": len(alerts)}


class CancelPriceAlertInput(BaseModel):
    alert_id: int = Field(description="Numeric ID of the price alert to deactivate")


@tool("cancel_price_alert", args_schema=CancelPriceAlertInput)
def cancel_price_alert(alert_id: int) -> dict:
    """Deactivate or cancel an existing price alert."""
    from farmer_store import deactivate_alert
    deactivate_alert(alert_id)
    return {"status": "cancelled", "alert_id": alert_id}


# ── 8. Government Schemes Tool ────────────────────────────────────────────────

class GovtSchemesInput(BaseModel):
    state: Optional[str] = Field(None, description="Farmer's state, e.g. Karnataka, Maharashtra")


@tool("get_govt_schemes", args_schema=GovtSchemesInput)
def get_govt_schemes(state: Optional[str] = None) -> dict:
    """Get active central and state agricultural welfare schemes, subsidies, and insurance options."""
    st = state
    if not st:
        f = _get_active_farmer_profile()
        st = f.get("state") or "India"

    schemes = [
        {
            "name": "PM Fasal Bima Yojana (PMFBY)",
            "benefit": "Comprehensive crop insurance against drought, floods, pests and unseasonal weather",
            "eligibility": "All farmers growing notified crops in notified areas",
            "how_to_apply": "Nearest nationalized bank, CSC center, or pmfby.gov.in before cutoff date",
        },
        {
            "name": "PM Kisan Samman Nidhi",
            "benefit": "Rs.6,000 per year income support in 3 equal installments of Rs.2,000",
            "eligibility": "Landholding farmer families with cultivable land",
            "how_to_apply": "Register at pmkisan.gov.in or through village revenue officer",
        },
        {
            "name": "Kisan Credit Card (KCC)",
            "benefit": "Subsidized crop production loans at 4% effective interest rate with prompt repayment",
            "eligibility": "Individual/joint cultivators, tenant farmers, self-help groups",
            "how_to_apply": "Apply at any rural, cooperative, or commercial bank branch",
        },
        {
            "name": "Soil Health Card Scheme",
            "benefit": "Free soil nutrient testing with tailored NPK and micronutrient recommendations",
            "eligibility": "All agricultural landowners",
            "how_to_apply": "Sample collection via local Agriculture Department / Krishi Bhavan",
        },
    ]

    return {
        "state": st,
        "schemes": schemes,
        "disclaimer": "Confirm details at your nearest agriculture office or the official scheme website.",
    }


# ── 9. Input Shops / Agricultural Centers Tool ────────────────────────────────

class FindInputShopsInput(BaseModel):
    location: Optional[str] = Field(None, description="Town, village, or district name")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lng: Optional[float] = Field(None, description="Longitude coordinate")


@tool("find_input_shops", args_schema=FindInputShopsInput)
def find_input_shops(
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict:
    """Find nearby agricultural input dealers, fertilizer/seed distributors, and Krishi Vigyan Kendras (KVK)."""
    f_lat, f_lng = lat, lng
    loc_name = location

    if f_lat is None or f_lng is None:
        f = _get_active_farmer_profile()
        f_lat = f.get("lat")
        f_lng = f.get("lng")
        if not loc_name:
            loc_name = f.get("district") or f.get("location")

    if not loc_name and (f_lat is None or f_lng is None):
        return {"missing": ["location"], "message": "Please share your village or district name to find input stores."}

    # Query Nominatim for agri seed/fertilizer stores if location string available
    shops = []
    if loc_name:
        try:
            res = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": f"agricultural supplies {loc_name}, India",
                    "format": "json",
                    "limit": 3,
                },
                headers={"User-Agent": "KrishiMitra/1.0"},
                timeout=5,
            )
            for r in res.json():
                shops.append({
                    "name": r.get("display_name", "").split(",")[0],
                    "address": r.get("display_name"),
                    "type": "Agricultural Supplies",
                })
        except Exception:
            pass

    if not shops:
        dist = loc_name or "local district"
        shops = [
            {
                "name": f"IFFCO Kisan Seva Kendra ({dist})",
                "type": "Fertilizers, Seeds & Pesticides",
                "address": f"Near APMC Mandi, {dist}",
            },
            {
                "name": f"Krishi Vigyan Kendra (KVK - {dist})",
                "type": "Certified Seeds & Expert Agronomy Consultation",
                "address": f"District Agricultural Training Centre, {dist}",
            },
            {
                "name": f"Primary Agricultural Credit Society (PACS - {dist})",
                "type": "Subsidized Urea, DAP, Seeds",
                "address": f"Block Development Office, {dist}",
            },
        ]

    return {
        "location": loc_name or f"{f_lat:.2f}, {f_lng:.2f}",
        "input_shops": shops,
        "note": "Check with your local Primary Agricultural Cooperative Society (PACS) or licensed dealer for government-subsidized inputs.",
    }


# ── 10. Update Farmer Profile Tool ────────────────────────────────────────────

class UpdateFarmerProfileInput(BaseModel):
    soil: Optional[str] = Field(None, description="Soil type, e.g. Black, Red, Alluvial, Sandy loam, Clay")
    water_source: Optional[str] = Field(None, description="Water or irrigation source, e.g. Borewell, Canal, Rainfed, Drip")
    crops: Optional[List[str]] = Field(None, description="List of crops currently cultivated, e.g. ['Tomato', 'Wheat']")
    farm_size_acres: Optional[float] = Field(None, description="Farm size in acres")


@tool("update_farmer_profile", args_schema=UpdateFarmerProfileInput)
def update_farmer_profile(
    soil: Optional[str] = None,
    water_source: Optional[str] = None,
    crops: Optional[List[str]] = None,
    farm_size_acres: Optional[float] = None,
) -> dict:
    """Update the farmer's agronomic profile (soil type, irrigation/water source, crops, farm size)."""
    phone = active_farmer_phone.get()
    if not phone:
        return {"error": "no_active_farmer", "message": "No active farmer session found."}

    from farmer_store import update_farmer_profile as db_update_profile, get_farmer

    updates = {}
    if soil:
        updates["soil_type"] = soil.strip().title()
    if water_source:
        updates["water_source"] = water_source.strip().title()
    if crops:
        clean_crops = [c.strip().title() for c in crops if c and c.strip()]
        if clean_crops:
            updates["crops"] = clean_crops
    if farm_size_acres is not None and farm_size_acres > 0:
        updates["farm_size_acres"] = float(farm_size_acres)

    if updates:
        db_update_profile(phone, **updates)

    updated = get_farmer(phone)
    return {
        "status": "updated",
        "soil_type": updated.get("soil_type"),
        "water_source": updated.get("water_source"),
        "crops": updated.get("crops"),
        "farm_size_acres": updated.get("farm_size_acres"),
    }


# List of all available LangChain tools
ALL_TOOLS = [
    get_weather,
    get_mandi_price,
    get_treatment,
    get_treatment_options,
    get_disease_progression,
    get_nearby_mandis,
    find_best_market,
    predict_price,
    create_price_alert,
    list_price_alerts,
    cancel_price_alert,
    get_govt_schemes,
    find_input_shops,
    update_farmer_profile,
]
