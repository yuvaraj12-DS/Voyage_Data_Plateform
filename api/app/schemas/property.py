from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    property_id: str
    tenant_id: str
    property_name: str
    property_type: str
    destination: str
    created_at: datetime
    updated_at: datetime