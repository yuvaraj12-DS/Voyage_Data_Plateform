from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base


class Ad(Base):
    __tablename__ = "marketing_ads"

    ad_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    ad_group_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("marketing_ad_groups.ad_group_id"),
        nullable=False,
    )

    campaign_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("marketing_campaigns.campaign_id"),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )

    ad_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    creative_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
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

    ad_group = relationship(
        "AdGroup",
        back_populates="ads",
    )