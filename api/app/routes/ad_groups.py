from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import AdGroup
from api.app.schemas.ad_group import (
    AdGroupListResponse,
    AdGroupResponse,
)


router = APIRouter(
    prefix="/api/v1/ad-groups",
    tags=["ad-groups"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=AdGroupListResponse,
)
def list_ad_groups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    campaign_id: str | None = None,
    status: str | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(AdGroup.tenant_id == tenant_id)

    if campaign_id:
        filters.append(AdGroup.campaign_id == campaign_id)

    if status:
        filters.append(AdGroup.status == status)

    if updated_after:
        filters.append(AdGroup.updated_at > updated_after)

    total_records = db.scalar(
        select(func.count())
        .select_from(AdGroup)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    ad_groups = (
        db.scalars(
            select(AdGroup)
            .where(*filters)
            .order_by(
                AdGroup.updated_at.asc(),
                AdGroup.ad_group_id.asc(),
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
        "data": ad_groups,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }