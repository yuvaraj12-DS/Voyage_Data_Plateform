from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MarketingBookingResponse(BaseModel):
    booking_id: str
    tenant_id: str
    property_id: str
    conversion_id: str
    session_id: str
    user_id: str | None
    booking_date: date
    booking_status: str
    gross_booking_value: Decimal
    net_revenue: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class MarketingBookingListResponse(BaseModel):
    data: list[MarketingBookingResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int