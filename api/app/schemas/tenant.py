from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: str
    tenant_name: str
    country: str
    currency: str
    created_at: datetime
    updated_at: datetime