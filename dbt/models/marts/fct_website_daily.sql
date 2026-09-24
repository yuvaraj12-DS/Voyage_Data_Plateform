with session_metrics as (

    select
        date(session_start) as date,
        tenant_id,
        source,
        medium,
        campaign_id,

        count(*)                             as sessions,
        sum(engaged_session)                 as engaged_sessions,
        sum(page_view_count)                 as page_views,
        sum(event_count)                     as events,
        sum(search_count)                    as searches,
        sum(property_view_count)             as property_views,
        sum(booking_start_count)            as booking_starts,
        sum(conversion_count)                as conversions,
        round(sum(conversion_value), 2)      as conversion_value,

        try_divide(
            sum(conversion_count),
            count(*)
        ) as conversion_rate

    from {{ ref('fct_web_session') }}
    group by
        date(session_start),
        tenant_id,
        source,
        medium,
        campaign_id

),

campaign_lookup as (

    select
        campaign_id,
        campaign_name,
        channel,
        campaign_type
    from {{ ref('stg_campaigns') }}

)

select
    sm.date,
    sm.tenant_id,
    sm.source,
    sm.medium,
    sm.campaign_id,

    sm.sessions,
    sm.engaged_sessions,
    sm.page_views,
    sm.events,
    sm.searches,
    sm.property_views,
    sm.booking_starts,
    sm.conversions,
    sm.conversion_value,
    sm.conversion_rate,

    cl.campaign_name,
    cl.channel,
    cl.campaign_type

from session_metrics sm
left join campaign_lookup cl
    on sm.campaign_id = cl.campaign_id