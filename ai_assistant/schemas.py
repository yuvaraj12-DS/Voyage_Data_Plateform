"""Validation schemas for LLM tool arguments."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DateFilterArgs(StrictArgs):
    start_date: str | None = None
    end_date: str | None = None
    tenant_id: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_iso_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from datetime import date
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD format.") from exc
        return parsed.isoformat()

    @model_validator(mode="after")
    def both_dates_or_none(self):
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Provide both start_date and end_date, or omit both.")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date.")
        return self


class MarketingArgs(DateFilterArgs):
    limit: int = Field(default=10, ge=1, le=50)


class WebsiteArgs(DateFilterArgs):
    pass


class FunnelArgs(DateFilterArgs):
    pass


class AttributionArgs(DateFilterArgs):
    model_type: Literal["first_click", "last_click", "linear", "all"] = "all"
    limit: int = Field(default=25, ge=1, le=100)


class HistoricalBookingArgs(StrictArgs):
    year: int | None = Field(default=None, ge=2014, le=2017)
    start_date: str | None = None
    end_date: str | None = None
    tenant_id: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_iso_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from datetime import date
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD format.") from exc

    @model_validator(mode="after")
    def validate_period(self):
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Provide both start_date and end_date, or omit both.")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date.")
        if self.year is not None and self.start_date is not None:
            raise ValueError("Use year or start_date/end_date, not both.")
        return self


class PropertyArgs(DateFilterArgs):
    limit: int = Field(default=10, ge=1, le=50)


class TenantArgs(DateFilterArgs):
    limit: int = Field(default=10, ge=1, le=50)


TOOL_ARGUMENT_MODELS = {
    "get_campaign_performance": MarketingArgs,
    "get_marketing_funnel": FunnelArgs,
    "get_website_performance": WebsiteArgs,
    "get_attribution_performance": AttributionArgs,
    "get_historical_booking_performance": HistoricalBookingArgs,
    "get_property_performance": PropertyArgs,
    "get_tenant_performance": TenantArgs,
}


def validate_tool_arguments(tool_name: str, arguments: dict) -> dict:
    model = TOOL_ARGUMENT_MODELS.get(tool_name)
    if model is None:
        raise ValueError("The requested tool is not approved.")
    validated = model.model_validate(arguments or {})
    return validated.model_dump(exclude_none=True)
