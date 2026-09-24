select
    campaign_id,
    session_id,
    tenant_id,
    user_id,
    device,
    country,
    landing_page,
    medium,
    source,
    session_start,
    session_end,
    updated_at
from {{ source('voyage_silver', 'fact_web_session') }}