select
    p.property_id,
    p.tenant_id,
    p.property_name,
    p.property_type,
    p.destination,
    b.booking_date,
    b.booking_count,
    b.completed_booking_count,
    b.cancelled_booking_count,
    b.confirmed_booking_count,
    b.room_nights,
    b.estimated_completed_booking_value,
    b.average_completed_adr,
    b.cancellation_rate

from {{ ref('stg_properties') }} p

inner join {{ ref('int_property_booking_performance') }} b
    on p.property_id = b.property_id
    and p.tenant_id = b.tenant_id