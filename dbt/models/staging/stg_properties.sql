select
    property_id,
    tenant_id,
    property_name,
    property_type,
    destination,
    created_at,
    updated_at

from {{ source('voyage_silver', 'dim_property') }}