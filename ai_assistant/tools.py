"""Approved business-query tools backed by trusted dbt analytical marts.

All SQL templates are authored here, use positional parameters, and query only
approved `voyage.dbt_dev` marts/dimensions. The LLM never supplies SQL or table names.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .config import (
    MARKETING_DEFAULT_END,
    MARKETING_DEFAULT_START,
    table_name,
)
from .databricks_client import fetch_all, fetch_one


MARKETING_FUNNEL = table_name("fct_marketing_funnel_daily")
CAMPAIGN_DAILY = table_name("fct_campaign_daily")
ATTRIBUTION_DAILY = table_name("fct_marketing_attribution_daily")
BOOKING_DAILY = table_name("fct_booking_daily")
PROPERTY_DAILY = table_name("fct_property_daily")
TENANT_PERFORMANCE = table_name("fct_tenant_performance")
DIM_TENANT = table_name("dim_tenant")


def _validate_date(value: str, label: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD format.") from exc


def _marketing_period(start_date: str | None, end_date: str | None) -> tuple[str, str]:
    if start_date is None and end_date is None:
        return MARKETING_DEFAULT_START, MARKETING_DEFAULT_END
    if start_date is None or end_date is None:
        raise ValueError("Provide both start_date and end_date, or omit both to use the default marketing window.")
    start = _validate_date(start_date, "start_date")
    end = _validate_date(end_date, "end_date")
    if start > end:
        raise ValueError("start_date must be on or before end_date.")
    return start, end


def _date_sql(column: str, start_date: str | None, end_date: str | None) -> tuple[str, list[Any], dict[str, str]]:
    if (start_date is None) != (end_date is None):
        raise ValueError("Provide both start_date and end_date, or omit both.")
    if start_date is None:
        return "", [], {}
    start = _validate_date(start_date, "start_date")
    end = _validate_date(end_date, "end_date")
    if start > end:
        raise ValueError("start_date must be on or before end_date.")
    return f" AND {column} >= CAST(? AS DATE) AND {column} <= CAST(? AS DATE)", [start, end], {"start_date": start, "end_date": end}


def _tenant_sql(tenant_id: str | None, column: str = "tenant_id") -> tuple[str, list[Any]]:
    if tenant_id is None:
        return "", []
    tenant = str(tenant_id).strip()
    if not tenant or len(tenant) > 80:
        raise ValueError("tenant_id must be a non-empty value of at most 80 characters.")
    return f" AND {column} = ?", [tenant]


def _package(tool: str, data: Any, sources: list[str], filters: dict, definitions: dict | None = None) -> dict:
    return {
        "ok": True,
        "tool": tool,
        "data": data,
        "source_tables": sources,
        "filters": filters,
        "metric_definitions": definitions or {},
    }


def get_website_performance(
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Return exactly the website sessions and website conversions used by Power BI."""
    start, end = _marketing_period(start_date, end_date)
    tenant_clause, tenant_params = _tenant_sql(tenant_id)
    query = f"""
        SELECT
            COALESCE(SUM(website_sessions), 0) AS website_sessions,
            COALESCE(SUM(website_conversions), 0) AS website_conversions
        FROM {MARKETING_FUNNEL}
        WHERE date >= CAST(? AS DATE) AND date <= CAST(? AS DATE)
        {tenant_clause}
    """
    row = fetch_one(query, [start, end, *tenant_params])
    return _package(
        "get_website_performance",
        row,
        [MARKETING_FUNNEL],
        {"start_date": start, "end_date": end, **({"tenant_id": tenant_id} if tenant_id else {})},
        {
            "website_sessions": "SUM(fct_marketing_funnel_daily.website_sessions)",
            "website_conversions": "SUM(fct_marketing_funnel_daily.website_conversions)",
        },
    )


def get_marketing_funnel(
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Return Power BI funnel totals and rates computed from aggregate totals."""
    start, end = _marketing_period(start_date, end_date)
    tenant_clause, tenant_params = _tenant_sql(tenant_id)
    query = f"""
        SELECT
            COALESCE(SUM(impressions), 0) AS total_impressions,
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(spend), 0) AS total_spend,
            COALESCE(SUM(website_sessions), 0) AS website_sessions,
            COALESCE(SUM(engaged_sessions), 0) AS engaged_sessions,
            COALESCE(SUM(website_page_views), 0) AS page_views,
            COALESCE(SUM(searches), 0) AS searches,
            COALESCE(SUM(property_views), 0) AS property_views,
            COALESCE(SUM(booking_starts), 0) AS booking_starts,
            COALESCE(SUM(website_conversions), 0) AS website_conversions,
            COALESCE(SUM(bookings), 0) AS bookings,
            COALESCE(SUM(gross_booking_value), 0) AS gross_booking_value,
            COALESCE(SUM(net_revenue), 0) AS net_revenue
        FROM {MARKETING_FUNNEL}
        WHERE date >= CAST(? AS DATE) AND date <= CAST(? AS DATE)
        {tenant_clause}
    """
    row = fetch_one(query, [start, end, *tenant_params])
    # Recompute ratios from totals, matching the DAX definitions; never average daily rates.
    impressions = float(row.get("total_impressions") or 0)
    clicks = float(row.get("total_clicks") or 0)
    sessions = float(row.get("website_sessions") or 0)
    searches = float(row.get("searches") or 0)
    property_views = float(row.get("property_views") or 0)
    booking_starts = float(row.get("booking_starts") or 0)
    conversions = float(row.get("website_conversions") or 0)
    spend = float(row.get("total_spend") or 0)
    bookings = float(row.get("bookings") or 0)
    row.update({
        "ctr": clicks / impressions if impressions else None,
        "cpc": spend / clicks if clicks else None,
        "click_to_session_rate": sessions / clicks if clicks else None,
        "website_conversion_rate": conversions / sessions if sessions else None,
        "cost_per_booking": spend / bookings if bookings else None,
        "roas": float(row.get("net_revenue") or 0) / spend if spend else None,
        "click_to_search_rate": searches / sessions if sessions else None,
        "search_to_property_view_rate": property_views / searches if searches else None,
        "property_view_to_booking_start_rate": booking_starts / property_views if property_views else None,
        "booking_start_to_conversion_rate": conversions / booking_starts if booking_starts else None,
    })
    return _package(
        "get_marketing_funnel",
        row,
        [MARKETING_FUNNEL],
        {"start_date": start, "end_date": end, **({"tenant_id": tenant_id} if tenant_id else {})},
        {
            "CTR": "Total Clicks / Total Impressions",
            "CPC": "Total Spend / Total Clicks",
            "Website Conversion Rate": "Website Conversions / Website Sessions",
            "Cost per Booking": "Total Spend / Bookings",
            "ROAS": "Net Revenue / Total Spend",
            "rates": "Ratios are stored as decimals; display as percentages by multiplying by 100.",
        },
    )


def get_campaign_performance(
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str | None = None,
    limit: int = 10,
) -> dict:
    """Return per-campaign totals and overall totals using the Power BI funnel mart."""
    start, end = _marketing_period(start_date, end_date)
    limit = max(1, min(int(limit), 50))
    tenant_clause, tenant_params = _tenant_sql(tenant_id)
    where = f"date >= CAST(? AS DATE) AND date <= CAST(? AS DATE) {tenant_clause}"
    base_params = [start, end, *tenant_params]

    total_query = f"""
        SELECT
            COALESCE(SUM(spend), 0) AS total_spend,
            COALESCE(SUM(impressions), 0) AS total_impressions,
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(website_sessions), 0) AS website_sessions,
            COALESCE(SUM(website_conversions), 0) AS website_conversions,
            COALESCE(SUM(bookings), 0) AS bookings,
            COALESCE(SUM(gross_booking_value), 0) AS gross_booking_value,
            COALESCE(SUM(net_revenue), 0) AS net_revenue
        FROM {MARKETING_FUNNEL}
        WHERE {where}
    """
    overall = fetch_one(total_query, base_params)
    spend = float(overall.get("total_spend") or 0)
    clicks = float(overall.get("total_clicks") or 0)
    impressions = float(overall.get("total_impressions") or 0)
    sessions = float(overall.get("website_sessions") or 0)
    bookings = float(overall.get("bookings") or 0)
    overall.update({
        "ctr": clicks / impressions if impressions else None,
        "cpc": spend / clicks if clicks else None,
        "website_conversion_rate": float(overall.get("website_conversions") or 0) / sessions if sessions else None,
        "cost_per_booking": spend / bookings if bookings else None,
        "roas": float(overall.get("net_revenue") or 0) / spend if spend else None,
    })

    campaign_query = f"""
        SELECT
            campaign_id,
            campaign_name,
            COALESCE(SUM(spend), 0) AS total_spend,
            COALESCE(SUM(impressions), 0) AS total_impressions,
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(website_sessions), 0) AS website_sessions,
            COALESCE(SUM(website_conversions), 0) AS website_conversions,
            COALESCE(SUM(bookings), 0) AS bookings,
            COALESCE(SUM(gross_booking_value), 0) AS gross_booking_value,
            COALESCE(SUM(net_revenue), 0) AS net_revenue
        FROM {MARKETING_FUNNEL}
        WHERE {where}
        GROUP BY campaign_id, campaign_name
        ORDER BY SUM(net_revenue) DESC
        LIMIT ?
    """
    campaigns = fetch_all(campaign_query, [*base_params, limit])
    for row in campaigns:
        row_spend = float(row.get("total_spend") or 0)
        row_clicks = float(row.get("total_clicks") or 0)
        row_impressions = float(row.get("total_impressions") or 0)
        row_sessions = float(row.get("website_sessions") or 0)
        row_bookings = float(row.get("bookings") or 0)
        row.update({
            "ctr": row_clicks / row_impressions if row_impressions else None,
            "cpc": row_spend / row_clicks if row_clicks else None,
            "website_conversion_rate": float(row.get("website_conversions") or 0) / row_sessions if row_sessions else None,
            "cost_per_booking": row_spend / row_bookings if row_bookings else None,
            "roas": float(row.get("net_revenue") or 0) / row_spend if row_spend else None,
        })
    return _package(
        "get_campaign_performance",
        {"overall": overall, "campaigns": campaigns},
        [MARKETING_FUNNEL],
        {"start_date": start, "end_date": end, "limit": limit, **({"tenant_id": tenant_id} if tenant_id else {})},
        {
            "ROAS": "SUM(net_revenue) / SUM(spend), not the average of daily ROAS values",
            "CTR": "SUM(clicks) / SUM(impressions)",
            "website_conversion_rate": "SUM(website_conversions) / SUM(website_sessions)",
        },
    )


def get_attribution_performance(
    model_type: str = "all",
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str | None = None,
    limit: int = 25,
) -> dict:
    """Compare first-click, last-click and linear attribution from the attribution mart."""
    start, end = _marketing_period(start_date, end_date)
    model_type = str(model_type or "all").lower().strip()
    allowed = {"first_click", "last_click", "linear", "all"}
    if model_type not in allowed:
        raise ValueError("model_type must be first_click, last_click, linear, or all.")
    limit = max(1, min(int(limit), 100))
    tenant_clause, tenant_params = _tenant_sql(tenant_id)
    attr_model_clause = ""
    model_params: list[Any] = []
    if model_type != "all":
        attr_model_clause = " AND attribution_model = ?"
        model_params.append(model_type)

    attr_where = f"date >= CAST(? AS DATE) AND date <= CAST(? AS DATE) {tenant_clause}{attr_model_clause}"
    attr_params = [start, end, *tenant_params, *model_params]
    model_totals = fetch_all(
        f"""
        SELECT
            attribution_model,
            COALESCE(SUM(attributed_bookings), 0) AS attributed_bookings,
            COALESCE(SUM(attributed_gross_booking_value), 0) AS attributed_gross_booking_value,
            COALESCE(SUM(attributed_net_revenue), 0) AS attributed_net_revenue
        FROM {ATTRIBUTION_DAILY}
        WHERE {attr_where}
        GROUP BY attribution_model
        ORDER BY attribution_model
        """,
        attr_params,
    )

    campaign_rows = fetch_all(
        f"""
        SELECT
            attribution_model,
            tenant_id,
            campaign_id,
            campaign_name,
            COALESCE(SUM(attributed_bookings), 0) AS attributed_bookings,
            COALESCE(SUM(attributed_gross_booking_value), 0) AS attributed_gross_booking_value,
            COALESCE(SUM(attributed_net_revenue), 0) AS attributed_net_revenue
        FROM {ATTRIBUTION_DAILY}
        WHERE {attr_where}
        GROUP BY attribution_model, tenant_id, campaign_id, campaign_name
        ORDER BY attribution_model, attributed_net_revenue DESC
        LIMIT ?
        """,
        [*attr_params, limit],
    )

    spend_where = f"date >= CAST(? AS DATE) AND date <= CAST(? AS DATE) {tenant_clause}"
    spend_params = [start, end, *tenant_params]
    spend_row = fetch_one(
        f"SELECT COALESCE(SUM(spend), 0) AS total_spend FROM {MARKETING_FUNNEL} WHERE {spend_where}",
        spend_params,
    )
    total_spend = float(spend_row.get("total_spend") or 0)
    for row in model_totals:
        revenue = float(row.get("attributed_net_revenue") or 0)
        row["total_spend"] = total_spend
        row["attributed_roas"] = revenue / total_spend if total_spend else None
    campaign_spend_rows = fetch_all(
        f"""
        SELECT tenant_id, campaign_id, COALESCE(SUM(spend), 0) AS total_spend
        FROM {MARKETING_FUNNEL}
        WHERE {spend_where}
        GROUP BY tenant_id, campaign_id
        """,
        spend_params,
    )
    spend_by_campaign = {
        (row.get("tenant_id"), row.get("campaign_id")): float(row.get("total_spend") or 0)
        for row in campaign_spend_rows
    }
    for row in campaign_rows:
        row_spend = spend_by_campaign.get((row.get("tenant_id"), row.get("campaign_id")), 0.0)
        row["total_spend"] = row_spend
        row["attributed_roas"] = (
            float(row.get("attributed_net_revenue") or 0) / row_spend if row_spend else None
        )

    return _package(
        "get_attribution_performance",
        {"model_totals": model_totals, "campaigns": campaign_rows, "total_spend": total_spend},
        [ATTRIBUTION_DAILY, MARKETING_FUNNEL],
        {
            "start_date": start,
            "end_date": end,
            "model_type": model_type,
            "limit": limit,
            **({"tenant_id": tenant_id} if tenant_id else {}),
        },
        {
            "attributed_net_revenue": "SUM(attributed_net_revenue) from fct_marketing_attribution_daily for the selected model and period",
            "attributed_roas": "Selected-model attributed net revenue / total spend for the same period and tenant filter, matching Power BI's measure definition",
            "models": "first_click, last_click and linear are separate models; do not relabel one model as another",
        },
    )


def get_historical_booking_performance(
    year: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Historical 2014-2017 booking KPIs using the same definitions as Power BI."""
    if year is not None:
        year = int(year)
        if year < 2014 or year > 2017:
            raise ValueError("The historical hotel-booking source covers 2014 through 2017.")
        if start_date or end_date:
            raise ValueError("Use year or start_date/end_date, not both.")
        start_date, end_date = f"{year}-01-01", f"{year}-12-31"
    date_clause, date_params, date_filters = _date_sql("booking_date", start_date, end_date)
    tenant_clause, tenant_params = _tenant_sql(tenant_id)
    query = f"""
        SELECT
            COALESCE(SUM(booking_count), 0) AS total_bookings,
            COALESCE(SUM(completed_booking_count), 0) AS completed_bookings,
            COALESCE(SUM(confirmed_booking_count), 0) AS confirmed_bookings,
            COALESCE(SUM(cancelled_booking_count), 0) AS cancelled_bookings,
            COALESCE(SUM(room_nights), 0) AS total_room_nights,
            COALESCE(SUM(estimated_completed_booking_value), 0) AS total_booking_value,
            CASE WHEN SUM(booking_count) > 0
                THEN SUM(cancelled_booking_count) * 1.0 / SUM(booking_count) END AS cancellation_rate,
            CASE WHEN SUM(booking_count) > 0
                THEN SUM(cancelled_booking_count) * 100.0 / SUM(booking_count) END AS cancellation_rate_percent,
            CASE WHEN SUM(completed_booking_count) > 0
                THEN SUM(estimated_completed_booking_value) / SUM(completed_booking_count) END AS average_adr
        FROM {BOOKING_DAILY}
        WHERE 1 = 1 {date_clause} {tenant_clause}
    """
    row = fetch_one(query, [*date_params, *tenant_params])
    filters = {**date_filters}
    if year is not None:
        filters["year"] = year
    if tenant_id:
        filters["tenant_id"] = tenant_id
    return _package(
        "get_historical_booking_performance",
        row,
        [BOOKING_DAILY],
        filters or {"period": "all available historical booking dates"},
        {
            "total_bookings": "SUM(booking_count)",
            "cancellation_rate": "SUM(cancelled_booking_count) / SUM(booking_count); percentage display equals cancellation_rate * 100",
            "average_adr": "SUM(estimated_completed_booking_value) / SUM(completed_booking_count), matching the Power BI measure",
            "historical_domain": "Real historical hotel-booking dataset, 2014-2017; do not combine with the synthetic 2026 marketing booking bridge",
        },
    )


def get_property_performance(
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str | None = None,
    limit: int = 10,
) -> dict:
    """Rank properties using historical booking facts."""
    limit = max(1, min(int(limit), 50))
    date_clause, date_params, date_filters = _date_sql("booking_date", start_date, end_date)
    tenant_clause, tenant_params = _tenant_sql(tenant_id)
    query = f"""
        SELECT
            property_id,
            property_name,
            tenant_id,
            COALESCE(SUM(booking_count), 0) AS total_bookings,
            COALESCE(SUM(completed_booking_count), 0) AS completed_bookings,
            COALESCE(SUM(cancelled_booking_count), 0) AS cancelled_bookings,
            COALESCE(SUM(estimated_completed_booking_value), 0) AS total_booking_value,
            CASE WHEN SUM(booking_count) > 0 THEN SUM(cancelled_booking_count) * 100.0 / SUM(booking_count) END AS cancellation_rate_percent
        FROM {PROPERTY_DAILY}
        WHERE 1 = 1 {date_clause} {tenant_clause}
        GROUP BY property_id, property_name, tenant_id
        ORDER BY SUM(estimated_completed_booking_value) DESC
        LIMIT ?
    """
    rows = fetch_all(query, [*date_params, *tenant_params, limit])
    filters = {**date_filters, "limit": limit}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    return _package(
        "get_property_performance",
        {"properties": rows},
        [PROPERTY_DAILY],
        filters or {"period": "all available historical booking dates", "limit": limit},
        {"total_booking_value": "SUM(estimated_completed_booking_value)", "cancellation_rate_percent": "100 * SUM(cancelled_booking_count) / SUM(booking_count)"},
    )


def get_tenant_performance(
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str | None = None,
    limit: int = 10,
) -> dict:
    """Rank tenants by historical bookings/value; supports an optional time window."""
    limit = max(1, min(int(limit), 50))
    if start_date is None and end_date is None:
        tenant_clause, tenant_params = _tenant_sql(tenant_id, "tenant_id")
        query = f"""
            SELECT
                tenant_id,
                tenant_name,
                COALESCE(booking_count, 0) AS total_bookings,
                COALESCE(total_room_nights, 0) AS total_room_nights,
                COALESCE(completed_booking_count, 0) AS completed_bookings,
                COALESCE(cancelled_booking_count, 0) AS cancelled_bookings,
                COALESCE(estimated_completed_booking_value, 0) AS total_booking_value,
                CASE WHEN completed_booking_count > 0
                    THEN estimated_completed_booking_value / completed_booking_count END AS average_adr,
                cancellation_rate * 100.0 AS cancellation_rate_percent
            FROM {TENANT_PERFORMANCE}
            WHERE 1 = 1 {tenant_clause}
            ORDER BY estimated_completed_booking_value DESC
            LIMIT ?
        """
        rows = fetch_all(query, [*tenant_params, limit])
        sources = [TENANT_PERFORMANCE]
        filters = {"limit": limit, "period": "all available historical booking dates"}
    else:
        date_clause, date_params, date_filters = _date_sql("b.booking_date", start_date, end_date)
        tenant_clause, tenant_params = _tenant_sql(tenant_id, "b.tenant_id")
        query = f"""
            SELECT
                b.tenant_id,
                t.tenant_name,
                COALESCE(SUM(b.booking_count), 0) AS total_bookings,
                COALESCE(SUM(b.room_nights), 0) AS total_room_nights,
                COALESCE(SUM(b.completed_booking_count), 0) AS completed_bookings,
                COALESCE(SUM(b.cancelled_booking_count), 0) AS cancelled_bookings,
                COALESCE(SUM(b.estimated_completed_booking_value), 0) AS total_booking_value,
                CASE WHEN SUM(b.completed_booking_count) > 0
                    THEN SUM(b.estimated_completed_booking_value) / SUM(b.completed_booking_count) END AS average_adr,
                CASE WHEN SUM(b.booking_count) > 0
                    THEN SUM(b.cancelled_booking_count) * 100.0 / SUM(b.booking_count) END AS cancellation_rate_percent
            FROM {BOOKING_DAILY} b
            LEFT JOIN {DIM_TENANT} t ON b.tenant_id = t.tenant_id
            WHERE 1 = 1 {date_clause} {tenant_clause}
            GROUP BY b.tenant_id, t.tenant_name
            ORDER BY SUM(b.estimated_completed_booking_value) DESC
            LIMIT ?
        """
        rows = fetch_all(query, [*date_params, *tenant_params, limit])
        sources = [BOOKING_DAILY, DIM_TENANT]
        filters = {**date_filters, "limit": limit}
        if tenant_id:
            filters["tenant_id"] = tenant_id
    return _package(
        "get_tenant_performance",
        {"tenants": rows},
        sources,
        filters,
        {
            "tenant bookings": "SUM(booking_count)",
            "tenant revenue": "SUM(estimated_completed_booking_value), matching the Power BI historical tenant measure",
            "domain": "Historical hotel bookings; synthetic marketing revenue is a separate 2026 domain",
        },
    )


AVAILABLE_TOOLS = {
    "get_website_performance": get_website_performance,
    "get_marketing_funnel": get_marketing_funnel,
    "get_campaign_performance": get_campaign_performance,
    "get_attribution_performance": get_attribution_performance,
    "get_historical_booking_performance": get_historical_booking_performance,
    "get_property_performance": get_property_performance,
    "get_tenant_performance": get_tenant_performance,
}
