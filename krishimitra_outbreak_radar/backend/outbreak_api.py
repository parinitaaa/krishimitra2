import os
from datetime import datetime, timedelta, timezone
from math import floor
from typing import Optional

import asyncpg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/outbreaks", tags=["Outbreak Radar"])
_pool: Optional[asyncpg.Pool] = None

def _database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)

async def initialize_outbreak_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            _database_url(),
            min_size=1,
            max_size=int(os.getenv("OUTBREAK_DB_POOL_MAX", "5")),
            command_timeout=10,
        )

async def close_outbreak_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

def get_pool():
    if _pool is None:
        raise HTTPException(
            status_code=503,
            detail="Outbreak Radar database pool is not initialized.",
        )
    return _pool

class DiseaseObservation(BaseModel):
    # Use a stable internal ID; never return it to the dashboard.
    farmer_id: str = Field(min_length=1, max_length=128)
    disease: str = Field(min_length=2, max_length=160)
    crop: Optional[str] = Field(default=None, max_length=100)
    confidence: float = Field(ge=0, le=1)
    severity: str = Field(default="Unknown", max_length=30)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

@router.get("/health")
async def outbreak_health():
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("select 1")
    return {"status": "ready"}

@router.post("/observations", status_code=201)
async def record_observation(item: DiseaseObservation):
    # Avoid recording low-confidence predictions as outbreak evidence.
    if item.confidence < 0.70:
        return {
            "status": "skipped",
            "reason": "Confidence below 0.70 threshold",
        }

    pool = get_pool()
    async with pool.acquire() as conn:
        row_id = await conn.fetchval(
            """
            insert into public.disease_observations
                (farmer_id, disease, crop, confidence, severity, latitude, longitude)
            values ($1, $2, $3, $4, $5, $6, $7)
            returning id
            """,
            item.farmer_id,
            item.disease.strip(),
            item.crop.strip() if item.crop else None,
            item.confidence,
            item.severity.strip() or "Unknown",
            item.latitude,
            item.longitude,
        )

    return {"status": "recorded", "observation_id": row_id}

@router.get("")
async def get_outbreak_signals(days: int = Query(default=7, ge=1, le=30)):
    pool = get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select farmer_id, disease, crop, confidence, severity,
                   latitude, longitude, detected_at
            from public.disease_observations
            where detected_at >= $1
            order by detected_at desc
            limit 10000
            """,
            cutoff,
        )

    # Approximate 0.05-degree grid cells (~5.5 km north-south).
    # Longitude cell width varies by latitude; use this as an MVP only.
    cells = {}
    for row in rows:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        lat_cell = floor(lat / 0.05)
        lon_width = max(0.02, 0.05 * abs(__import__("math").cos(__import__("math").radians(lat))))
        lon_cell = floor(lon / lon_width)
        key = (row["disease"], lat_cell, lon_cell)
        cell = cells.setdefault(key, {
            "disease": row["disease"],
            "crop": row["crop"],
            "lat_sum": 0.0,
            "lon_sum": 0.0,
            "count": 0,
            "farmers": set(),
            "confidence_sum": 0.0,
            "severities": [],
            "latest": row["detected_at"],
        })
        cell["lat_sum"] += lat
        cell["lon_sum"] += lon
        cell["count"] += 1
        cell["farmers"].add(row["farmer_id"])
        cell["confidence_sum"] += float(row["confidence"])
        cell["severities"].append(row["severity"])
        if row["detected_at"] > cell["latest"]:
            cell["latest"] = row["detected_at"]

    signals = []
    for (disease, lat_cell, lon_cell), cell in cells.items():
        unique_farmers = len(cell["farmers"])
        if unique_farmers < 3:
            continue

        avg_confidence = cell["confidence_sum"] / cell["count"]
        severe_count = sum(
            1 for s in cell["severities"]
            if (s or "").strip().lower() == "severe"
        )

        # Heuristic activity label for triage, not a verified epidemiological risk.
        if unique_farmers >= 10 or (unique_farmers >= 5 and severe_count >= 2):
            level = "high"
        elif unique_farmers >= 5:
            level = "moderate"
        else:
            level = "watch"

        signals.append({
            "id": f"{disease}:{lat_cell}:{lon_cell}",
            "disease": disease,
            "crop": cell["crop"],
            "latitude": round(cell["lat_sum"] / cell["count"], 5),
            "longitude": round(cell["lon_sum"] / cell["count"], 5),
            "observations": cell["count"],
            "unique_farmers": unique_farmers,
            "average_confidence": round(avg_confidence, 3),
            "severe_observations": severe_count,
            "level": level,
            "latest_detection": cell["latest"].isoformat(),
            "window_days": days,
        })

    signals.sort(
        key=lambda x: (
            {"high": 3, "moderate": 2, "watch": 1}[x["level"]],
            x["unique_farmers"],
            x["observations"],
        ),
        reverse=True,
    )

    return {
        "status": "success",
        "window_days": days,
        "signals": signals,
        "total_signals": len(signals),
        "message": (
            "Signals represent clusters of model detections and require "
            "verification; they do not confirm disease spread."
        ),
    }
