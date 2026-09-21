select *
from {{ ref('stg_campaign_daily_metrics') }}

where impressions < 0
   or clicks < 0
   or conversions < 0
   or spend < 0
   or revenue < 0
   or clicks > impressions
   or conversions > clicks