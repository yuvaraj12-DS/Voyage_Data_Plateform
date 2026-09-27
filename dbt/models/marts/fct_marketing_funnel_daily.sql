with marketing as (

    select
        date,
        tenant_id,
        campaign_id,
        campaign_name,
        channel,
        campaign_type,
        objective,
        campaign_status,

        impressions,
        clicks,
        spend,

        ctr,
        cpc

    from {{ ref('fct_campaign_daily') }}

),

website as (

    select *
    from {{ ref('int_campaign_website_daily') }}

),

last_click_bookings as (

    select
        booking_date as date,
        tenant_id,
        campaign_id,

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

    where attribution_model = 'last_click'

    group by
        booking_date,
        tenant_id,
        campaign_id

)

select
    m.date,
    m.tenant_id,
    m.campaign_id,

    m.campaign_name,
    m.channel,
    m.campaign_type,
    m.objective,
    m.campaign_status,

    m.impressions,
    m.clicks,
    m.spend,

    coalesce(
        w.website_sessions,
        0
    ) as website_sessions,

    coalesce(
        w.engaged_sessions,
        0
    ) as engaged_sessions,

    coalesce(
        w.website_page_views,
        0
    ) as website_page_views,

    coalesce(
        w.searches,
        0
    ) as searches,

    coalesce(
        w.property_views,
        0
    ) as property_views,

    coalesce(
        w.booking_starts,
        0
    ) as booking_starts,

    coalesce(
        w.website_conversions,
        0
    ) as website_conversions,

    coalesce(
        w.website_conversion_value,
        0
    ) as website_conversion_value,

    coalesce(
        b.attributed_bookings,
        0
    ) as bookings,

    coalesce(
        b.attributed_gross_booking_value,
        0
    ) as gross_booking_value,

    coalesce(
        b.attributed_net_revenue,
        0
    ) as net_revenue,

    m.ctr,
    m.cpc,

    try_divide(
        coalesce(w.website_sessions, 0),
        m.clicks
    ) as click_to_session_rate,

    try_divide(
        coalesce(w.website_conversions, 0),
        coalesce(w.website_sessions, 0)
    ) as website_conversion_rate,

    try_divide(
        coalesce(b.attributed_bookings, 0),
        coalesce(w.website_sessions, 0)
    ) as booking_rate,

    try_divide(
        m.spend,
        coalesce(b.attributed_bookings, 0)
    ) as cost_per_booking,

    try_divide(
        coalesce(b.attributed_net_revenue, 0),
        m.spend
    ) as last_click_roas

from marketing m

left join website w
    on m.date = w.date
   and m.tenant_id = w.tenant_id
   and m.campaign_id = w.campaign_id

left join last_click_bookings b
    on m.date = b.date
   and m.tenant_id = b.tenant_id
   and m.campaign_id = b.campaign_id