# services/price_fetcher.py

import os
import re
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from models.price import MandiPrice
from services.db import SessionLocal
from services.market_service import karnataka_rows_exist

DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY")
DATA_GOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DATA_GOV_BASE_URL = "https://api.data.gov.in/resource"

COMMODITIES = [
    "Tomato", "Onion", "Potato", "Brinjal", "Cabbage",
    "Cauliflower", "Beans", "Pumpkin", "Carrot", "Garlic",
    "Ginger", "Green Chilli", "Wheat", "Rice", "Maize",
    "Soyabean", "Groundnut", "Mustard", "Cotton", "Sugarcane"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def _safe_float(value):
    try:
        clean = re.sub(r"[^\d.]", "", str(value))
        return float(clean) if clean else 0.0
    except Exception:
        return 0.0


def _parse_date(raw_date: str):
    if not raw_date:
        return datetime.utcnow().date()

    raw_date = raw_date.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw_date, fmt).date()
        except ValueError:
            continue

    return datetime.utcnow().date()


def upsert_record(db: Session, row: dict):
    stmt = insert(MandiPrice).values(
        state=row.get("state", "").strip(),
        district=row.get("district", "").strip(),
        market=row.get("market", "").strip(),
        commodity=row.get("commodity", "").strip(),
        variety=row.get("variety", "").strip(),
        min_price=_safe_float(row.get("min_price", 0)),
        max_price=_safe_float(row.get("max_price", 0)),
        modal_price=_safe_float(row.get("modal_price", 0)),
        arrival_date=_parse_date(str(row.get("arrival_date", ""))),
        fetched_at=datetime.utcnow(),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_market_commodity_date",
        set_={
            "min_price": stmt.excluded.min_price,
            "max_price": stmt.excluded.max_price,
            "modal_price": stmt.excluded.modal_price,
            "fetched_at": stmt.excluded.fetched_at,
        }
    )

    db.execute(stmt)


def _extract_field(record: dict, *candidate_keys, default=""):
    for k in candidate_keys:
        if k in record and record[k] is not None:
            val = str(record[k]).strip()
            if val:
                return val
    return default


def fetch_and_store(commodity: str, db: Session, page_limit: int = 100, max_pages: int = 5) -> int:
    """
    Official source fetch from data.gov.in with pagination support,
    case-insensitive field extraction, and error handling.
    """
    api_key = os.getenv("DATA_GOV_API_KEY") or DATA_GOV_API_KEY
    if not api_key:
        print("[data.gov] Warning: DATA_GOV_API_KEY is not configured.")
        return 0

    url = f"{DATA_GOV_BASE_URL}/{DATA_GOV_RESOURCE_ID}"
    offset = 0
    total_stored = 0

    for page in range(max_pages):
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": page_limit,
            "offset": offset,
            "filters[commodity]": commodity,
        }

        records = []
        try:
            # Fast timeout (6s) so slow gov servers don't stall scheduler or API responses
            response = requests.get(url, params=params, timeout=6)
            if response.status_code == 429:
                print(f"[data.gov] Rate limit reached while fetching {commodity}. Backing off.")
                break
            response.raise_for_status()
            data = response.json()
            records = data.get("records", []) if isinstance(data, dict) else []
        except requests.exceptions.RequestException:
            # Mask any accidental query params or key strings in logs
            print(f"[data.gov] Official API timed out/unavailable for {commodity}. Switching to live website fallback.")
            break
        except Exception:
            print(f"[data.gov] Failed to parse response for {commodity}.")
            break

        if not records:
            break

        page_count = 0
        for r in records:
            try:
                state = _extract_field(r, "state", "State")
                district = _extract_field(r, "district", "District")
                market = _extract_field(r, "market", "Market")
                comm = _extract_field(r, "commodity", "Commodity", default=commodity)
                variety = _extract_field(r, "variety", "Variety", default="General")
                arrival_date = _extract_field(r, "arrival_date", "Arrival_Date", "arrivalDate", "Arrival Date")

                min_price = _extract_field(r, "min_price", "Min_Price", "Min Price", default="0")
                max_price = _extract_field(r, "max_price", "Max_Price", "Max Price", default="0")
                modal_price = _extract_field(r, "modal_price", "Modal_Price", "Modal Price", default="0")

                if not market or not state:
                    continue

                row = {
                    "state": state,
                    "district": district,
                    "market": market,
                    "commodity": comm,
                    "variety": variety,
                    "min_price": min_price,
                    "max_price": max_price,
                    "modal_price": modal_price,
                    "arrival_date": arrival_date,
                }
                upsert_record(db, row)
                page_count += 1
            except Exception:
                continue

        try:
            db.commit()
        except Exception:
            db.rollback()

        total_stored += page_count

        if len(records) < page_limit:
            break

        offset += page_limit
        time.sleep(0.3)

    return total_stored


# Key Karnataka APMC markets on NaPanta for general vegetable/crop fallback
NAPANTA_KARNATAKA_MARKETS = [
    {"market": "Ramanagara", "district": "Bangalore", "url": "https://www.napanta.com/market-price/karnataka/bangalore/ramanagara/"},
    {"market": "Bangalore", "district": "Bangalore", "url": "https://www.napanta.com/market-price/karnataka/bangalore/bangalore/"},
    {"market": "Kolar", "district": "Kolar", "url": "https://www.napanta.com/market-price/karnataka/kolar/kolar/"},
    {"market": "Chintamani", "district": "Kolar", "url": "https://www.napanta.com/market-price/karnataka/kolar/chintamani/"},
    {"market": "Mysore", "district": "Mysore", "url": "https://www.napanta.com/market-price/karnataka/mysore/mysore/"},
    {"market": "Hubli (Amaragol)", "district": "Dharwad", "url": "https://www.napanta.com/market-price/karnataka/dharwad/hubli-amaragol/"},
]


def scrape_napanta_commodity_page(commodity: str, db: Session) -> int:
    """
    Scrapes live prices directly from NaPanta's commodity portal:
    https://www.napanta.com/agri-commodity-prices/karnataka/<slug>/
    This covers Grains (Wheat, Rice, Maize), Pulses, Vegetables, etc.
    """
    slug = commodity.strip().lower().replace(" ", "-")
    url = f"https://www.napanta.com/agri-commodity-prices/karnataka/{slug}/"
    today_date = datetime.utcnow().date()
    total_inserted = 0

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return 0

        soup = BeautifulSoup(resp.text, "html.parser")
        # Find district sub-links for this commodity
        district_links = [
            a["href"] for a in soup.find_all("a", href=True)
            if f"/agri-commodity-prices/karnataka/{slug}/" in a["href"]
            and a["href"].strip("/") != f"agri-commodity-prices/karnataka/{slug}"
        ]

        # Check top 3 trading districts
        for dlink in list(dict.fromkeys(district_links))[:3]:
            d_url = f"https://www.napanta.com{dlink}" if not dlink.startswith("http") else dlink
            parts = [p for p in dlink.strip("/").split("/") if p]
            district_name = parts[-1].capitalize() if parts else "Karnataka"

            try:
                d_resp = requests.get(d_url, headers=HEADERS, timeout=8)
                if d_resp.status_code != 200:
                    continue

                d_soup = BeautifulSoup(d_resp.text, "html.parser")
                table = d_soup.find("table")
                if not table:
                    continue

                for tr in table.find_all("tr")[1:]:
                    cells = tr.find_all(["th", "td"])
                    if len(cells) < 5:
                        continue

                    market_name = cells[0].get_text(" ", strip=True)
                    variety = cells[1].get_text(" ", strip=True) if len(cells) > 1 else "General"
                    min_p = _safe_float(cells[2].get_text(" ", strip=True))
                    modal_p = _safe_float(cells[3].get_text(" ", strip=True))
                    max_p = _safe_float(cells[4].get_text(" ", strip=True))

                    if not market_name or (min_p == 0 and modal_p == 0 and max_p == 0):
                        continue

                    row = {
                        "state": "Karnataka",
                        "district": district_name,
                        "market": market_name,
                        "commodity": commodity.capitalize(),
                        "variety": variety or "General",
                        "min_price": min_p,
                        "max_price": max_p,
                        "modal_price": modal_p or min_p,
                        "arrival_date": today_date,
                    }
                    upsert_record(db, row)
                    total_inserted += 1

                db.commit()
                time.sleep(0.2)
            except Exception:
                continue

    except Exception:
        pass

    return total_inserted


def scrape_napanta_karnataka(commodity: str, db: Session) -> int:
    """
    Scrapes live APMC market prices from NaPanta for Karnataka markets.
    First tries the commodity-specific index (covers grains like Wheat, Rice, Pulses),
    then checks key market APMC tables (covers daily Vegetables).
    """
    # 1. Try commodity-level index first (works great for Wheat, Rice, Maize, etc.)
    inserted = scrape_napanta_commodity_page(commodity, db)
    if inserted > 0:
        return inserted

    # 2. Check general market APMC tables (works great for daily Vegetables)
    total_inserted = 0
    today_date = datetime.utcnow().date()
    target_comm = commodity.strip().lower()

    for item in NAPANTA_KARNATAKA_MARKETS:
        market_name = item["market"]
        district_name = item["district"]
        url = item["url"]

        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table")
            if not table:
                continue

            rows = table.find_all("tr")[1:]
            for tr in rows:
                cells = tr.find_all(["th", "td"])
                if len(cells) < 5:
                    continue

                scraped_comm = cells[0].get_text(" ", strip=True)
                variety = cells[1].get_text(" ", strip=True) if len(cells) > 1 else "General"
                min_p = _safe_float(cells[2].get_text(" ", strip=True)) if len(cells) > 2 else 0.0
                modal_p = _safe_float(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else 0.0
                max_p = _safe_float(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else 0.0

                if target_comm not in scraped_comm.lower() and scraped_comm.lower() not in target_comm:
                    continue

                row = {
                    "state": "Karnataka",
                    "district": district_name,
                    "market": market_name,
                    "commodity": commodity.capitalize(),
                    "variety": variety or "General",
                    "min_price": min_p,
                    "max_price": max_p,
                    "modal_price": modal_p or min_p,
                    "arrival_date": today_date,
                }

                try:
                    upsert_record(db, row)
                    total_inserted += 1
                except Exception:
                    continue

            db.commit()
            time.sleep(0.2)
        except Exception:
            continue

    return total_inserted


def fetch_with_fallback(commodity: str, db: Session, force_scrape: bool = False) -> dict:
    """
    1. Try official Data.gov.in API
    2. If official API returns 0 or fails, scrape live website prices
    """
    official_count = 0
    fallback_count = 0

    try:
        official_count = fetch_and_store(commodity, db)
    except Exception as e:
        print(f"[official] {commodity} error: {e}")

    # Fallback to website scraping if official API returned 0 or force_scrape is requested
    if official_count == 0 or force_scrape:
        try:
            fallback_count = scrape_napanta_karnataka(commodity, db)
        except Exception as e:
            print(f"[fallback] {commodity} error: {e}")

    return {
        "commodity": commodity,
        "official_count": official_count,
        "fallback_count": fallback_count,
        "total_added": official_count + fallback_count,
    }


def is_commodity_fetched_today(commodity: str, db: Session) -> bool:
    """
    Checks if prices for this commodity were already fetched today.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    row = (
        db.query(MandiPrice.id)
        .filter(
            func.lower(MandiPrice.commodity) == commodity.strip().lower(),
            MandiPrice.fetched_at >= today_start
        )
        .first()
    )
    return row is not None


def ensure_commodity_prices_fresh(commodity: str, db: Session):
    """
    Check if commodity data is fresh for today. If not, fetch from official API
    or fallback website and upsert into database before returning data.
    """
    if not is_commodity_fetched_today(commodity, db):
        print(f"[mandi_cache] No today's fetch found for {commodity}. Fetching fresh prices...")
        fetch_with_fallback(commodity, db)


def run_daily_fetch():
    """
    Fetch all commodities from official API,
    then fill Karnataka gaps using fallback scraper.
    """
    db = SessionLocal()
    total = 0
    details = []

    print(f"[{datetime.utcnow()}] Starting mandi fetch...")

    try:
        for commodity in COMMODITIES:
            result = fetch_with_fallback(commodity, db)
            total += result["total_added"]
            details.append(result)
            print(
                f"{commodity}: official={result['official_count']} "
                f"fallback={result['fallback_count']} "
                f"total={result['total_added']}"
            )
    finally:
        db.close()

    print(f"[{datetime.utcnow()}] Fetch complete. Total inserted: {total}")
    return {
        "total": total,
        "details": details
    }