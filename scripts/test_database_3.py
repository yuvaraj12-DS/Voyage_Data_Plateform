from sqlalchemy import select

from api.app.database import SessionLocal
from api.app.models import Tenant


def main() -> None:
    db = SessionLocal()

    try:
        statement = select(Tenant)

        tenant = db.scalars(statement).first()

        if tenant is None:
            print("No tenants found.")
            return

        print("Tenant:", tenant.tenant_name)
        print("Bookings:")

        for booking in tenant.bookings:
            print(
                " ",
                booking.booking_id,
                booking.status,
                booking.adr,
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()