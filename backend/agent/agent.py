# backend/agent/agent.py
"""
LangChain tool-calling agent for KrishiMitra.
Uses ChatGroq with typed LangChain tools, dynamic per-turn context injection,
stateful slot filling, chat_history persistence, and friendly localized fallbacks.
"""

from __future__ import annotations

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
    month = datetime.now().month
    if 6 <= month <= 10:
        return "Kharif (Monsoon season - sowing/harvesting for rice, maize, cotton, pulses)"
    elif month >= 11 or month <= 3:
        return "Rabi (Winter season - sowing/harvesting for wheat, mustard, gram, potato)"
    else:
        return "Zaid (Summer season - vegetables, pulses, fodder)"


def _build_system_prompt(farmer: dict) -> str:
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
    phone = farmer.get("phone", "")
    open_cases = get_open_disease_cases(phone) if phone else []
    cases_summary = "None"
    if open_cases:
        cases_summary = "; ".join(
            f"{c.get('crop')} {c.get('disease')} (Severity: {c.get('severity_level') or 'Unknown'})"
            for c in open_cases[:3]
        )

    today_str = datetime.now().strftime("%A, %d %B %Y")
    season_str = _get_current_season()

    lang_instructions = {
        "hindi": "Reply in Hindi using clean Devanagari script. Use respectful address like '{name} ji'.",
        "kannada": "Reply in Kannada using clean Kannada script. Use respectful address like '{name} ಅವರೇ'.",
        "english": "Reply in clear, warm Indian English. Address the farmer courteously.",
    }.get(lang, "Reply in the farmer's preferred language.")

    prompt = f"""You are KrishiMitra (कृषि-मित्र), an expert AI agronomy and farming advisor for Indian farmers.

═══ FARMER PROFILE & CONTEXT ═══
• Name: {name or 'Farmer Friend'} (Respectful address: {salutation})
• Registered Language: {lang.upper()} ({lang_instructions})
• Farm Location: {region}
• Cultivated Crops: {crops_str}
• Soil Type: {soil}
• Irrigation / Water Source: {water}
• Farm Size: {area}
• Open Crop Disease Cases: {cases_summary}
• Today's Date: {today_str}
• Agricultural Season: {season_str}

═══ CORE OPERATIONAL RULES ═══
1. STRICT LANGUAGE MATCH: You MUST reply in the farmer's registered language ({lang.upper()}).
   - Hindi: pure Devanagari script (no English transliteration).
   - Kannada: pure Kannada script.
   - English: clear English.
2. NATURAL & PRACTICAL: Keep answers concise, highly practical, and tailored to Indian farming conditions.
3. NEVER REVEAL INTERNAL TOOL NAMES: Never mention tools like 'get_weather', 'predict_price', 'find_best_market', etc. Present the information naturally as your direct knowledge.
4. ONE QUESTION AT A TIME: When asking for clarification or missing information (e.g. crop name or location), ask exactly ONE clear question.
5. AMBIGUOUS CROP HANDLING: If the farmer asks a crop-specific question (e.g. price, advice) without specifying the crop and has multiple crops registered ({crops_str}), gently ask which one they are inquiring about.
6. HONESTY: If market price or data is unavailable for a crop, state honestly that current live price data is not available. Never invent fake prices.
7. NO FORCED CLOSING PHRASES: Do NOT append repetitive boilerplate lines like 'Koi aur madad chahiye? 🌾' at the end of every message. Conclude replies naturally.
8. RESPECTFUL ADDRESS: Occasionally address the farmer by their respectful name ({salutation}).
"""
    return prompt


def _get_history_messages(farmer_id: str) -> list[BaseMessage]:
    raw_history = get_chat_history(farmer_id, limit=10)
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
                # Fill slot with user's current reply
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
        system_prompt = _build_system_prompt(farmer)
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        messages.extend(_get_history_messages(clean_phone))
        messages.append(HumanMessage(content=effective_message))

        # ── 4. Initialize LLM & Tool Binding ──────────────────────────────────
        if client is None:
            client = ChatGroq(
                model_name=GROQ_MODEL,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=0.2,
                max_tokens=800,
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

            # Fake assistant tool call & tool result in messages
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

            # Let LLM synthesize final reply
            final_res = await client.ainvoke(messages)
            return final_res.content

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

            # Second turn to generate final message based on tool outputs
            final_response = await client.ainvoke(messages)
            return final_response.content

        return response.content

    except Exception as e:
        logger.exception(f"[Agent] process_message failure for {clean_phone}: {e}")
        return FALLBACK_MESSAGES.get(lang, FALLBACK_MESSAGES["english"])

    finally:
        active_farmer_phone.reset(token)