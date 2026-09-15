select
    customer_id,
    tenant_id,
    country,
    customer_type,
    created_at,
    updated_at

from {{ source('voyage_silver', 'dim_customer') }}