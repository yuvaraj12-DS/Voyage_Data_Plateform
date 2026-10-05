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
'''
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
'''

# COMMAND ----------

# Monitoring Summary
#
# Finalizes voyage.monitoring.pipeline_run_audit.
#
# Reads:
#   voyage.monitoring.freshness_results
#   voyage.monitoring.data_quality_results
#   existing pipeline_run_audit stage statuses
#
# The notebook does NOT hard-code Airbyte / Databricks / dbt as SUCCESS.
#
# It supports:
#   PASS
#   WARN
#   FAIL
#   SKIPPED
#   N/A
#   UNKNOWN
#
# Recommended Airflow / Databricks Job behavior:
#   monitoring_summary should run with ALL_DONE so that
#   monitoring is recorded even when an upstream task fails.


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
# Helper: optional widget
# ---------------------------------------------------------------------------

def get_optional_widget(name):
    try:
        value = dbutils.widgets.get(name)

        if value is not None and str(value).strip():
            return str(value).strip()

    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Read existing audit row
# ---------------------------------------------------------------------------

existing_rows = spark.sql(
    f"""
    SELECT
        run_id,
        started_at,
        airbyte_status,
        databricks_status,
        dbt_status
    FROM voyage.monitoring.pipeline_run_audit
    WHERE run_id = '{pipeline_run_id}'
    """
).collect()


existing = existing_rows[0] if existing_rows else None


# ---------------------------------------------------------------------------
# Determine stage statuses
#
# Priority:
# 1. Explicit widget value
# 2. Existing audit row value
# 3. UNKNOWN
# ---------------------------------------------------------------------------

airbyte_status = (
    get_optional_widget("airbyte_status")
    or (
        existing["airbyte_status"]
        if existing is not None
        and existing["airbyte_status"] is not None
        else None
    )
    or "UNKNOWN"
)


databricks_status = (
    get_optional_widget("databricks_status")
    or (
        existing["databricks_status"]
        if existing is not None
        and existing["databricks_status"] is not None
        else None
    )
    or "UNKNOWN"
)


dbt_status = (
    get_optional_widget("dbt_status")
    or (
        existing["dbt_status"]
        if existing is not None
        and existing["dbt_status"] is not None
        else None
    )
    or "UNKNOWN"
)


# ---------------------------------------------------------------------------
# Read freshness results
# ---------------------------------------------------------------------------

freshness_rows = spark.sql(
    f"""
    SELECT
        dataset,
        status,
        age_minutes
    FROM voyage.monitoring.freshness_results
    WHERE pipeline_run_id = '{pipeline_run_id}'
    ORDER BY dataset
    """
).collect()


# ---------------------------------------------------------------------------
# Determine freshness status
# ---------------------------------------------------------------------------

if not freshness_rows:

    freshness_status = "SKIPPED"

elif any(
    row["status"] == "ERROR"
    for row in freshness_rows
):

    freshness_status = "FAIL"

elif any(
    row["status"] == "WARN"
    for row in freshness_rows
):

    freshness_status = "WARN"

elif any(
    row["status"] == "PASS"
    for row in freshness_rows
):

    freshness_status = "PASS"

else:

    freshness_status = "N/A"


# ---------------------------------------------------------------------------
# Read DQ results
# ---------------------------------------------------------------------------

dq_rows = spark.sql(
    f"""
    SELECT
        check_name,
        domain,
        check_type,
        status,
        expected_value,
        actual_value
    FROM voyage.monitoring.data_quality_results
    WHERE pipeline_run_id = '{pipeline_run_id}'
    ORDER BY check_name
    """
).collect()


# ---------------------------------------------------------------------------
# Determine DQ status
# ---------------------------------------------------------------------------

if not dq_rows:

    dq_status = "SKIPPED"

elif any(
    row["status"] == "FAIL"
    for row in dq_rows
):

    dq_status = "FAIL"

elif any(
    row["status"] == "SKIPPED"
    for row in dq_rows
):

    dq_status = "SKIPPED"

else:

    dq_status = "PASS"


# ---------------------------------------------------------------------------
# Normalize stage statuses
# ---------------------------------------------------------------------------

STAGE_FAILURES = {
    "FAIL",
    "FAILED",
    "ERROR",
    "CANCELLED",
    "TIMEOUT",
}

STAGE_UNKNOWN = {
    "UNKNOWN",
    "SKIPPED",
}


# ---------------------------------------------------------------------------
# Determine overall status
# ---------------------------------------------------------------------------

all_stage_statuses = [
    airbyte_status.upper(),
    databricks_status.upper(),
    dbt_status.upper(),
    dq_status.upper(),
    freshness_status.upper(),
]


if any(
    status in STAGE_FAILURES
    for status in all_stage_statuses
):

    overall_status = "FAILED"

elif any(
    status in STAGE_UNKNOWN
    for status in all_stage_statuses
):

    overall_status = "UNKNOWN"

elif freshness_status == "WARN":

    overall_status = "SUCCESS_WITH_WARNINGS"

else:

    overall_status = "SUCCESS"


# ---------------------------------------------------------------------------
# Build error / warning message
# ---------------------------------------------------------------------------

messages = []


# Freshness errors

freshness_failures = [
    row["dataset"]
    for row in freshness_rows
    if row["status"] == "ERROR"
]

if freshness_failures:

    messages.append(
        "Freshness failed for: "
        + ", ".join(freshness_failures)
    )


# DQ failures

dq_failures = [
    row["check_name"]
    for row in dq_rows
    if row["status"] == "FAIL"
]

if dq_failures:

    messages.append(
        "DQ failed for: "
        + ", ".join(dq_failures)
    )


# DQ skipped

dq_skipped = [
    row["check_name"]
    for row in dq_rows
    if row["status"] == "SKIPPED"
]

if dq_skipped:

    messages.append(
        "DQ skipped: "
        + ", ".join(dq_skipped)
    )


# Stage failures

for stage_name, stage_status in [
    ("Airbyte", airbyte_status),
    ("Databricks", databricks_status),
    ("dbt", dbt_status),
]:

    if stage_status.upper() in STAGE_FAILURES:

        messages.append(
            f"{stage_name} status: {stage_status}"
        )


# Stage unknown

for stage_name, stage_status in [
    ("Airbyte", airbyte_status),
    ("Databricks", databricks_status),
    ("dbt", dbt_status),
]:

    if stage_status.upper() in STAGE_UNKNOWN:

        messages.append(
            f"{stage_name} status unknown"
        )


error_message = (
    " | ".join(messages)
    if messages
    else None
)


# ---------------------------------------------------------------------------
# SQL string helper
# ---------------------------------------------------------------------------

def sql_string(value):
    if value is None:
        return "NULL"

    escaped = str(value).replace(
        "'",
        "''",
    )

    return f"'{escaped}'"


# ---------------------------------------------------------------------------
# Update existing audit row OR insert a new one
# ---------------------------------------------------------------------------

if existing:

    spark.sql(
        f"""
        UPDATE voyage.monitoring.pipeline_run_audit

        SET
            ended_at = current_timestamp(),
            status = {sql_string(overall_status)},
            airbyte_status = {sql_string(airbyte_status)},
            databricks_status = {sql_string(databricks_status)},
            dbt_status = {sql_string(dbt_status)},
            dq_status = {sql_string(dq_status)},
            freshness_status = {sql_string(freshness_status)},
            error_message = {sql_string(error_message)}

        WHERE run_id = {sql_string(pipeline_run_id)}
        """
    )

    print(
        "\nUpdated existing pipeline_run_audit row."
    )

else:

    spark.sql(
        f"""
        INSERT INTO voyage.monitoring.pipeline_run_audit
        (
            run_id,
            pipeline_name,
            started_at,
            ended_at,
            status,
            airbyte_status,
            databricks_status,
            dbt_status,
            dq_status,
            freshness_status,
            records_processed,
            error_message
        )

        VALUES
        (
            {sql_string(pipeline_run_id)},
            'voyage_daily_pipeline',
            current_timestamp(),
            current_timestamp(),
            {sql_string(overall_status)},
            {sql_string(airbyte_status)},
            {sql_string(databricks_status)},
            {sql_string(dbt_status)},
            {sql_string(dq_status)},
            {sql_string(freshness_status)},
            NULL,
            {sql_string(error_message)}
        )
        """
    )

    print(
        "\nInserted new pipeline_run_audit row."
    )


# ===========================================================================
# Print summary
# ===========================================================================

print(
    "\n"
    + "=" * 70
)

print(
    "PIPELINE RUN SUMMARY"
)

print(
    "=" * 70
)

print(
    f"Run ID:             {pipeline_run_id}"
)

print(
    "Pipeline:           voyage_daily_pipeline"
)

print(
    f"Overall Status:     {overall_status}"
)

print(
    "=" * 70
)

print(
    f"Airbyte:            {airbyte_status}"
)

print(
    f"Databricks:         {databricks_status}"
)

print(
    f"dbt:                {dbt_status}"
)

print(
    f"Data Quality:       {dq_status}"
)

print(
    f"Freshness:          {freshness_status}"
)

print(
    "=" * 70
)


# ---------------------------------------------------------------------------
# Freshness details
# ---------------------------------------------------------------------------

if freshness_rows:

    print(
        "\nFreshness Details:"
    )

    for row in freshness_rows:

        age_text = (
            str(row["age_minutes"])
            if row["age_minutes"] is not None
            else "N/A"
        )

        print(
            f"  {row['dataset']:<35} "
            f"{row['status']:<7} "
            f"({age_text} min)"
        )


# ---------------------------------------------------------------------------
# DQ details
# ---------------------------------------------------------------------------

if dq_rows:

    print(
        "\nDQ Check Results:"
    )

    for row in dq_rows:

        print(
            f"  {row['check_name']:<40} "
            f"{row['status']}"
        )


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

if error_message:

    print(
        "\nMessages:"
    )

    print(
        f"  {error_message}"
    )


print(
    "\n"
    + "=" * 70
)

print(
    "Monitoring summary complete."
)

print(
    "=" * 70
)