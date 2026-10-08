"""Append one campaign performance row per campaign for a target UTC date."""

import argparse
import random
from datetime import date, datetime, timezone
from decimal import Decimal

from api.app.database import SessionLocal
from api.app.models.campaign import Campaign
from api.app.models.campaign_daily_metric import CampaignDailyMetric

RANDOM_SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Append one marketing campaign metric row per campaign for a UTC date."
        )
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now(timezone.utc).date(),
        help="UTC metric date in YYYY-MM-DD format (default: today in UTC).",
    )
    return parser.parse_args()


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp with microseconds."""

    timestamp = datetime.now(timezone.utc)
    if timestamp.microsecond == 0:
        timestamp = timestamp.replace(microsecond=1)
    return timestamp


def campaign_seed(campaign_id: str, metric_date: date) -> int:
    """Create a deterministic campaign/date-specific pseudo-random seed."""

    return sum(ord(character) for character in campaign_id) + metric_date.toordinal()


def generate_campaign_metrics(campaign: Campaign, metric_date: date) -> CampaignDailyMetric:
    rng = random.Random(campaign_seed(campaign.campaign_id, metric_date) + RANDOM_SEED)

    channel_factor = 1.25 if campaign.channel == "google" else 1.0
    base_impressions = 28000 if campaign.channel == "google" else 36000
    base_ctr = 0.040 if campaign.channel == "google" else 0.032
    base_cpc = 0.70 if campaign.channel == "google" else 0.55

    seasonal_factor = 1.0
    if metric_date.month in (6, 7, 8):
        seasonal_factor = 1.20
    elif metric_date.month in (4, 5):
        seasonal_factor = 0.90

    impressions = max(
        1000,
        int(base_impressions * channel_factor * seasonal_factor * rng.uniform(0.85, 1.15)),
    )

    ctr = max(
        0.008,
        min(0.12, base_ctr * channel_factor * rng.uniform(0.85, 1.15)),
    )
    clicks = min(impressions, max(1, int(impressions * ctr)))

    cpc = max(0.20, base_cpc * rng.uniform(0.85, 1.15))
    spend = Decimal(str(round(clicks * cpc, 2)))

    conversion_rate = max(
        0.01,
        min(0.18, 0.025 * channel_factor * rng.uniform(0.80, 1.20)),
    )
    conversions = min(clicks, max(0, int(clicks * conversion_rate)))

    average_booking_value = rng.uniform(180, 420)
    revenue = Decimal(
        str(round(conversions * average_booking_value * rng.uniform(0.90, 1.10), 2))
    )

    return CampaignDailyMetric(
        date=metric_date,
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.campaign_id,
        impressions=impressions,
        clicks=clicks,
        spend=spend,
        conversions=conversions,
        revenue=revenue,
        updated_at=utc_now(),
    )


def main() -> int:
    target_date = parse_args().date
    db = SessionLocal()

    try:
        existing_metrics = (
            db.query(CampaignDailyMetric)
            .filter(CampaignDailyMetric.date == target_date)
            .first()
        )
        if existing_metrics is not None:
            raise RuntimeError(
                f"Campaign metrics already exist for {target_date}. "
                "No historical rows were modified."
            )

        campaigns = db.query(Campaign).order_by(Campaign.campaign_id.asc()).all()
        if not campaigns:
            raise RuntimeError("No campaigns found. Populate the campaign source first.")

        metric_rows = [
            generate_campaign_metrics(campaign, target_date)
            for campaign in campaigns
        ]

        for row in metric_rows:
            if not (0 <= row.clicks <= row.impressions):
                raise RuntimeError(
                    f"Invalid clicks/impressions for campaign {row.campaign_id}: "
                    f"{row.clicks} > {row.impressions}"
                )
            if not (0 <= row.conversions <= row.clicks):
                raise RuntimeError(
                    f"Invalid conversions/clicks for campaign {row.campaign_id}: "
                    f"{row.conversions} > {row.clicks}"
                )
            if row.spend < 0 or row.revenue < 0:
                raise RuntimeError(
                    f"Negative spend or revenue generated for campaign {row.campaign_id}."
                )

        db.bulk_save_objects(metric_rows)
        db.commit()

        print(f"Campaign metrics append for UTC date {target_date}:")
        print(f"  campaigns: {len(campaigns)}")
        print(f"  rows inserted: {len(metric_rows)}")
        print("  constraints enforced: clicks <= impressions, conversions <= clicks")
        print("  spend/revenue are non-negative and updated_at is refreshed")
        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
