# Phase 7 — Website Analytics Domain

## Objective

This phase adds a synthetic GA4-style website analytics domain to the VoyageData platform. The goal was to model session activity, page views, and event-level engagement while preserving campaign attribution context through `campaign_id`.

## Source

The website dataset is synthetic and covers the period from 2026-04-01 to 2026-09-30. It contains:

- web sessions
- page views
- website events

The primary funnel is:

search availability → property view → booking start → purchase

Purchase events include a synthetic conversion value to support later marketing attribution and conversion analysis.

## Operational Source

PostgreSQL tables:

- `web_sessions`
- `web_page_views`
- `web_events`

FastAPI endpoints:

- `/api/v1/web-sessions`
- `/api/v1/web-page-views`
- `/api/v1/web-events`

## Ingestion

Airbyte ingests the three streams into:

`s3://voyage-data-plateform-yuvaraj-india/raw/airbyte/voyage_raw/`

The streams support both full refresh and incremental extraction using `updated_at`.

## Databricks

Bronze:

- `voyage.bronze.web_sessions`
- `voyage.bronze.web_page_views`
- `voyage.bronze.web_events`

Silver:

- `voyage.silver.fact_web_session`
- `voyage.silver.fact_web_page_view`
- `voyage.silver.fact_web_event`

Silver retains only the latest record for each source business key.

## dbt

Staging:

- `stg_web_sessions`
- `stg_web_page_views`
- `stg_web_events`

Intermediate:

- `int_web_session_metrics`

Marts:

- `fct_web_session`
- `fct_website_daily`

The session intermediate model aggregates page views and events before joining them to sessions to avoid fan-out and duplicate metric counts.

## Grain

`fct_web_session`:

One row per session.

`fct_website_daily`:

One row per tenant, date, source, medium, and campaign.

## Validation

The validation checks include:

- source-to-Silver counts
- session, page-view, and event relationships
- campaign ID integrity
- unique session grain
- unique daily grain
- valid funnel metrics
- Silver-to-mart reconciliation

## Scope Limitation

The website conversion value is synthetic.

It is intentionally not tied directly to the historical hotel booking records because the operational booking source contains 2014–2017 data, while the synthetic marketing and website domains cover 2026.

Marketing attribution and the booking/conversion bridge are addressed in a later phase.