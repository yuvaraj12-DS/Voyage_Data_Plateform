from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class Campaign(Base):
    __tablename__ = "marketing_campaigns"

    campaign_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )

    campaign_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    campaign_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    objective: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
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
        back_populates="campaigns",
    )

    ad_groups = relationship(
        "AdGroup",
        back_populates="campaign",
    )
    daily_metrics = relationship(
        "CampaignDailyMetric",
        back_populates="campaign",
    )    