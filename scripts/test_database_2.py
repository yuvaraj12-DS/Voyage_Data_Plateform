from sqlalchemy import select

from api.app.database import SessionLocal
from api.app.models import Booking


def main() -> None:
    db = SessionLocal()

    try:
        statement = select(Booking)

        booking = db.scalars(statement).first()

        if booking is None:
            print("No bookings found.")
            return

        print("Booking:", booking.booking_id)
        print("Tenant:", booking.tenant.tenant_name)
        print("Property:", booking.property.property_name)
        print("Customer:", booking.customer.customer_id)

    finally:
        db.close()


if __name__ == "__main__":
    main()