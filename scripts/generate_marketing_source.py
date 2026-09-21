from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.app.database import SessionLocal
from api.app.models import Ad, AdGroup, Campaign, CampaignDailyMetric


RANDOM_SEED = 42

START_DATE = date(2026, 4, 1)
END_DATE = date(2026, 9, 30)

CAMPAIGNS = [
    {
        "campaign_id": "CMP001",
        "tenant_id": "TENANT001",
        "campaign_name": "Mallorca Summer 2026",
        "channel": "google",
        "campaign_type": "SEARCH",
        "objective": "CONVERSIONS",
    },
    {
        "campaign_id": "CMP002",
        "tenant_id": "TENANT001",
        "campaign_name": "Mallorca Family Holiday",
        "channel": "meta",
        "campaign_type": "SOCIAL",
        "objective": "CONVERSIONS",
    },
    {
        "campaign_id": "CMP003",
        "tenant_id": "TENANT001",
        "campaign_name": "Mallorca Luxury Escape",
        "channel": "google",
        "campaign_type": "SEARCH",
        "objective": "CONVERSIONS",
    },
    {
        "campaign_id": "CMP004",
        "tenant_id": "TENANT002",
        "campaign_name": "Barcelona Summer 2026",
        "channel": "google",
        "campaign_type": "SEARCH",
        "objective": "CONVERSIONS",
    },
    {
        "campaign_id": "CMP005",
        "tenant_id": "TENANT002",
        "campaign_name": "Barcelona Weekend Packages",
        "channel": "meta",
        "campaign_type": "SOCIAL",
        "objective": "CONVERSIONS",
    },
    {
        "campaign_id": "CMP006",
        "tenant_id": "TENANT002",
        "campaign_name": "Barcelona Premium Hotels",
        "channel": "google",
        "campaign_type": "DISPLAY",
        "objective": "CONVERSIONS",
    },
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def clear_marketing_data(db: Session) -> None:
    db.execute(delete(CampaignDailyMetric))
    db.execute(delete(Ad))
    db.execute(delete(AdGroup))
    db.execute(delete(Campaign))
    db.commit()


def build_source_data(db: Session) -> None:
    random.seed(RANDOM_SEED)

    now = utc_now()

    # Keep campaign characteristics stable so metrics remain reproducible.
    campaign_quality = {
        "CMP001": 1.25,
        "CMP002": 0.95,
        "CMP003": 1.45,
        "CMP004": 1.10,
        "CMP005": 0.90,
        "CMP006": 1.35,
    }

    # 1. Campaigns
    campaign_objects = []

    for campaign in CAMPAIGNS:
        campaign_obj = Campaign(
            campaign_id=campaign["campaign_id"],
            tenant_id=campaign["tenant_id"],
            campaign_name=campaign["campaign_name"],
            channel=campaign["channel"],
            campaign_type=campaign["campaign_type"],
            objective=campaign["objective"],
            status="ACTIVE",
            start_date=START_DATE,
            end_date=END_DATE,
            created_at=now,
            updated_at=now,
        )

        campaign_objects.append(campaign_obj)

    db.add_all(campaign_objects)
    db.flush()

    # 2. Ad groups
    ad_group_objects = []
    ad_group_counter = 1

    for campaign in CAMPAIGNS:
        for group_number in range(1, 3):
            ad_group_id = f"AG{ad_group_counter:03d}"

            ad_group = AdGroup(
                ad_group_id=ad_group_id,
                campaign_id=campaign["campaign_id"],
                tenant_id=campaign["tenant_id"],
                ad_group_name=f"{campaign['campaign_name']} - Group {group_number}",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )

            ad_group_objects.append(ad_group)
            ad_group_counter += 1

    db.add_all(ad_group_objects)
    db.flush()

    # 3. Ads
    ad_objects = []
    ad_counter = 1

    for ad_group in ad_group_objects:
        for ad_number in range(1, 3):
            ad_id = f"AD{ad_counter:03d}"

            ad = Ad(
                ad_id=ad_id,
                ad_group_id=ad_group.ad_group_id,
                campaign_id=ad_group.campaign_id,
                tenant_id=ad_group.tenant_id,
                ad_name=f"{ad_group.ad_group_name} - Ad {ad_number}",
                creative_type="IMAGE" if ad_number == 1 else "TEXT",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )

            ad_objects.append(ad)
            ad_counter += 1

    db.add_all(ad_objects)
    db.flush()

    # 4. Daily campaign metrics
    metric_objects = []

    for campaign in CAMPAIGNS:
        quality = campaign_quality[campaign["campaign_id"]]

        if campaign["channel"] == "google":
            base_impressions = 28000
            base_ctr = 0.040
            base_cpc = 0.70
        else:
            base_impressions = 36000
            base_ctr = 0.032
            base_cpc = 0.55

        for metric_date in daterange(START_DATE, END_DATE):
            seasonal_factor = 1.0

            # Slightly stronger demand during June-August.
            if metric_date.month in (6, 7, 8):
                seasonal_factor = 1.20
            elif metric_date.month in (4, 5):
                seasonal_factor = 0.90

            daily_noise = random.uniform(0.85, 1.15)

            impressions = max(
                1000,
                int(
                    base_impressions
                    * quality
                    * seasonal_factor
                    * daily_noise
                ),
            )

            ctr = max(
                0.005,
                min(
                    0.12,
                    base_ctr
                    * quality
                    * random.uniform(0.85, 1.15),
                ),
            )

            clicks = min(
                impressions,
                max(1, int(impressions * ctr)),
            )

            cpc = max(
                0.20,
                base_cpc
                * random.uniform(0.85, 1.15),
            )

            spend = Decimal(str(round(clicks * cpc, 2)))

            conversion_rate = max(
                0.01,
                min(
                    0.20,
                    0.025
                    * quality
                    * random.uniform(0.80, 1.20),
                ),
            )

            conversions = min(
                clicks,
                max(0, int(clicks * conversion_rate)),
            )

            average_booking_value = random.uniform(180, 420)

            revenue = Decimal(
                str(
                    round(
                        conversions
                        * average_booking_value
                        * random.uniform(0.90, 1.10),
                        2,
                    )
                )
            )

            metric_objects.append(
                CampaignDailyMetric(
                    date=metric_date,
                    tenant_id=campaign["tenant_id"],
                    campaign_id=campaign["campaign_id"],
                    impressions=impressions,
                    clicks=clicks,
                    spend=spend,
                    conversions=conversions,
                    revenue=revenue,
                    updated_at=now,
                )
            )

    db.add_all(metric_objects)
    db.commit()

    print(f"Created campaigns: {len(campaign_objects)}")
    print(f"Created ad groups: {len(ad_group_objects)}")
    print(f"Created ads: {len(ad_objects)}")
    print(f"Created daily metrics: {len(metric_objects)}")


def main() -> None:
    db = SessionLocal()

    try:
        print("Clearing existing marketing source data...")
        clear_marketing_data(db)

        print("Generating marketing source data...")
        build_source_data(db)

        print("Marketing source generation completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()