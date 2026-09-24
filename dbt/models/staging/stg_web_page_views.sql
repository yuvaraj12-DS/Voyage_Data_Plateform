select
    page_view_id,
    session_id,
    tenant_id,
    page_path,
    page_title,
    referrer,
    duration_seconds,
    page_viewed_at,
    updated_at
from {{ source('voyage_silver', 'fact_web_page_view') }}
