from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import Booking
from api.app.schemas.booking import (
    BookingListResponse,
    BookingResponse,
)


router = APIRouter(
    prefix="/api/v1/bookings",
    tags=["bookings"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=BookingListResponse)
def list_bookings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    status: str | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(Booking.tenant_id == tenant_id)

    if status:
        filters.append(Booking.status == status)

    if updated_after:
        filters.append(Booking.updated_at > updated_after)

    total_records = db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    statement = (
        select(Booking)
        .where(*filters)
        .order_by(
            Booking.updated_at.asc(),
            Booking.booking_id.asc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    bookings = db.scalars(statement).all()

    total_pages = ceil(total_records / page_size) if total_records else 0

    return {
        "data": bookings,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)

    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="Booking not found.",
        )

    return booking