select
    event_id,
    session_id,
    tenant_id,
    event_name,
    try_cast(nullif(trim(event_value), '') as decimal(18, 2)) as event_value,
    page_path,
    event_timestamp,
    updated_at
from {{ source('voyage_silver', 'fact_web_event') }}