select
    booking_date,
    tenant_id,
    property_id
from {{ ref('fct_property_daily') }}
group by
    booking_date,
    tenant_id,
    property_id
having count(*) > 1