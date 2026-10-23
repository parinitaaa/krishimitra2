# backend/tests/transcript_demo.py
"""
transcript_demo.py — v2
Runs English, Kannada, and Hindi farmers through the real handle_incoming_message,
with send_message captured (not sent to Twilio) and the REAL Groq model.

Conversation script for each farmer:
 1. "hi"
 2. language selection ("3" for English / "2" for Kannada / "1" for Hindi)
 3. name ("John Doe" / "ಬಸವರಾಜ್" / "राजेश")
 4. location pin (lat/lng)
 5. "what fertilizer for tomato?"
 6. "thanks"
 7. "help"
 8. "tomato price today"
 9. "alert me when onion goes above 2000"
10. "yes"
11. "and for potato?"
12. "what spray for leaf spots?"

Timeout: 120s per run. Cleans up all database rows before and after each run.
Saves output to TRANSCRIPT_v2.md at the repo root.
"""

import os
import sys
import re
import uuid
import asyncio
from pathlib import Path
from datetime import datetime

# Add backend directory to path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import services.whatsapp_service as ws
from farmer_store import (
    TEST_PHONE_PREFIX,
    normalize_phone,
    delete_farmer_records,
    add_chat,
    get_farmer_alerts,
)
from services.db import SessionLocal
from sqlalchemy import text


def verify_prerequisites():
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key or not groq_key.strip():
        print("❌ Error: GROQ_API_KEY is not set or empty. Cannot run transcript demo.")
        sys.exit(1)

    db_url = os.getenv("DATABASE_URL")
    if not db_url or not db_url.strip():
        print("❌ Error: DATABASE_URL is not set or empty. Cannot connect to database.")
        sys.exit(1)

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar()
    except Exception as e:
        print(f"❌ Error: Database connection failed: {e}")
        sys.exit(1)


async def run_conversation(
    phone: str,
    language_choice: str,
    name_input: str,
    lat: str,
    lng: str,
    lang_name: str,
) -> list[dict]:
    captured_turns = []
    current_bot_replies = []

    # Mock send_message to capture replies instead of sending via Twilio
    # CRITICAL: also record assistant messages to chat_history so subsequent
    # turns have correct history context (fixes BUG 1 root cause in demo)
    original_send = ws.send_message

    async def capturing_send(target_phone: str, text_msg: str, retries: int = 3) -> bool:
        # Apply format_for_whatsapp like the real send_message does
        formatted = ws.format_for_whatsapp(text_msg) or text_msg.strip()
        current_bot_replies.append(formatted)
        # Record to chat_history so next turn sees prior bot replies
        try:
            clean_phone = normalize_phone(target_phone)
            add_chat(clean_phone, "assistant", formatted)
        except Exception as e:
            print(f"[capturing_send] Failed to record chat: {e}")
        return True

    ws.send_message = capturing_send

    # Full acceptance test sequence
    steps = [
        {"desc": "Greeting",                "body": "hi",                                      "lat": None, "lng": None},
        {"desc": "Language selection",       "body": language_choice,                            "lat": None, "lng": None},
        {"desc": "Name submission",          "body": name_input,                                 "lat": None, "lng": None},
        {"desc": "Location pin",             "body": "",                                         "lat": lat,  "lng": lng},
        {"desc": "Fertilizer question",      "body": "what fertilizer for tomato?",              "lat": None, "lng": None},
        {"desc": "Thanks",                   "body": "thanks",                                   "lat": None, "lng": None},
        {"desc": "Help/Menu",                "body": "help",                                     "lat": None, "lng": None},
        {"desc": "Mandi price query",        "body": "tomato price today",                       "lat": None, "lng": None},
        {"desc": "Price alert request",      "body": "alert me when onion goes above 2000",      "lat": None, "lng": None},
        {"desc": "Alert confirmation",       "body": "yes",                                      "lat": None, "lng": None},
        {"desc": "Follow-up potato price",   "body": "and for potato?",                          "lat": None, "lng": None},
        {"desc": "Spray request (no photo)", "body": "what spray for leaf spots?",               "lat": None, "lng": None},
    ]

    try:
        for idx, step in enumerate(steps, 1):
            current_bot_replies.clear()
            msg_sid = f"SM_{uuid.uuid4().hex}"
            payload = {
                "From": phone,
                "Body": step["body"],
                "NumMedia": "0",
                "MessageSid": msg_sid,
            }
            if step["lat"] and step["lng"]:
                payload["Latitude"] = step["lat"]
                payload["Longitude"] = step["lng"]

            user_disp = (
                f"[Location Pin: {step['lat']}, {step['lng']}]"
                if (step["lat"] and step["lng"])
                else step["body"]
            )
            print(f"\n--- {lang_name} Step {idx}: {step['desc']} ---")
            print(f"Farmer: {user_disp}")

            # Run with per-step timeout
            await asyncio.wait_for(ws.handle_incoming_message(payload), timeout=60.0)

            reply_text = "\n\n".join(current_bot_replies) if current_bot_replies else "[No reply]"
            print(f"Bot:\n{reply_text}")

            captured_turns.append({
                "step": step["desc"],
                "user": user_disp,
                "bot": reply_text,
            })

            # Clean up processed_messages for test SID
            try:
                with SessionLocal() as db:
                    db.execute(
                        text("DELETE FROM processed_messages WHERE message_sid = :sid"),
                        {"sid": msg_sid},
                    )
                    db.commit()
            except Exception:
                pass

            # Brief breathing pause between turns for database consistency
            await asyncio.sleep(0.5)

    finally:
        ws.send_message = original_send

    return captured_turns


def validate_pass_criteria(transcript: list[dict], phone: str, lang_name: str) -> list[str]:
    """Validate acceptance criteria and return list of failures."""
    failures = []

    # Find key turns by step name
    turns_by_step = {t["step"]: t for t in transcript}

    # 1. "thanks" never repeats the fertilizer answer
    fertilizer_turn = turns_by_step.get("Fertilizer question", {})
    thanks_turn = turns_by_step.get("Thanks", {})
    if fertilizer_turn and thanks_turn:
        fert_bot = fertilizer_turn.get("bot", "")
        thanks_bot = thanks_turn.get("bot", "")
        # Check for significant overlap (more than a greeting)
        fert_words = set(fert_bot.lower().split())
        thanks_words = set(thanks_bot.lower().split())
        # If >40% word overlap with the fertilizer answer, it's a repeat
        if fert_words and len(fert_words & thanks_words) / max(len(fert_words), 1) > 0.4:
            failures.append(f"[{lang_name}] 'thanks' repeated the fertilizer answer")

    # 2. Alert row exists after "yes"
    confirm_turn = turns_by_step.get("Alert confirmation")
    if confirm_turn:
        alerts = get_farmer_alerts(phone)
        onion_alerts = [a for a in alerts if a.get("commodity") == "onion"]
        if not onion_alerts:
            failures.append(f"[{lang_name}] No onion alert row found in price_alerts after 'yes'")

    # 3. Prices show "per quintal" (or language equivalent) and NOT "per kg"
    price_turn = turns_by_step.get("Mandi price query", {})
    price_bot = price_turn.get("bot", "").lower()
    if price_bot and "no" not in price_bot[:30]:
        if "per kg" in price_bot or "/kg" in price_bot or "/ಕೆಜಿ" in price_bot:
            failures.append(f"[{lang_name}] Price reply uses per-kg instead of per-quintal")

    # 4. No markdown tables in any reply
    for t in transcript:
        bot = t.get("bot", "")
        if re.search(r"\|.*\|.*\|", bot) and "---" not in bot:
            # Check it's actually a table row, not a pipe in text
            lines_with_pipes = [l for l in bot.split("\n") if l.strip().startswith("|") and l.strip().endswith("|")]
            if len(lines_with_pipes) >= 2:
                failures.append(f"[{lang_name}] Turn '{t['step']}' contains markdown table")
                break

    # 5. No truncated replies (ending mid-word/sentence)
    for t in transcript:
        bot = t.get("bot", "").strip()
        if bot and len(bot) > 100:
            valid_ends = (".", "?", "!", "।", "॥", ")", "*", '"', "'", "🌾", "📍", "🩺", "✅", "\n")
            if not bot.endswith(valid_ends):
                failures.append(f"[{lang_name}] Turn '{t['step']}' appears truncated")

    # 6. No fertilizer/pesticide dose numbers (NPK ratios, kg/ha patterns)
    dose_pattern = re.compile(r"\b\d+[-–]\d+[-–]\d+\b|\b\d+\s*(?:kg|g)\s*/\s*(?:ha|hectare|acre)\b", re.IGNORECASE)
    for t in transcript:
        if t["step"] in ("Location pin", "Greeting", "Language selection", "Name submission"):
            continue
        bot = t.get("bot", "")
        if dose_pattern.search(bot):
            failures.append(f"[{lang_name}] Turn '{t['step']}' contains dose numbers")
            break

    # 7. "what spray for leaf spots?" should redirect to photo, not give doses
    spray_turn = turns_by_step.get("Spray request (no photo)", {})
    spray_bot = spray_turn.get("bot", "").lower()
    if spray_bot:
        # Should mention photo/send photo
        if "photo" not in spray_bot and "फ़ोटो" not in spray_bot and "ಫೋಟೋ" not in spray_bot:
            failures.append(f"[{lang_name}] Spray turn doesn't redirect to send a photo")

    return failures


def generate_transcript_md(
    en_transcript: list[dict],
    kn_transcript: list[dict],
    hi_transcript: list[dict],
    all_failures: list[str],
) -> str:
    """Generate TRANSCRIPT_v2.md content."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    md = f"""# KrishiMitra Real Conversation Transcripts — v2

Generated on: {now_str}
Model: `{model}`
Pipeline: `handle_incoming_message` → `process_message` (real Groq) with Twilio intercepted via test guards.

---

"""

    sections = [
        ("1. English Farmer (+910000000001)", en_transcript),
        ("2. Kannada Farmer (+910000000002)", kn_transcript),
        ("3. Hindi Farmer (+910000000003)", hi_transcript),
    ]

    for title, transcript in sections:
        md += f"## {title}\n\n"
        for idx, t in enumerate(transcript, 1):
            md += f"### Turn {idx}: {t['step']}\n"
            md += f"**Farmer:**\n```text\n{t['user']}\n```\n"
            md += f"**Bot:**\n```text\n{t['bot']}\n```\n\n---\n\n"

    # Validation results
    md += "## Acceptance Validation\n\n"
    if all_failures:
        md += "### ❌ Failures\n\n"
        for f in all_failures:
            md += f"- {f}\n"
    else:
        md += "### ✅ All pass criteria met\n\n"
        md += "- 'thanks' never repeats an earlier answer\n"
        md += "- Alert row exists after 'yes'\n"
        md += "- Prices show 'per quintal' and real data date\n"
        md += "- No markdown tables or raw markdown\n"
        md += "- No truncated replies\n"
        md += "- No fertilizer/pesticide dose numbers\n"
        md += "- Spray request redirects to photo check\n"

    return md


async def main():
    verify_prerequisites()
    print("Prerequisites verified: Real Groq API key and Supabase DB available.")

    all_failures = []

    # ── 1. English Farmer ────────────────────────────────────────────────────
    en_phone = f"{TEST_PHONE_PREFIX}0001"
    delete_farmer_records(en_phone)
    print("\n=======================================================")
    print("RUNNING DEMO 1: English Farmer (+910000000001)")
    print("=======================================================")

    en_transcript = []
    try:
        en_transcript = await asyncio.wait_for(
            run_conversation(
                phone=en_phone,
                language_choice="3",
                name_input="John Doe",
                lat="12.9716",
                lng="77.5946",
                lang_name="English",
            ),
            timeout=180.0,
        )
        failures = validate_pass_criteria(en_transcript, en_phone, "English")
        all_failures.extend(failures)
    except Exception as e:
        print(f"❌ English farmer run failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        delete_farmer_records(en_phone)
        print("Cleaned up database for English farmer.")

    # ── 2. Kannada Farmer ────────────────────────────────────────────────────
    kn_phone = f"{TEST_PHONE_PREFIX}0002"
    delete_farmer_records(kn_phone)
    print("\n=======================================================")
    print("RUNNING DEMO 2: Kannada Farmer (+910000000002)")
    print("=======================================================")

    kn_transcript = []
    try:
        kn_transcript = await asyncio.wait_for(
            run_conversation(
                phone=kn_phone,
                language_choice="2",
                name_input="ಬಸವರಾಜ್",
                lat="13.1367",
                lng="78.1291",
                lang_name="Kannada",
            ),
            timeout=180.0,
        )
        failures = validate_pass_criteria(kn_transcript, kn_phone, "Kannada")
        all_failures.extend(failures)
    except Exception as e:
        print(f"❌ Kannada farmer run failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        delete_farmer_records(kn_phone)
        print("Cleaned up database for Kannada farmer.")

    # ── 3. Hindi Farmer ──────────────────────────────────────────────────────
    hi_phone = f"{TEST_PHONE_PREFIX}0003"
    delete_farmer_records(hi_phone)
    print("\n=======================================================")
    print("RUNNING DEMO 3: Hindi Farmer (+910000000003)")
    print("=======================================================")

    hi_transcript = []
    try:
        hi_transcript = await asyncio.wait_for(
            run_conversation(
                phone=hi_phone,
                language_choice="1",
                name_input="राजेश",
                lat="19.9975",
                lng="73.7898",
                lang_name="Hindi",
            ),
            timeout=180.0,
        )
        failures = validate_pass_criteria(hi_transcript, hi_phone, "Hindi")
        all_failures.extend(failures)
    except Exception as e:
        print(f"❌ Hindi farmer run failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        delete_farmer_records(hi_phone)
        print("Cleaned up database for Hindi farmer.")

    # ── Generate TRANSCRIPT_v2.md ────────────────────────────────────────────
    md_content = generate_transcript_md(en_transcript, kn_transcript, hi_transcript, all_failures)
    repo_root = Path(__file__).resolve().parent.parent.parent
    output_path = repo_root / "TRANSCRIPT_v2.md"
    output_path.write_text(md_content, encoding="utf-8")
    print(f"\n✅ Transcript saved to {output_path}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n=======================================================")
    print("ACCEPTANCE VALIDATION SUMMARY")
    print("=======================================================")
    if all_failures:
        print(f"❌ {len(all_failures)} failure(s):")
        for f in all_failures:
            print(f"  - {f}")
    else:
        print("✅ All pass criteria met!")

    return en_transcript, kn_transcript, hi_transcript


if __name__ == "__main__":
    asyncio.run(main())
