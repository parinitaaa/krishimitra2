# backend/tests/test_langchain_agent.py
"""
Unit and acceptance tests for LangChain tool-calling agent (ChatGroq).
Tests:
- Tool execution & no tool names in final output
- Slot filling multi-turn flow (one clarifying question -> completion)
- Honest mandi price (no mock fallback, returns error: no_data)
- Government schemes (farmer's real state + mandatory disclaimer)
- Language consistency & context injection
- History persistence across turns
- Localized friendly fallback on error
"""

import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langchain_core.messages import AIMessage, HumanMessage

from agent.agent import process_message, _build_system_prompt, FALLBACK_MESSAGES
from agent.tools import (
    get_weather,
    get_mandi_price,
    get_treatment,
    get_govt_schemes,
    predict_price,
    create_price_alert,
    list_price_alerts,
    cancel_price_alert,
    ALL_TOOLS,
)
from farmer_store import (
    get_farmer,
    update_farmer_profile,
    add_chat,
    get_state,
    clear_state,
    get_farmer_alerts,
    set_farmer_language,
    save_farmer_location,
)


class TestLangChainAgent(unittest.IsolatedAsyncioTestCase):
    test_phone = "+919777700001"

    async def asyncSetUp(self):
        clear_state(self.test_phone)
        update_farmer_profile(
            self.test_phone,
            name="Ramesh Patil",
            language="hindi",
            location="Nashik, Maharashtra",
            district="Nashik",
            state="Maharashtra",
            lat=19.9975,
            lng=73.7898,
            crops=["Tomato", "Onion"],
            soil_type="Black",
            water_source="Borewell",
            farm_size_acres=3.5,
        )
        save_farmer_location(self.test_phone, lat=19.9975, lng=73.7898)

    async def asyncTearDown(self):
        clear_state(self.test_phone)

    def test_01_mandi_price_no_mock_fallback(self):
        """Mandi price tool must NOT return hardcoded mock prices when data is missing."""
        res = get_mandi_price.invoke({"crop": "dragonfruit_uncommon_crop", "state": "Maharashtra"})
        self.assertEqual(res.get("error"), "no_data")
        self.assertEqual(res.get("crop"), "dragonfruit_uncommon_crop")
        # Check standard crop with no live API key also doesn't return fake hardcoded dict
        with patch.dict("os.environ", {"AGMARKNET_API_KEY": ""}):
            res2 = get_mandi_price.invoke({"crop": "unregistered_crop_123"})
            self.assertEqual(res2.get("error"), "no_data")
            self.assertNotIn("modal", str(res2).lower())

    def test_02_govt_schemes_uses_real_state_and_disclaimer(self):
        """Government schemes tool must use the real state and include official office disclaimer."""
        res = get_govt_schemes.invoke({"state": "Karnataka"})
        self.assertEqual(res.get("state"), "Karnataka")
        self.assertIn("confirm details at your nearest agriculture office or the official scheme website", res.get("disclaimer", "").lower())
        self.assertTrue(len(res.get("schemes", [])) >= 4)

    def test_03_system_prompt_context_injection(self):
        """System prompt must inject identity, registered language, crops, soil, season, and rules."""
        farmer = get_farmer(self.test_phone)
        prompt = _build_system_prompt(farmer)
        self.assertIn("Ramesh Patil", prompt)
        self.assertIn("HINDI", prompt)
        self.assertIn("Tomato, Onion", prompt)
        self.assertIn("Black", prompt)
        self.assertIn("Borewell", prompt)
        self.assertIn("3.5 acres", prompt)
        # Operational rules
        self.assertIn("NEVER REVEAL INTERNAL TOOL NAMES", prompt)
        self.assertIn("ONE QUESTION AT A TIME", prompt)
        self.assertIn("AMBIGUOUS CROP HANDLING", prompt)
        self.assertIn("NO FORCED CLOSING PHRASES", prompt)

    async def test_04_mock_llm_tool_execution_and_no_tool_names_in_output(self):
        """Agent executes tools and synthesizes natural response with no internal tool names."""
        mock_client = MagicMock()
        mock_bind = MagicMock()

        # Turn 1: LLM decides to call get_weather
        call_msg = AIMessage(
            content="",
            tool_calls=[{"name": "get_weather", "args": {"location": "Nashik"}, "id": "call_w1"}],
        )
        # Turn 2: LLM receives tool output and responds naturally
        final_msg = AIMessage(
            content="नासिक में आज तापमान 28°C है और आर्द्रता 65% है। मौसम छिड़काव के लिए अनुकूल है।"
        )

        mock_bind.ainvoke = AsyncMock(return_value=call_msg)
        mock_client.bind_tools = MagicMock(return_value=mock_bind)
        mock_client.ainvoke = AsyncMock(return_value=final_msg)

        reply = await process_message(
            farmer_id=self.test_phone,
            message="आज का मौसम कैसा है?",
            client=mock_client,
        )

        self.assertIn("नासिक", reply)
        self.assertNotIn("get_weather", reply)
        self.assertNotIn("tool_call", reply)
        self.assertNotIn("tool_calls", reply)
        self.assertNotIn("args", reply)

    async def test_05_slot_filling_multi_turn_flow(self):
        """When input is missing, asks one clarifying question, saves state, and completes on next turn."""
        mock_client = MagicMock()
        mock_bind = MagicMock()

        # Turn 1: User asks "Predict price". Tool returns {"missing": ["crop"]}.
        # LLM asks clarifying question: "Which crop?"
        call_pred = AIMessage(
            content="",
            tool_calls=[{"name": "predict_price", "args": {"crop": ""}, "id": "call_p1"}],
        )
        clarify_msg = AIMessage(
            content="आप किस फसल का भाव पूर्वानुमान जानना चाहते हैं — टमाटर या प्याज?"
        )
        mock_bind.ainvoke = AsyncMock(return_value=call_pred)
        mock_client.bind_tools = MagicMock(return_value=mock_bind)
        mock_client.ainvoke = AsyncMock(return_value=clarify_msg)

        reply1 = await process_message(
            farmer_id=self.test_phone,
            message="भाव का क्या अनुमान है?",
            client=mock_client,
        )

        self.assertIn("टमाटर या प्याज", reply1)
        # Verify slot filling state is saved in DB
        state = get_state(self.test_phone)
        self.assertIsNotNone(state)
        self.assertEqual(state.get("flow"), "slot_filling")
        self.assertEqual(state.get("step"), "awaiting_input")
        self.assertEqual(state.get("data", {}).get("missing"), "crop")

        # Turn 2: Farmer replies "Tomato". Agent resumes slot and completes task.
        completed_msg = AIMessage(
            content="टमाटर का भाव अगले 7 दिनों में 5% बढ़ने की संभावना है। सलाह: कुछ दिन रोककर बेचें।"
        )
        mock_client.ainvoke = AsyncMock(return_value=completed_msg)

        reply2 = await process_message(
            farmer_id=self.test_phone,
            message="टमाटर",
            client=mock_client,
        )

        self.assertIn("टमाटर", reply2)
        # Verify slot filling state is cleared
        cleared_state = get_state(self.test_phone)
        self.assertIsNone(cleared_state)

    async def test_06_price_alert_lifecycle_via_tools(self):
        """Create, list, and cancel price alerts using typed LangChain tools."""
        from agent.tools import active_farmer_phone
        tok = active_farmer_phone.set(self.test_phone)
        try:
            # 1. Create alert
            created = create_price_alert.invoke({
                "crop": "Tomato",
                "target_price": 2500.0,
                "direction": "above",
            })
            self.assertEqual(created.get("status"), "created")
            self.assertEqual(created.get("crop"), "Tomato")

            # 2. List alerts
            alerts_res = list_price_alerts.invoke({})
            active_list = alerts_res.get("alerts", [])
            self.assertTrue(len(active_list) >= 1)
            target_alert = next((a for a in active_list if a["commodity"] == "tomato"), None)
            self.assertIsNotNone(target_alert)
            self.assertEqual(target_alert["target_price"], 2500.0)

            # 3. Cancel alert
            cancelled = cancel_price_alert.invoke({"alert_id": target_alert["id"]})
            self.assertEqual(cancelled.get("status"), "cancelled")

            # 4. Verify no longer in active list
            remaining = list_price_alerts.invoke({}).get("alerts", [])
            self.assertFalse(any(a["id"] == target_alert["id"] for a in remaining))
        finally:
            active_farmer_phone.reset(tok)

    async def test_07_language_consistency_and_localized_error_fallback(self):
        """On unexpected exception, returns localized friendly message in stored language without exposing error trace."""
        # Set Kannada language
        set_farmer_language(self.test_phone, "kannada")

        mock_client = MagicMock()
        mock_client.bind_tools.side_effect = RuntimeError("Groq rate limit exceeded")

        reply = await process_message(
            farmer_id=self.test_phone,
            message="ಹವಾಮಾನ ಹೇಗಿದೆ?",
            client=mock_client,
        )

        # Must return friendly Kannada fallback
        self.assertEqual(reply, FALLBACK_MESSAGES["kannada"])
        self.assertNotIn("RuntimeError", reply)
        self.assertNotIn("rate limit", reply)
        self.assertNotIn("Sorry, please try again. Error:", reply)


if __name__ == "__main__":
    unittest.main()
