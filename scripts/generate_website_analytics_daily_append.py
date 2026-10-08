"""
Append one day's synthetic website analytics without changing existing rows.

The target date is configured below. The script refuses to run if any
website analytics already exist for that date.
"""

from datetime import date, datetime, time, timedelta, timezone
import random

from api.app.database import SessionLocal
from api.app.models.campaign import Campaign
from api.app.models.tenant import Tenant
from api.app.models.web_event import WebEvent
from api.app.models.web_page_view import WebPageView
from api.app.models.web_session import WebSession


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_DATE = datetime.now(timezone.utc).date()
SESSION_COUNT = 200
MIN_PURCHASES = 5
MAX_PURCHASES = 15
RANDOM_SEED = 42

COUNTRIES = [
    "IN",
    "GB",
    "US",
    "DE",
    "FR",
    "AE",
    "AU",
    "CA",
    "SG",
]

DEVICES = [
    "desktop",
    "mobile",
    "tablet",
]

LANDING_PAGES = [
    "/",
    "/destinations",
    "/hotels",
    "/search",
]

PAGE_TITLES = {
    "/": "VoyageData Travel",
    "/destinations": "Destinations",
    "/hotels": "Hotels",
    "/search": "Search Availability",
    "/hotel": "Hotel Details",
    "/booking": "Booking",
    "/confirmation": "Booking Confirmation",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp with microseconds."""

    timestamp = datetime.now(timezone.utc)
    if timestamp.microsecond == 0:
        timestamp += timedelta(microseconds=1)
    return timestamp


def random_datetime_for_target_date() -> datetime:
    """Choose a session start that leaves room for a full session that day."""

    day_start = datetime.combine(TARGET_DATE, time.min, tzinfo=timezone.utc)
    latest_start_second = 24 * 60 * 60 - 45 * 60 - 1

    return day_start + timedelta(
        seconds=random.randint(0, latest_start_second)
    )


def weighted_choice() -> tuple[str, str]:
    """Choose a traffic source and medium using the existing generator mix."""

    value = random.random()

    if value < 0.30:
        return "google", "cpc"
    if value < 0.50:
        return "facebook", "paid_social"
    if value < 0.70:
        return "google", "organic"
    if value < 0.85:
        return "direct", "none"
    return "partner", "referral"


def choose_campaign(
    tenant_id: str,
    source: str,
    medium: str,
    campaigns_by_tenant_channel: dict[tuple[str, str], list[str]],
) -> str | None:
    """Select a campaign only for paid traffic."""

    if source == "google" and medium == "cpc":
        channel = "google"
    elif source == "facebook" and medium == "paid_social":
        channel = "meta"
    else:
        return None

    campaigns = campaigns_by_tenant_channel.get((tenant_id, channel), [])
    return random.choice(campaigns) if campaigns else None


def choose_page_sequence(
    searched: bool,
    property_viewed: bool,
    booking_started: bool,
    purchased: bool,
) -> list[str]:
    """Create a realistic page-view sequence of between roughly 2 and 6 pages."""

    pages = [random.choice(LANDING_PAGES)]

    if searched:
        pages.append("/search")
    if property_viewed:
        pages.append("/hotel")
    if booking_started:
        pages.append("/booking")
    if purchased:
        pages.append("/confirmation")

    possible_pages = ["/destinations", "/hotels", "/hotel", "/search"]

    while len(pages) < 2:
        pages.append(random.choice(possible_pages))
    while len(pages) < random.randint(2, 6):
        pages.append(random.choice(possible_pages))

    return pages[:6]


def target_date_exists(db, day_start: datetime, next_day: datetime) -> bool:
    """Return whether any of the three tables already contain target-day activity."""

    return any(
        db.query(model)
        .filter(timestamp_column >= day_start, timestamp_column < next_day)
        .first()
        is not None
        for model, timestamp_column in (
            (WebSession, WebSession.session_start),
            (WebPageView, WebPageView.page_viewed_at),
            (WebEvent, WebEvent.event_timestamp),
        )
    )


def any_id_exists(db, model, id_column, ids: list[str]) -> bool:
    """Check generated IDs in bounded batches before attempting the insert."""

    batch_size = 500
    return any(
        db.query(model)
        .filter(id_column.in_(ids[index:index + batch_size]))
        .first()
        is not None
        for index in range(0, len(ids), batch_size)
    )


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def main() -> None:
    random.seed(RANDOM_SEED)

    db = SessionLocal()

    try:
        day_start = datetime.combine(TARGET_DATE, time.min, tzinfo=timezone.utc)
        next_day = day_start + timedelta(days=1)

        if target_date_exists(db, day_start, next_day):
            raise RuntimeError(
                f"Website analytics already exist for {TARGET_DATE}. "
                "No rows were changed."
            )

        tenants = db.query(Tenant).all()
        campaigns = db.query(Campaign).all()

        if not tenants:
            raise RuntimeError(
                "No tenants found. Populate the booking source first."
            )
        if not campaigns:
            raise RuntimeError(
                "No marketing campaigns found. Run the marketing generator first."
            )

        tenant_ids = [tenant.tenant_id for tenant in tenants]
        campaigns_by_tenant_channel: dict[tuple[str, str], list[str]] = {}

        for campaign in campaigns:
            key = (campaign.tenant_id, campaign.channel.lower())
            campaigns_by_tenant_channel.setdefault(key, []).append(
                campaign.campaign_id
            )

        purchase_count = random.randint(MIN_PURCHASES, MAX_PURCHASES)
        purchase_sessions = set(
            random.sample(
                range(1, SESSION_COUNT + 1),
                purchase_count,
            )
        )

        sessions = []
        page_views = []
        events = []
        page_view_counter = 1
        event_counter = 1
        user_ids = [f"WEBUSER{i:06d}" for i in range(1, 12_001)]

        for session_number in range(1, SESSION_COUNT + 1):
            session_id = (
                f"WEBSESS{TARGET_DATE:%Y%m%d}{session_number:06d}"
            )
            tenant_id = random.choice(tenant_ids)
            user_id = random.choice(user_ids) if random.random() < 0.70 else None
            session_start = random_datetime_for_target_date()
            session_duration = random.randint(60, 45 * 60)
            session_end = session_start + timedelta(seconds=session_duration)

            source, medium = weighted_choice()
            campaign_id = choose_campaign(
                tenant_id=tenant_id,
                source=source,
                medium=medium,
                campaigns_by_tenant_channel=campaigns_by_tenant_channel,
            )

            sessions.append(
                WebSession(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_start=session_start,
                    session_end=session_end,
                    source=source,
                    medium=medium,
                    campaign_id=campaign_id,
                    device=random.choice(DEVICES),
                    country=random.choice(COUNTRIES),
                    landing_page=random.choice(LANDING_PAGES),
                    updated_at=utc_now(),
                )
            )

            purchased = session_number in purchase_sessions
            if purchased:
                searched = True
                property_viewed = True
                booking_started = True
            else:
                searched = random.random() < 0.40
                property_viewed = searched and random.random() < 0.625
                booking_started = property_viewed and random.random() < 0.48

            page_sequence = choose_page_sequence(
                searched=searched,
                property_viewed=property_viewed,
                booking_started=booking_started,
                purchased=purchased,
            )
            available_seconds = session_duration - 1
            page_offsets = sorted(
                random.sample(
                    range(1, available_seconds + 1),
                    len(page_sequence),
                )
            )

            for page_number, page_path in enumerate(page_sequence):
                viewed_at = session_start + timedelta(
                    seconds=page_offsets[page_number]
                )
                page_views.append(
                    WebPageView(
                        page_view_id=(
                            f"WEBPV{TARGET_DATE:%Y%m%d}{page_view_counter:07d}"
                        ),
                        tenant_id=tenant_id,
                        session_id=session_id,
                        page_viewed_at=viewed_at,
                        page_path=page_path,
                        page_title=PAGE_TITLES.get(page_path, "VoyageData"),
                        referrer=(
                            f"{source}/{medium}"
                            if source != "direct"
                            else None
                        ),
                        duration_seconds=random.randint(5, 120),
                        updated_at=utc_now(),
                    )
                )
                page_view_counter += 1

            event_specs = []
            if searched:
                event_specs.append("search_availability")
            if property_viewed:
                event_specs.append("view_property")
            if booking_started:
                event_specs.append("begin_booking")
            if purchased:
                event_specs.append("purchase")

            event_offsets = sorted(
                random.sample(
                    range(1, available_seconds + 1),
                    len(event_specs),
                )
            )

            for event_name, event_offset in zip(event_specs, event_offsets):
                event_timestamp = session_start + timedelta(seconds=event_offset)
                event_value = (
                    round(random.uniform(400, 2500), 2)
                    if event_name == "purchase"
                    else None
                )
                page_path = {
                    "purchase": "/confirmation",
                    "begin_booking": "/booking",
                    "view_property": "/hotel",
                    "search_availability": "/search",
                }[event_name]

                events.append(
                    WebEvent(
                        event_id=(
                            f"WEBEVT{TARGET_DATE:%Y%m%d}{event_counter:07d}"
                        ),
                        tenant_id=tenant_id,
                        session_id=session_id,
                        event_timestamp=event_timestamp,
                        event_name=event_name,
                        page_path=page_path,
                        event_value=event_value,
                        updated_at=utc_now(),
                    )
                )
                event_counter += 1

        generated_dates_match = all(
            day_start <= timestamp < next_day
            for timestamp in (
                [session.session_start for session in sessions]
                + [page_view.page_viewed_at for page_view in page_views]
                + [event.event_timestamp for event in events]
            )
        )
        if not generated_dates_match:
            raise RuntimeError(
                f"Generated activity fell outside target date {TARGET_DATE}."
            )

        purchase_events = [
            event for event in events if event.event_name == "purchase"
        ]
        if not MIN_PURCHASES <= len(purchase_events) <= MAX_PURCHASES:
            raise RuntimeError(
                f"Expected {MIN_PURCHASES}-{MAX_PURCHASES} purchases; "
                f"generated {len(purchase_events)}."
            )

        session_ids = [session.session_id for session in sessions]
        page_view_ids = [page_view.page_view_id for page_view in page_views]
        event_ids = [event.event_id for event in events]
        if (
            any_id_exists(db, WebSession, WebSession.session_id, session_ids)
            or any_id_exists(
                db, WebPageView, WebPageView.page_view_id, page_view_ids
            )
            or any_id_exists(db, WebEvent, WebEvent.event_id, event_ids)
        ):
            raise RuntimeError(
                "A generated ID already exists. No rows were inserted."
            )

        db.bulk_save_objects(sessions)
        db.bulk_save_objects(page_views)
        db.bulk_save_objects(events)
        db.commit()

        print(f"Appended website analytics for {TARGET_DATE}:")
        print(f"  - web_sessions: {len(sessions)}")
        print(f"  - web_page_views: {len(page_views)}")
        print(f"  - web_events: {len(events)}")
        print(f"  - purchase events: {len(purchase_events)}")
        print("Existing website analytics rows were not deleted or updated.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
