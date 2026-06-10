# Plan: Carrier, Shipment, and Delivery Data

> Created: 2026-06-09
> Status: ✅ Done (2026-06-10)
> Origin: `analytics_improvement_opportunities.md` § Carrier, Shipment, and Delivery Data

## Objective

Measure end-to-end fulfillment including carrier performance and customer delivery, not just internal order processing.

## What this unlocks

- Carrier performance ranking
- Average delivery time (shipped → delivered)
- On-time delivery rate vs promised date
- Delivery failure / return-to-sender rate
- Delivery delay alerts
- SLA by carrier / channel / region

## Data needed

- `fact_shipments` with: tracking number, carrier, shipped_at, delivered_at, promised_date, carrier status events
- `dim_carriers` dimension
- Return-to-sender events
- Carrier API or platform export (GHN, GHTK, Shopee Express, etc.)

## Current state

- `fact_shipments` does not exist
- `fact_orders.first_shipped_at` available — covers internal processing time only
- Logistics Operations dashboard (existing) covers created→shipped, not shipped→delivered

## Implementation steps

- [x] Identify carrier data source — shipment data embedded in `payload.fulfillments[].shipment` (no external API needed)
- [x] Add `shipment_status` + `delivered_at` to `std_fulfillments` (sourced from `$.shipment.status`, `$.shipment.modified_on`)
- [x] Fix status mapping: Sapo uses `received`/`fulfilled` not `success`/`shipping`
- [x] Enrich `fact_fulfillments` with `shipment_status`, `delivered_at`, `days_to_deliver`, `is_delivered`
- [x] Update `schema.yml` — document new columns
- [ ] Build `dim_carriers` dimension (carrier_key, carrier_name, carrier_code) — deferred, carrier_id currently an opaque ID
- [ ] Add delivery SLA tab to Logistics Operations dashboard
- [ ] Add carrier performance ranking card

## Decisions

- `fact_shipments` not created — `fact_fulfillments` already has same grain (`fulfillment_id`); shipment fields added there instead (DRY)
- External carrier API (GHN/GHTK) not needed — `$.shipment.*` in order payload has sufficient data for SLA metrics

## Dependency

Independent of other plans. Can be done after internal logistics dashboard is stable.
