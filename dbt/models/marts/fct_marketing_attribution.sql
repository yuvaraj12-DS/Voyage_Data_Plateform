with matched as (

    select *
    from {{ ref('int_booking_touchpoints') }}

),

first_click as (

    select
        booking_id,
        conversion_id,
        tenant_id,
        booking_session_id,
        user_id,
        property_id,
        booking_date,
        conversion_timestamp,
        booking_status,
        gross_booking_value,
        net_revenue,

        touchpoint_session_id,
        touchpoint_timestamp,
        campaign_id,
        source,
        medium,

        'first_click' as attribution_model,

        cast(1.0 as double) as attribution_weight,

        gross_booking_value as raw_gross_allocation,
        net_revenue as raw_net_allocation

    from matched
    where first_touch_rank = 1

),

last_click as (

    select
        booking_id,
        conversion_id,
        tenant_id,
        booking_session_id,
        user_id,
        property_id,
        booking_date,
        conversion_timestamp,
        booking_status,
        gross_booking_value,
        net_revenue,

        touchpoint_session_id,
        touchpoint_timestamp,
        campaign_id,
        source,
        medium,

        'last_click' as attribution_model,

        cast(1.0 as double) as attribution_weight,

        gross_booking_value as raw_gross_allocation,
        net_revenue as raw_net_allocation

    from matched
    where last_touch_rank = 1

),

linear_base as (

    select
        booking_id,
        conversion_id,
        tenant_id,
        booking_session_id,
        user_id,
        property_id,
        booking_date,
        conversion_timestamp,
        booking_status,
        gross_booking_value,
        net_revenue,

        touchpoint_session_id,
        touchpoint_timestamp,
        campaign_id,
        source,
        medium,

        'linear' as attribution_model,

        cast(
            1.0 / eligible_touchpoint_count
            as decimal(18, 12)
        ) as attribution_weight,

        cast(
            gross_booking_value
            * (1.0 / eligible_touchpoint_count)
            as decimal(24, 12)
        ) as preliminary_gross_allocation,

        cast(
            net_revenue
            * (1.0 / eligible_touchpoint_count)
            as decimal(24, 12)
        ) as preliminary_net_allocation

    from matched

),

linear_with_totals as (

    select
        *,
        sum(preliminary_gross_allocation) over (
            partition by booking_id
        ) as allocated_gross_total,

        sum(preliminary_net_allocation) over (
            partition by booking_id
        ) as allocated_net_total

    from linear_base

),

linear_final as (

    select
        booking_id,
        conversion_id,
        tenant_id,
        booking_session_id,
        user_id,
        property_id,
        booking_date,
        conversion_timestamp,
        booking_status,
        gross_booking_value,
        net_revenue,

        touchpoint_session_id,
        touchpoint_timestamp,
        campaign_id,
        source,
        medium,

        attribution_model,
        attribution_weight,

        preliminary_gross_allocation
        + case
            when row_number() over (
                partition by booking_id
                order by touchpoint_timestamp desc,
                         touchpoint_session_id desc
            ) = 1
            then gross_booking_value - allocated_gross_total
            else 0
          end as final_gross_allocation,

        preliminary_net_allocation
        + case
            when row_number() over (
                partition by booking_id
                order by touchpoint_timestamp desc,
                         touchpoint_session_id desc
            ) = 1
            then net_revenue - allocated_net_total
            else 0
          end as final_net_allocation

    from linear_with_totals

),

combined as (

    select
        booking_id,
        conversion_id,
        tenant_id,
        booking_session_id,
        user_id,
        property_id,
        booking_date,
        conversion_timestamp,
        booking_status,
        gross_booking_value,
        net_revenue,

        touchpoint_session_id,
        touchpoint_timestamp,
        campaign_id,
        source,
        medium,

        attribution_model,
        attribution_weight,

        raw_gross_allocation as attributed_gross_booking_value,
        raw_net_allocation as attributed_net_revenue

    from first_click

    union all

    select
        booking_id,
        conversion_id,
        tenant_id,
        booking_session_id,
        user_id,
        property_id,
        booking_date,
        conversion_timestamp,
        booking_status,
        gross_booking_value,
        net_revenue,

        touchpoint_session_id,
        touchpoint_timestamp,
        campaign_id,
        source,
        medium,

        attribution_model,
        attribution_weight,

        raw_gross_allocation,
        raw_net_allocation

    from last_click

    union all

    select
        booking_id,
        conversion_id,
        tenant_id,
        booking_session_id,
        user_id,
        property_id,
        booking_date,
        conversion_timestamp,
        booking_status,
        gross_booking_value,
        net_revenue,

        touchpoint_session_id,
        touchpoint_timestamp,
        campaign_id,
        source,
        medium,

        attribution_model,
        attribution_weight,

        final_gross_allocation,
        final_net_allocation

    from linear_final

)

select
    a.booking_id,
    a.conversion_id,
    a.tenant_id,
    a.booking_session_id,
    a.user_id,
    a.property_id,

    a.booking_date,
    a.conversion_timestamp,
    a.booking_status,

    a.gross_booking_value,
    a.net_revenue,

    a.touchpoint_session_id,
    a.touchpoint_timestamp,

    a.campaign_id,

    c.campaign_name,
    c.channel,
    c.campaign_type,
    c.objective,

    a.source,
    a.medium,

    a.attribution_model,
    a.attribution_weight,

    a.attribution_weight as attributed_bookings,

    cast(
        a.attributed_gross_booking_value
        as decimal(18, 8)
    ) as attributed_gross_booking_value,

    cast(
        a.attributed_net_revenue
        as decimal(18, 8)
    ) as attributed_net_revenue,

    30 as lookback_days

from combined a

left join {{ ref('stg_campaigns') }} c
    on a.campaign_id = c.campaign_id
   and a.tenant_id = c.tenant_id