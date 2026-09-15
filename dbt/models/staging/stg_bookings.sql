select
    booking_id,
    tenant_id,
    property_id,
    customer_id,
    booking_date,
    arrival_date,
    departure_date,
    adults,
    children,
    room_nights,
    adr,
    market_segment,
    status,
    created_at,
    updated_at

from {{ source('voyage_silver', 'fact_booking') }}