"""Read-only checks for one day's appended website analytics."""

import argparse
from datetime import date, datetime, time, timedelta, timezone

from api.app.database import SessionLocal
from api.app.models.web_event import WebEvent
from api.app.models.web_page_view import WebPageView
from api.app.models.web_session import WebSession


MIN_PURCHASES = 5
MAX_PURCHASES = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check website analytics rows for a UTC activity date."
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now(timezone.utc).date(),
        help="UTC activity date in YYYY-MM-DD format (default: today in UTC).",
    )
    return parser.parse_args()


def rows_for_day(db, model, timestamp_column, day_start, next_day):
    return (
        db.query(model)
        .filter(timestamp_column >= day_start, timestamp_column < next_day)
        .all()
    )


def main() -> int:
    target_date = parse_args().date
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    next_day = day_start + timedelta(days=1)
    db = SessionLocal()

    try:
        sessions = rows_for_day(
            db, WebSession, WebSession.session_start, day_start, next_day
        )
        page_views = rows_for_day(
            db, WebPageView, WebPageView.page_viewed_at, day_start, next_day
        )
        events = rows_for_day(
            db, WebEvent, WebEvent.event_timestamp, day_start, next_day
        )

        purchases = [
            event for event in events if event.event_name == "purchase"
        ]
        all_rows = sessions + page_views + events
        updated_timestamps = [row.updated_at for row in all_rows]
        zero_microsecond_rows = [
            row
            for row in all_rows
            if row.updated_at is None or row.updated_at.microsecond == 0
        ]
        sessions_ending_outside_date = [
            session
            for session in sessions
            if not day_start <= session.session_end < next_day
        ]
        purchases_without_value = [
            event for event in purchases if event.event_value is None
        ]

        print(f"Website analytics check for UTC date {target_date}")
        print(f"  web_sessions: {len(sessions)}")
        print(f"  web_page_views: {len(page_views)}")
        print(f"  web_events: {len(events)}")
        print(f"  purchase events: {len(purchases)}")

        if updated_timestamps:
            print(
                "  updated_at range: "
                f"{min(updated_timestamps).isoformat()} to "
                f"{max(updated_timestamps).isoformat()}"
            )
        else:
            print("  updated_at range: no rows")

        problems = []
        if not MIN_PURCHASES <= len(purchases) <= MAX_PURCHASES:
            problems.append(
                f"purchase count must be {MIN_PURCHASES}-{MAX_PURCHASES}"
            )
        if zero_microsecond_rows:
            problems.append(
                f"{len(zero_microsecond_rows)} row(s) have no updated_at "
                "microseconds"
            )
        if sessions_ending_outside_date:
            problems.append(
                f"{len(sessions_ending_outside_date)} session(s) end outside "
                "the target date"
            )
        if purchases_without_value:
            problems.append(
                f"{len(purchases_without_value)} purchase event(s) have no value"
            )

        if problems:
            print("  RESULT: FAILED")
            for problem in problems:
                print(f"  - {problem}")
            return 1

        print("  RESULT: PASSED")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
