from sqlalchemy import select

from api.app.database import SessionLocal
from api.app.models import Booking


def main() -> None:
    db = SessionLocal()

    try:
        statement = select(Booking)

        bookings = db.scalars(statement).all()

        for booking in bookings:
            print(
                booking.booking_id,
                booking.tenant_id,
                booking.property_id,
                booking.customer_id,
                booking.status,
                booking.adr,
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()