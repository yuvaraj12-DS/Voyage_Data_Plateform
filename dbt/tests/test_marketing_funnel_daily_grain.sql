select
    date,
    tenant_id,
    campaign_id,
    count(*) as record_count

from {{ ref('fct_marketing_funnel_daily') }}

group by
    date,
    tenant_id,
    campaign_id

having count(*) > 1