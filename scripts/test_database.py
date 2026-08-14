from sqlalchemy import select

from api.app.database import SessionLocal
from api.app.models import Tenant


def main() -> None:
    db = SessionLocal()

    try:
        statement = select(Tenant)

        tenants = db.scalars(statement).all()

        for tenant in tenants:
            print(
                tenant.tenant_id,
                tenant.tenant_name,
                tenant.country,
                tenant.currency,
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()