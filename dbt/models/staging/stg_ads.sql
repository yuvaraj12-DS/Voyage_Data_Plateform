select
    ad_id,
    ad_group_id,
    campaign_id,
    tenant_id,
    ad_name,
    creative_type,
    status,
    created_at,
    updated_at

from {{ source('voyage_silver', 'dim_ad') }}