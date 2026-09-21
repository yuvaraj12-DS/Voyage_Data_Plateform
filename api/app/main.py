from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.routes import (
    ad_groups,
    ads,
    bookings,
    campaigns,
    customers,
    campaign_performance,
    properties,
    tenants,
)


app = FastAPI(
    title="Voyage Booking API",
    version="1.0.0",
)


app.include_router(bookings.router)
app.include_router(customers.router)
app.include_router(properties.router)
app.include_router(tenants.router)
app.include_router(campaigns.router)
app.include_router(ad_groups.router)
app.include_router(ads.router)
app.include_router(campaign_performance.router)

@app.get("/health")
def health(
    db: Session = Depends(get_db),
):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "ok",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable.",
        ) from exc