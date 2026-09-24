from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class WebEvent(Base):
    __tablename__ = "web_events"

    event_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("web_sessions.session_id"),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    event_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    page_path: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    event_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    tenant = relationship(
        "Tenant",
        back_populates="web_events",
    )
    session = relationship(
        "WebSession",
        back_populates="events",
    )