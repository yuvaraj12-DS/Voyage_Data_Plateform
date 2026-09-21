from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CampaignPerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_id: int
    date: date
    tenant_id: str
    campaign_id: str
    impressions: int
    clicks: int
    spend: Decimal
    conversions: int
    revenue: Decimal
    updated_at: datetime


class CampaignPerformanceListResponse(BaseModel):
    data: list[CampaignPerformanceResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int