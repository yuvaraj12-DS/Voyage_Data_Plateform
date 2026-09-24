from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import WebEvent
from api.app.schemas.web_event import WebEventListResponse, WebEventResponse


router = APIRouter(
    prefix="/api/v1/web-events",
    tags=["web-events"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=WebEventListResponse,
)
def list_web_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    session_id: str | None = None,
    event_name: str | None = None,
    updated_after: datetime | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(WebEvent.tenant_id == tenant_id)

    if session_id:
        filters.append(WebEvent.session_id == session_id)

    if event_name:
        filters.append(WebEvent.event_name == event_name)

    if updated_after:
        filters.append(WebEvent.updated_at > updated_after)

    total_records = db.scalar(
        select(func.count())
        .select_from(WebEvent)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    web_events = (
        db.scalars(
            select(WebEvent)
            .where(*filters)
            .order_by(
                WebEvent.updated_at.asc(),
                WebEvent.event_id.asc(),
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
        "data": web_events,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
    }