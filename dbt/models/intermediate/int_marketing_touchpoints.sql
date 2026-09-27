select
    tenant_id,
    user_id,
    session_id,
    campaign_id,
    source,
    medium,
    session_start

from {{ source('voyage_silver', 'fact_web_session') }}
where campaign_id is not null