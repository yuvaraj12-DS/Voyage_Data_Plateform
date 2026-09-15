select
    tenant_id,
    tenant_name,
    country,
    currency,
    created_at,
    updated_at

from {{ source('voyage_silver', 'dim_tenant') }}