from sqlalchemy.orm import Session
from math import radians, cos, sin, asin, sqrt
import math
from sqlalchemy import text
import uuid
from farmer_store import TEST_PHONE_PREFIX, is_test_phone, normalize_phone

def distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in km using Haversine formula."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999999.0
    dlon = radians(lon2 - lon1)
    dlat = radians(lat1 - lat2)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371 * c


def get_direction(lat1, lon1, lat2, lon2):
    """
    Returns compass direction from farmer (lat1, lon1) -> outbreak (lat2, lon2).
    """
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = (
        math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
        - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    )

    bearing = math.degrees(math.atan2(y, x))
    bearing = (bearing + 360) % 360

    directions = [
        "North", "North-East", "East", "South-East",
        "South", "South-West", "West", "North-West"
    ]

    index = round(bearing / 45) % 8
    return directions[index]


def get_case_by_id(db: Session, case_id: str | uuid.UUID) -> dict | None:
    """Fetch disease case record by id."""
    try:
        row = db.execute(
            text("""
                SELECT id, phone, crop, disease, status, confidence,
                       severity_level, severity_source, severity_score,
                       lat, lng, spread_modes, outbreak_evaluated_at, created_at
                FROM disease_cases
                WHERE id = :case_id
            """),
            {"case_id": str(case_id)},
        ).mappings().first()
        return dict(row) if row else None
    except Exception:
        db.rollback()
        return None


def get_eligible_outbreak_recipients(db: Session, reporter_phone: str) -> list[dict]:
    """
    Fetch potential recipient farmers:
    - onboarding_step == 'done'
    - proactive_opt_in is True (or default true/null)
    - lat & lng not null
    - excluding reporter
    - test isolation: if reporter is a test phone, query only test phones; else exclude test phones.
    """
    rep_clean = normalize_phone(reporter_phone)
    is_test = is_test_phone(rep_clean)

    if is_test:
        sql = text("""
            SELECT phone, name, language, lat, lng, crops, proactive_opt_in
            FROM farmers
            WHERE lat IS NOT NULL
              AND lng IS NOT NULL
              AND onboarding_step = 'done'
              AND (proactive_opt_in IS TRUE OR proactive_opt_in IS NULL)
              AND phone != :reporter_phone
              AND phone LIKE :test_prefix
        """)
    else:
        sql = text("""
            SELECT phone, name, language, lat, lng, crops, proactive_opt_in
            FROM farmers
            WHERE lat IS NOT NULL
              AND lng IS NOT NULL
              AND onboarding_step = 'done'
              AND (proactive_opt_in IS TRUE OR proactive_opt_in IS NULL)
              AND phone != :reporter_phone
              AND phone NOT LIKE :test_prefix
        """)

    rows = db.execute(
        sql,
        {"reporter_phone": rep_clean, "test_prefix": f"{TEST_PHONE_PREFIX}%"},
    ).mappings().all()
    return [dict(r) for r in rows]


def count_farmer_recent_outbreak_alerts(db: Session, phone: str, hours: int = 24) -> int:
    """Count outbreak alerts sent to this farmer in the last N hours."""
    clean = normalize_phone(phone)
    val = db.execute(
        text("""
            SELECT count(*) FROM outbreak_alerts_sent
            WHERE recipient_phone = :phone
              AND sent_at >= NOW() - (:hours || ' hours')::interval
        """),
        {"phone": clean, "hours": hours},
    ).scalar()
    return int(val or 0)


def try_claim_outbreak_alert(db: Session, case_id: str | uuid.UUID, recipient_phone: str) -> bool:
    """
    Idempotent insert into outbreak_alerts_sent on conflict do nothing.
    Returns True if inserted successfully (claimed), False if conflict.
    """
    clean = normalize_phone(recipient_phone)
    res = db.execute(
        text("""
            INSERT INTO outbreak_alerts_sent (case_id, recipient_phone, sent_at)
            VALUES (:case_id, :phone, NOW())
            ON CONFLICT (case_id, recipient_phone) DO NOTHING
            RETURNING id;
        """),
        {"case_id": str(case_id), "phone": clean},
    ).fetchone()
    db.commit()
    return res is not None


def delete_outbreak_alert_sent(db: Session, case_id: str | uuid.UUID, recipient_phone: str) -> None:
    """Roll back claim on send failure so later runs can retry."""
    clean = normalize_phone(recipient_phone)
    db.execute(
        text("""
            DELETE FROM outbreak_alerts_sent
            WHERE case_id = :case_id AND recipient_phone = :phone
        """),
        {"case_id": str(case_id), "phone": clean},
    )
    db.commit()


def mark_case_outbreak_evaluated(db: Session, case_id: str | uuid.UUID) -> None:
    """Update disease_cases.outbreak_evaluated_at to NOW()."""
    db.execute(
        text("UPDATE disease_cases SET outbreak_evaluated_at = NOW() WHERE id = :case_id"),
        {"case_id": str(case_id)},
    )
    db.commit()