select
    date,
    tenant_id,
    campaign_id,

    sum(sessions) as website_sessions,

    sum(engaged_sessions) as engaged_sessions,

    sum(page_views) as website_page_views,

    sum(searches) as searches,

    sum(property_views) as property_views,

    sum(booking_starts) as booking_starts,

    sum(conversions) as website_conversions,

    round(
        sum(conversion_value),
        2
    ) as website_conversion_value

from {{ ref('fct_website_daily') }}

where campaign_id is not null

group by
    date,
    tenant_id,
    campaign_id