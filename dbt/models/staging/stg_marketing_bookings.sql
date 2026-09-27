select
    booking_id,
    tenant_id,
    property_id,
    user_id,
    conversion_id,
    session_id,
    booking_status,
    booking_date,
    gross_booking_value,
    net_revenue,
    created_at,
    updated_at

from {{ source('voyage_silver', 'fact_marketing_booking') }}