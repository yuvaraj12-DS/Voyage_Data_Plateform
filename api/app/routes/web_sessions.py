from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import WebSession
from api.app.schemas.web_session import WebSessionListResponse, WebSessionResponse


router = APIRouter(
    prefix="/api/v1/web-sessions",
    tags=["web-sessions"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=WebSessionListResponse,
)
def list_web_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    source: str | None = None,
    medium: str | None = None,
    campaign_id: str | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(WebSession.tenant_id == tenant_id)

    if source:
        filters.append(WebSession.source == source)

    if medium:
        filters.append(WebSession.medium == medium)

    if campaign_id:
        filters.append(WebSession.campaign_id == campaign_id)

    if updated_after:
        filters.append(WebSession.updated_at > updated_after)

    total_records = db.scalar(
        select(func.count())
        .select_from(WebSession)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    web_sessions = (
        db.scalars(
            select(WebSession)
            .where(*filters)
            .order_by(
                WebSession.updated_at.asc(),
                WebSession.session_id.asc(),
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
        "data": web_sessions,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }