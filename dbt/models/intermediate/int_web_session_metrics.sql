with sessions as (

    select *
    from {{ ref('stg_web_sessions') }}

),

page_views as (

    select
        session_id,
        count(*) as page_view_count,
        sum(duration_seconds) as total_page_view_seconds
    from {{ ref('stg_web_page_views') }}
    group by session_id

),

events as (

    select
        session_id,
        count(*) as event_count,

        sum(
            case when event_name = 'search_availability'
                 then 1 else 0 end
        ) as search_count,

        sum(
            case when event_name = 'view_property'
                 then 1 else 0 end
        ) as property_view_count,

        sum(
            case when event_name = 'begin_booking'
                 then 1 else 0 end
        ) as booking_start_count,

        sum(
            case when event_name = 'purchase'
                 then 1 else 0 end
        ) as conversion_count,

        sum(
            case
                when event_name = 'purchase'
                then coalesce(event_value, cast(0 as decimal(18, 2)))
                else cast(0 as decimal(18, 2))
            end
        ) as conversion_value

    from {{ ref('stg_web_events') }}
    group by session_id

)

select
    s.session_id,
    s.tenant_id,
    s.user_id,
    s.session_start,
    s.session_end,
    s.source,
    s.medium,
    s.campaign_id,
    s.device,
    s.country,
    s.landing_page,

    coalesce(p.page_view_count, 0) as page_view_count,
    coalesce(p.total_page_view_seconds, 0) as total_page_view_seconds,

    coalesce(e.event_count, 0) as event_count,
    coalesce(e.search_count, 0) as search_count,
    coalesce(e.property_view_count, 0) as property_view_count,
    coalesce(e.booking_start_count, 0) as booking_start_count,
    coalesce(e.conversion_count, 0) as conversion_count,
    coalesce(e.conversion_value, cast(0 as decimal(18, 2))) as conversion_value,

    case
        when coalesce(p.page_view_count, 0) >= 2
          or coalesce(e.event_count, 0) > 0
        then 1
        else 0
    end as engaged_session,

    timestampdiff(second, s.session_start, s.session_end)
        as session_duration_seconds,

    s.updated_at

from sessions s
left join page_views p
    on s.session_id = p.session_id
left join events e
    on s.session_id = e.session_id