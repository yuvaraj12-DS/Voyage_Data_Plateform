from sqlalchemy import func, update
from sqlalchemy.orm import Session

from api.app.database import engine
from api.app.models import Booking


BOOKING_ID = "BK000003"


with Session(engine) as db:
    booking = db.get(Booking, BOOKING_ID)

    if booking is None:
        raise RuntimeError(f"Booking {BOOKING_ID} was not found.")

    before = booking.updated_at

    db.execute(
        update(Booking)
        .where(Booking.booking_id == BOOKING_ID)
        .values(updated_at=func.now())
    )

    db.commit()

    booking = db.get(Booking, BOOKING_ID)

    print(f"Booking ID: {BOOKING_ID}")
    print(f"Before updated_at: {before}")
    print(f"After updated_at:  {booking.updated_at}")