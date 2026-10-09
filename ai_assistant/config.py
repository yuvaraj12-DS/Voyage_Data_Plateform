"""Central configuration for the VoyageData AI Analyst.

Configuration is loaded from ai_assistant/.env first, then the repository-root
.env_ai as a backwards-compatible fallback. Environment variables override both.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent

# Prefer the new location, but keep the currently used root .env_ai working.
load_dotenv(PACKAGE_DIR / ".env", override=False)
load_dotenv(PROJECT_ROOT / ".env_ai", override=False)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b").strip()
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME", "").strip()
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH", "").strip()
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "").strip()
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "voyage").strip()
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA", "dbt_dev").strip()

# The app currently mirrors the Power BI core-marketing reporting window.
MARKETING_DEFAULT_START = os.getenv("MARKETING_DEFAULT_START", "2026-04-01")
MARKETING_DEFAULT_END = os.getenv("MARKETING_DEFAULT_END", "2026-09-30")

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_sql_identifier(value: str, label: str) -> str:
    """Validate configurable catalog/schema identifiers before SQL interpolation."""
    if not value or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {label} identifier in configuration.")
    return value


def table_name(name: str) -> str:
    """Return a fully qualified name for a known table.

    `name` is always a hard-coded table name from the approved tool layer;
    table names are never accepted from the LLM.
    """
    safe_catalog = validate_sql_identifier(DATABRICKS_CATALOG, "catalog")
    safe_schema = validate_sql_identifier(DATABRICKS_SCHEMA, "schema")
    safe_table = validate_sql_identifier(name, "table")
    return f"{safe_catalog}.{safe_schema}.{safe_table}"


def validate_runtime_config(require_llm: bool = True) -> None:
    missing = []
    if not DATABRICKS_SERVER_HOSTNAME:
        missing.append("DATABRICKS_SERVER_HOSTNAME")
    if not DATABRICKS_HTTP_PATH:
        missing.append("DATABRICKS_HTTP_PATH")
    if not DATABRICKS_TOKEN:
        missing.append("DATABRICKS_TOKEN")
    if require_llm and not OLLAMA_API_KEY and OLLAMA_BASE_URL.startswith("https://ollama.com"):
        missing.append("OLLAMA_API_KEY")
    if not OLLAMA_MODEL:
        missing.append("OLLAMA_MODEL")
    if missing:
        raise RuntimeError("Missing required environment setting(s): " + ", ".join(missing))
