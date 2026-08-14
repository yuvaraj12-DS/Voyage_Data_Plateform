# Architecture

## Target Architecture

Source Systems
    ↓
Airbyte
    ↓
AWS S3 Raw Data Lake
    ↓
Databricks
    ↓
Bronze / Silver
    ↓
dbt
    ↓
Gold Analytical Models
    ↓
BI / AI Analytics

Airflow will orchestrate the end-to-end workflow.

## Source Systems

### Marketing

A synthetic REST API representing a digital advertising
platform such as Google Ads or Meta Ads.

### Booking

A synthetic booking REST API backed by the public Hotel
Booking Demand dataset.

### Website Analytics

Synthetic web events representing sessions, page views,
campaign interactions and purchases.

## Storage

AWS S3 will be used as the raw data lake.

## Processing

Databricks will be used for lakehouse processing and Delta
table storage.

## Transformation

dbt will create staging, intermediate and analytical models.

## Orchestration

Airflow will coordinate ingestion, processing, transformation,
testing and monitoring.

The PostgreSQL database represents the operational booking source. FastAPI exposes the source through authenticated REST endpoints. Airbyte will consume these endpoints in the next phase.