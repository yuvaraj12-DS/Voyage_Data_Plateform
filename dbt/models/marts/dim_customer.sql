select
    c.customer_id,
    c.tenant_id,
    c.country,
    c.customer_type,
    c.created_at,
    c.updated_at,

    coalesce(b.booking_count, 0) as booking_count,
    coalesce(b.completed_booking_count, 0) as completed_booking_count,
    coalesce(b.cancelled_booking_count, 0) as cancelled_booking_count,
    coalesce(b.confirmed_booking_count, 0) as confirmed_booking_count,
    coalesce(b.total_room_nights, 0) as total_room_nights,
    coalesce(
        b.estimated_completed_booking_value,
        0
    ) as estimated_completed_booking_value,

    b.first_booking_date,
    b.latest_booking_date,

    case
        when coalesce(b.booking_count, 0) > 1
            then true
        else false
    end as is_repeat_customer

from {{ ref('stg_customers') }} c

left join {{ ref('int_customer_booking_summary') }} b
    on c.customer_id = b.customer_id
    and c.tenant_id = b.tenant_id