select
    date,
    tenant_id,
    campaign_id,
    count(*) as record_count

from {{ ref('stg_campaign_daily_metrics') }}

group by
    date,
    tenant_id,
    campaign_id

having count(*) > 1