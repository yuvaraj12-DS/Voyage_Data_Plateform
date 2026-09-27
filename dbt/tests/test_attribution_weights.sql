select
    booking_id,
    attribution_model,
    round(sum(attribution_weight), 6) as total_weight
from {{ ref('fct_marketing_attribution') }}
group by
    booking_id,
    attribution_model
having abs(
    round(sum(attribution_weight), 6) - 1.0
) > 0.000001