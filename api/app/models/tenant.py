from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    tenant_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
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

    properties = relationship(
        "Property",
        back_populates="tenant",
    )

    customers = relationship(
        "Customer",
        back_populates="tenant",
    )

    bookings = relationship(
        "Booking",
        back_populates="tenant",
    )
    campaigns = relationship(
        "Campaign",
        back_populates="tenant",
    )