from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ad_group_id: str
    campaign_id: str
    tenant_id: str
    ad_group_name: str
    status: str
    created_at: datetime
    updated_at: datetime


class AdGroupListResponse(BaseModel):
    data: list[AdGroupResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int