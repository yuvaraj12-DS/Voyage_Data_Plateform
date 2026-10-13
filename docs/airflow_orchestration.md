# Phase 10 — Airflow Orchestration

## Objective

This phase operationalizes the VoyageData platform by introducing Apache Airflow as the external workflow orchestrator. The goal was to move from isolated ingestion and transformation steps into a managed, repeatable pipeline with scheduling, dependency handling, and failure control.

## Architecture

Airflow
→ Airbyte
→ S3
→ Databricks Bronze
→ Databricks Silver
→ dbt Gold
→ Validation

This flow represents the orchestration layer that coordinates the end-to-end movement of source data through raw storage, lakehouse processing, and final analytical models.

## Responsibilities

### Airflow

- pipeline scheduling
- task dependencies
- retries
- failure handling
- orchestration across Airbyte and Databricks

### Airbyte

- source ingestion
- incremental cursor management
- raw S3 replication

### Databricks

- Bronze ingestion
- Silver processing
- dbt execution
- final validation

### dbt

- analytical transformations
- data quality tests
- Gold/analytical marts

## Scheduling

The demonstration pipeline runs daily.

Automatic historical catchup is intentionally disabled because Airbyte incremental state should not be automatically rewound based on Airflow logical dates.

## Failure Handling

Airflow stops downstream processing when an Airbyte sync fails.

Databricks processing begins only after successful ingestion, and the dbt build includes model execution and data tests.

## Incremental Behavior

The pipeline preserves the existing incremental design:

source update
→ Airbyte cursor
→ new raw version
→ Bronze version
→ Silver latest-record selection
→ dbt rebuild/test

## Idempotency

Silver models deduplicate business keys using the latest source update and the Airbyte extraction timestamp.

## Backfills

Historical reprocessing is a deliberate operational action that uses an Airbyte reset/full refresh followed by Bronze, Silver, and dbt processing.