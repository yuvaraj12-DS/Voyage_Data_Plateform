from sqlalchemy import inspect

from api.app.database import engine
from api.app.models.base import Base

# Import marketing models so SQLAlchemy registers their tables with Base.metadata.
from api.app.models.campaign import Campaign  # noqa: F401
from api.app.models.ad_group import AdGroup  # noqa: F401
from api.app.models.ad import Ad  # noqa: F401
from api.app.models.campaign_daily_metric import CampaignDailyMetric  # noqa: F401


MARKETING_TABLES = [
    "marketing_campaigns",
    "marketing_ad_groups",
    "marketing_ads",
    "marketing_campaign_daily_metrics",
]


def main() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    tables_to_create = [
        table_name
        for table_name in MARKETING_TABLES
        if table_name not in existing_tables
    ]

    if not tables_to_create:
        print("Marketing tables already exist. Nothing to create.")
        return

    Base.metadata.create_all(
        bind=engine,
        tables=[
            table
            for table in Base.metadata.tables.values()
            if table.name in tables_to_create
        ],
    )

    print("Created marketing tables:")
    for table_name in tables_to_create:
        print(f"  - {table_name}")


if __name__ == "__main__":
    main()