select
    date,
    tenant_id,
    campaign_id,
    count(*) as record_count

from {{ ref('int_campaign_daily_performance') }}

group by
    date,
    tenant_id,
    campaign_id

having count(*) > 1