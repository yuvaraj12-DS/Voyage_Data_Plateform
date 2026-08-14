from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import Tenant
from api.app.schemas.tenant import TenantResponse


router = APIRouter(
    prefix="/api/v1/tenants",
    tags=["tenants"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=list[TenantResponse])
def list_tenants(
    db: Session = Depends(get_db),
):
    statement = select(Tenant).order_by(Tenant.tenant_id)

    return db.scalars(statement).all()