from __future__ import annotations

import argparse
import calendar
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.app.database import SessionLocal
from api.app.models import (
    Booking,
    BookingRejection,
    Customer,
    Property,
    Tenant,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT_DIR / "data" / "raw" / "hotel_bookings.csv"


HOTEL_CONFIG = {
    "Resort Hotel": {
        "tenant_id": "TENANT001",
        "tenant_name": "Mallorca Travel Co",
        "property_id": "PROP001",
        "property_name": "Mallorca Resort Hotel",
        "destination": "Mallorca",
    },
    "City Hotel": {
        "tenant_id": "TENANT002",
        "tenant_name": "Barcelona Travel Co",
        "property_id": "PROP002",
        "property_name": "Barcelona City Hotel",
        "destination": "Barcelona",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Hotel Booking Demand data into PostgreSQL."
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing source-system data before loading.",
    )

    return parser.parse_args()


def reset_database(db: Session) -> None:
    db.execute(
        text(
            """
            TRUNCATE TABLE
                booking_rejections,
                bookings,
                customers,
                properties,
                tenants
            RESTART IDENTITY CASCADE
            """
        )
    )

    db.commit()


def build_arrival_date(df: pd.DataFrame) -> pd.Series:
    month_lookup = {
        month: index
        for index, month in enumerate(calendar.month_name)
        if month
    }

    month_numbers = df["arrival_date_month"].map(month_lookup)

    return pd.to_datetime(
        {
            "year": df["arrival_date_year"],
            "month": month_numbers,
            "day": df["arrival_date_day_of_month"],
        }
    )


def build_status(row: pd.Series) -> str:
    if int(row["is_canceled"]) == 1:
        return "CANCELLED"

    if row["reservation_status"] == "Check-Out":
        return "COMPLETED"

    return "CONFIRMED"


def validate_source(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    children = df["children"].fillna(0)

    room_nights = (
        df["stays_in_weekend_nights"]
        + df["stays_in_week_nights"]
    )

    arrival_date = df["arrival_date"]

    departure_date = arrival_date + pd.to_timedelta(
        room_nights,
        unit="D",
    )

    invalid_adr = df["adr"].isna() | (df["adr"] < 0)
    invalid_adults = df["adults"].isna() | (df["adults"] < 0)
    invalid_children = children < 0
    invalid_room_nights = room_nights < 0
    invalid_dates = departure_date < arrival_date

    invalid = (
        invalid_adr
        | invalid_adults
        | invalid_children
        | invalid_room_nights
        | invalid_dates
    )

    reasons = []

    for index in df.index:
        row_reasons = []

        if invalid_adr.loc[index]:
            row_reasons.append("invalid_adr")

        if invalid_adults.loc[index]:
            row_reasons.append("invalid_adults")

        if invalid_children.loc[index]:
            row_reasons.append("invalid_children")

        if invalid_room_nights.loc[index]:
            row_reasons.append("invalid_room_nights")

        if invalid_dates.loc[index]:
            row_reasons.append("invalid_dates")

        reasons.append("|".join(row_reasons))

    return invalid, pd.Series(reasons, index=df.index)


def build_source_records(
    df: pd.DataFrame,
) -> tuple[
    list[dict],
    list[dict],
    list[dict],
    list[dict],
    list[dict],
]:
    df = df.copy()

    df["children"] = df["children"].fillna(0)

    df["arrival_date"] = build_arrival_date(df)

    df["booking_date"] = (
        df["arrival_date"]
        - pd.to_timedelta(df["lead_time"], unit="D")
    )

    df["room_nights"] = (
        df["stays_in_weekend_nights"]
        + df["stays_in_week_nights"]
    )

    df["departure_date"] = (
        df["arrival_date"]
        + pd.to_timedelta(df["room_nights"], unit="D")
    )

    invalid_mask, rejection_reasons = validate_source(df)

    tenants: dict[str, dict] = {}
    properties: dict[str, dict] = {}

    for hotel, config in HOTEL_CONFIG.items():
        tenants[config["tenant_id"]] = {
            "tenant_id": config["tenant_id"],
            "tenant_name": config["tenant_name"],
            "country": "ES",
            "currency": "EUR",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        properties[config["property_id"]] = {
            "property_id": config["property_id"],
            "tenant_id": config["tenant_id"],
            "property_name": config["property_name"],
            "property_type": "hotel",
            "destination": config["destination"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    customer_records: list[dict] = []
    booking_records: list[dict] = []
    rejection_records: list[dict] = []

    for source_index, row in df.iterrows():
        source_row_number = int(source_index) + 2

        booking_id = f"BK{source_index + 1:06d}"

        config = HOTEL_CONFIG[row["hotel"]]

        customer_id = f"CUS{source_index + 1:06d}"

        if invalid_mask.loc[source_index]:
            rejection_records.append(
                {
                    "source_file": SOURCE_FILE.name,
                    "source_row_number": source_row_number,
                    "booking_id": booking_id,
                    "reason": rejection_reasons.loc[source_index],
                    "raw_adr": (
                        None
                        if pd.isna(row["adr"])
                        else Decimal(str(row["adr"]))
                    ),
                    "rejected_at": datetime.now(timezone.utc),
                }
            )
            continue

        created_at = pd.Timestamp(
            row["booking_date"]
        ).tz_localize("UTC").to_pydatetime()

        status_date = pd.to_datetime(
            row["reservation_status_date"],
            errors="coerce",
        )

        if pd.isna(status_date):
            updated_at = created_at
        else:
            status_date = status_date.tz_localize("UTC").to_pydatetime()
            updated_at = max(created_at, status_date)

        customer_records.append(
            {
                "customer_id": customer_id,
                "tenant_id": config["tenant_id"],
                "country": (
                    None
                    if pd.isna(row["country"])
                    else str(row["country"])
                ),
                "customer_type": (
                    None
                    if pd.isna(row["customer_type"])
                    else str(row["customer_type"])
                ),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

        booking_records.append(
            {
                "booking_id": booking_id,
                "tenant_id": config["tenant_id"],
                "property_id": config["property_id"],
                "customer_id": customer_id,
                "booking_date": row["booking_date"].date(),
                "arrival_date": row["arrival_date"].date(),
                "departure_date": row["departure_date"].date(),
                "adults": int(row["adults"]),
                "children": int(row["children"]),
                "room_nights": int(row["room_nights"]),
                "adr": Decimal(str(row["adr"])),
                "market_segment": (
                    None
                    if pd.isna(row["market_segment"])
                    else str(row["market_segment"])
                ),
                "status": build_status(row),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    return (
        list(tenants.values()),
        list(properties.values()),
        customer_records,
        booking_records,
        rejection_records,
    )


def insert_in_batches(
    db: Session,
    model,
    records: list[dict],
    batch_size: int = 5000,
) -> None:
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]

        db.execute(
            model.__table__.insert(),
            batch,
        )

        end = min(start + batch_size, len(records))

        print(
            f"Prepared {end}/{len(records)} "
            f"for {model.__tablename__}"
        )

def main() -> None:
    args = parse_args()

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    print(f"Reading source file: {SOURCE_FILE}")

    df = pd.read_csv(SOURCE_FILE)

    print(f"Source rows: {len(df):,}")

    (
        tenants,
        properties,
        customers,
        bookings,
        rejections,
    ) = build_source_records(df)

    print(f"Valid bookings: {len(bookings):,}")
    print(f"Rejected bookings: {len(rejections):,}")

    db = SessionLocal()

    try:
        if args.reset:
            print("Resetting source tables...")
            reset_database(db)

        insert_in_batches(db, Tenant, tenants)
        insert_in_batches(db, Property, properties)
        insert_in_batches(db, Customer, customers)
        insert_in_batches(db, Booking, bookings)
        insert_in_batches(db, BookingRejection, rejections)
        db.commit()
        
        print("Source load completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()