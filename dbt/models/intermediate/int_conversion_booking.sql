with purchase_events as (

    select
        event_id as conversion_id,
        session_id,
        tenant_id,
        event_timestamp as conversion_timestamp

    from {{ source('voyage_silver', 'fact_web_event') }}
    where event_name = 'purchase'

),

marketing_bookings as (

    select
        booking_id,
        conversion_id,
        tenant_id,
        session_id,
        user_id,
        booking_date,
        property_id,
        booking_status,
        gross_booking_value,
        net_revenue

    from {{ ref('stg_marketing_bookings') }}

)

select
    pe.conversion_id,
    mb.booking_id,
    mb.tenant_id,
    mb.session_id,
    mb.user_id,
    pe.conversion_timestamp,
    mb.booking_date,
    mb.property_id,
    mb.booking_status,
    mb.gross_booking_value,
    mb.net_revenue

from purchase_events pe
inner join marketing_bookings mb
    on pe.conversion_id = mb.conversion_id