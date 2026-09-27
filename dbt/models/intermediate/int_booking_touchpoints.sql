with bookings as (

    select
        conversion_id,
        booking_id,
        tenant_id,
        session_id as booking_session_id,
        user_id,
        conversion_timestamp,
        booking_date,
        property_id,
        booking_status,
        gross_booking_value,
        net_revenue
    from {{ ref('int_conversion_booking') }}

),

touchpoints as (

    select
        session_id as touchpoint_session_id,
        tenant_id,
        user_id,
        session_start as touchpoint_timestamp,
        campaign_id,
        source,
        medium
    from {{ ref('int_marketing_touchpoints') }}

),

matched as (

    select
        b.conversion_id,
        b.booking_id,
        b.tenant_id,
        b.booking_session_id,
        b.user_id,
        b.conversion_timestamp,
        b.booking_date,
        b.property_id,
        b.booking_status,
        b.gross_booking_value,
        b.net_revenue,

        t.touchpoint_session_id,
        t.touchpoint_timestamp,
        t.campaign_id,
        t.source,
        t.medium,

        row_number() over (
            partition by b.booking_id
            order by
                t.touchpoint_timestamp asc,
                t.touchpoint_session_id asc
        ) as first_touch_rank,

        row_number() over (
            partition by b.booking_id
            order by
                t.touchpoint_timestamp desc,
                t.touchpoint_session_id desc
        ) as last_touch_rank,

        count(*) over (
            partition by b.booking_id
        ) as eligible_touchpoint_count

    from bookings b

    inner join touchpoints t
        on t.tenant_id = b.tenant_id

       and t.touchpoint_timestamp <= b.conversion_timestamp

       and t.touchpoint_timestamp >=
           b.conversion_timestamp - interval 30 days

       and (
            (
                b.user_id is not null
                and t.user_id = b.user_id
            )
            or
            (
                b.user_id is null
                and t.touchpoint_session_id = b.booking_session_id
            )
       )

)

select *
from matched