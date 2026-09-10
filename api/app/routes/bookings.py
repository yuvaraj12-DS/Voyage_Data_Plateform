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
    limit: int | None = Query(default=None, ge=1),
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

    # Optional cap used for controlled ingestion tests.
    effective_total = min(total_records, limit) if limit else total_records

    offset = (page - 1) * page_size

    # If the requested page starts beyond the test limit,
    # return an empty page.
    if offset >= effective_total:
        bookings = []
    else:
        effective_page_size = min(
            page_size,
            effective_total - offset,
        )

        statement = (
            select(Booking)
            .where(*filters)
            .order_by(
                Booking.updated_at.asc(),
                Booking.booking_id.asc(),
            )
            .offset(offset)
            .limit(effective_page_size)
        )

        bookings = db.scalars(statement).all()

    total_pages = (
        ceil(effective_total / page_size)
        if effective_total
        else 0
    )

    return {
        "data": bookings,
        "page": page,
        "page_size": page_size,
        "total_records": effective_total,
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