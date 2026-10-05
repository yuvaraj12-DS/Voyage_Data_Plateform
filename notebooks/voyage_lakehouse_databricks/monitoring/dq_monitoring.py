# Databricks notebook source
# DBTITLE 1,DQ Monitoring
# MAGIC %md
# MAGIC # Data Quality Monitoring
# MAGIC
# MAGIC Runs structured DQ checks across all dbt_dev fact tables, dimension tables, and silver sources.
# MAGIC Writes results to `voyage.monitoring.data_quality_results`.
# MAGIC
# MAGIC **20 checks** across 5 domains:
# MAGIC
# MAGIC | # | Check | Domain | Type |
# MAGIC |---|---|---|---|
# MAGIC | 1-7 | Fact table completeness (rows > 0) | bookings, marketing, website, attribution | completeness |
# MAGIC | 8-12 | Dimension table completeness (rows > 0) | dimensions | completeness |
# MAGIC | 13 | Campaign duplicate grain | marketing | uniqueness |
# MAGIC | 14 | Booking duplicate IDs | bookings | uniqueness |
# MAGIC | 15 | Marketing metric validity (negative values, ranges) | marketing | validity |
# MAGIC | 16 | Website event name validity (4 valid values) | website | validity |
# MAGIC | 17 | Orphan campaign check | website | referential |
# MAGIC | 18 | Orphan property check | bookings | referential |
# MAGIC | 19 | Website silver vs dbt mart reconciliation | website | reconciliation |
# MAGIC | 20 | Marketing silver vs dbt mart reconciliation | marketing | reconciliation |
# MAGIC
# MAGIC **Behaviour**: Writes one row per check to `data_quality_results`. Raises `RuntimeError` if any check returns `FAIL`.

# COMMAND ----------

# DQ Monitoring
#
# Runs structured data-quality checks and writes results to:
#   voyage.monitoring.data_quality_results
#
# If freshness has already failed for this pipeline run,
# DQ is recorded as SKIPPED because dbt/analytical data should
# not be treated as a valid current-run result.
#
# Raises RuntimeError if any executed DQ check returns FAIL.


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
# Current timestamp
# ---------------------------------------------------------------------------

checked_at = (
    spark.sql(
        "SELECT current_timestamp() AS ts"
    ).collect()[0]["ts"]
)


# ---------------------------------------------------------------------------
# Check whether freshness already failed
# ---------------------------------------------------------------------------

freshness_error_rows = spark.sql(
    f"""
    SELECT dataset, status
    FROM voyage.monitoring.freshness_results
    WHERE pipeline_run_id = '{pipeline_run_id}'
      AND status = 'ERROR'
    """
).collect()


# ---------------------------------------------------------------------------
# If freshness failed, record DQ as SKIPPED
# ---------------------------------------------------------------------------

if freshness_error_rows:

    failed_datasets = [
        row["dataset"]
        for row in freshness_error_rows
    ]

    skipped_result = [
        (
            pipeline_run_id,
            "dq_monitoring_execution",
            "monitoring",
            "execution",
            "SKIPPED",
            "Freshness must not be ERROR",
            f"Freshness failed for: {', '.join(failed_datasets)}",
            checked_at,
        )
    ]

    skipped_df = spark.createDataFrame(
        skipped_result,
        [
            "pipeline_run_id",
            "check_name",
            "domain",
            "check_type",
            "status",
            "expected_value",
            "actual_value",
            "checked_at",
        ],
    )

    skipped_df.write.mode(
        "append"
    ).saveAsTable(
        "voyage.monitoring.data_quality_results"
    )

    print(
        "\nDQ monitoring SKIPPED."
    )

    print(
        "Freshness failed for: "
        + ", ".join(failed_datasets)
    )

    print(
        "DQ was not executed against potentially stale "
        "analytical data."
    )

    dbutils.notebook.exit(
        "DQ monitoring skipped because freshness failed."
    )


# ---------------------------------------------------------------------------
# Normal DQ execution
# ---------------------------------------------------------------------------

results = []
has_failure = False


def add_result(
    check_name,
    domain,
    check_type,
    status,
    expected,
    actual,
):
    global has_failure

    results.append(
        (
            pipeline_run_id,
            check_name,
            domain,
            check_type,
            status,
            str(expected),
            str(actual),
            checked_at,
        )
    )

    if status == "FAIL":
        has_failure = True

    print(
        f"  {status:7} | "
        f"{domain:15} | "
        f"{check_type:15} | "
        f"{check_name}"
    )


print(
    f"\n{'STATUS':7} | "
    f"{'DOMAIN':15} | "
    f"{'CHECK TYPE':15} | "
    f"{'CHECK NAME'}"
)

print("-" * 90)


# ===========================================================================
# 1. Completeness checks
# ===========================================================================

COMPLETENESS_TABLES = [
    (
        "booking_fact_completeness",
        "bookings",
        "voyage.dbt_dev.fct_booking_daily",
    ),
    (
        "campaign_daily_completeness",
        "marketing",
        "voyage.dbt_dev.fct_campaign_daily",
    ),
    (
        "website_daily_completeness",
        "website",
        "voyage.dbt_dev.fct_website_daily",
    ),
    (
        "marketing_funnel_completeness",
        "marketing",
        "voyage.dbt_dev.fct_marketing_funnel_daily",
    ),
    (
        "marketing_attribution_completeness",
        "attribution",
        "voyage.dbt_dev.fct_marketing_attribution_daily",
    ),
    (
        "property_daily_completeness",
        "bookings",
        "voyage.dbt_dev.fct_property_daily",
    ),
    (
        "tenant_performance_completeness",
        "bookings",
        "voyage.dbt_dev.fct_tenant_performance",
    ),
]


for check_name, domain, table in COMPLETENESS_TABLES:

    row_count = spark.sql(
        f"""
        SELECT COUNT(*) AS cnt
        FROM {table}
        """
    ).collect()[0]["cnt"]

    status = (
        "PASS"
        if row_count > 0
        else "FAIL"
    )

    add_result(
        check_name,
        domain,
        "completeness",
        status,
        "> 0",
        row_count,
    )


# ===========================================================================
# 2. Campaign duplicate grain
# ===========================================================================

duplicate_groups = spark.sql(
    """
    SELECT COUNT(*) AS cnt
    FROM (
        SELECT
            tenant_id,
            campaign_id,
            date
        FROM voyage.dbt_dev.fct_campaign_daily
        GROUP BY
            tenant_id,
            campaign_id,
            date
        HAVING COUNT(*) > 1
    )
    """
).collect()[0]["cnt"]


add_result(
    "campaign_duplicate_grain",
    "marketing",
    "uniqueness",
    "PASS" if duplicate_groups == 0 else "FAIL",
    "0",
    duplicate_groups,
)


# ===========================================================================
# 3. Marketing metric validity
# ===========================================================================

invalid_rows = spark.sql(
    """
    SELECT COUNT(*) AS cnt
    FROM voyage.dbt_dev.fct_campaign_daily
    WHERE impressions < 0
       OR clicks < 0
       OR conversions < 0
       OR spend < 0
       OR revenue < 0
       OR clicks > impressions
       OR conversions > clicks
       OR ctr < 0
       OR ctr > 1
       OR cpc < 0
       OR conversion_rate < 0
       OR conversion_rate > 1
       OR roas < 0
    """
).collect()[0]["cnt"]


add_result(
    "marketing_metric_validity",
    "marketing",
    "validity",
    "PASS" if invalid_rows == 0 else "FAIL",
    "0",
    invalid_rows,
)


# ===========================================================================
# 4. Referential integrity: orphan campaigns
# ===========================================================================

orphan_campaigns = spark.sql(
    """
    SELECT COUNT(*) AS cnt
    FROM voyage.dbt_dev.fct_web_session s
    LEFT JOIN voyage.dbt_dev.stg_campaigns c
        ON s.campaign_id = c.campaign_id
    WHERE s.campaign_id IS NOT NULL
      AND c.campaign_id IS NULL
    """
).collect()[0]["cnt"]


add_result(
    "orphan_campaign_check",
    "website",
    "referential",
    "PASS" if orphan_campaigns == 0 else "FAIL",
    "0",
    orphan_campaigns,
)


# ===========================================================================
# 5. Website Silver → dbt reconciliation
# ===========================================================================

website_recon = spark.sql(
    """
    WITH silver_sessions AS (
        SELECT COUNT(*) AS sessions
        FROM voyage.silver.fact_web_session
    ),

    silver_page_views AS (
        SELECT COUNT(*) AS page_views
        FROM voyage.silver.fact_web_page_view
    ),

    silver_events AS (
        SELECT COUNT(*) AS events
        FROM voyage.silver.fact_web_event
    ),

    silver_conversions AS (
        SELECT
            COUNT(*) AS conversions,
            ROUND(
                COALESCE(
                    SUM(event_value),
                    0
                ),
                2
            ) AS conversion_value
        FROM voyage.silver.fact_web_event
        WHERE event_name = 'purchase'
    ),

    session_mart AS (
        SELECT
            COUNT(*) AS sessions,
            COALESCE(SUM(page_view_count), 0) AS page_views,
            COALESCE(SUM(event_count), 0) AS events,
            COALESCE(SUM(conversion_count), 0) AS conversions,
            ROUND(
                COALESCE(
                    SUM(conversion_value),
                    0
                ),
                2
            ) AS conversion_value
        FROM voyage.dbt_dev.fct_web_session
    )

    SELECT
        CASE
            WHEN ss.sessions = sm.sessions
             AND sp.page_views = sm.page_views
             AND se.events = sm.events
             AND sc.conversions = sm.conversions
             AND sc.conversion_value = sm.conversion_value
            THEN 'PASS'
            ELSE 'FAIL'
        END AS recon_status

    FROM silver_sessions ss
    CROSS JOIN silver_page_views sp
    CROSS JOIN silver_events se
    CROSS JOIN silver_conversions sc
    CROSS JOIN session_mart sm
    """
).collect()[0]["recon_status"]


add_result(
    "website_reconciliation",
    "website",
    "reconciliation",
    website_recon,
    "MATCH",
    website_recon,
)


# ===========================================================================
# 6. Marketing Silver → dbt reconciliation
# ===========================================================================

marketing_recon = spark.sql(
    """
    WITH silver AS (
        SELECT
            COUNT(*) AS row_count,
            COALESCE(SUM(impressions), 0) AS impressions,
            COALESCE(SUM(clicks), 0) AS clicks,
            ROUND(
                COALESCE(SUM(spend), 0),
                2
            ) AS spend,
            COALESCE(SUM(conversions), 0) AS conversions,
            ROUND(
                COALESCE(SUM(revenue), 0),
                2
            ) AS revenue
        FROM voyage.silver.fact_campaign_daily
    ),

    mart AS (
        SELECT
            COUNT(*) AS row_count,
            COALESCE(SUM(impressions), 0) AS impressions,
            COALESCE(SUM(clicks), 0) AS clicks,
            ROUND(
                COALESCE(SUM(spend), 0),
                2
            ) AS spend,
            COALESCE(SUM(conversions), 0) AS conversions,
            ROUND(
                COALESCE(SUM(revenue), 0),
                2
            ) AS revenue
        FROM voyage.dbt_dev.fct_campaign_daily
    )

    SELECT
        CASE
            WHEN s.row_count = m.row_count
             AND s.impressions = m.impressions
             AND s.clicks = m.clicks
             AND s.spend = m.spend
             AND s.conversions = m.conversions
             AND s.revenue = m.revenue
            THEN 'PASS'
            ELSE 'FAIL'
        END AS recon_status

    FROM silver s
    CROSS JOIN mart m
    """
).collect()[0]["recon_status"]


add_result(
    "marketing_reconciliation",
    "marketing",
    "reconciliation",
    marketing_recon,
    "MATCH",
    marketing_recon,
)


# ===========================================================================
# 7. Duplicate booking IDs
# ===========================================================================

booking_dupes = spark.sql(
    """
    SELECT COUNT(*) AS cnt
    FROM (
        SELECT booking_id
        FROM voyage.silver.fact_booking
        GROUP BY booking_id
        HAVING COUNT(*) > 1
    )
    """
).collect()[0]["cnt"]


add_result(
    "booking_duplicate_check",
    "bookings",
    "uniqueness",
    "PASS" if booking_dupes == 0 else "FAIL",
    "0",
    booking_dupes,
)


# ===========================================================================
# 8. Orphan property IDs
# ===========================================================================

orphan_properties = spark.sql(
    """
    SELECT COUNT(*) AS cnt
    FROM voyage.silver.fact_booking b
    LEFT JOIN voyage.silver.dim_property p
        ON b.property_id = p.property_id
    WHERE b.property_id IS NOT NULL
      AND p.property_id IS NULL
    """
).collect()[0]["cnt"]


add_result(
    "booking_orphan_property_check",
    "bookings",
    "referential",
    "PASS" if orphan_properties == 0 else "FAIL",
    "0",
    orphan_properties,
)


# ===========================================================================
# 9. Website event validity
# ===========================================================================

invalid_events = spark.sql(
    """
    SELECT COUNT(*) AS cnt
    FROM voyage.silver.fact_web_event
    WHERE event_name NOT IN (
        'search_availability',
        'view_property',
        'begin_booking',
        'purchase'
    )
    """
).collect()[0]["cnt"]


add_result(
    "website_event_validity",
    "website",
    "validity",
    "PASS" if invalid_events == 0 else "FAIL",
    "0",
    invalid_events,
)


# ===========================================================================
# 10. Dimension completeness
# ===========================================================================

DIM_TABLES = [
    (
        "dim_date_completeness",
        "voyage.dbt_dev.dim_date",
    ),
    (
        "dim_tenant_completeness",
        "voyage.dbt_dev.dim_tenant",
    ),
    (
        "dim_campaign_completeness",
        "voyage.dbt_dev.dim_campaign",
    ),
    (
        "dim_property_completeness",
        "voyage.dbt_dev.dim_property",
    ),
    (
        "dim_customer_completeness",
        "voyage.dbt_dev.dim_customer",
    ),
]


for check_name, table in DIM_TABLES:

    row_count = spark.sql(
        f"""
        SELECT COUNT(*) AS cnt
        FROM {table}
        """
    ).collect()[0]["cnt"]

    status = (
        "PASS"
        if row_count > 0
        else "FAIL"
    )

    add_result(
        check_name,
        "dimensions",
        "completeness",
        status,
        "> 0",
        row_count,
    )


# ===========================================================================
# Write DQ results
# ===========================================================================

dq_df = spark.createDataFrame(
    results,
    [
        "pipeline_run_id",
        "check_name",
        "domain",
        "check_type",
        "status",
        "expected_value",
        "actual_value",
        "checked_at",
    ],
)


dq_df.write.mode(
    "append"
).saveAsTable(
    "voyage.monitoring.data_quality_results"
)


print(
    f"\nWrote {len(results)} DQ checks "
    "to voyage.monitoring.data_quality_results"
)


# ===========================================================================
# Fail pipeline if any executed DQ check failed
# ===========================================================================

if has_failure:

    failed_checks = [
        row[1]
        for row in results
        if row[4] == "FAIL"
    ]

    raise RuntimeError(
        "Data quality validation FAILED for: "
        f"{', '.join(failed_checks)}. "
        "Pipeline stopped. See "
        "voyage.monitoring.data_quality_results."
    )


print(
    "\nAll executed DQ checks passed. "
    "Pipeline may continue."
)