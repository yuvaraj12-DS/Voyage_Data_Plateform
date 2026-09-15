select *
from {{ ref('fct_booking_daily') }}
where
    booking_count < 0
    or completed_booking_count < 0
    or confirmed_booking_count < 0
    or cancelled_booking_count < 0
    or room_nights < 0
    or cancellation_rate < 0
    or cancellation_rate > 1