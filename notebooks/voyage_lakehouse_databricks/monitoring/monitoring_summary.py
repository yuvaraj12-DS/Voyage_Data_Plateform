# Databricks notebook source
# DBTITLE 1,Monitoring Summary
# MAGIC %md
# MAGIC # Monitoring Summary
# MAGIC
# MAGIC Final task in the pipeline. Reads freshness and DQ results for this run, then updates the `pipeline_run_audit` row with final statuses.
# MAGIC
# MAGIC **Inputs**: `pipeline_run_id` (widget)
# MAGIC
# MAGIC **Logic**:
# MAGIC 1. Read `voyage.monitoring.freshness_results` for this run -> determine `freshness_status`
# MAGIC 2. Read `voyage.monitoring.data_quality_results` for this run -> determine `dq_status`
# MAGIC 3. Set `dbt_status = SUCCESS` (this task runs after dbt_build)
# MAGIC 4. Set `databricks_status = SUCCESS` (bronze + silver tasks succeeded)
# MAGIC 5. Compute overall `status` from all sub-statuses
# MAGIC 6. UPDATE `pipeline_run_audit` with `ended_at`, all statuses, `error_message`
# MAGIC 7. Print a summary report

# COMMAND ----------

# DBTITLE 1,Monitoring summary logic
# Monitoring Summary — finalizes the pipeline_run_audit row
# Reads freshness + DQ results, computes overall status, prints summary

from datetime import datetime

# --- Pipeline run ID ---
try:
    pipeline_run_id = dbutils.widgets.get("pipeline_run_id")
except Exception:
    pipeline_run_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"Pipeline run ID: {pipeline_run_id}")

# --- Read freshness results ---
freshness_rows = spark.sql(f"""
    SELECT dataset, status, age_minutes
    FROM voyage.monitoring.freshness_results
    WHERE pipeline_run_id = '{pipeline_run_id}'
""").collect()

if not freshness_rows:
    freshness_status = "SKIPPED"
elif any(r["status"] == "ERROR" for r in freshness_rows):
    freshness_status = "FAIL"
elif any(r["status"] == "WARN" for r in freshness_rows):
    freshness_status = "WARN"
else:
    freshness_status = "PASS"

# --- Read DQ results ---
dq_rows = spark.sql(f"""
    SELECT check_name, status
    FROM voyage.monitoring.data_quality_results
    WHERE pipeline_run_id = '{pipeline_run_id}'
""").collect()

if not dq_rows:
    dq_status = "SKIPPED"
elif any(r["status"] == "FAIL" for r in dq_rows):
    dq_status = "FAIL"
else:
    dq_status = "PASS"

# --- Sub-statuses (this task runs after dbt_build + validation succeeded) ---
airbyte_status    = "SUCCESS"
databricks_status = "SUCCESS"
dbt_status        = "SUCCESS"

# --- Overall status ---
all_statuses = [airbyte_status, databricks_status, dbt_status, dq_status, freshness_status]
overall_status = "FAILED" if "FAIL" in all_statuses else "SUCCESS"

# --- Error message ---
error_message = "NULL"
if freshness_status == "FAIL":
    failed_ds = [r["dataset"] for r in freshness_rows if r["status"] == "ERROR"]
    error_message = f"'Freshness failed for: {', '.join(failed_ds)}'"
elif dq_status == "FAIL":
    failed_checks = [r["check_name"] for r in dq_rows if r["status"] == "FAIL"]
    error_message = f"'DQ failed for: {', '.join(failed_checks)}'"

# --- Update or insert pipeline_run_audit row ---
existing = spark.sql(f"""
    SELECT run_id FROM voyage.monitoring.pipeline_run_audit
    WHERE run_id = '{pipeline_run_id}'
""").collect()

if existing:
    spark.sql(f"""
        UPDATE voyage.monitoring.pipeline_run_audit
        SET ended_at = current_timestamp(),
            status = '{overall_status}',
            airbyte_status = '{airbyte_status}',
            databricks_status = '{databricks_status}',
            dbt_status = '{dbt_status}',
            dq_status = '{dq_status}',
            freshness_status = '{freshness_status}',
            error_message = {error_message}
        WHERE run_id = '{pipeline_run_id}'
    """)
    print("Updated existing pipeline_run_audit row")
else:
    spark.sql(f"""
        INSERT INTO voyage.monitoring.pipeline_run_audit
        VALUES (
            '{pipeline_run_id}',
            'voyage_daily_pipeline',
            current_timestamp(),
            current_timestamp(),
            '{overall_status}',
            '{airbyte_status}',
            '{databricks_status}',
            '{dbt_status}',
            '{dq_status}',
            '{freshness_status}',
            NULL,
            {error_message}
        )
    """)
    print("Inserted new pipeline_run_audit row (no existing row found)")

# --- Print summary ---
print(f"\n{'='*60}")
print(f"  PIPELINE RUN SUMMARY")
print(f"{'='*60}")
print(f"  Run ID:           {pipeline_run_id}")
print(f"  Pipeline:         voyage_daily_pipeline")
print(f"  Overall Status:   {overall_status}")
print(f"{'='*60}")
print(f"  Airbyte:          {airbyte_status}")
print(f"  Databricks:       {databricks_status}")
print(f"  dbt:              {dbt_status}")
print(f"  Data Quality:     {dq_status}")
print(f"  Freshness:        {freshness_status}")
print(f"{'='*60}")

if freshness_rows:
    print(f"\n  Freshness Details:")
    for r in freshness_rows:
        print(f"    {r['dataset']:<35} {r['status']:6} ({r['age_minutes']} min)")

if dq_rows:
    print(f"\n  DQ Check Results:")
    for r in dq_rows:
        print(f"    {r['check_name']:<40} {r['status']}")

if error_message != "NULL":
    print(f"\n  ERROR: {error_message}")

print(f"\n{'='*60}")
print(f"  Monitoring summary complete.")
print(f"{'='*60}")