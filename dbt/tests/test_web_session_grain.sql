select
    session_id,
    count(*) as record_count
from {{ ref('fct_web_session') }}
group by session_id
having count(*) > 1