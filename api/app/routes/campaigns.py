from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import Campaign
from api.app.schemas.campaign import (
    CampaignListResponse,
    CampaignResponse,
)


router = APIRouter(
    prefix="/api/v1/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=CampaignListResponse,
)
def list_campaigns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(Campaign.tenant_id == tenant_id)

    if status:
        filters.append(Campaign.status == status)

    if channel:
        filters.append(Campaign.channel == channel)

    if updated_after:
        filters.append(Campaign.updated_at > updated_after)

    total_records = db.scalar(
        select(func.count())
        .select_from(Campaign)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    campaigns = (
        db.scalars(
            select(Campaign)
            .where(*filters)
            .order_by(
                Campaign.updated_at.asc(),
                Campaign.campaign_id.asc(),
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
        "data": campaigns,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }