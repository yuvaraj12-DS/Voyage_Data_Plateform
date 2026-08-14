from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    booking_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )

    property_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("properties.property_id"),
        nullable=False,
    )

    customer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("customers.customer_id"),
        nullable=False,
    )

    booking_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    arrival_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    departure_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    adults: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    children: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    room_nights: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    adr: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    market_segment: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    tenant = relationship(
        "Tenant",
        back_populates="bookings",
    )

    property = relationship(
        "Property",
        back_populates="bookings",
    )

    customer = relationship(
        "Customer",
        back_populates="bookings",
    )