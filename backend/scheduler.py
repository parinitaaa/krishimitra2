"""
scheduler.py
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.whatsapp_service import send_proactive_message
from services.market_service import get_latest_prices, find_best_mandi_for_commodity
from services.db import SessionLocal
from services.i18n import get_string, get_salutation
from farmer_store import (
    get_eligible_briefing_farmers,
    get_open_disease_cases,
    get_active_alerts,
    deactivate_alert,
    get_farmer_location,
    get_farmer_language,
)
from scripts.scrape_karnataka_napanta import run as run_karnataka_scraper

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
_executor = ThreadPoolExecutor(max_workers=1)


async def _fetch_farmer_weather(farmer: dict) -> dict | None:
    """
    Fetch weather using the same code/logic as the get_weather tool.
    Uses lat/lng or district or location. If weather fails or is missing, returns None.
    """
    import os
    import requests

    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        return None

    lat = farmer.get("lat")
    lng = farmer.get("lng")
    loc = farmer.get("district") or farmer.get("location")

    def _sync_weather():
        try:
            if lat is not None and lng is not None:
                params = {"lat": lat, "lon": lng, "appid": key, "units": "metric"}
            elif loc:
                params = {"q": f"{loc}, India", "appid": key, "units": "metric"}
            else:
                return None

            res = requests.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params=params,
                timeout=6,
            )
            if res.status_code != 200:
                return None
            data = res.json()
            main = data.get("main", {})
            temp = main.get("temp")
            humidity = main.get("humidity")
            weather_desc = data.get("weather", [{}])[0].get("description", "clear")
            if temp is None:
                return None
            place_name = data.get("name") or loc or (f"{lat:.2f}, {lng:.2f}" if lat is not None else "")
            return {
                "temp": round(temp),
                "humidity": humidity if humidity is not None else "--",
                "condition": weather_desc,
                "location": place_name,
            }
        except Exception as e:
            print(f"[Scheduler] Weather fetch failed for {farmer.get('phone')}: {e}")
            return None

    return await asyncio.to_thread(_sync_weather)


def _fetch_farmer_crop_prices_sync(crops: list, lat: float | None, lng: float | None, state: str | None, location: str | None) -> list[dict]:
    """
    Find prices for up to 2 crops near farmer's location using existing read functions.
    Mandi freeze strictly respected: uses find_best_mandi_for_commodity or get_latest_prices.
    """
    if not crops:
        return []

    crop_prices = []
    with SessionLocal() as db:
        for crop in crops[:2]:
            clean_crop = crop.strip().lower()
            try:
                # 1. If coordinates exist, use find_best_mandi_for_commodity
                if lat is not None and lng is not None:
                    mandis = find_best_mandi_for_commodity(
                        farmer_lat=lat,
                        farmer_lng=lng,
                        commodity=clean_crop,
                        radius_km=300,
                        top_n=1,
                        db=db,
                    )
                    if mandis:
                        m = mandis[0]
                        crop_prices.append({
                            "crop": crop,
                            "price": m["modal_price"],
                            "market": m["market"],
                            "date": m.get("date") or m.get("arrival_date") or "",
                        })
                        continue

                # 2. Fall back to state / location with get_latest_prices
                target_state = state or location or ""
                if target_state:
                    prices = get_latest_prices(clean_crop, target_state, db)
                    if prices:
                        p = prices[0]
                        crop_prices.append({
                            "crop": crop,
                            "price": p["modal_price"],
                            "market": p["market"],
                            "date": p.get("date") or p.get("arrival_date") or "",
                        })
            except Exception as e:
                print(f"[Scheduler] Error reading prices for {crop}: {e}")
                continue

    return crop_prices


async def _process_single_farmer_briefing(farmer: dict):
    """
    Build and send localized morning briefing for a single farmer.
    Failure never stops or propagates to other farmers.
    """
    phone = farmer.get("phone")
    lang = (farmer.get("language") or "english").lower()
    name = farmer.get("name")
    crops = farmer.get("crops") or []
    lat = farmer.get("lat")
    lng = farmer.get("lng")
    loc = farmer.get("location")
    district = farmer.get("district")
    state = farmer.get("state")

    # 1. Greeting
    if name and name.strip():
        salutation = get_salutation(name, lang)
        greeting = get_string("briefing_greeting", lang, salutation=salutation)
    else:
        greeting = get_string("briefing_greeting_neutral", lang)

    sections = [greeting]

    # 2. Weather: real weather via get_weather logic; if fails, omit line completely
    weather_info = await _fetch_farmer_weather(farmer)
    if weather_info:
        weather_place = weather_info.get("location") or district or loc or ""
        weather_line = get_string(
            "briefing_weather",
            lang,
            location=weather_place,
            condition=weather_info["condition"],
            temp=weather_info["temp"],
            humidity=weather_info["humidity"],
        )
        sections.append(weather_line)

    # 3. Prices for up to 2 crops
    prices = await asyncio.to_thread(
        _fetch_farmer_crop_prices_sync, crops, lat, lng, state, loc
    )
    if prices:
        items = []
        for p in prices:
            items.append(get_string(
                "briefing_price_item",
                lang,
                crop=p["crop"],
                price=p["price"],
                market=p["market"],
                date=p["date"],
            ))
        price_section = get_string("briefing_price_section", lang, items="\n".join(items))
        sections.append(price_section)

    # 4. Open disease case follow-up (one line if any)
    cases = await asyncio.to_thread(get_open_disease_cases, phone)
    if cases:
        c = cases[0]
        case_line = get_string(
            "briefing_disease_followup",
            lang,
            disease=c.get("disease", "Crop disease"),
            crop=c.get("crop", "crop"),
        )
        sections.append(case_line)

    # 5. Closing friendly line
    closing = get_string("briefing_closing", lang)
    if closing:
        sections.append(closing)

    full_message = "\n\n".join(sections)
    await send_proactive_message(phone, full_message)


async def morning_briefing():
    print(f"[Scheduler] Running morning briefing — {datetime.now()}")
    farmers = await asyncio.to_thread(get_eligible_briefing_farmers)
    print(f"[Scheduler] Eligible farmers for briefing: {len(farmers)}")

    sem = asyncio.Semaphore(5)

    async def _bounded_briefing(farmer):
        async with sem:
            try:
                await _process_single_farmer_briefing(farmer)
            except Exception as e:
                print(f"[Scheduler] Failed briefing for {farmer.get('phone')}: {e}")

    await asyncio.gather(*[_bounded_briefing(f) for f in farmers], return_exceptions=True)
    print(f"[Scheduler] Morning briefing done. Processed for {len(farmers)} farmers.")


async def daily_karnataka_scrape():
    print(f"[Scheduler] Running Karnataka scrape — {datetime.now()}")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, run_karnataka_scraper)
        print("[Scheduler] Karnataka scrape completed.")
    except Exception as e:
        print(f"[Scheduler] Karnataka scrape failed: {e}")


async def _process_single_alert(alert: dict, sem: asyncio.Semaphore):
    """Check a single alert with concurrency semaphore and send localized alert on trigger."""
    async with sem:
        try:
            phone = alert["phone"]
            commodity = alert["commodity"]

            # DB call through asyncio.to_thread
            location = await asyncio.to_thread(get_farmer_location, phone)
            if not location:
                print(f"[Alerts] No location for {phone}, skipping alert")
                return

            def _query_mandi_sync():
                with SessionLocal() as db:
                    return find_best_mandi_for_commodity(
                        farmer_lat=location["lat"],
                        farmer_lng=location["lng"],
                        commodity=commodity,
                        radius_km=300,
                        top_n=1,
                        db=db,
                    )

            mandis = await asyncio.to_thread(_query_mandi_sync)
            if not mandis:
                print(f"[Alerts] No nearby mandi data for {phone} / {commodity}")
                return

            nearest = mandis[0]
            current_price = nearest["modal_price"]
            market_name = nearest["market"]
            distance_km = nearest["distance_km"]

            triggered = (
                alert["direction"] == "above" and current_price >= alert["target_price"]
                or
                alert["direction"] == "below" and current_price <= alert["target_price"]
            )

            print(
                f"[Alerts] {phone} | {commodity} | "
                f"current=Rs.{current_price} | "
                f"target={alert['direction']} Rs.{alert['target_price']} | "
                f"triggered={triggered}"
            )

            if triggered:
                farmer_lang = await asyncio.to_thread(get_farmer_language, phone)
                lang = (farmer_lang or "english").lower()

                dir_key = "price_direction_above" if alert["direction"] == "above" else "price_direction_below"
                direction_word = get_string(dir_key, lang)

                msg = get_string(
                    "price_alert_triggered",
                    lang,
                    crop=commodity.title(),
                    price=current_price,
                    market=market_name,
                    distance_km=distance_km,
                    target_price=alert["target_price"],
                    direction=direction_word,
                )
                await send_proactive_message(phone, msg)
                await asyncio.to_thread(deactivate_alert, alert["id"])
                print(f"[Alerts] ✅ Fired and deactivated for {phone}")

        except Exception as e:
            print(f"[Alerts] Failed alert evaluation for {alert.get('phone')}: {e}")


async def check_price_alerts():
    """
    Runs every hour.
    For each active alert, checks prices at mandis NEAR that farmer.
    Only fires if the farmer's nearest mandi crosses the threshold.
    """
    alerts = await asyncio.to_thread(get_active_alerts)
    if not alerts:
        print("[Alerts] No active alerts to check.")
        return

    print(f"[Alerts] Checking {len(alerts)} alerts...")
    sem = asyncio.Semaphore(5)
    await asyncio.gather(*[_process_single_alert(alert, sem) for alert in alerts], return_exceptions=True)

def _organic_mild_lines(disease_name: str) -> str:
    db_path = Path(__file__).resolve().parent / "data" / "disease_db.json"
    if not db_path.exists():
        return (
            "  • Neem oil spray (subah jaldi)\n"
            "  • Prabhavit patte hatakar jal mein mila dein\n"
            "  • Poudhon ke beech hawa ka raasta rakhein"
        )
    data = json.loads(db_path.read_text(encoding="utf-8"))
    dn = disease_name.lower()
    for key, val in data.items():
        if dn in key.lower() or key.lower() in dn:
            org = (val.get("remedies") or {}).get("organic") or []
            pick = org[:4] if org else [
                "Neem oil / neem leaf extract — halka spray",
                "Infected leaves hata dein",
                "Paani ka jamav na hone dein",
            ]
            return "\n".join(f"  • {line}" for line in pick)
    return (
        "  • Neem-based spray (dose: dukaan / krishi kendra se puchein)\n"
        "  • Gunkari pattiyan alag karein\n"
        "  • Yadi halat gambhir ho to najdeeki krishi kendra jayein"
    )


def _buy_links(disease_name: str) -> str:
    q = quote_plus(f"{disease_name} agricultural fungicide pesticide India")
    return (
        "\n*Online khareed (udaharan / verify karke khareedein):*\n"
        f"• https://www.amazon.in/s?k={q}\n"
        f"• https://www.ugaoo.com/search?q={quote_plus(disease_name)}\n"
    )


async def send_disease_followup_round(
    phone: str, disease_name: str, crop_type: str, round_idx: int
):
    from farmer_store import normalize_phone, get_farmer, get_farmer_location

    tz = ZoneInfo("Asia/Kolkata")
    pid = normalize_phone(phone)
    prof = get_farmer(pid)
    name_val = prof.get("name")
    name = name_val.split()[0] if name_val else "Kisan"

    mild = _organic_mild_lines(disease_name)
    links = _buy_links(disease_name)

    mandi_line = ""
    loc = get_farmer_location(pid)
    if loc:
        db = SessionLocal()
        try:
            crop_key = (crop_type or "tomato").strip().lower()
            ms = find_best_mandi_for_commodity(
                farmer_lat=loc["lat"],
                farmer_lng=loc["lng"],
                commodity=crop_key,
                radius_km=500,
                top_n=2,
                db=db,
            )
            if ms:
                m0 = ms[0]
                mandi_line = (
                    f"\n\n*Paas ki mandi ({crop_key.title()}):*\n"
                    f"• {m0['market']}, {m0['state']} — "
                    f"Rs.{m0['modal_price']}/q (~{m0['distance_km']} km)"
                )
        finally:
            db.close()

    day_label = 2 * (round_idx + 1)
    msg = (
        f"Namaste {name} ji 🌾\n\n"
        f"*Follow-up* (din {day_label}): *{disease_name}* — fasl ab kaisi hai?\n"
        f"Agar theek ho gayi ho to bataiye; warna *nayi photo* bhejein 📸\n\n"
        f"*Halka / dekhbhal:*\n{mild}"
        f"{mandi_line}\n"
        f"{links}"
    )
    await send_proactive_message(pid, msg)
    print(f"[Scheduler] Disease follow-up r{round_idx} → {pid}")

    if round_idx < 2:
        next_run = datetime.now(tz) + timedelta(days=2)
        nid = f"disease_fu_{pid}_{round_idx + 1}"
        scheduler.add_job(
            send_disease_followup_round,
            trigger="date",
            run_date=next_run,
            args=[pid, disease_name, crop_type, round_idx + 1],
            id=nid,
            replace_existing=True,
        )


def schedule_disease_followup_series(phone: str, disease_name: str, crop_type: str):
    from farmer_store import normalize_phone

    tz = ZoneInfo("Asia/Kolkata")
    pid = normalize_phone(phone)
    run_at = datetime.now(tz) + timedelta(days=2)
    jid = f"disease_fu_{pid}_0"
    scheduler.add_job(
        send_disease_followup_round,
        trigger="date",
        run_date=run_at,
        args=[pid, disease_name, crop_type, 0],
        id=jid,
        replace_existing=True,
    )
    print(f"[Scheduler] Disease follow-up series scheduled for {pid} @ {run_at}")


def _get_all_farmers() -> list:
    from sqlalchemy import text
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT phone, name, crops, location FROM farmers")
        ).fetchall()
    return [
        {
            "phone":    row[0],
            "name":     row[1] if row[1] else None,
            "crops":    row[2] or [],
            "location": row[3] if row[3] else None,
        }
        for row in rows
    ]


def register_jobs(sched):
    """Registers morning briefing, daily karnataka scrape, and price alerts jobs."""
    sched.add_job(
        morning_briefing,
        trigger="cron",
        hour=7, minute=0,
        id="morning_briefing_job",
        replace_existing=True,
    )
    sched.add_job(
        daily_karnataka_scrape,
        trigger="cron",
        hour=10, minute=20,
        id="daily_karnataka_scrape",
        replace_existing=True,
    )
    sched.add_job(
        check_price_alerts,
        "cron", minute=0,       # every hour at :00
        id="price_alerts_job",
        replace_existing=True,
    )


def register_daily_price_fetch(sched):
    """Registers daily mandi price fetch in executor."""
    from services.price_fetcher import run_daily_fetch
    loop = asyncio.get_event_loop()
    sched.add_job(
        lambda: loop.run_in_executor(_executor, run_daily_fetch),
        trigger="cron", hour=0, minute=0,
        id="daily_price_fetch", replace_existing=True,
    )


def start_scheduler():
    """Start scheduler and log registered jobs."""
    if not scheduler.running:
        scheduler.start()

    print("[Scheduler] Started. Registered jobs:")
    for job in scheduler.get_jobs():
        print(f"  {job.id} → next run: {job.next_run_time}")

