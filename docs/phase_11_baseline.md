## Airbyte
- 4 incremental connections
- S3 destination
- cursor = updated_at

## Databricks
- Bronze
- Silver
- dbt analytical layer
- validation job

## Airflow
- voyage_daily_pipeline
- serialized Airbyte syncs
- Databricks Job trigger
- retries

## dbt
- models
- tests
- documentation