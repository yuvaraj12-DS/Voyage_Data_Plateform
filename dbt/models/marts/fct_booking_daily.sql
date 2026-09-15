select
    booking_date,
    tenant_id,
    property_id,
    booking_count,
    completed_booking_count,
    confirmed_booking_count,
    cancelled_booking_count,
    room_nights,
    estimated_completed_booking_value,
    average_completed_adr,
    cancellation_rate

from {{ ref('int_booking_daily') }}
