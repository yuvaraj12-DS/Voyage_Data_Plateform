## Airbyte
- four incremental connections
- S3 destination
- cursor set to `updated_at`

## Databricks
- Bronze layer
- Silver layer
- dbt analytical layer
- validation job

## Airflow
- `voyage_daily_pipeline`
- serialized Airbyte sync sequence
- Databricks job trigger
- retry handling

## dbt
- models
- tests
- documentation