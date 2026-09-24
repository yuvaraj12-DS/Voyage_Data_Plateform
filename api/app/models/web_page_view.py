from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class WebPageView(Base):
    __tablename__ = "web_page_views"

    page_view_id: Mapped[str] = mapped_column(
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
    page_viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    page_path: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    page_title: Mapped[str] = mapped_column(
        String(200),    
        nullable=False,
    )
    referrer: Mapped[str] = mapped_column(
        String(200),
        nullable=True,
    )
    duration_seconds: Mapped[int] = mapped_column(
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    tenant = relationship(
        "Tenant",
        back_populates="web_page_views",
    )
    session = relationship(
        "WebSession",
        back_populates="page_views",
    )