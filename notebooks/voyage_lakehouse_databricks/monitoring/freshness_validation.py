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

# DBTITLE 1,Freshness check logic
# Freshness Validation — checks _airbyte_extracted_at per bronze table
# Writes results to voyage.monitoring.freshness_results
# Fails (raises exception) if any dataset has ERROR status

from datetime import datetime

# --- Pipeline run ID (from widget or auto-generated) ---
try:
    pipeline_run_id = dbutils.widgets.get("pipeline_run_id")
except Exception:
    pipeline_run_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"Pipeline run ID: {pipeline_run_id}")

# --- Datasets to check ---
DATASETS = [
    ("bookings",                      "voyage.bronze.bookings"),
    ("customers",                      "voyage.bronze.customers"),
    ("marketing_bookings",            "voyage.bronze.marketing_bookings"),
    ("marketing_campaigns",          "voyage.bronze.marketing_campaigns"),
    ("marketing_campaign_performance","voyage.bronze.marketing_campaign_performance"),
    ("marketing_ad_groups",           "voyage.bronze.marketing_ad_groups"),
    ("marketing_ads",                  "voyage.bronze.marketing_ads"),
    ("website_events",                "voyage.bronze.website_events"),
    ("website_sessions",              "voyage.bronze.website_sessions"),
    ("website_page_views",           "voyage.bronze.website_page_views"),
    ("properties",                     "voyage.bronze.properties"),
    ("tenants",                        "voyage.bronze.tenants"),
]

# --- SLA thresholds (minutes) ---
PASS_THRESHOLD  = 120   # < 2 hours
ERROR_THRESHOLD = 360   # > 6 hours

# --- Get current timestamp from Spark (UTC) ---
checked_at = spark.sql("SELECT current_timestamp() AS ts").collect()[0]["ts"]

results = []
has_error = False

print(f"\n{'Dataset':<35} {'Max Loaded At':<28} {'Age (min)':<12} {'Status'}")
print("-" * 90)

for dataset_name, table_name in DATASETS:
    max_loaded_at = spark.sql(
        f"SELECT max(timestamp_millis(_airbyte_extracted_at)) AS max_loaded_at FROM {table_name}"
    ).collect()[0]["max_loaded_at"]

    if max_loaded_at is None:
        # Table is empty — treat as ERROR
        results.append((pipeline_run_id, dataset_name, checked_at, checked_at, 999999, "ERROR"))
        has_error = True
        print(f"{dataset_name:<35} {'NULL':<28} {'N/A':<12} ERROR")
        continue

    age_minutes = int((checked_at - max_loaded_at).total_seconds() / 60)

    if age_minutes < PASS_THRESHOLD:
        status = "PASS"
    elif age_minutes < ERROR_THRESHOLD:
        status = "WARN"
    else:
        status = "ERROR"
        has_error = True

    results.append((pipeline_run_id, dataset_name, max_loaded_at, checked_at, age_minutes, status))
    print(f"{dataset_name:<35} {str(max_loaded_at):<28} {age_minutes:<12} {status}")

# --- Write results to monitoring table ---
freshness_df = spark.createDataFrame(
    results,
    ["pipeline_run_id", "dataset", "max_loaded_at", "checked_at", "age_minutes", "status"]
)

freshness_df.write.mode("append").saveAsTable("voyage.monitoring.freshness_results")

print(f"\nWrote {len(results)} freshness checks to voyage.monitoring.freshness_results")

# --- Fail if any ERROR ---
if has_error:
    error_datasets = [r[1] for r in results if r[5] == "ERROR"]
    raise RuntimeError(
        f"Freshness validation FAILED for: {', '.join(error_datasets)}. "
        f"Pipeline stopped to prevent downstream processing on stale data."
    )

print("\nAll freshness checks passed (PASS or WARN). Pipeline may continue.")