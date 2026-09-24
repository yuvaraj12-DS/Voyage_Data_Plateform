select *
from {{ ref('fct_web_session') }}
where page_view_count < 0
   or event_count < 0
   or search_count < 0
   or property_view_count < 0
   or booking_start_count < 0
   or conversion_count < 0
   or conversion_value < 0
   or session_duration_seconds < 0
   or conversion_count > 1