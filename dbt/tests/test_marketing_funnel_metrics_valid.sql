select *
from {{ ref('fct_marketing_funnel_daily') }}

where impressions < 0
   or clicks < 0
   or spend < 0

   or website_sessions < 0
   or engaged_sessions < 0
   or website_page_views < 0
   or searches < 0
   or property_views < 0
   or booking_starts < 0
   or website_conversions < 0

   or bookings < 0
   or gross_booking_value < 0
   or net_revenue < 0

   or engaged_sessions > website_sessions

   or website_conversions > website_sessions

   or gross_booking_value < net_revenue

   or website_conversion_rate < 0
   or website_conversion_rate > 1

   or last_click_roas < 0