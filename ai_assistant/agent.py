"""Ollama Cloud tool-calling agent with fixed, approved business tools only."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from ollama import Client
from pydantic import ValidationError

from .config import OLLAMA_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from .prompts import build_system_prompt
from .schemas import validate_tool_arguments
from .tools import AVAILABLE_TOOLS


TOOL_SPECS = [
    {"type": "function", "function": {"name": "get_website_performance", "description": "Return only website sessions and website conversions, matching the Power BI measures for the requested period.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string", "description": "Period start in YYYY-MM-DD; omit with end_date to use default marketing window."}, "end_date": {"type": "string", "description": "Period end in YYYY-MM-DD."}, "tenant_id": {"type": "string", "description": "Optional tenant ID filter."}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_marketing_funnel", "description": "Get aggregate marketing funnel totals and calculated rates for the requested period.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string", "description": "Period start YYYY-MM-DD."}, "end_date": {"type": "string", "description": "Period end YYYY-MM-DD."}, "tenant_id": {"type": "string", "description": "Optional tenant ID filter."}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_campaign_performance", "description": "Get overall and per-campaign marketing KPIs including spend, net revenue and ROAS. Default period is 2026-04-01 through 2026-09-30.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string", "description": "Period start YYYY-MM-DD."}, "end_date": {"type": "string", "description": "Period end YYYY-MM-DD."}, "tenant_id": {"type": "string", "description": "Optional tenant ID filter."}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_attribution_performance", "description": "Get attribution totals and campaign results for first_click, last_click, linear, or all models.", "parameters": {"type": "object", "properties": {"model_type": {"type": "string", "enum": ["first_click", "last_click", "linear", "all"]}, "start_date": {"type": "string", "description": "Period start YYYY-MM-DD."}, "end_date": {"type": "string", "description": "Period end YYYY-MM-DD."}, "tenant_id": {"type": "string", "description": "Optional tenant ID filter."}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_historical_booking_performance", "description": "Get historical hotel booking KPIs from 2014-2017. Use year for a single calendar year, or start_date/end_date for a custom period.", "parameters": {"type": "object", "properties": {"year": {"type": "integer", "minimum": 2014, "maximum": 2017}, "start_date": {"type": "string", "description": "Period start YYYY-MM-DD."}, "end_date": {"type": "string", "description": "Period end YYYY-MM-DD."}, "tenant_id": {"type": "string", "description": "Optional tenant ID filter."}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_property_performance", "description": "Rank properties by historical bookings/value, optionally by date range and tenant.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string", "description": "Optional start YYYY-MM-DD; provide together with end_date."}, "end_date": {"type": "string", "description": "Optional end YYYY-MM-DD; provide together with start_date."}, "tenant_id": {"type": "string", "description": "Optional tenant ID filter."}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_tenant_performance", "description": "Rank tenants by historical hotel bookings and completed booking value. Supports optional dates.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string", "description": "Optional start YYYY-MM-DD; provide together with end_date."}, "end_date": {"type": "string", "description": "Optional end YYYY-MM-DD; provide together with start_date."}, "tenant_id": {"type": "string", "description": "Optional tenant ID filter."}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, "additionalProperties": False}}},
]

_DATA_REQUEST_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(total|how many|how much|what was|what were|which|compare|highest|lowest|rank|ranking|trend|during|between|in 20\d{2}|for 20\d{2})\b",
        r"\b(sessions|conversions|clicks|impressions|spend|revenue|bookings|cancellation rate|cancelled|canceled|adr|room nights|roas|ctr|cpc|attribution|campaign performance|tenant performance|property performance|funnel)\b",
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    )
]
_DEFINITION_ONLY = re.compile(r"^\s*(what is|what does|define|explain|how do you calculate|what is the formula for)\b", re.IGNORECASE)


def _requires_data_tool(question: str) -> bool:
    text = question.strip()
    if _DEFINITION_ONLY.search(text) and not re.search(r"\b(our|my|total|overall|in 20\d{2}|this month|last month|for|during|compare|highest|lowest)\b", text, re.IGNORECASE):
        return False
    return any(pattern.search(text) for pattern in _DATA_REQUEST_PATTERNS)


def _get_client() -> Client:
    if OLLAMA_BASE_URL.startswith("https://ollama.com") and not OLLAMA_API_KEY:
        raise RuntimeError("OLLAMA_API_KEY is not configured for Ollama Cloud.")
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None
    return Client(host=OLLAMA_BASE_URL, headers=headers, timeout=OLLAMA_TIMEOUT_SECONDS)


def _tool_value(tool_call: Any) -> tuple[str, dict]:
    function = getattr(tool_call, "function", None)
    if function is None and isinstance(tool_call, dict):
        function = tool_call.get("function", {})
    name = getattr(function, "name", None) if not isinstance(function, dict) else function.get("name")
    arguments = getattr(function, "arguments", None) if not isinstance(function, dict) else function.get("arguments")
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if not isinstance(arguments, dict):
        arguments = {}
    if not isinstance(name, str):
        raise ValueError("The model returned an invalid tool call.")
    return name, arguments


def _safe_error_result() -> dict:
    return {
        "answer": "I couldn't verify the requested result because the approved data query failed. No metric has been inferred. Please retry, or check the Databricks connection and requested filters.",
        "tool_results": [],
        "sources": [],
        "error": True,
    }


def ask(question: str, history: list[dict[str, str]] | None = None) -> dict:
    """Answer a question using Ollama tool-calling and approved SQL tools."""
    question = (question or "").strip()
    if not question:
        return {"answer": "Please enter a question.", "tool_results": [], "sources": [], "error": False}

    try:
        client = _get_client()
    except Exception:
        return _safe_error_result()

    messages: list[Any] = [{"role": "system", "content": build_system_prompt(date.today())}]
    
    # Preserve conversation context safely within history buffer token ranges
    for item in (history or [])[-6:]:
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            messages.append({"role": item["role"], "content": str(item["content"])[:4000]})
    messages.append({"role": "user", "content": question})

    collected_results: list[dict] = []
    used_tool = False

    # Guard array loop preventing agent processing recursion runs
    for _ in range(4):
        try:
            response = client.chat(model=OLLAMA_MODEL, messages=messages, tools=TOOL_SPECS, stream=False, options={"temperature": 0})
        except Exception:
            return _safe_error_result()

        assistant_message = response.message
        tool_calls = getattr(assistant_message, "tool_calls", None) or []
        if not tool_calls:
            answer = (getattr(assistant_message, "content", None) or "").strip()
            
            # Anti-hallucination boundary check matching grounding framework metrics
            if _requires_data_tool(question) and not used_tool:
                return {
                    "answer": "I couldn't identify and execute an approved data query for that metric, so I won't guess. Please rephrase the question with the metric and period, for example: 'What were website sessions and conversions from 2026-09-01 to 2026-09-30?'",
                    "tool_results": [],
                    "sources": [],
                    "error": True,
                }
            return {
                "answer": answer or "I couldn't produce a verified answer. Please rephrase the question.",
                "tool_results": collected_results,
                "sources": sorted({table for result in collected_results for table in result.get("source_tables", [])}),
                "error": False,
            }

        messages.append(assistant_message)
        for tool_call in tool_calls:
            try:
                tool_name, raw_arguments = _tool_value(tool_call)
                if tool_name not in AVAILABLE_TOOLS:
                    raise ValueError("The requested tool is not approved.")
                
                # Check metrics data boundaries using strictly declared Pydantic structures
                validated_arguments = validate_tool_arguments(tool_name, raw_arguments)
                result = AVAILABLE_TOOLS[tool_name](**validated_arguments)
                if result.get("ok") is not True:
                    return _safe_error_result()

                used_tool = True
                collected_results.append(result)
                tool_message = {
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
                messages.append(tool_message)
            except (ValidationError, ValueError, TypeError, json.JSONDecodeError):
                return {
                    "answer": "I couldn't run that query because its filters or tool arguments were invalid. Please specify the date range clearly (YYYY-MM-DD) and use a supported attribution model if applicable.",
                    "tool_results": [],
                    "sources": [],
                    "error": True,
                }
            except Exception:
                return _safe_error_result()

    return {
        "answer": "I stopped after several tool steps to avoid an uncontrolled query loop. Please narrow the question or specify a date range.",
        "tool_results": collected_results,
        "sources": sorted({table for result in collected_results for table in result.get("source_tables", [])}),
        "error": True,
    }