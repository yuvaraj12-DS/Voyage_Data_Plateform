from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import Ad
from api.app.schemas.ad import AdListResponse, AdResponse


router = APIRouter(
    prefix="/api/v1/ads",
    tags=["ads"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=AdListResponse,
)
def list_ads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    status: str | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(Ad.tenant_id == tenant_id)

    if campaign_id:
        filters.append(Ad.campaign_id == campaign_id)

    if ad_group_id:
        filters.append(Ad.ad_group_id == ad_group_id)

    if status:
        filters.append(Ad.status == status)

    if updated_after:
        filters.append(Ad.updated_at > updated_after)

    total_records = db.scalar(
        select(func.count())
        .select_from(Ad)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    ads = (
        db.scalars(
            select(Ad)
            .where(*filters)
            .order_by(
                Ad.updated_at.asc(),
                Ad.ad_id.asc(),
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
        "data": ads,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }