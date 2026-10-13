# Phase 6 — Marketing Data Domain

## Objective

This phase extends the VoyageData platform with a synthetic travel marketing domain designed to support campaign-level advertising performance analysis across multiple tenants and channels.

The domain simulates Google Ads and Meta Ads style data without depending on a real advertising account.

## Data Model

The marketing domain contains four operational entities:

- campaigns
- ad groups
- ads
- campaign daily metrics

The hierarchy is:

Tenant → Campaign → Ad Group → Ad

Campaign daily metrics store daily campaign-level performance.

Every marketing business table contains `tenant_id` to preserve the multi-tenant design.

## Synthetic Data

The marketing source contains:

- 2 tenants
- 6 campaigns
- 12 ad groups
- 24 ads
- 1,098 campaign-day metric records

The synthetic performance period is:

`2026-04-01` through `2026-09-30`

The campaign performance data follows a small set of business constraints:

- clicks cannot exceed impressions
- conversions cannot exceed clicks
- spend cannot be negative
- revenue cannot be negative

## Ingestion

Marketing data is exposed through the FastAPI application and ingested into the platform through Airbyte.

Airbyte streams:

- campaigns
- ad_groups
- ads
- campaign_performance

The streams support incremental extraction using `updated_at` and the API `updated_after` parameter.

Raw Airbyte data is stored in Amazon S3 under:

`raw/airbyte/voyage_raw/`

The raw layer preserves Airbyte records and incremental versions.

## Databricks

Marketing raw data is loaded into the Databricks Bronze layer and deduplicated into Silver.

Silver models:

- `voyage.silver.dim_campaign`
- `voyage.silver.dim_ad_group`
- `voyage.silver.dim_ad`
- `voyage.silver.fact_campaign_daily`

Silver retains the latest record for each business key using `updated_at` and the Airbyte extraction timestamp.

Referential integrity checks between the marketing entities returned zero orphan records.

## dbt Transformation

dbt provides the analytical transformation layer.

### Staging

- `stg_campaigns`
- `stg_ad_groups`
- `stg_ads`
- `stg_campaign_daily_metrics`

### Intermediate

`int_campaign_daily_performance`

This model joins campaign performance with campaign attributes and calculates:

- CTR
- CPC
- conversion rate
- ROAS

### Final Mart

`fct_campaign_daily`

Grain:

> One row per tenant, campaign, and date.

Columns include:

- date
- tenant_id
- campaign_id
- campaign_name
- channel
- campaign_type
- objective
- campaign_status
- impressions
- clicks
- spend
- conversions
- revenue
- ctr
- cpc
- conversion_rate
- roas
- updated_at

Ad group and ad staging models are intentionally not joined into the campaign-day fact because the current performance source is at campaign-day grain and does not contain ad-group or ad-level metric identifiers. Keeping those dimensions separate avoids metric duplication from a fan-out join.

## Validation

Final marketing validation confirmed:

- 1,098 final fact rows
- 1,098 unique tenant/campaign/date combinations
- 6 campaigns
- 2 tenants
- campaign period from 2026-04-01 to 2026-09-30
- no invalid metric values
- no unexpected null values in required analytical fields
- Silver-to-mart reconciliation passed

The final mart totals reconcile exactly with the Databricks Silver campaign performance fact for:

- impressions
- clicks
- spend
- conversions
- revenue

## Result

The marketing domain now provides a complete pipeline from the source API through Airbyte, S3, Databricks Bronze and Silver, dbt transformation, and the final campaign-day analytical mart.