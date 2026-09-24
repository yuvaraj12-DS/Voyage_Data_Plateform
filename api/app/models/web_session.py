from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class WebSession(Base):
    __tablename__ = "web_sessions"

    session_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )

    session_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    session_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    medium: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    campaign_id: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    device: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    landing_page: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    tenant = relationship(
        "Tenant",
        back_populates="web_sessions",
    )

    page_views = relationship(
        "WebPageView",
        back_populates="session",
    )

    events = relationship(
        "WebEvent",
        back_populates="session",
    )
