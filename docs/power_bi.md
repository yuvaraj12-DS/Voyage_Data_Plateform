# Power BI Business Intelligence

## Objective

Expose the trusted dbt analytical marts through a Power BI semantic model
and provide business-facing analytics for marketing, website funnel,
attribution, and historical booking performance.

## Data Source

Power BI connects to Databricks and consumes only analytical dbt models.

Raw, Bronze, Silver, staging, and intermediate models are not exposed
directly to report users.

## Marketing Analytics

The marketing report covers:

- spend
- impressions
- clicks
- CTR
- CPC
- website sessions
- conversions
- bookings
- gross booking value
- net revenue
- ROAS

## Attribution

The report supports:

- first-click
- last-click
- linear

Attribution revenue is based on the synthetic 2026 marketing transaction
domain.

## Historical Booking Analytics

The historical booking pages use the real Kaggle Hotel Booking Demand
source, representing the 2014–2017 booking domain.

A single stray zero-booking record dated 2013 was excluded as non-representative; the effective data range is 18-03-2014 to 31-08-2017. Two apparent volume spikes (Oct 2014, Jul 2015) were investigated and traced to legitimate group-block reservations released/cancelled in bulk at one property — confirmed against source booking data, not a data quality issue.

This domain is intentionally kept separate from the synthetic 2026 marketing
journey.

## Data Modeling

Power BI uses a star-schema approach with shared dimensions for:

- date
- tenant
- campaign
- property
- customer

and analytical fact tables for marketing, website, attribution, and
historical booking metrics.

'dim_customer' is intentionally unconnected to any fact table, since no fact carries a 'customer_id' — it exists as a standalone lookup for customer-level exploration and does not participate in cross-filtering.

## Validation

Power BI totals were compared against dbt analytical marts to confirm that
the BI layer does not change business metrics.