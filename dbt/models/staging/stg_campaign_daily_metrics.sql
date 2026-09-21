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

from {{ source('voyage_silver', 'fact_campaign_daily') }}