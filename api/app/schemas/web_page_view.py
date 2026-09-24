from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WebPageViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_view_id: str
    session_id: str
    tenant_id: str
    page_viewed_at: datetime
    page_path: str
    page_title: str
    referrer: str | None=None
    duration_seconds: int
    updated_at: datetime
    
class WebPageViewListResponse(BaseModel):
    data: list[WebPageViewResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int    