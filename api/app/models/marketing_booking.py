from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Column,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base

class MarketingBooking(Base):
    __tablename__ = "marketing_bookings"

    __table_args__ = (
        UniqueConstraint(
            "conversion_id",
            name="uq_marketing_bookings_conversion_id",
        ),
    )

    booking_id = Column(
        String,
        primary_key=True,
        index=True,
    )

    tenant_id = Column(
        String,
        ForeignKey("tenants.tenant_id"),
        nullable=False,
        index=True,
    )

    property_id = Column(
        String,
        ForeignKey("properties.property_id"),
        nullable=False,
        index=True,
    )

    conversion_id = Column(
        String,
        nullable=False,
        index=True,
    )

    session_id = Column(
        String,
        nullable=False,
        index=True,
    )

    user_id = Column(
        String,
        nullable=True,
        index=True,
    )

    booking_date = Column(
        Date,
        nullable=False,
        index=True,
    )

    booking_status = Column(
        String,
        nullable=False,
        index=True,
    )

    gross_booking_value = Column(
        Numeric(14, 2),
        nullable=False,
    )

    net_revenue = Column(
        Numeric(14, 2),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )