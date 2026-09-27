from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import MarketingBooking
from api.app.schemas.marketing_booking import (
    MarketingBookingListResponse,
)


router = APIRouter(
    prefix="/api/v1/marketing-bookings",
    tags=["marketing-bookings"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=MarketingBookingListResponse,
)
def list_marketing_bookings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    tenant_id: str | None = None,
    property_id: str | None = None,
    booking_status: str | None = None,
    conversion_id: str | None = None,
    session_id: str | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(
            MarketingBooking.tenant_id == tenant_id
        )

    if property_id:
        filters.append(
            MarketingBooking.property_id == property_id
        )

    if booking_status:
        filters.append(
            MarketingBooking.booking_status == booking_status
        )

    if conversion_id:
        filters.append(
            MarketingBooking.conversion_id == conversion_id
        )

    if session_id:
        filters.append(
            MarketingBooking.session_id == session_id
        )

    if updated_after:
        filters.append(
            MarketingBooking.updated_at > updated_after
        )

    total_records = (
        db.scalar(
            select(func.count())
            .select_from(MarketingBooking)
            .where(*filters)
        )
        or 0
    )

    offset = (page - 1) * page_size

    bookings = (
        db.scalars(
            select(MarketingBooking)
            .where(*filters)
            .order_by(
                MarketingBooking.updated_at.asc(),
                MarketingBooking.booking_id.asc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        .all()
    )

    total_pages = (
        ceil(total_records / page_size)
        if total_records
        else 0
    )

    return {
        "data": bookings,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }