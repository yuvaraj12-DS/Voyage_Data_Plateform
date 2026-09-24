from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WebEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    session_id: str
    tenant_id: str
    event_name: str
    event_timestamp: datetime
    page_path: str
    event_value: Decimal | None = None
    updated_at: datetime

class WebEventListResponse(BaseModel):
    data: list[WebEventResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int