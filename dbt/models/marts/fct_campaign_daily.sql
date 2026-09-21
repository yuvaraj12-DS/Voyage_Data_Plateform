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
    conversions,
    revenue,

    ctr,
    cpc,
    conversion_rate,
    roas,
    updated_at

from {{ ref('int_campaign_daily_performance') }}