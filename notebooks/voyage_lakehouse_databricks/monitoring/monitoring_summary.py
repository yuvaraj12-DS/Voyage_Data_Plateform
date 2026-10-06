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

# Monitoring Summary
#
# Finalizes voyage.monitoring.pipeline_run_audit.
#
# Status sources:
#
# Airbyte:
#   Passed from Airflow as a Databricks job parameter.
#
# Freshness / dbt / validation / DQ:
#   Passed as Databricks task result states.
#
# The monitoring_summary task should use:
#
#   Run if = ALL_DONE
#
# so that it runs even when an upstream task fails.


from datetime import datetime


# ---------------------------------------------------------------------------
# Helper: get widget safely
# ---------------------------------------------------------------------------

def get_widget(name, default="UNKNOWN"):

    try:
        value = dbutils.widgets.get(name)

        if value is not None and str(value).strip():

            return str(value).strip()

    except Exception:

        pass

    return default


# ---------------------------------------------------------------------------
# Pipeline run ID
# ---------------------------------------------------------------------------

pipeline_run_id = get_widget(
    "pipeline_run_id",
    f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
)


# ---------------------------------------------------------------------------
# External / upstream statuses
# ---------------------------------------------------------------------------

airbyte_status = get_widget(
    "airbyte_status",
    "UNKNOWN",
)


freshness_task_state = get_widget(
    "freshness_task_state",
    "UNKNOWN",
).lower()


dbt_task_state = get_widget(
    "dbt_task_state",
    "UNKNOWN",
).lower()


validation_task_state = get_widget(
    "validation_task_state",
    "UNKNOWN",
).lower()


dq_task_state = get_widget(
    "dq_task_state",
    "UNKNOWN",
).lower()


print(
    f"Pipeline run ID: {pipeline_run_id}"
)

print(
    f"Airbyte status: {airbyte_status}"
)

print(
    f"Freshness task state: {freshness_task_state}"
)

print(
    f"dbt task state: {dbt_task_state}"
)

print(
    f"Validation task state: {validation_task_state}"
)

print(
    f"DQ task state: {dq_task_state}"
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
# Normalize DQ status
# ---------------------------------------------------------------------------

if dq_task_state in {
    "upstream_failed",
    "upstream_canceled",
    "excluded",
    "canceled",
}:

    dq_status = "SKIPPED"

elif dq_task_state in {
    "failed",
    "timedout",
    "evicted",
}:

    dq_status = "FAIL"

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

elif dq_rows:

    dq_status = "PASS"

else:

    dq_status = "SKIPPED"


# ---------------------------------------------------------------------------
# Normalize dbt status
# ---------------------------------------------------------------------------

if dbt_task_state == "success":

    dbt_status = "SUCCESS"

elif dbt_task_state in {
    "failed",
    "canceled",
    "timedout",
    "evicted",
}:

    dbt_status = "FAILED"

elif dbt_task_state in {
    "upstream_failed",
    "upstream_canceled",
    "excluded",
}:

    dbt_status = "NOT_RUN"

else:

    dbt_status = "UNKNOWN"


# ---------------------------------------------------------------------------
# Normalize Databricks processing status
#
# This represents the Databricks transformation portion of
# this pipeline run, not the health of the Databricks platform itself.
# ---------------------------------------------------------------------------

databricks_task_states = [
    freshness_task_state,
    dbt_task_state,
    validation_task_state,
    dq_task_state,
]


if any(
    state in {
        "failed",
        "canceled",
        "timedout",
        "evicted",
        "upstream_failed",
        "upstream_canceled",
    }
    for state in databricks_task_states
):

    databricks_status = "FAILED"

elif all(
    state == "success"
    for state in databricks_task_states
):

    databricks_status = "SUCCESS"

elif any(
    state in {
        "excluded",
        "upstream_failed",
        "upstream_canceled",
    }
    for state in databricks_task_states
):

    databricks_status = "PARTIAL"

else:

    databricks_status = "UNKNOWN"


# ---------------------------------------------------------------------------
# Overall status
# ---------------------------------------------------------------------------

failure_statuses = {
    "FAILED",
    "FAIL",
    "ERROR",
}

not_run_statuses = {
    "NOT_RUN",
    "SKIPPED",
    "UNKNOWN",
}


if (
    str(airbyte_status).upper() in failure_statuses
    or databricks_status == "FAILED"
    or dbt_status == "FAILED"
    or freshness_status == "FAIL"
    or dq_status == "FAIL"
):

    overall_status = "FAILED"


elif (
    freshness_status == "WARN"
):

    overall_status = "SUCCESS_WITH_WARNINGS"


elif (
    databricks_status == "PARTIAL"
    or dbt_status in not_run_statuses
    or dq_status == "SKIPPED"
):

    overall_status = "PARTIAL"


elif (
    str(airbyte_status).upper() == "UNKNOWN"
    or databricks_status == "UNKNOWN"
):

    overall_status = "UNKNOWN"


else:

    overall_status = "SUCCESS"


# ---------------------------------------------------------------------------
# Build message list
# ---------------------------------------------------------------------------

messages = []


# Airbyte

if str(airbyte_status).upper() in failure_statuses:

    messages.append(
        f"Airbyte status: {airbyte_status}"
    )

elif str(airbyte_status).upper() == "UNKNOWN":

    messages.append(
        "Airbyte status unknown"
    )


# Freshness

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


# dbt

if dbt_status == "FAILED":

    messages.append(
        "dbt build failed"
    )

elif dbt_status == "NOT_RUN":

    messages.append(
        "dbt build not run because an upstream task failed"
    )


# Validation

if validation_task_state in {
    "failed",
    "timedout",
    "canceled",
    "evicted",
}:

    messages.append(
        "Pipeline validation failed"
    )

elif validation_task_state in {
    "upstream_failed",
    "upstream_canceled",
    "excluded",
}:

    messages.append(
        "Pipeline validation not run"
    )


# DQ

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

elif dq_status == "SKIPPED":

    messages.append(
        "DQ monitoring skipped"
    )


# ---------------------------------------------------------------------------
# Final error message
# ---------------------------------------------------------------------------

error_message = (
    " | ".join(messages)
    if messages
    else None
)


# ---------------------------------------------------------------------------
# SQL helper
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
# Merge monitoring audit row
#
# This also makes monitoring_summary idempotent.
# ---------------------------------------------------------------------------

summary_df = spark.createDataFrame(
    [
        (
            pipeline_run_id,
            "voyage_daily_pipeline",
            overall_status,
            str(airbyte_status),
            databricks_status,
            dbt_status,
            dq_status,
            freshness_status,
            error_message,
        )
    ],
    [
        "run_id",
        "pipeline_name",
        "status",
        "airbyte_status",
        "databricks_status",
        "dbt_status",
        "dq_status",
        "freshness_status",
        "error_message",
    ],
)

summary_df.createOrReplaceTempView(
    "monitoring_summary_current"
)


spark.sql(
    """
    MERGE INTO voyage.monitoring.pipeline_run_audit AS target

    USING monitoring_summary_current AS source

    ON target.run_id = source.run_id

    WHEN MATCHED THEN

        UPDATE SET
            target.ended_at = current_timestamp(),
            target.status = source.status,
            target.airbyte_status = source.airbyte_status,
            target.databricks_status = source.databricks_status,
            target.dbt_status = source.dbt_status,
            target.dq_status = source.dq_status,
            target.freshness_status = source.freshness_status,
            target.error_message = source.error_message

    WHEN NOT MATCHED THEN

        INSERT (
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

        VALUES (
            source.run_id,
            source.pipeline_name,
            current_timestamp(),
            current_timestamp(),
            source.status,
            source.airbyte_status,
            source.databricks_status,
            source.dbt_status,
            source.dq_status,
            source.freshness_status,
            NULL,
            source.error_message
        )
    """
)


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