from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class Property(Base):
    __tablename__ = "properties"

    property_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )

    property_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    property_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    destination: Mapped[str] = mapped_column(
        String(100),
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
        back_populates="properties",
    )

    bookings = relationship(
        "Booking",
        back_populates="property",
    )