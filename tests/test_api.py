from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient

from api.app.config import settings
from api.app.main import app


client = TestClient(app)

HEADERS = {
    "X-API-Key": settings.api_key,
}


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_bookings_require_api_key():
    response = client.get(
        "/api/v1/bookings?page=1&page_size=5"
    )

    assert response.status_code == 401


def test_list_bookings():
    response = client.get(
        "/api/v1/bookings?page=1&page_size=5",
        headers=HEADERS,
    )

    assert response.status_code == 200

    body = response.json()

    assert "data" in body
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert body["total_records"] >= 0


def test_booking_not_found():
    response = client.get(
        "/api/v1/bookings/DOES_NOT_EXIST",
        headers=HEADERS,
    )

    assert response.status_code == 404


def test_future_incremental_filter_returns_empty():
    future_time = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    ).isoformat()

    response = client.get(
        "/api/v1/bookings",
        params={
            "updated_after": future_time,
            "page": 1,
            "page_size": 5,
        },
        headers=HEADERS,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["data"] == []