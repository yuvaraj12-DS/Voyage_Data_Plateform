select
    booking_date as date,
    tenant_id,
    campaign_id,
    campaign_name,
    channel,
    attribution_model,

    round(
        sum(attributed_bookings),
        6
    ) as attributed_bookings,

    round(
        sum(attributed_gross_booking_value),
        2
    ) as attributed_gross_booking_value,

    round(
        sum(attributed_net_revenue),
        2
    ) as attributed_net_revenue

from {{ ref('fct_marketing_attribution') }}

group by
    booking_date,
    tenant_id,
    campaign_id,
    campaign_name,
    channel,
    attribution_model