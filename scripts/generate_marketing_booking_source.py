"""
Generate synthetic 2026 marketing bookings from website purchase events.

One website purchase event produces exactly one synthetic marketing booking.

This creates the explicit bridge:

campaign
    -> website session
    -> purchase event
    -> marketing booking
    -> revenue
"""

from datetime import datetime, timedelta
import random
from sqlalchemy import func, text

from api.app.database import SessionLocal
from api.app.models.marketing_booking import MarketingBooking
from api.app.models.property import Property
from api.app.models.tenant import Tenant
from api.app.models.web_event import WebEvent
from api.app.models.web_session import WebSession


RANDOM_SEED = 42

START_DATE = datetime(2026, 4, 1)
END_DATE_EXCLUSIVE = datetime(2026, 10, 1)

CANCELLED_RATE = 0.08


def add_microseconds(base_datetime: datetime, max_seconds: int) -> datetime:
    return base_datetime + timedelta(
        seconds=random.randint(1, max_seconds),
        microseconds=random.randint(1, 999999),
    )


def main():
    random.seed(RANDOM_SEED)

    db = SessionLocal()

    try:
        # ---------------------------------------------------------------
        # Load existing tenants/properties.
        # ---------------------------------------------------------------

        tenants = db.query(Tenant).all()

        if not tenants:
            raise RuntimeError(
                "No tenants found. Existing booking source is required."
            )

        properties = db.query(Property).all()

        if not properties:
            raise RuntimeError(
                "No properties found. Existing property source is required."
            )

        properties_by_tenant = {}

        for prop in properties:
            properties_by_tenant.setdefault(
                prop.tenant_id,
                [],
            ).append(prop.property_id)

        # ---------------------------------------------------------------
        # Load purchase events and their website sessions.
        # ---------------------------------------------------------------

        purchases = (
            db.query(WebEvent, WebSession)
            .join(
                WebSession,
                WebEvent.session_id == WebSession.session_id,
            )
            .filter(
                WebEvent.event_name == "purchase",
                WebEvent.event_timestamp >= START_DATE,
                WebEvent.event_timestamp < END_DATE_EXCLUSIVE,
            )
            .order_by(
                WebEvent.event_timestamp.asc(),
                WebEvent.event_id.asc(),
            )
            .all()
        )

        if not purchases:
            raise RuntimeError(
                "No purchase events found. Generate website analytics first."
            )

        print(f"Purchase events found: {len(purchases)}")

        # ---------------------------------------------------------------
        # Clear only synthetic marketing bookings.
        # ---------------------------------------------------------------

        deleted = (
            db.query(MarketingBooking)
            .delete(synchronize_session=False)
        )

        db.commit()

        print(
            f"Cleared existing marketing_bookings: {deleted}"
        )

        # ---------------------------------------------------------------
        # Generate one booking per purchase event.
        # ---------------------------------------------------------------

        bookings = []

        for number, (event, session) in enumerate(
            purchases,
            start=1,
        ):
            tenant_id = event.tenant_id

            tenant_properties = properties_by_tenant.get(
                tenant_id,
                [],
            )

            if not tenant_properties:
                raise RuntimeError(
                    f"No properties found for tenant {tenant_id}"
                )

            property_id = random.choice(tenant_properties)

            gross_booking_value = round(
                float(event.event_value),
                2,
            )

            booking_status = (
                "CANCELLED"
                if random.random() < CANCELLED_RATE
                else "CONFIRMED"
            )

            if booking_status == "CANCELLED":
                net_revenue = 0.0
            else:
                retention_factor = random.uniform(
                    0.85,
                    0.98,
                )

                net_revenue = round(
                    gross_booking_value * retention_factor,
                    2,
                )

            created_at = add_microseconds(
                event.event_timestamp,
                60,
            )

            updated_at = add_microseconds(
                created_at,
                120,
            )

            bookings.append(
                MarketingBooking(
                    booking_id=f"MKTBOOK{number:06d}",
                    tenant_id=tenant_id,
                    property_id=property_id,
                    conversion_id=event.event_id,
                    session_id=event.session_id,
                    user_id=session.user_id,
                    booking_date=event.event_timestamp.date(),
                    booking_status=booking_status,
                    gross_booking_value=gross_booking_value,
                    net_revenue=net_revenue,
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )

        # ---------------------------------------------------------------
        # Insert.
        # ---------------------------------------------------------------

        db.bulk_save_objects(bookings)
        db.commit()

        print(
            f"Generated marketing bookings: {len(bookings)}"
        )

        # ---------------------------------------------------------------
        # Validation.
        # ---------------------------------------------------------------

        booking_count = (
            db.query(MarketingBooking).count()
        )

        purchase_count = (
            db.query(WebEvent)
            .filter(
                WebEvent.event_name == "purchase",
                WebEvent.event_timestamp >= START_DATE,
                WebEvent.event_timestamp < END_DATE_EXCLUSIVE,
            )
            .count()
        )

        duplicate_conversion_ids = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT conversion_id
                        FROM marketing_bookings
                        GROUP BY conversion_id
                        HAVING COUNT(*) > 1
                    ) x
                    """
                )
            ).scalar()
        )

        orphan_sessions = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM marketing_bookings mb
                    LEFT JOIN web_sessions ws
                        ON mb.session_id = ws.session_id
                    WHERE ws.session_id IS NULL
                    """
                )
            ).scalar()
        )

        orphan_conversions = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM marketing_bookings mb
                    LEFT JOIN web_events we
                        ON mb.conversion_id = we.event_id
                    WHERE we.event_id IS NULL
                    """
                )
            ).scalar()
        )

        orphan_tenants = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM marketing_bookings mb
                    LEFT JOIN tenants t
                        ON mb.tenant_id = t.tenant_id
                    WHERE t.tenant_id IS NULL
                    """
                )
            ).scalar()
        )

        orphan_properties = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM marketing_bookings mb
                    LEFT JOIN properties p
                        ON mb.property_id = p.property_id
                    WHERE p.property_id IS NULL
                    """
                )
            ).scalar()
        )

        invalid_values = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM marketing_bookings
                    WHERE gross_booking_value < 0
                       OR net_revenue < 0
                       OR net_revenue > gross_booking_value
                    """
                )
            ).scalar()
        )

        invalid_status_revenue = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM marketing_bookings
                    WHERE
                        (
                            booking_status = 'CANCELLED'
                            AND net_revenue <> 0
                        )
                        OR
                        (
                            booking_status = 'CONFIRMED'
                            AND net_revenue <= 0
                        )
                    """
                )
            ).scalar()
        )

        print("\nValidation:")
        print(f"  purchase events: {purchase_count}")
        print(f"  marketing bookings: {booking_count}")
        print(
            f"  duplicate conversion IDs: "
            f"{duplicate_conversion_ids}"
        )
        print(f"  orphan sessions: {orphan_sessions}")
        print(f"  orphan conversions: {orphan_conversions}")
        print(f"  orphan tenants: {orphan_tenants}")
        print(f"  orphan properties: {orphan_properties}")
        print(f"  invalid values: {invalid_values}")
        print(
            f"  invalid status/revenue combinations: "
            f"{invalid_status_revenue}"
        )

        checks = [
            booking_count == purchase_count,
            duplicate_conversion_ids == 0,
            orphan_sessions == 0,
            orphan_conversions == 0,
            orphan_tenants == 0,
            orphan_properties == 0,
            invalid_values == 0,
            invalid_status_revenue == 0,
        ]

        if not all(checks):
            raise RuntimeError(
                "Marketing booking validation failed."
            )

        print(
            "\nMarketing booking source generation "
            "completed successfully."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()