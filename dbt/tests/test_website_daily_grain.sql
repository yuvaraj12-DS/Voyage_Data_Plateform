select
    date,
    tenant_id,
    source,
    medium,
    campaign_id,
    count(*) as record_count
from {{ ref('fct_website_daily') }}
group by
    date,
    tenant_id,
    source,
    medium,
    campaign_id
having count(*) > 1