select
    campaign_id,
    tenant_id,
    campaign_name,
    channel,
    campaign_type,
    objective,
    status,
    start_date,
    end_date,
    created_at,
    updated_at

from {{ source('voyage_silver', 'dim_campaign') }}