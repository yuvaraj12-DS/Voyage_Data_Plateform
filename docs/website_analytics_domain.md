# Phase 7 — Website Analytics Domain

## Objective

Add a synthetic GA4-style website analytics domain to the VoyageData platform.

The domain provides session, page-view, and event-level website activity and preserves campaign attribution metadata through `campaign_id`.

## Source

The website data is synthetic and covers:

2026-04-01 through 2026-09-30

The source contains:

- web sessions
- page views
- website events

The main funnel is:

search availability → property view → booking start → purchase

Purchase events contain a synthetic conversion value.

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

The streams support full refresh and incremental extraction using `updated_at`.

## Databricks

Bronze:

- `voyage.bronze.web_sessions`
- `voyage.bronze.web_page_views`
- `voyage.bronze.web_events`

Silver:

- `voyage.silver.fact_web_session`
- `voyage.silver.fact_web_page_view`
- `voyage.silver.fact_web_event`

Silver retains the latest record for each source business key.

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

The session intermediate model aggregates page views and events before joining them to sessions to avoid fan-out and metric duplication.

## Grain

`fct_web_session`:

one row per session

`fct_website_daily`:

one row per tenant, date, source, medium, and campaign

## Validation

Validate:

- source to Silver counts
- session/page-view/event relationships
- campaign ID integrity
- unique session grain
- unique daily grain
- valid funnel metrics
- Silver-to-mart reconciliation

## Scope Limitation

The website conversion value is synthetic.

It is intentionally not represented as a direct link to the existing hotel booking records because the operational booking source contains historical 2014–2017 data while the synthetic marketing and website domains cover 2026.

Marketing attribution and booking/conversion linkage are addressed in a later phase.