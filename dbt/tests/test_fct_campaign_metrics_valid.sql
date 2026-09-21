select *
from {{ ref('fct_campaign_daily') }}

where impressions < 0
   or clicks < 0
   or conversions < 0
   or spend < 0
   or revenue < 0
   or clicks > impressions
   or conversions > clicks
   or ctr < 0
   or ctr > 1
   or cpc < 0
   or conversion_rate < 0
   or conversion_rate > 1
   or roas < 0