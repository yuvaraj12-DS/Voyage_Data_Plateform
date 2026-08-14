from datetime import datetime, timezone

from api.app.database import SessionLocal
from api.app.models import Tenant


def main() -> None:
    db = SessionLocal()

    try:
        tenant = Tenant(
            tenant_id="TENANT002",
            tenant_name="Ibiza Travel Co",
            country="ES",
            currency="EUR",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db.add(tenant)
        db.commit()

        print("TENANT002 created successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()