with bookings as (

    select
        booking_id,
        customer_id,
        tenant_id,
        booking_date,
        room_nights,
        adr,
        status

    from {{ ref('stg_bookings') }}

),

customer_booking_summary as (

    select
        customer_id,
        tenant_id,

        count(*) as booking_count,

        count(
            case
                when status = 'COMPLETED' then 1
            end
        ) as completed_booking_count,

        count(
            case
                when status = 'CANCELLED' then 1
            end
        ) as cancelled_booking_count,

        count(
            case
                when status = 'CONFIRMED' then 1
            end
        ) as confirmed_booking_count,

        sum(room_nights) as total_room_nights,

        sum(
            case
                when status = 'COMPLETED'
                    then adr * room_nights
                else 0
            end
        ) as estimated_completed_booking_value,

        min(booking_date) as first_booking_date,

        max(booking_date) as latest_booking_date

    from bookings

    group by
        customer_id,
        tenant_id

)

select *
from customer_booking_summary