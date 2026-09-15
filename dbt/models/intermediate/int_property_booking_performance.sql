with bookings as (

    select
        booking_id,
        tenant_id,
        property_id,
        booking_date,
        room_nights,
        adr,
        status

    from {{ ref('stg_bookings') }}

),

property_performance as (

    select
        booking_date,
        tenant_id,
        property_id,

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

        sum(room_nights) as room_nights,

        sum(
            case
                when status = 'COMPLETED'
                    then adr * room_nights
                else 0
            end
        ) as estimated_completed_booking_value,

        avg(
            case
                when status = 'COMPLETED'
                    then adr
            end
        ) as average_completed_adr

    from bookings

    group by
        booking_date,
        tenant_id,
        property_id

)

select
    booking_date,
    tenant_id,
    property_id,
    booking_count,
    completed_booking_count,
    cancelled_booking_count,
    confirmed_booking_count,
    room_nights,
    estimated_completed_booking_value,
    average_completed_adr,

    case
        when booking_count > 0
            then cancelled_booking_count * 1.0 / booking_count
        else 0
    end as cancellation_rate

from property_performance