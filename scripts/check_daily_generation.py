"""Read-only validation for one day's website, booking, and campaign data."""

import argparse
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from api.app.database import SessionLocal
from api.app.models.campaign import Campaign
from api.app.models.campaign_daily_metric import CampaignDailyMetric
from api.app.models.marketing_booking import MarketingBooking
from api.app.models.property import Property
from api.app.models.web_event import WebEvent
from api.app.models.web_page_view import WebPageView
from api.app.models.web_session import WebSession


SESSION_COUNT = 200
MIN_PURCHASES = 5
MAX_PURCHASES = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate daily website analytics, marketing bookings, "
            "and campaign metrics."
        )
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now(timezone.utc).date(),
        help="UTC activity date in YYYY-MM-DD format (default: today in UTC).",
    )
    return parser.parse_args()


def is_in_day(timestamp: datetime, day_start: datetime, next_day: datetime) -> bool:
    return day_start <= timestamp < next_day


def main() -> int:
    target_date = parse_args().date
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    next_day = day_start + timedelta(days=1)
    db = SessionLocal()
    checks: list[tuple[str, bool, str]] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append((name, passed, detail))

    try:
        sessions = (
            db.query(WebSession)
            .filter(
                WebSession.session_start >= day_start,
                WebSession.session_start < next_day,
            )
            .all()
        )
        page_views = (
            db.query(WebPageView)
            .filter(
                WebPageView.page_viewed_at >= day_start,
                WebPageView.page_viewed_at < next_day,
            )
            .all()
        )
        events = (
            db.query(WebEvent)
            .filter(
                WebEvent.event_timestamp >= day_start,
                WebEvent.event_timestamp < next_day,
            )
            .all()
        )
        purchases = [event for event in events if event.event_name == "purchase"]
        sessions_by_id = {session.session_id: session for session in sessions}

        record(
            "Website sessions",
            len(sessions) == SESSION_COUNT,
            f"found {len(sessions)}; expected {SESSION_COUNT}",
        )
        record(
            "Website page views exist",
            bool(page_views),
            f"found {len(page_views)}",
        )
        record(
            "Website events exist",
            bool(events),
            f"found {len(events)}",
        )
        record(
            "Purchase count",
            MIN_PURCHASES <= len(purchases) <= MAX_PURCHASES,
            f"found {len(purchases)}; expected {MIN_PURCHASES}-{MAX_PURCHASES}",
        )
        record(
            "Purchase values",
            all(event.event_value is not None for event in purchases),
            f"{sum(event.event_value is None for event in purchases)} purchase(s) lack event_value",
        )
        record(
            "Sessions end within target UTC date",
            all(is_in_day(session.session_end, day_start, next_day) for session in sessions),
            f"{sum(not is_in_day(session.session_end, day_start, next_day) for session in sessions)} outside target date",
        )

        page_views_by_session = Counter(view.session_id for view in page_views)
        record(
            "Every session has at least two page views",
            bool(sessions)
            and all(page_views_by_session[session.session_id] >= 2 for session in sessions),
            f"{sum(page_views_by_session[session.session_id] < 2 for session in sessions)} session(s) have fewer than two",
        )

        invalid_page_view_links = [
            view
            for view in page_views
            if view.session_id not in sessions_by_id
            or sessions_by_id[view.session_id].tenant_id != view.tenant_id
        ]
        invalid_event_links = [
            event
            for event in events
            if event.session_id not in sessions_by_id
            or sessions_by_id[event.session_id].tenant_id != event.tenant_id
        ]
        record(
            "Page-view session and tenant links",
            not invalid_page_view_links,
            f"{len(invalid_page_view_links)} invalid link(s)",
        )
        record(
            "Event session and tenant links",
            not invalid_event_links,
            f"{len(invalid_event_links)} invalid link(s)",
        )

        website_rows = sessions + page_views + events
        rows_without_fresh_microseconds = [
            row
            for row in website_rows
            if row.updated_at is None or row.updated_at.microsecond == 0
        ]
        record(
            "Website updated_at timestamps have microseconds",
            not rows_without_fresh_microseconds,
            f"{len(rows_without_fresh_microseconds)} row(s) have zero/missing microseconds",
        )

        purchase_ids = [event.event_id for event in purchases]
        bookings = (
            db.query(MarketingBooking)
            .filter(MarketingBooking.conversion_id.in_(purchase_ids))
            .all()
            if purchase_ids
            else []
        )
        bookings_by_conversion = Counter(
            booking.conversion_id for booking in bookings
        )
        missing_bookings = [
            event.event_id
            for event in purchases
            if bookings_by_conversion[event.event_id] != 1
        ]
        extra_or_duplicate_bookings = [
            conversion_id
            for conversion_id, count in bookings_by_conversion.items()
            if conversion_id not in set(purchase_ids) or count != 1
        ]
        record(
            "One booking per purchase",
            not missing_bookings and not extra_or_duplicate_bookings,
            f"{len(bookings)} booking(s) for {len(purchases)} purchase(s); "
            f"{len(missing_bookings)} missing/multiple purchase mapping(s)",
        )

        purchase_by_id = {event.event_id: event for event in purchases}
        properties_by_id = {
            prop.property_id: prop
            for prop in db.query(Property).all()
        }
        invalid_booking_links = [
            booking
            for booking in bookings
            if booking.conversion_id not in purchase_by_id
            or (
                booking.conversion_id in purchase_by_id
                and (
                    booking.tenant_id
                    != purchase_by_id[booking.conversion_id].tenant_id
                    or booking.session_id
                    != purchase_by_id[booking.conversion_id].session_id
                    or booking.booking_date
                    != purchase_by_id[booking.conversion_id].event_timestamp.date()
                    or booking.user_id
                    != sessions_by_id.get(booking.session_id, booking).user_id
                )
            )
            or booking.property_id not in properties_by_id
            or (
                booking.property_id in properties_by_id
                and properties_by_id[booking.property_id].tenant_id != booking.tenant_id
            )
        ]
        record(
            "Booking source and tenant links",
            not invalid_booking_links,
            f"{len(invalid_booking_links)} invalid booking link(s)",
        )

        invalid_bookings = [
            booking
            for booking in bookings
            if booking.gross_booking_value < 0
            or booking.net_revenue < 0
            or booking.net_revenue > booking.gross_booking_value
            or booking.booking_status not in {"CONFIRMED", "CANCELLED"}
            or (
                booking.booking_status == "CANCELLED"
                and booking.net_revenue != 0
            )
            or booking.updated_at.microsecond == 0
        ]
        record(
            "Booking amounts, status, and updated_at",
            not invalid_bookings,
            f"{len(invalid_bookings)} invalid booking row(s)",
        )

        campaigns = db.query(Campaign).all()
        campaign_metrics = (
            db.query(CampaignDailyMetric)
            .filter(CampaignDailyMetric.date == target_date)
            .all()
        )
        expected_campaigns = {campaign.campaign_id for campaign in campaigns}
        metric_counts = Counter(metric.campaign_id for metric in campaign_metrics)
        actual_campaigns = set(metric_counts)
        campaign_rows_valid = (
            bool(campaigns)
            and len(campaign_metrics) == len(campaigns)
            and actual_campaigns == expected_campaigns
            and all(metric_counts[campaign_id] == 1 for campaign_id in expected_campaigns)
        )
        record(
            "One campaign metric per campaign",
            campaign_rows_valid,
            f"{len(campaign_metrics)} metric row(s) for {len(campaigns)} campaign(s)",
        )

        campaigns_by_id = {campaign.campaign_id: campaign for campaign in campaigns}
        invalid_metrics = [
            metric
            for metric in campaign_metrics
            if metric.clicks < 0
            or metric.clicks > metric.impressions
            or metric.conversions < 0
            or metric.conversions > metric.clicks
            or metric.spend < 0
            or metric.revenue < 0
            or metric.updated_at.microsecond == 0
            or metric.campaign_id not in campaigns_by_id
            or (
                metric.campaign_id in campaigns_by_id
                and metric.tenant_id
                != campaigns_by_id[metric.campaign_id].tenant_id
            )
        ]
        record(
            "Campaign metric constraints, tenant, and updated_at",
            not invalid_metrics,
            f"{len(invalid_metrics)} invalid metric row(s)",
        )

        print(f"Daily generation validation for UTC date {target_date}:")
        for name, passed, detail in checks:
            print(f"  {'PASS' if passed else 'FAIL'} - {name}: {detail}")
        failures = sum(not passed for _, passed, _ in checks)
        print(f"Result: {'PASSED' if failures == 0 else f'FAILED ({failures} check(s))'}")
        return 0 if failures == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
