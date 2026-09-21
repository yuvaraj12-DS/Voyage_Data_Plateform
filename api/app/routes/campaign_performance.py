from datetime import date, datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import CampaignDailyMetric
from api.app.schemas.campaign_performance import (
    CampaignPerformanceListResponse,
    CampaignPerformanceResponse,
)


router = APIRouter(
    prefix="/api/v1/campaign-performance",
    tags=["campaign-performance"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=CampaignPerformanceListResponse,
)
def list_campaign_performance(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    campaign_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(
            CampaignDailyMetric.tenant_id == tenant_id
        )

    if campaign_id:
        filters.append(
            CampaignDailyMetric.campaign_id == campaign_id
        )

    if start_date:
        filters.append(
            CampaignDailyMetric.date >= start_date
        )

    if end_date:
        filters.append(
            CampaignDailyMetric.date <= end_date
        )

    if updated_after:
        filters.append(
            CampaignDailyMetric.updated_at > updated_after
        )

    total_records = db.scalar(
        select(func.count())
        .select_from(CampaignDailyMetric)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    metrics = (
        db.scalars(
            select(CampaignDailyMetric)
            .where(*filters)
            .order_by(
                CampaignDailyMetric.updated_at.asc(),
                CampaignDailyMetric.metric_id.asc(),
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
        "data": metrics,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }