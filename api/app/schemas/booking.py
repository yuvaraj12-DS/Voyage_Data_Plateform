from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_id: str
    tenant_id: str
    property_id: str
    customer_id: str
    booking_date: date
    arrival_date: date
    departure_date: date
    adults: int
    children: int
    room_nights: int
    adr: Decimal
    market_segment: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class BookingListResponse(BaseModel):
    data: list[BookingResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int