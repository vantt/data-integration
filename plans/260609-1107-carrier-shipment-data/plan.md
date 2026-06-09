# Plan: Carrier, Shipment, and Delivery Data

> Created: 2026-06-09
> Status: ❌ Not started
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

- [ ] Identify carrier data source (GHN/GHTK API, Sapo shipping integration, manual export)
- [ ] Build `dim_carriers` dimension (carrier_key, carrier_name, carrier_code)
- [ ] Build ingestion for shipment tracking events (per-tracking-number status history)
- [ ] Create `fact_shipments` mart: grain (tracking_number, event_type)
- [ ] Create `int_shipment_sla` with computed fields: days_to_deliver, is_on_time, is_failed
- [ ] Add delivery SLA tab to Logistics Operations dashboard
- [ ] Add carrier performance ranking card

## Dependency

Independent of other plans. Can be done after internal logistics dashboard is stable.
