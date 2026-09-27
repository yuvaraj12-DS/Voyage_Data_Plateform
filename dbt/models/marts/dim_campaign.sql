select
    campaign_id,
    tenant_id,
    campaign_name,
    channel,
    campaign_type,
    objective,
    status as campaign_status,
    start_date,
    end_date,
    created_at,
    updated_at
from {{ ref('stg_campaigns') }}