from sqlalchemy import inspect

from api.app.database import engine
from api.app.models.base import Base

# Import website analytics models so SQLAlchemy registers their tables with Base.metadata.
from api.app.models.web_session import WebSession  # noqa: F401
from api.app.models.web_page_view import WebPageView  # noqa: F401
from api.app.models.web_event import WebEvent  # noqa: F401


WEBSITE_ANALYTICS_TABLES = [
    "web_sessions",
    "web_page_views",
    "web_events",
]


def main() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    tables_to_create = [
        table_name
        for table_name in WEBSITE_ANALYTICS_TABLES
        if table_name not in existing_tables
    ]

    if not tables_to_create:
        print("Website analytics tables already exist. Nothing to create.")
        return

    Base.metadata.create_all(
        bind=engine,
        tables=[
            table
            for table in Base.metadata.tables.values()
            if table.name in tables_to_create
        ],
    )

    print("Created website analytics tables:")
    for table_name in tables_to_create:
        print(f"  - {table_name}")


if __name__ == "__main__":
    main()