with date_range as (

    select
        explode(
            sequence(
                to_date('2013-01-01'),
                to_date('2027-12-31'),
                interval 1 day
            )
        ) as date_day

),

final as (

    select
        date_day,
        year(date_day) as year,
        quarter(date_day) as quarter,
        month(date_day) as month,
        monthname(date_day) as month_name,
        weekofyear(date_day) as week_of_year,
        dayofmonth(date_day) as day_of_month,
        dayofweek(date_day) as day_of_week,
        date_format(date_day, 'EEEE') as day_name,

        case
            when dayofweek(date_day) in (1, 7) then true
            else false
        end as is_weekend

    from date_range

)

select *
from final