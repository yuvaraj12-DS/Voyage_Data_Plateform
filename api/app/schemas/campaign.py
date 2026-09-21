from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: str
    tenant_id: str
    campaign_name: str
    channel: str
    campaign_type: str
    objective: str
    status: str
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    data: list[CampaignResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int