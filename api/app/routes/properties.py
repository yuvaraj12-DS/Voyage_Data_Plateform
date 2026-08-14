from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import Property
from api.app.schemas.property import PropertyResponse


router = APIRouter(
    prefix="/api/v1/properties",
    tags=["properties"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=list[PropertyResponse])
def list_properties(
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Property)

    if tenant_id:
        statement = statement.where(
            Property.tenant_id == tenant_id
        )

    statement = statement.order_by(Property.property_id)

    return db.scalars(statement).all()