"""Streamlit interface for VoyageData AI Analyst."""
from __future__ import annotations

import os
import sys

# Force Python to recognize the root project directory workspace paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from ai_assistant.agent import ask
from ai_assistant.config import OLLAMA_MODEL, DATABRICKS_CATALOG, DATABRICKS_SCHEMA

st.set_page_config(page_title="VoyageData AI Analyst", layout="wide")
st.title("VoyageData AI Analyst")
st.caption("Conversational analytics grounded in trusted dbt analytical marts.")

with st.sidebar:
    st.subheader("Data and model")
    st.write(f"**Analytical layer:** `{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}`")
    st.write(f"**Model:** `{OLLAMA_MODEL}`")
    st.caption("Data questions are answered through approved, parameterized SQL tools. The model cannot submit arbitrary SQL.")
    st.warning("Demo note: this app does not authenticate individual users or enforce per-user tenant access. Keep it private until an authentication and authorization layer is added.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            st.caption("Source: " + ", ".join(f"`{source}`" for source in message["sources"]))
        for item in message.get("display_data", []):
            st.dataframe(pd.DataFrame(item), use_container_width=True, hide_index=True)

prompt = st.chat_input("Ask about marketing, funnel, attribution, properties, tenants, or historical bookings...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking the approved analytical tools..."):
            history = [
                {"role": item["role"], "content": item["content"]}
                for item in st.session_state.messages[:-1]
                if item["role"] in {"user", "assistant"}
            ]
            result = ask(prompt, history=history)
        st.markdown(result["answer"])

        display_data = []
        for tool_result in result.get("tool_results", []):
            data = tool_result.get("data")
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list) and value:
                        st.markdown(f"**Supporting data — {key.replace('_', ' ').title()}**")
                        frame_data = value
                        st.dataframe(pd.DataFrame(frame_data), use_container_width=True, hide_index=True)
                        display_data.append(frame_data)
                    elif isinstance(value, dict) and value:
                        st.markdown(f"**Retrieved metrics — {key.replace('_', ' ').title()}**")
                        frame_data = [value]
                        st.dataframe(pd.DataFrame(frame_data), use_container_width=True, hide_index=True)
                        display_data.append(frame_data)
                # For a single flat result row, render it as one table.
                if data and all(not isinstance(value, (dict, list)) for value in data.values()):
                    frame_data = [data]
                    st.dataframe(pd.DataFrame(frame_data), use_container_width=True, hide_index=True)
                    display_data.append(frame_data)
        sources = result.get("sources", [])
        if sources:
            st.caption("Source: " + ", ".join(f"`{source}`" for source in sources))
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": sources,
            "display_data": display_data,
        })
