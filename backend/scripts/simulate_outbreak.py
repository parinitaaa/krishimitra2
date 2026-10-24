#!/usr/bin/env python3
"""
scripts/simulate_outbreak.py

Simulate or execute outbreak alerts for a disease case.
Usage:
    python scripts/simulate_outbreak.py --case <case_id>
    python scripts/simulate_outbreak.py --case <case_id> --send

With no --send, it forces dry-run and prints who would be alerted and the localized message preview.
It must never call Twilio without --send.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure stdout and stderr handle utf-8 (Kannada, Hindi, Emojis) on Windows
try:
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure backend root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from services.db import SessionLocal
from outbreak.db_queries import get_case_by_id
from outbreak.service import evaluate_case
from farmer_store import normalize_phone


def _mask_phone(phone: str) -> str:
    p = str(phone)
    if len(p) <= 6:
        return "***"
    return p[:3] + "******" + p[-3:]


async def main_async():
    parser = argparse.ArgumentParser(description="Simulate outbreak alert evaluation for a disease case.")
    parser.add_argument("--case", required=True, help="UUID or ID of the disease_case")
    parser.add_argument("--send", action="store_true", default=False, help="Actually send messages via Twilio / proactive sender. Default is dry-run.")
    args = parser.parse_args()

    case_id = args.case.strip()
    is_dry_run = not args.send

    # If --send is NOT provided, force dry-run in environment as well
    if is_dry_run:
        os.environ["OUTBREAK_DRY_RUN"] = "true"

    # Inspect the case details first
    with SessionLocal() as db:
        case = get_case_by_id(db, case_id)

    if not case:
        print(f"❌ Error: Case '{case_id}' was not found in disease_cases table.")
        sys.exit(1)

    print("=" * 65)
    mode_label = "[LIVE SEND MODE]" if not is_dry_run else "[DRY RUN - NO TWILIO CALLS]"
    print(f"KRISHIMITRA OUTBREAK EVALUATION: {mode_label}")
    print("=" * 65)
    print(f"Case ID:        {case['id']}")
    print(f"Disease:        {case.get('disease')}")
    print(f"Crop:           {case.get('crop')}")
    print(f"Confidence:     {case.get('confidence')}")
    print(f"Severity:       {case.get('severity_level')} (source: {case.get('severity_source')})")
    print(f"Reporter:       {_mask_phone(case.get('phone'))} at ({case.get('lat')}, {case.get('lng')})")
    print(f"Case Status:    {case.get('status')}")
    print(f"Evaluated At:   {case.get('outbreak_evaluated_at') or 'Not yet evaluated'}")
    print("-" * 65)

    result = await evaluate_case(case_id, dry_run=is_dry_run)

    print("\nEVALUATION RESULTS:")
    print(f"Status:         {result.get('status')}")
    print(f"Spread Modes:   {result.get('spread_modes', [])}")
    print(f"Radius:         {result.get('radius_km')} km")
    print(f"Alerts Sent:    {result.get('alerts_sent', 0)}")
    print(f"Alerts Skipped: {result.get('alerts_skipped', 0)}")

    candidates = result.get("candidates", [])
    print(f"\nCandidates Evaluated: {len(candidates)}")
    print("=" * 65)

    for idx, c in enumerate(candidates, 1):
        print(f"\n[{idx}] Recipient: {_mask_phone(c['phone'])} | Language: {c['language'].upper()}")
        print(f"    Distance:  {c['distance_km']} km ({c['direction_localized']})")
        print(f"    Match:     {c['match_type']}")
        print("    Message Text:")
        print("    " + "-" * 50)
        for line in c["message"].split("\n"):
            print(f"    {line}")
        print("    " + "-" * 50)

    print("\nSimulation complete.")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
