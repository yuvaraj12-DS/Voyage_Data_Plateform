select *
from {{ ref('fct_website_daily') }}
where sessions < 0
   or engaged_sessions < 0
   or page_views < 0
   or events < 0
   or searches < 0
   or property_views < 0
   or booking_starts < 0
   or conversions < 0
   or conversion_value < 0
   or engaged_sessions > sessions
   or conversions > sessions
   or conversion_rate < 0
   or conversion_rate > 1