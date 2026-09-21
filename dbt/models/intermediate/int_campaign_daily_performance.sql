with performance as (

    select
        metric_id,
        date,
        tenant_id,
        campaign_id,
        impressions,
        clicks,
        spend,
        conversions,
        revenue,
        updated_at

    from {{ ref('stg_campaign_daily_metrics') }}

),

campaigns as (

    select
        campaign_id,
        campaign_name,
        tenant_id,
        channel,
        campaign_type,
        objective,
        status,
        start_date,
        end_date

    from {{ ref('stg_campaigns') }}

),

final as (

    select
        p.metric_id,
        p.date,
        p.tenant_id,
        p.campaign_id,

        c.campaign_name,
        c.channel,
        c.campaign_type,
        c.objective,
        c.status as campaign_status,

        p.impressions,
        p.clicks,
        p.spend,
        p.conversions,
        p.revenue,

        round(
            try_divide(
                cast(p.clicks as double),
                p.impressions
            ),
            4
        ) as ctr,

        round(
            try_divide(
                cast(p.spend as double),
                p.clicks
            ),
            4
        ) as cpc,

        round(
            try_divide(
                cast(p.conversions as double),
                p.clicks
            ),
            4
        ) as conversion_rate,

        round(
            try_divide(
                cast(p.revenue as double),
                p.spend
            ),
            4
        ) as roas,

        p.updated_at

    from performance p

    left join campaigns c
        on p.campaign_id = c.campaign_id
        and p.tenant_id = c.tenant_id

)

select *
from final