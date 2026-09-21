from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ad_id: str
    ad_group_id: str
    campaign_id: str
    tenant_id: str
    ad_name: str
    creative_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class AdListResponse(BaseModel):
    data: list[AdResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int