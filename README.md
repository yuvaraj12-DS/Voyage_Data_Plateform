
# VoyageData — Travel Marketing Data Platform

## Project Overview

VoyageData is a production-style travel marketing data platform
designed to unify marketing, booking, and website analytics data.

The platform will ingest data from multiple source systems,
store raw data in AWS S3, process data using Databricks,
transform analytical models using dbt, and orchestrate the
end-to-end workflow using Airflow.

## Business Problem

Travel companies often have marketing, booking, and website
data distributed across different systems.

The objective of this project is to build a reliable platform
that allows the business to analyze marketing spend, bookings,
revenue, conversion rates, and ROAS in a unified analytical layer.

## Status

Phase 1 — Project Foundation

## Current Status

Phase 2 — Source System

Completed:

- PostgreSQL source database
- Operational booking schema
- Synthetic tenants and properties
- Booking data loader
- Source-data validation
- Rejected-record handling
- FastAPI REST API
- API-key authentication
- Pagination
- Tenant filtering
- Incremental timestamp filtering

# VoyageData AI Analyst — Phase 12 replacement set

This package is designed to replace the existing `ai_assistant` Python files while keeping the application architecture small and auditable.

## Files

- `config.py`: environment/configuration loading. Loads `ai_assistant/.env` first and supports the existing repository-root `.env_ai` file as a fallback.
- `databricks_client.py`: parameterized read query wrapper.
- `schemas.py`: validation of model-provided tool arguments.
- `tools.py`: approved SQL queries mapped to the existing Power BI semantic definitions.
- `prompts.py`: business definitions and instructions not to invent metrics.
- `agent.py`: Ollama tool-calling loop; only registered tools are callable.
- `app.py`: Streamlit chat UI with retrieved data and source tables.
- `inspection_schema.py`: live Databricks schema inspector.
- `test_agent.py`: offline input/routing tests.
- `test_ollama_cloud.py`: Ollama connection smoke test.
- `validate_grounding.py`: live checks of metric reconciliation.

## Installation

From the repository root, in `.venv-ai`:

```powershell
pip install -r .\requirements-ai.txt
```

Configuration can be kept in the current repository-root `.env_ai` file. Alternatively, copy `ai_assistant/.env.example` to `ai_assistant/.env` and populate it. The `ai_assistant/.env` values take precedence over `.env_ai` because it is loaded first.

For direct access to `https://ollama.com`, set an Ollama Cloud API key. The model name should match the model shown in your Ollama Cloud account/API; the direct cloud endpoint commonly uses a name such as `gpt-oss:20b` rather than the local-router `gpt-oss:20b-cloud` name.

## Commands

Run these from the repository root:

```powershell
python -m unittest ai_assistant.test_agent -v
python -m ai_assistant.test_ollama_cloud
python -m ai_assistant.inspection_schema
python -m ai_assistant.validate_grounding
streamlit run ai_assistant/app.py
```

## Metric semantics

Marketing and website answers mirror the Power BI measures sourced from `fct_marketing_funnel_daily`. Attribution queries use `fct_marketing_attribution_daily` and preserve `first_click`, `last_click`, and `linear`. Historical booking metrics use `fct_booking_daily`, properties use `fct_property_daily`, and all-time tenant summary metrics use `fct_tenant_performance`.

Historical hotel bookings (2014-2017) and synthetic marketing/website transactions (2026) are separate domains and must not be presented as one continuous campaign-to-booking history.

## Security limitations

The app has no end-user authentication or server-enforced per-user tenant authorization. Do not expose it publicly yet. Use a least-privilege Databricks identity with `SELECT` access only to the approved marts. A `tenant_id` supplied as a query filter is not an authorization boundary; add authenticated identity and server-side tenant enforcement before a multi-tenant deployment.
