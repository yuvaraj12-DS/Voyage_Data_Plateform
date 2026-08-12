# Data Dictionary

## Campaign

| Column | Type | Description |
|---|---|---|
| campaign_id | string | Unique campaign identifier |
| campaign_name | string | Human-readable campaign name |
| channel | string | Marketing channel |
| campaign_type | string | Campaign type |
| status | string | Campaign status |
| start_date | date | Campaign start date |
| end_date | date | Campaign end date |

## Campaign Daily Performance

| Column | Type | Description |
|---|---|---|
| campaign_id | string | Campaign identifier |
| date | date | Performance date |
| impressions | integer | Advertisement impressions |
| clicks | integer | Advertisement clicks |
| spend | decimal | Advertising spend |
| conversions | integer | Number of conversions |
| revenue | decimal | Attributed booking revenue |

## Booking

| Column | Type | Description |
|---|---|---|
| booking_id | string | Unique booking identifier |
| hotel | string | Hotel type |
| arrival_date | date | Guest arrival date |
| booking_date | date | Booking creation date |
| lead_time | integer | Days between booking and arrival |
| adults | integer | Number of adults |
| children | integer | Number of children |
| nights | integer | Total stay length |
| market_segment | string | Booking market segment |
| adr | decimal | Average daily rate |
| is_canceled | boolean | Whether booking was cancelled |