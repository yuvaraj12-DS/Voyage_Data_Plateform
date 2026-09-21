from datetime import date as date_type, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class CampaignDailyMetric(Base):
    __tablename__ = "marketing_campaign_daily_metrics"

    metric_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    date: Mapped[date_type] = mapped_column(
        Date,
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )

    campaign_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("marketing_campaigns.campaign_id"),
        nullable=False,
    )

    impressions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    clicks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    spend: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    conversions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    campaign = relationship(
        "Campaign",
        back_populates="daily_metrics",
    )