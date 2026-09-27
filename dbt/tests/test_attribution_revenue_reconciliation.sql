with attributed as (

    select
        booking_id,
        attribution_model,
        round(
            sum(attributed_net_revenue),
            2
        ) as attributed_net_revenue

    from {{ ref('fct_marketing_attribution') }}

    group by
        booking_id,
        attribution_model

),

source_bookings as (

    select
        booking_id,
        round(net_revenue, 2) as net_revenue

    from {{ ref('stg_marketing_bookings') }}

)

select
    a.booking_id,
    a.attribution_model,
    a.attributed_net_revenue,
    s.net_revenue,
    round(
        a.attributed_net_revenue - s.net_revenue,
        2
    ) as difference

from attributed a

inner join source_bookings s
    on a.booking_id = s.booking_id

where abs(
    round(
        a.attributed_net_revenue - s.net_revenue,
        2
    )
) > 0.01