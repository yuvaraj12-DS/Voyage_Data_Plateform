"""
Generate synthetic website analytics source data for VoyageData.

Creates:
    - web_sessions
    - web_page_views
    - web_events

Period:
    2026-04-01 through 2026-09-30

The generated data is intentionally synthetic and is designed to behave
like a GA4-style website analytics source for the VoyageData platform.
"""

from datetime import datetime, timedelta, date
import random

from api.app.database import SessionLocal
from api.app.models.campaign import Campaign
from api.app.models.tenant import Tenant
from api.app.models.web_session import WebSession
from api.app.models.web_page_view import WebPageView
from api.app.models.web_event import WebEvent


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RANDOM_SEED = 42

START_DATE = date(2026, 4, 1)
END_DATE = date(2026, 9, 30)

SESSION_COUNT = 30_000

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

EVENT_NAMES = [
    "search_availability",
    "view_property",
    "begin_booking",
    "purchase",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_datetime(start_date: date, end_date: date) -> datetime:
    """Return a random datetime within the supplied date range."""

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

    total_seconds = int((end_dt - start_dt).total_seconds())

    return start_dt + timedelta(
        seconds=random.randint(0, total_seconds - 1)
    )


def weighted_choice():
    """
    Traffic mix:

        Google CPC       30%
        Facebook paid    20%
        Google organic   20%
        Direct            15%
        Referral          15%
    """

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
    campaigns_by_tenant_channel: dict,
):
    """
    Select a campaign only for paid traffic.

    Google CPC -> campaigns with channel='google'
    Facebook paid social -> campaigns with channel='meta'
    Other traffic -> NULL campaign_id
    """

    if source == "google" and medium == "cpc":
        channel = "google"

    elif source == "facebook" and medium == "paid_social":
        channel = "meta"

    else:
        return None

    campaigns = campaigns_by_tenant_channel.get(
        (tenant_id, channel),
        [],
    )

    if not campaigns:
        return None

    return random.choice(campaigns)


def choose_page_sequence(
    searched: bool,
    property_viewed: bool,
    booking_started: bool,
    purchased: bool,
):
    """
    Create a realistic page-view sequence while keeping the number
    of page views between roughly 2 and 6 per session.
    """

    pages = [
        random.choice(LANDING_PAGES)
    ]

    if searched:
        pages.append("/search")

    if property_viewed:
        pages.append("/hotel")

    if booking_started:
        pages.append("/booking")

    if purchased:
        pages.append("/confirmation")

    # Add normal browsing pages until the session has 2–6 page views.
    possible_pages = [
        "/destinations",
        "/hotels",
        "/hotel",
        "/search",
    ]

    while len(pages) < 2:
        pages.append(random.choice(possible_pages))

    while len(pages) < random.randint(2, 6):
        pages.append(random.choice(possible_pages))

    return pages[:6]


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def main():
    random.seed(RANDOM_SEED)

    db = SessionLocal()

    try:
        # ---------------------------------------------------------------
        # Load existing tenants and campaigns.
        # ---------------------------------------------------------------

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

        campaigns_by_tenant_channel = {}

        for campaign in campaigns:
            key = (
                campaign.tenant_id,
                campaign.channel.lower(),
            )

            campaigns_by_tenant_channel.setdefault(key, []).append(
                campaign.campaign_id
            )

        # ---------------------------------------------------------------
        # Clear ONLY website analytics tables.
        # Delete children before sessions because of foreign keys.
        # ---------------------------------------------------------------

        deleted_events = (
            db.query(WebEvent)
            .delete(synchronize_session=False)
        )

        deleted_page_views = (
            db.query(WebPageView)
            .delete(synchronize_session=False)
        )

        deleted_sessions = (
            db.query(WebSession)
            .delete(synchronize_session=False)
        )

        db.commit()

        print("Cleared existing website analytics data:")
        print(f"  - web_events: {deleted_events}")
        print(f"  - web_page_views: {deleted_page_views}")
        print(f"  - web_sessions: {deleted_sessions}")

        # ---------------------------------------------------------------
        # Generate data.
        # ---------------------------------------------------------------

        sessions = []
        page_views = []
        events = []

        # Reusable synthetic users.
        user_ids = [
            f"WEBUSER{i:06d}"
            for i in range(1, 12_001)
        ]

        page_view_counter = 1
        event_counter = 1

        for session_number in range(1, SESSION_COUNT + 1):

            session_id = f"WEBSESS{session_number:06d}"

            tenant_id = random.choice(tenant_ids)

            user_id = (
                random.choice(user_ids)
                if random.random() < 0.70
                else None
            )

            session_start = random_datetime(
                START_DATE,
                END_DATE,
            )

            session_duration = random.randint(
                60,
                45 * 60,
            )

            session_end = session_start + timedelta(
                seconds=session_duration
            )

            source, medium = weighted_choice()

            campaign_id = choose_campaign(
                tenant_id=tenant_id,
                source=source,
                medium=medium,
                campaigns_by_tenant_channel=campaigns_by_tenant_channel,
            )

            device = random.choice(DEVICES)
            country = random.choice(COUNTRIES)
            landing_page = random.choice(LANDING_PAGES)

            updated_at = session_end + timedelta(
                seconds=random.randint(1, 120),
                microseconds=random.randint(1, 999999),
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
                    device=device,
                    country=country,
                    landing_page=landing_page,
                    updated_at=updated_at,
                )
            )

            # -----------------------------------------------------------
            # Funnel probabilities.
            #
            # Search:       ~40%
            # Property view: ~25% overall
            # Booking start: ~12% overall
            # Purchase:      ~5% overall
            # -----------------------------------------------------------

            searched = random.random() < 0.40

            property_viewed = (
                searched
                and random.random() < 0.625
            )

            booking_started = (
                property_viewed
                and random.random() < 0.48
            )

            purchased = (
                booking_started
                and random.random() < 0.42
            )

            # -----------------------------------------------------------
            # Page views
            # -----------------------------------------------------------

            page_sequence = choose_page_sequence(
                searched=searched,
                property_viewed=property_viewed,
                booking_started=booking_started,
                purchased=purchased,
            )

            available_seconds = max(
                session_duration - 1,
                len(page_sequence),
            )

            time_offsets = sorted(
                random.sample(
                    range(1, available_seconds + 1),
                    len(page_sequence),
                )
            )

            for page_number, page_path in enumerate(page_sequence):

                viewed_at = session_start + timedelta(
                    seconds=time_offsets[page_number]
                )

                duration_seconds = random.randint(
                    5,
                    120,
                )

                page_views.append(
                    WebPageView(
                        page_view_id=f"WEBPV{page_view_counter:07d}",
                        tenant_id=tenant_id,
                        session_id=session_id,
                        page_viewed_at=viewed_at,
                        page_path=page_path,
                        page_title=PAGE_TITLES.get(
                            page_path,
                            "VoyageData",
                        ),
                        referrer=(
                            f"{source}/{medium}"
                            if source not in {"direct"}
                            else None
                        ),
                        duration_seconds=duration_seconds,
                        updated_at=viewed_at + timedelta(
                            seconds=random.randint(1, 60)
                        ),
                    )
                )

                page_view_counter += 1

            # -----------------------------------------------------------
            # Events
            # -----------------------------------------------------------

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
                    range(
                        1,
                        available_seconds + 1,
                    ),
                    len(event_specs),
                )
            ) if event_specs else []

            for event_name, event_offset in zip(
                event_specs,
                event_offsets,
            ):

                event_timestamp = (
                    session_start
                    + timedelta(seconds=event_offset)
                )

                event_value = None

                if event_name == "purchase":
                    event_value = round(
                        random.uniform(400, 2500),
                        2,
                    )

                events.append(
                    WebEvent(
                        event_id=f"WEBEVT{event_counter:07d}",
                        tenant_id=tenant_id,
                        session_id=session_id,
                        event_timestamp=event_timestamp,
                        event_name=event_name,
                        page_path=(
                            "/confirmation"
                            if event_name == "purchase"
                            else (
                                "/booking"
                                if event_name == "begin_booking"
                                else (
                                    "/hotel"
                                    if event_name == "view_property"
                                    else "/search"
                                )
                            )
                        ),
                        event_value=event_value,
                        updated_at=event_timestamp + timedelta(
                            seconds=random.randint(1, 60)
                        ),
                    )
                )

                event_counter += 1

        # ---------------------------------------------------------------
        # Bulk insert.
        # ---------------------------------------------------------------

        print("\nGenerated:")
        print(f"  - web_sessions: {len(sessions)}")
        print(f"  - web_page_views: {len(page_views)}")
        print(f"  - web_events: {len(events)}")

        db.bulk_save_objects(sessions)
        db.commit()

        db.bulk_save_objects(page_views)
        db.commit()

        db.bulk_save_objects(events)
        db.commit()

        # ---------------------------------------------------------------
        # Validation
        # ---------------------------------------------------------------

        session_count = db.query(WebSession).count()
        page_view_count = db.query(WebPageView).count()
        event_count = db.query(WebEvent).count()

        page_view_orphans = (
            db.query(WebPageView)
            .outerjoin(
                WebSession,
                WebPageView.session_id == WebSession.session_id,
            )
            .filter(WebSession.session_id.is_(None))
            .count()
        )

        event_orphans = (
            db.query(WebEvent)
            .outerjoin(
                WebSession,
                WebEvent.session_id == WebSession.session_id,
            )
            .filter(WebSession.session_id.is_(None))
            .count()
        )

        invalid_session_times = (
            db.query(WebSession)
            .filter(WebSession.session_end < WebSession.session_start)
            .count()
        )

        negative_event_values = (
            db.query(WebEvent)
            .filter(WebEvent.event_value < 0)
            .count()
        )

        purchase_without_value = (
            db.query(WebEvent)
            .filter(
                WebEvent.event_name == "purchase",
                WebEvent.event_value.is_(None),
            )
            .count()
        )

        # Paid campaign IDs must exist in the marketing source.
        campaign_ids = {
            campaign.campaign_id
            for campaign in campaigns
        }

        paid_sessions = (
            db.query(WebSession)
            .filter(WebSession.campaign_id.is_not(None))
            .all()
        )

        invalid_paid_campaign_ids = sum(
            1
            for session in paid_sessions
            if session.campaign_id not in campaign_ids
        )

        print("\nValidation:")
        print(f"  sessions: {session_count}")
        print(f"  page_views: {page_view_count}")
        print(f"  events: {event_count}")
        print(f"  page_view orphans: {page_view_orphans}")
        print(f"  event orphans: {event_orphans}")
        print(f"  invalid session times: {invalid_session_times}")
        print(f"  negative event values: {negative_event_values}")
        print(f"  purchase events without value: {purchase_without_value}")
        print(
            f"  invalid paid campaign IDs: "
            f"{invalid_paid_campaign_ids}"
        )

        validation_failed = any(
            [
                page_view_orphans > 0,
                event_orphans > 0,
                invalid_session_times > 0,
                negative_event_values > 0,
                purchase_without_value > 0,
                invalid_paid_campaign_ids > 0,
            ]
        )

        if validation_failed:
            raise RuntimeError(
                "Website analytics validation failed. "
                "Review the validation output above."
            )

        print("\nWebsite analytics source generation completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()