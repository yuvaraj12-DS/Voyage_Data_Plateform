select *
from {{ ref('dim_customer') }}
where
    booking_count < 0
    or completed_booking_count < 0
    or cancelled_booking_count < 0
    or confirmed_booking_count < 0
    or total_room_nights < 0
    or estimated_completed_booking_value < 0