from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    tenant_id: str
    country: str | None
    customer_type: str | None
    created_at: datetime
    updated_at: datetime