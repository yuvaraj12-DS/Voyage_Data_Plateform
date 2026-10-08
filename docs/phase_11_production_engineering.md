# Phase 11 — Production Engineering, Monitoring and CI/CD

## Objective

Harden the VoyageData platform with monitoring, data-quality validation,
freshness checks, structured Airflow logging, failure handling and CI/CD.

## Monitoring

- Airbyte synchronization status
- Bronze data freshness
- dbt execution status
- pipeline validation
- data-quality validation
- pipeline audit history

## Freshness policy

Strict freshness:

- marketing_bookings
- marketing_campaign_performance
- website_events
- website_sessions
- website_page_views

Reference datasets:

- bookings
- customers
- properties
- tenants
- marketing_campaigns
- marketing_ad_groups
- marketing_ads

Reference datasets are reported as N/A because they are not expected to
change every pipeline run.

## Airflow

Daily orchestration:

Airbyte
→ S3
→ Databricks
→ dbt
→ validation
→ monitoring

Failure and retry callbacks provide structured operational logging.

## Data quality

The monitoring layer validates:

- completeness
- duplicates
- referential integrity
- campaign grain
- website event validity
- booking validity
- Silver-to-dbt reconciliation
- dimension completeness

## CI/CD

GitHub Actions validates:

- dbt installation
- dbt project configuration
- dbt compilation
- Python syntax
- dbt build and tests

CI uses the isolated `voyage.dbt_ci` schema.

## Security

Credentials are stored as GitHub repository secrets and are not committed
to the repository.

## Final status

Phase 11 completed after successful:

- Airflow orchestration
- freshness validation
- data-quality validation
- monitoring audit
- GitHub Actions CI