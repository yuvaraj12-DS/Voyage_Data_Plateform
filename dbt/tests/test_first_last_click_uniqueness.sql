select
    booking_id,
    attribution_model,
    count(*) as record_count
from {{ ref('fct_marketing_attribution') }}
where attribution_model in (
    'first_click',
    'last_click'
)
group by
    booking_id,
    attribution_model
having count(*) > 1