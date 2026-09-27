# Phase 8 — Cross-Domain Funnel and Marketing Attribution

## Objective

Connect the synthetic 2026 marketing, website, conversion, and transaction
domains into an end-to-end travel marketing funnel.

The resulting analytical journey is:

Campaign → Website Session → Purchase → Booking → Revenue

## Synthetic Transaction Bridge

Website `purchase` events are used as the source for synthetic 2026 marketing
bookings.

Each purchase event generates exactly one marketing booking through
`conversion_id`.

This creates an explicit cross-domain relationship without inventing joins
between unrelated historical data.

## Historical Booking Domain

The original Kaggle Hotel Booking Demand dataset remains the historical
operational booking domain and contains real historical booking data from
2014–2017.

Those records are not joined to the synthetic 2026 marketing journey because
there is no valid session, transaction, or booking relationship between the
two periods.

## Attribution

Marketing attribution uses a 30-day lookback window.

Supported models:

- first-click
- last-click
- linear

Attribution is based on synthetic website sessions that contain a
non-null `campaign_id`.

## Funnel

The final campaign-level funnel contains:

- impressions
- clicks
- spend
- website sessions
- engagement
- website conversions
- attributed bookings
- gross booking value
- net revenue
- cost per booking
- ROAS

The final funnel uses last-click attribution for campaign-level booking and
revenue metrics.

The detailed attribution mart retains first-click, last-click, and linear
models separately.

## Data Quality

Validation covers:

- conversion-to-booking uniqueness
- booking referential integrity
- campaign integrity
- attribution weight reconciliation
- revenue reconciliation
- funnel grain
- metric validity
- source-to-model reconciliation