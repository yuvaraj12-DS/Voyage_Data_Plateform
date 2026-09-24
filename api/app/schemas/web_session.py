from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WebSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    tenant_id: str
    user_id: str | None=None
    session_start: datetime
    session_end: datetime
    source: str
    medium: str
    campaign_id: str | None=None
    device: str
    country: str
    landing_page: str
    updated_at: datetime

class WebSessionListResponse(BaseModel):
    data: list[WebSessionResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int