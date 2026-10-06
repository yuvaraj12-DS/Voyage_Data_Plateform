# Databricks notebook source
# DBTITLE 1,Freshness Validation
# MAGIC %md
# MAGIC # Freshness Validation
# MAGIC
# MAGIC Checks data freshness across all bronze source tables using `_airbyte_extracted_at` (epoch milliseconds).
# MAGIC
# MAGIC **SLA Thresholds** (portfolio-level):
# MAGIC - < 2 hours (120 min)  -> `PASS`
# MAGIC - 2-6 hours (120-360 min) -> `WARN`
# MAGIC - > 6 hours (360 min)  -> `ERROR`
# MAGIC
# MAGIC **Behaviour**: Writes one row per dataset to `voyage.monitoring.freshness_results`.
# MAGIC If any dataset returns `ERROR`, the notebook raises an exception to fail the Databricks Job task
# MAGIC and stop downstream processing (dbt_build, validation).

# COMMAND ----------

# Freshness Validation
#
# Checks freshness of active Bronze source tables using
# _airbyte_extracted_at (epoch milliseconds).
#
# Freshness policy:
#   < 2 hours       -> PASS
#   2-6 hours       -> WARN
#   > 6 hours       -> ERROR
#
# Historical/reference/metadata datasets are recorded as N/A.
#
# Results are written idempotently to:
#   voyage.monitoring.freshness_results
#
# Key:
#   pipeline_run_id + dataset
#
# If the Databricks task retries, the existing row is UPDATED
# instead of another duplicate row being INSERTED.
#
# If any actively monitored dataset has ERROR, the notebook
# raises an exception so downstream dbt processing stops.


from datetime import datetime


# ---------------------------------------------------------------------------
# Pipeline run ID
# ---------------------------------------------------------------------------

try:
    pipeline_run_id = dbutils.widgets.get("pipeline_run_id")
except Exception:
    pipeline_run_id = (
        f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

print(f"Pipeline run ID: {pipeline_run_id}")


# ---------------------------------------------------------------------------
# Dataset freshness policy
#
# True  = actively expected to receive new/updated data
# False = historical/reference/metadata
# ---------------------------------------------------------------------------

DATASETS = [
    # Historical / reference / metadata
    ("bookings",                        "voyage.bronze.bookings",                        False),
    ("customers",                       "voyage.bronze.customers",                       False),
    ("properties",                      "voyage.bronze.properties",                      False),
    ("tenants",                         "voyage.bronze.tenants",                         False),

    ("marketing_campaigns",             "voyage.bronze.marketing_campaigns",             False),
    ("marketing_ad_groups",             "voyage.bronze.marketing_ad_groups",             False),
    ("marketing_ads",                   "voyage.bronze.marketing_ads",                   False),

    # Active / strict freshness monitoring
    ("marketing_bookings",              "voyage.bronze.marketing_bookings",              True),
    ("marketing_campaign_performance",  "voyage.bronze.marketing_campaign_performance",  True),

    ("website_events",                  "voyage.bronze.website_events",                  True),
    ("website_sessions",                "voyage.bronze.website_sessions",                True),
    ("website_page_views",              "voyage.bronze.website_page_views",              True),
]


# ---------------------------------------------------------------------------
# SLA thresholds
# ---------------------------------------------------------------------------

PASS_THRESHOLD = 120     # < 2 hours
ERROR_THRESHOLD = 360    # > 6 hours


# ---------------------------------------------------------------------------
# Current timestamp
# ---------------------------------------------------------------------------

checked_at = (
    spark.sql(
        "SELECT current_timestamp() AS ts"
    ).collect()[0]["ts"]
)


# ---------------------------------------------------------------------------
# Collect results
# ---------------------------------------------------------------------------

results = []
has_error = False

print(
    f"\n{'Dataset':<35} "
    f"{'Max Loaded At':<28} "
    f"{'Age (min)':<12} "
    f"{'Policy':<12} "
    f"{'Status'}"
)

print("-" * 110)


# ---------------------------------------------------------------------------
# Check each dataset
# ---------------------------------------------------------------------------

for dataset_name, table_name, freshness_required in DATASETS:

    try:
        max_loaded_at = spark.sql(
            f"""
            SELECT
                MAX(
                    timestamp_millis(_airbyte_extracted_at)
                ) AS max_loaded_at
            FROM {table_name}
            """
        ).collect()[0]["max_loaded_at"]

    except Exception as exc:

        status = "ERROR"
        age_minutes = None
        has_error = True

        results.append(
            (
                pipeline_run_id,
                dataset_name,
                None,
                checked_at,
                age_minutes,
                status,
            )
        )

        print(
            f"{dataset_name:<35} "
            f"{'READ ERROR':<28} "
            f"{'N/A':<12} "
            f"{'STRICT':<12} "
            f"ERROR"
        )

        print(
            f"  Error: {str(exc)[:300]}"
        )

        continue

    # -----------------------------------------------------------------------
    # Historical / reference / metadata
    # -----------------------------------------------------------------------

    if not freshness_required:

        results.append(
            (
                pipeline_run_id,
                dataset_name,
                max_loaded_at,
                checked_at,
                None,
                "N/A",
            )
        )

        print(
            f"{dataset_name:<35} "
            f"{str(max_loaded_at):<28} "
            f"{'N/A':<12} "
            f"{'REFERENCE':<12} "
            f"N/A"
        )

        continue

    # -----------------------------------------------------------------------
    # Active dataset with strict freshness SLA
    # -----------------------------------------------------------------------

    if max_loaded_at is None:

        status = "ERROR"
        age_minutes = None
        has_error = True

        results.append(
            (
                pipeline_run_id,
                dataset_name,
                None,
                checked_at,
                age_minutes,
                status,
            )
        )

        print(
            f"{dataset_name:<35} "
            f"{'NULL':<28} "
            f"{'N/A':<12} "
            f"{'STRICT':<12} "
            f"ERROR"
        )

        continue

    age_minutes = int(
        (
            checked_at - max_loaded_at
        ).total_seconds() / 60
    )

    if age_minutes < PASS_THRESHOLD:
        status = "PASS"

    elif age_minutes < ERROR_THRESHOLD:
        status = "WARN"

    else:
        status = "ERROR"
        has_error = True

    results.append(
        (
            pipeline_run_id,
            dataset_name,
            max_loaded_at,
            checked_at,
            age_minutes,
            status,
        )
    )

    print(
        f"{dataset_name:<35} "
        f"{str(max_loaded_at):<28} "
        f"{age_minutes:<12} "
        f"{'STRICT':<12} "
        f"{status}"
    )


# ---------------------------------------------------------------------------
# Create DataFrame
# ---------------------------------------------------------------------------

freshness_df = spark.createDataFrame(
    results,
    [
        "pipeline_run_id",
        "dataset",
        "max_loaded_at",
        "checked_at",
        "age_minutes",
        "status",
    ],
)


# ---------------------------------------------------------------------------
# Idempotent MERGE
#
# One row per:
#   pipeline_run_id + dataset
#
# Existing row -> UPDATE
# New row      -> INSERT
# ---------------------------------------------------------------------------

freshness_df.createOrReplaceTempView(
    "freshness_results_current"
)

spark.sql(
    """
    MERGE INTO voyage.monitoring.freshness_results AS target

    USING freshness_results_current AS source

    ON target.pipeline_run_id = source.pipeline_run_id
       AND target.dataset = source.dataset

    WHEN MATCHED THEN
        UPDATE SET
            target.max_loaded_at = source.max_loaded_at,
            target.checked_at = source.checked_at,
            target.age_minutes = source.age_minutes,
            target.status = source.status

    WHEN NOT MATCHED THEN
        INSERT (
            pipeline_run_id,
            dataset,
            max_loaded_at,
            checked_at,
            age_minutes,
            status
        )
        VALUES (
            source.pipeline_run_id,
            source.dataset,
            source.max_loaded_at,
            source.checked_at,
            source.age_minutes,
            source.status
        )
    """
)


print(
    f"\nUpserted {len(results)} freshness checks "
    "into voyage.monitoring.freshness_results"
)


# ---------------------------------------------------------------------------
# Fail pipeline if an actively monitored dataset is ERROR
# ---------------------------------------------------------------------------

if has_error:

    error_datasets = [
        row[1]
        for row in results
        if row[5] == "ERROR"
    ]

    raise RuntimeError(
        "Freshness validation FAILED for: "
        f"{', '.join(error_datasets)}. "
        "Pipeline stopped because one or more actively "
        "monitored datasets are stale or unavailable."
    )


print(
    "\nFreshness validation completed successfully. "
    "No active dataset is in ERROR status."
)