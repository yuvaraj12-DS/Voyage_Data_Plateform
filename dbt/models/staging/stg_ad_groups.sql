select
    ad_group_id,
    campaign_id,
    tenant_id,
    ad_group_name,
    status,
    created_at,
    updated_at

from {{ source('voyage_silver', 'dim_ad_group') }}