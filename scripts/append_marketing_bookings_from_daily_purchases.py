"""Append marketing bookings linked to website purchase events for one UTC day."""

import argparse
from datetime import date, datetime, time, timedelta, timezone
import random
from uuid import uuid4

from api.app.database import SessionLocal
from api.app.models.marketing_booking import MarketingBooking
from api.app.models.property import Property
from api.app.models.web_event import WebEvent
from api.app.models.web_session import WebSession


RANDOM_SEED = 42
CANCELLED_RATE = 0.08


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create one marketing booking for each purchase event on a UTC date."
        )
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now(timezone.utc).date(),
        help="Purchase event date in YYYY-MM-DD format (default: today in UTC).",
    )
    return parser.parse_args()


def utc_now() -> datetime:
    """Return an aware UTC timestamp with non-zero microseconds."""

    timestamp = datetime.now(timezone.utc)
    if timestamp.microsecond == 0:
        timestamp += timedelta(microseconds=1)
    return timestamp


def add_microseconds(base_datetime: datetime, max_seconds: int) -> datetime:
    """Preserve the existing generator's booking-created timestamp convention."""

    return base_datetime + timedelta(
        seconds=random.randint(1, max_seconds),
        microseconds=random.randint(1, 999999),
    )


def main() -> int:
    target_date = parse_args().date
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    next_day = day_start + timedelta(days=1)
    random.seed(RANDOM_SEED)
    db = SessionLocal()

    try:
        purchases = (
            db.query(WebEvent, WebSession)
            .join(
                WebSession,
                WebEvent.session_id == WebSession.session_id,
            )
            .filter(
                WebEvent.event_name == "purchase",
                WebEvent.event_timestamp >= day_start,
                WebEvent.event_timestamp < next_day,
            )
            .order_by(
                WebEvent.event_timestamp.asc(),
                WebEvent.event_id.asc(),
            )
            .all()
        )

        if not purchases:
            print(f"No purchase events found for UTC date {target_date}.")
            return 0

        purchase_ids = [event.event_id for event, _ in purchases]
        existing_bookings = (
            db.query(MarketingBooking)
            .filter(MarketingBooking.conversion_id.in_(purchase_ids))
            .all()
        )
        existing_by_conversion: dict[str, list[MarketingBooking]] = {}
        for booking in existing_bookings:
            existing_by_conversion.setdefault(
                booking.conversion_id,
                [],
            ).append(booking)

        duplicate_conversions = [
            conversion_id
            for conversion_id, bookings in existing_by_conversion.items()
            if len(bookings) > 1
        ]
        if duplicate_conversions:
            raise RuntimeError(
                "Multiple marketing bookings already exist for purchase "
                f"conversion(s): {', '.join(duplicate_conversions)}"
            )

        missing_purchases = [
            (event, session)
            for event, session in purchases
            if event.event_id not in existing_by_conversion
        ]
        if not missing_purchases:
            print(
                f"All {len(purchases)} purchase event(s) for {target_date} "
                "already have a marketing booking. No rows were added."
            )
            return 0

        properties_by_tenant: dict[str, list[str]] = {}
        for prop in db.query(Property).all():
            properties_by_tenant.setdefault(prop.tenant_id, []).append(
                prop.property_id
            )

        bookings = []
        for event, session in missing_purchases:
            if session.tenant_id != event.tenant_id:
                raise RuntimeError(
                    f"Purchase {event.event_id} and session "
                    f"{session.session_id} have different tenant IDs."
                )

            tenant_properties = properties_by_tenant.get(event.tenant_id, [])
            if not tenant_properties:
                raise RuntimeError(
                    f"No properties found for tenant {event.tenant_id}; "
                    "no bookings were inserted."
                )
            if event.event_value is None:
                raise RuntimeError(
                    f"Purchase {event.event_id} has no event_value; "
                    "no bookings were inserted."
                )

            gross_booking_value = round(float(event.event_value), 2)
            booking_status = (
                "CANCELLED"
                if random.random() < CANCELLED_RATE
                else "CONFIRMED"
            )
            if booking_status == "CANCELLED":
                net_revenue = 0.0
            else:
                net_revenue = round(
                    gross_booking_value * random.uniform(0.85, 0.98),
                    2,
                )

            created_at = add_microseconds(event.event_timestamp, 60)

            bookings.append(
                MarketingBooking(
                    booking_id=f"MKTBOOK{uuid4().hex.upper()}",
                    tenant_id=event.tenant_id,
                    property_id=random.choice(tenant_properties),
                    conversion_id=event.event_id,
                    session_id=event.session_id,
                    user_id=session.user_id,
                    booking_date=event.event_timestamp.date(),
                    booking_status=booking_status,
                    gross_booking_value=gross_booking_value,
                    net_revenue=net_revenue,
                    created_at=created_at,
                    updated_at=utc_now(),
                )
            )

        db.bulk_save_objects(bookings)
        db.commit()

        print(f"Marketing booking append for UTC date {target_date}:")
        print(f"  purchase events found: {len(purchases)}")
        print(f"  bookings already present: {len(existing_bookings)}")
        print(f"  new bookings created: {len(bookings)}")
        print("  conversion_id: source purchase event_id")
        print("  session_id, user_id, tenant_id: source purchase/session")
        print("  property_id: selected from the same tenant")
        print("  updated_at: current UTC timestamp with microseconds")
        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
