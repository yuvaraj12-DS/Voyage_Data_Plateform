from sqlalchemy import inspect
from api.app.database import engine
from api.app.models.base import Base

from api.app.models.marketing_booking import MarketingBooking


def main():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "marketing_bookings" not in existing_tables:
        Base.metadata.create_all(
            bind=engine,
            tables=[MarketingBooking.__table__],
        )
        print("Created table: marketing_bookings")
    else:
        print("Table already exists: marketing_bookings")


if __name__ == "__main__":
    main()