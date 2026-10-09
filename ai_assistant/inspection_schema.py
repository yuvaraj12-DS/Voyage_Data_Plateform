"""Inspect the current approved analytical schema in Databricks."""
from __future__ import annotations

from .config import DATABRICKS_CATALOG, DATABRICKS_SCHEMA, validate_sql_identifier
from .databricks_client import fetch_all

TABLES = [
    "dim_campaign", "dim_customer", "dim_date", "dim_property", "dim_tenant",
    "fct_booking_daily", "fct_campaign_daily", "fct_marketing_attribution",
    "fct_marketing_attribution_daily", "fct_marketing_funnel_daily",
    "fct_property_daily", "fct_tenant_performance", "fct_web_session", "fct_website_daily",
]


def main() -> None:
    print("=" * 54)
    print("VOYAGE DATA PLATFORM SCHEMA INSPECTOR")
    print(f"Connecting to: {DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}")
    print("=" * 54)
    safe_catalog = validate_sql_identifier(DATABRICKS_CATALOG, "catalog")
    safe_schema = validate_sql_identifier(DATABRICKS_SCHEMA, "schema")
    rows = fetch_all(
        f"""SELECT table_name, ordinal_position, column_name, data_type
           FROM {safe_catalog}.information_schema.columns
           WHERE table_schema = ?
           ORDER BY table_name, ordinal_position""",
        [safe_schema],
    )
    by_table: dict[str, list[dict]] = {}
    for row in rows:
        by_table.setdefault(row["table_name"], []).append(row)
    for table in TABLES:
        if table not in by_table:
            print(f"\nTABLE: {table} — NOT FOUND")
            continue
        print(f"\nTABLE: {table}\n" + "-" * 40)
        for column in by_table[table]:
            print(f"  • {column['column_name']:<36} ({column['data_type']})")
    print("\nSchema inspection complete.")


if __name__ == "__main__":
    main()
