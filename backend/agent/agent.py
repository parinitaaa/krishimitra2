# backend/agent/agent.py
"""
LangChain tool-calling agent for KrishiMitra.
Uses ChatGroq with typed LangChain tools, dynamic per-turn context injection,
stateful slot filling, chat_history persistence, and friendly localized fallbacks.
"""

from __future__ import annotations

import re
import os
import json
import logging
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from langchain_groq import ChatGroq
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)

from config import GROQ_MODEL
from agent.tools import ALL_TOOLS, active_farmer_phone
from farmer_store import (
    get_farmer,
    normalize_phone,
    get_chat_history,
    get_state,
    set_state,
    clear_state,
    get_open_disease_cases,
)
from services.i18n import get_salutation

logger = logging.getLogger(__name__)

TOOL_MAP = {t.name: t for t in ALL_TOOLS}

FALLBACK_MESSAGES = {
    "hindi": "माफ़ कीजिये, अभी जानकारी प्राप्त करने में तकनीकी समस्या आ रही है। कृपया कुछ समय बाद पुनः प्रयास करें।",
    "kannada": "ಕ್ಷಮಿಸಿ, ಮಾಹಿತಿಯನ್ನು ಪಡೆಯುವಲ್ಲಿ ತಾಂತ್ರಿಕ ಸಮಸ್ಯೆಯಾಗಿದೆ. ದಯವಿಟ್ಟು ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸಿ.",
    "english": "I'm sorry, I encountered a temporary issue retrieving that information. Please try again in a moment.",
}


def _get_current_season() -> str:
    """Map month to agricultural season with realistic transition notes."""
    now = datetime.now()
    month = now.month
    day = now.day

    if 6 <= month <= 9:
        return "Kharif (Monsoon season - vegetative growth & flowering for paddy, maize, cotton, pulses)"
    elif month == 10:
        if day >= 15:
            return "Late October (Seasonal transition: Kharif harvesting concluding, Rabi sowing & field preparation begins)"
        else:
            return "Early October (Kharif maturity and harvest season begins)"
    elif month in (11, 12, 1, 2):
        return "Rabi (Winter season - sowing and growth for wheat, mustard, gram, potato)"
    elif month == 3:
        return "March (Transition: Rabi harvest season, early summer preparation)"
    else:
        return "Zaid (Summer season - vegetables, pulses, fodder crops with irrigation)"


def _is_truncated(text: str, finish_reason: str | None = None) -> bool:
    """Check if the text was cut off by max_tokens or ends without a standard sentence terminator."""
    if finish_reason == "length":
        return True
    if not text or len(text.strip()) < 120:
        return False
    t = text.strip()
    valid_terminators = (".", "?", "!", "।", "॥", "\n", ")", "*", '"', "'", "🌾", "📍", "🩺", "✅")
    return not t.endswith(valid_terminators)


def _build_system_prompt(farmer: dict, phone: str = "") -> str:
    name = farmer.get("name")
    lang = (farmer.get("language") or "english").lower()
    salutation = get_salutation(name, lang)
    crops = farmer.get("crops") or []
    crops_str = ", ".join(crops) if crops else "Not specified"
    soil = farmer.get("soil_type") or "Not specified"
    water = farmer.get("water_source") or "Not specified"
    area = f"{farmer.get('farm_size_acres')} acres" if farmer.get('farm_size_acres') else "Not specified"
    loc = farmer.get("location") or "Not specified"
    district = farmer.get("district") or ""
    state = farmer.get("state") or ""
    region = f"{district}, {state}".strip(", ") or loc

    # Open disease cases
    clean_phone = phone or farmer.get("phone", "")
    open_cases = get_open_disease_cases(clean_phone) if clean_phone else []
    cases_summary = "None"
    if open_cases:
        cases_summary = "; ".join(
            f"{c.get('crop')} {c.get('disease')} (Severity: {c.get('severity_level') or 'Unknown'})"
            for c in open_cases[:3]
        )

    today_str = datetime.now().strftime("%A, %d %B %Y")
    season_str = _get_current_season()

    # Name frequency policy: at most once in every 4 replies, never as first words
    salutation_instruction = "Do not use the farmer's name in this reply."
    if name and clean_phone:
        raw_history = get_chat_history(clean_phone, limit=8)
        assistant_msgs = [h.get("content", "") for h in raw_history if h.get("role") == "assistant"]
        recent = assistant_msgs[-3:] if len(assistant_msgs) >= 3 else assistant_msgs
        used_recently = any(name.lower() in m.lower() for m in recent)
        if not used_recently:
            salutation_instruction = (
                f"You may occasionally use the respectful name '{salutation}', but at most once in this message "
                "and NEVER as the very first words of your reply."
            )

    lang_instructions = {
        "hindi": "Reply in Hindi using clean Devanagari script. Keep language pure Hindi (no English transliteration).",
        "kannada": "Reply in Kannada using clean Kannada script.",
        "english": "Reply in clear, warm Indian English.",
    }.get(lang, "Reply in the farmer's registered language.")

    prompt = f"""You are KrishiMitra (कृषि-मित्र), an expert AI agronomy and farming advisor for Indian farmers.

═══ FARMER PROFILE & CONTEXT ═══
• Name: {name or 'Farmer Friend'} ({salutation_instruction})
• Registered Language: {lang.upper()} ({lang_instructions})
• Farm Location: {region}
• Cultivated Crops: {crops_str}
• Soil Type: {soil}
• Irrigation / Water Source: {water}
• Farm Size: {area}
• Open Crop Disease Cases: {cases_summary}
• Today's Date: {today_str}
• Agricultural Season: {season_str}

═══ WHATSAPP FORMAT & TONE RULES ═══
1. BREVITY: Keep answers short. Default to 2-4 concise, helpful sentences.
2. NO TABLES: NEVER output markdown tables (| col | col |).
3. NO HEADINGS: NEVER use markdown headers (# or ##).
4. BULLETS: Use at most 4 plain "•" bullet points.
5. BOLD: Use at most one *bold* word or phrase in the entire message.
6. ONE QUESTION AT A TIME: Answer the farmer's question first, then ask at most ONE clarifying question if needed.
7. AMBIGUOUS CROP HANDLING: If the farmer asks a crop-specific question without specifying the crop and has multiple crops registered ({crops_str}), gently ask which one they are inquiring about.
8. NO FORCED CLOSING PHRASES: Do NOT append repetitive boilerplate lines like 'Koi aur madad chahiye? 🌾' at the end of every message. Conclude replies naturally.
9. NEVER REVEAL INTERNAL TOOL NAMES: Present information as your own knowledge, never mention tool names or schemas.

═══ SAFE AGRONOMY & NO-DOSE POLICY (STRICT) ═══
1. NO DOSES FROM MEMORY: Do NOT give fertilizer or pesticide doses, NPK ratios (e.g. 10-10-20), spray schedules, or tank-mix numbers from memory.
2. CROP NUTRITION:
   - For fertilizer or crop nutrition questions, explain principles in 2-3 short sentences:
     * Balanced nutrition depends on growth stage (basal vs vegetative vs flowering/fruit development).
     * Incorporate organic matter (well-rotted farmyard manure/compost) for soil health.
     * State clearly that exact fertilizer doses must come from a soil test and the State Agricultural University's Package of Practices, or your nearest Raitha Samparka Kendra / Krishi Vigyan Kendra (KVK).
   - Ask exactly ONE question: current growth stage of the crop OR the soil type.
   - Offer to explain more simply if needed.
3. DISEASE & PEST TREATMENT:
   - For disease treatment, use only verified disease diagnosis data (disease_db.json).
   - If a farmer asks for a spray or treatment without a photo (e.g. 'what spray for leaf spots?'):
     * DO NOT prescribe chemicals or pesticide doses.
     * Direct the farmer to send a clear photo of the affected leaf so the crop doctor can diagnose the disease safely, rather than spraying blindly.

═══ MANDI PRICES & UNITS ═══
1. ALL mandi prices are in ₹ per quintal (100 kg). NEVER label them per kg or ₹/kg.
2. If the farmer asks for per-kg price, divide the quintal price by 100, and explicitly state you converted it from the mandi quintal rate.
3. REAL DATA DATES: Every price quoted must say "latest data from <date>" using the actual date from the tool result. Never say "today's price" or use today's date if the data date is different.
4. Keep market place names exactly as written in the data (no machine transliteration).
5. Show at most 3 nearby markets.

═══ PRICE ALERTS & HONESTY ═══
1. When asked to set a price alert, restate in one short sentence: crop, target price per quintal, direction ('above' or 'below'), and mandi (or 'nearby mandis'), and ask 'Shall I set this? (yes/no)'.
2. Do NOT call create_price_alert until the farmer confirms with 'yes'.
3. HONESTY RULE: NEVER claim an alert or record was created or saved unless confirmed by the tool result in the current turn. If a tool fails, report the error plainly.
"""
    return prompt


def _get_history_messages(farmer_id: str, current_user_message: str = None) -> list[BaseMessage]:
    """
    Retrieve recent chat history.
    If the current user message was already recorded in DB prior to process_message,
    drop the duplicate trailing user message so it is only added once and last.
    """
    raw_history = get_chat_history(farmer_id, limit=10)
    if raw_history and current_user_message:
        last = raw_history[-1]
        if last.get("role") == "user" and last.get("content", "").strip() == current_user_message.strip():
            raw_history = raw_history[:-1]

    messages: list[BaseMessage] = []
    for h in raw_history:
        role = h.get("role")
        content = h.get("content") or ""
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


async def process_message(
    farmer_id: str,
    message: str,
    disease_result: dict = None,
    client: Optional[ChatGroq] = None,
) -> str:
    """
    Main entry point for processing incoming farmer messages.
    Executes LangChain tool-calling agent with Groq.
    """
    clean_phone = normalize_phone(farmer_id)
    token = active_farmer_phone.set(clean_phone)

    farmer = get_farmer(clean_phone)
    lang = (farmer.get("language") or "english").lower()

    try:
        # ── 1. Check for active slot filling from previous turn ────────────────
        pending_state = get_state(clean_phone)
        resume_tool_call = None
        if pending_state and pending_state.get("flow") == "slot_filling":
            data = pending_state.get("data") or {}
            tool_name = data.get("tool")
            missing_field = data.get("missing")
            partial_args = data.get("args") or {}
            if tool_name in TOOL_MAP and missing_field:
                partial_args[missing_field] = message.strip()
                resume_tool_call = (tool_name, partial_args)
                clear_state(clean_phone)

        # ── 2. Format incoming message with diagnosis context if present ──────
        effective_message = message
        if disease_result and not disease_result.get("error"):
            disease = disease_result.get("disease", "")
            conf = disease_result.get("confidence", "")
            severity = disease_result.get("severity", {})
            urgency = disease_result.get("urgency", "")
            prog = disease_result.get("progression", {})
            diag_ctx = (
                f"[PHOTO DIAGNOSIS RESULT]\n"
                f"Disease: {disease}\n"
                f"Confidence: {conf}\n"
                f"Severity: {severity.get('level', 'Unknown')} ({severity.get('description', '')})\n"
                f"Urgency: {urgency}\n"
            )
            if prog:
                diag_ctx += (
                    f"Spread risk: {prog.get('day_7_spread', '?')} in 7 days\n"
                    f"Warning: {prog.get('warning', '')}\n"
                )
            effective_message = f"{diag_ctx}\nFarmer inquiry: {message or 'Please examine this leaf photo and guide me.'}"

        # ── 3. Build Conversation Messages ─────────────────────────────────────
        system_prompt = _build_system_prompt(farmer, clean_phone)
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        messages.extend(_get_history_messages(clean_phone, current_user_message=message))
        messages.append(HumanMessage(content=effective_message))

        # Log exact messages sent to LLM for debugging & BUG 1 validation
        logger.info(f"[Agent] Sending {len(messages)} messages to LLM for {clean_phone}:")
        for idx, m in enumerate(messages):
            m_role = m.__class__.__name__
            snippet = (m.content or "")[:80].replace("\n", " ")
            logger.info(f"  [{idx}] {m_role}: {snippet}")

        # ── 4. Initialize LLM & Tool Binding ──────────────────────────────────
        max_toks = 1500 if lang in ("kannada", "hindi") else 800
        if client is None:
            client = ChatGroq(
                model_name=GROQ_MODEL,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=0.2,
                max_tokens=max_toks,
                reasoning_effort="low",
            )

        llm_with_tools = client.bind_tools(ALL_TOOLS)

        # If resuming a filled slot directly, execute the tool
        if resume_tool_call:
            t_name, t_args = resume_tool_call
            tool_obj = TOOL_MAP[t_name]
            try:
                tool_output = tool_obj.invoke(t_args)
            except Exception as e:
                tool_output = {"error": str(e)}

            call_id = f"call_resumed_{int(datetime.now().timestamp())}"
            messages.append(
                AIMessage(
                    content="",
                    tool_calls=[{"name": t_name, "args": t_args, "id": call_id}],
                )
            )
            messages.append(
                ToolMessage(
                    content=json.dumps(tool_output, ensure_ascii=False),
                    tool_call_id=call_id,
                )
            )
            final_res = await client.ainvoke(messages)
            reply = final_res.content
        else:
            # ── 5. Standard Turn Execution ────────────────────────────────────────
            response = await llm_with_tools.ainvoke(messages)

            # If LLM requests tool execution
            if response.tool_calls:
                messages.append(response)
                for tool_call in response.tool_calls:
                    name = tool_call["name"]
                    args = tool_call["args"]
                    call_id = tool_call["id"]
                    tool_obj = TOOL_MAP.get(name)

                    if not tool_obj:
                        output = {"error": f"Tool '{name}' is not registered."}
                    else:
                        try:
                            output = tool_obj.invoke(args)
                        except Exception as e:
                            output = {"error": f"Tool execution failed: {str(e)}"}

                    # Check if tool reported missing input for slot-filling
                    if isinstance(output, dict) and output.get("missing"):
                        missing_list = output["missing"]
                        if missing_list:
                            first_missing = missing_list[0]
                            set_state(
                                clean_phone,
                                flow="slot_filling",
                                step="awaiting_input",
                                data={
                                    "tool": name,
                                    "args": args,
                                    "missing": first_missing,
                                },
                            )

                    messages.append(
                        ToolMessage(
                            content=json.dumps(output, ensure_ascii=False),
                            tool_call_id=call_id,
                        )
                    )

                final_response = await client.ainvoke(messages)
                reply = final_response.content
                finish_reason = getattr(final_response, "response_metadata", {}).get("finish_reason")
            else:
                reply = response.content
                finish_reason = getattr(response, "response_metadata", {}).get("finish_reason")

            # ── 6. Truncation Detection & Regeneration (BUG 6) ─────────────────────
            if _is_truncated(reply, finish_reason):
                logger.warning(
                    f"[Agent] Detected truncation for {clean_phone} (finish_reason={finish_reason}). Regenerating once..."
                )
                messages.append(AIMessage(content=reply))
                messages.append(
                    HumanMessage(
                        content="Your previous response was cut off. Please reply completely and concisely in under 80 words in the same language."
                    )
                )
                try:
                    regen_res = await client.ainvoke(messages)
                    if regen_res and regen_res.content and len(regen_res.content.strip()) > 10:
                        reply = regen_res.content
                except Exception as re_err:
                    logger.error(f"[Agent] Truncation regeneration failed: {re_err}")

        # ── 7. Post-process: prevent farmer's name from leading every reply ────────
        farmer_name = farmer.get("name")
        if farmer_name and reply:
            clean_name = farmer_name.strip()
            lead_pattern = rf"^(?:hello|hi|namaste|namaskara|ನಮಸ್ಕಾರ)?\s*{re.escape(clean_name)}(?:\s+(?:ji|avare|ಅವರೇ|जी))?[\s,:-]+"
            if re.match(lead_pattern, reply.strip(), re.IGNORECASE):
                reply = re.sub(lead_pattern, "", reply.strip(), flags=re.IGNORECASE).strip()
                if reply:
                    reply = reply[0].upper() + reply[1:]

        return reply

    except Exception as e:
        logger.exception(f"[Agent] process_message failure for {clean_phone}: {e}")
        return FALLBACK_MESSAGES.get(lang, FALLBACK_MESSAGES["english"])

    finally:
        active_farmer_phone.reset(token)