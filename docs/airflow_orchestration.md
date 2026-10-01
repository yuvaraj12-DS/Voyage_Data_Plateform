# Phase 10 — Airflow Orchestration

## Objective

Operationalize the VoyageData platform by introducing Apache Airflow as
the external workflow orchestrator.

## Architecture

Airflow
→ Airbyte
→ S3
→ Databricks Bronze
→ Databricks Silver
→ dbt Gold
→ Validation

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

Automatic historical catchup is disabled because Airbyte incremental state
should not be automatically rewound according to Airflow logical dates.

## Failure Handling

Airflow stops downstream processing when the Airbyte sync fails.

Databricks processing only begins after successful ingestion.

dbt build includes model execution and data tests.

## Incremental Behavior

The pipeline preserves the existing incremental design:

source update
→ Airbyte cursor
→ new raw version
→ Bronze version
→ Silver latest-record selection
→ dbt rebuild/test

## Idempotency

Silver models deduplicate business keys using the latest source update and
Airbyte extraction timestamp.

## Backfills

Historical reprocessing is a deliberate operational action using an Airbyte
reset/full refresh followed by Bronze, Silver and dbt processing.