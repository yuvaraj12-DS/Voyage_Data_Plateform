"""Live checks that AI business tools follow the dashboard's metric definitions.

Requires a valid Databricks connection. It reports actual retrieved values but has
no hard-coded expected totals, since the upstream datasets continue to change.
"""
from __future__ import annotations

import math

from .tools import (
    get_attribution_performance,
    get_historical_booking_performance,
    get_marketing_funnel,
    get_website_performance,
)


def _close(left, right, tolerance: float = 1e-8) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)


def main() -> None:
    period = {"start_date": "2026-09-01", "end_date": "2026-09-30"}
    website = get_website_performance(**period)
    funnel = get_marketing_funnel(**period)
    if not website["ok"] or not funnel["ok"]:
        raise SystemExit("FAIL: marketing tool did not return a valid result")

    w = website["data"]
    f = funnel["data"]
    for website_key, funnel_key in (
        ("website_sessions", "website_sessions"),
        ("website_conversions", "website_conversions"),
    ):
        if int(w.get(website_key) or 0) != int(f.get(funnel_key) or 0):
            raise SystemExit(f"FAIL: {website_key} does not reconcile between website and funnel tools")

    clicks = float(f.get("total_clicks") or 0)
    impressions = float(f.get("total_impressions") or 0)
    if not _close(f.get("ctr"), clicks / impressions if impressions else None):
        raise SystemExit("FAIL: CTR does not match SUM(clicks) / SUM(impressions)")

    historical = get_historical_booking_performance(year=2016)
    h = historical["data"]
    bookings = float(h.get("total_bookings") or 0)
    cancelled = float(h.get("cancelled_bookings") or 0)
    expected_rate = cancelled / bookings if bookings else None
    if not _close(h.get("cancellation_rate"), expected_rate):
        raise SystemExit("FAIL: historical cancellation rate does not reconcile")

    attribution = get_attribution_performance(model_type="all", **period)
    observed_models = {row["attribution_model"] for row in attribution["data"]["model_totals"]}
    if not observed_models.issubset({"first_click", "last_click", "linear"}):
        raise SystemExit(f"FAIL: unsupported attribution model returned: {observed_models}")

    print("VoyageData AI grounding checks PASSED")
    print(f"Website sessions, Sep 2026: {w.get('website_sessions')}")
    print(f"Website conversions, Sep 2026: {w.get('website_conversions')}")
    print(f"Historical 2016 bookings: {h.get('total_bookings')}")
    print(f"Historical 2016 cancellation rate: {h.get('cancellation_rate_percent')}%")
    print(f"Attribution models present: {', '.join(sorted(observed_models))}")


if __name__ == "__main__":
    main()
