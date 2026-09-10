from sqlalchemy import func, update
from sqlalchemy.orm import Session

from api.app.database import engine
from api.app.models import Customer


CUSTOMER_ID = "CUS073716"


with Session(engine) as db:
    customer = db.get(Customer, CUSTOMER_ID)

    if customer is None:
        raise RuntimeError(f"Customer {CUSTOMER_ID} was not found.")

    before = customer.updated_at

    db.execute(
        update(Customer)
        .where(Customer.customer_id == CUSTOMER_ID)
        .values(updated_at=func.now())
    )

    db.commit()

    customer = db.get(Customer, CUSTOMER_ID)

    print(f"Customer ID: {CUSTOMER_ID}")
    print(f"Before updated_at: {before}")
    print(f"After updated_at:  {customer.updated_at}")