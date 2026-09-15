with booking_summary as (

    select
        tenant_id,
        count(*) as booking_count,
        sum(room_nights) as total_room_nights,
        sum(case when status = 'COMPLETED' then 1 else 0 end) as completed_booking_count,
        sum(case when status = 'CANCELLED' then 1 else 0 end) as cancelled_booking_count,
        sum(case when status = 'CONFIRMED' then 1 else 0 end) as confirmed_booking_count,
        sum(
            case
                when status = 'COMPLETED' then adr * room_nights
                else 0
            end
        ) as estimated_completed_booking_value,
        min(booking_date) as first_booking_date,
        max(booking_date) as last_booking_date

    from {{ ref('stg_bookings') }}

    group by tenant_id

),

final as (

    select
        t.tenant_id,
        t.tenant_name,

        coalesce(b.booking_count, 0) as booking_count,
        coalesce(b.total_room_nights, 0) as total_room_nights,
        coalesce(b.completed_booking_count, 0) as completed_booking_count,
        coalesce(b.cancelled_booking_count, 0) as cancelled_booking_count,
        coalesce(b.confirmed_booking_count, 0) as confirmed_booking_count,
        coalesce(b.estimated_completed_booking_value, 0) as estimated_completed_booking_value,
        b.first_booking_date,
        b.last_booking_date,

        case
            when coalesce(b.booking_count, 0) > 0
                then round(
                    cast(b.completed_booking_count as double) / b.booking_count,
                    4
                )
            else 0
        end as completion_rate,

        case
            when coalesce(b.booking_count, 0) > 0
                then round(
                    cast(b.cancelled_booking_count as double) / b.booking_count,
                    4
                )
            else 0
        end as cancellation_rate

    from {{ ref('stg_tenants') }} t
    left join booking_summary b
        on t.tenant_id = b.tenant_id

)

select *
from final