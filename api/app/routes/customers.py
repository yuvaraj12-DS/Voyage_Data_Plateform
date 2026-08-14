from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.dependencies import require_api_key
from api.app.models import Customer
from api.app.schemas.customer import CustomerResponse


router = APIRouter(
    prefix="/api/v1/customers",
    tags=["customers"],
    dependencies=[Depends(require_api_key)],
)


@router.get("")
def list_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    filters = []

    if tenant_id:
        filters.append(Customer.tenant_id == tenant_id)

    total_records = db.scalar(
        select(func.count())
        .select_from(Customer)
        .where(*filters)
    ) or 0

    statement = (
        select(Customer)
        .where(*filters)
        .order_by(Customer.customer_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    customers = db.scalars(statement).all()

    return {
        "data": [
            CustomerResponse.model_validate(customer)
            for customer in customers
        ],
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": ceil(total_records / page_size)
        if total_records
        else 0,
    }