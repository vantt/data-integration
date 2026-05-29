# detailView — Documentation

| Doc | What it covers |
|---|---|
| [PRD.md](PRD.md) | Problem, goals/non-goals, functional + non-functional requirements, **hexagonal architecture**, data contract, deployment, risks, acceptance criteria |
| [UI_SPECS.md](UI_SPECS.md) | Global shell + floating-header search, 2:1 two-column layout, all tabs mapped to columns, states/badges/caveats, HTMX contract, **§8 ASCII layout mockups** (handoff for `claude design`) |
| [plan.md](plan.md) | Build plan, confirmed decisions, parallelization, data caveats |

## Key data caveats (must be honored by any change)
- **US orders**: `fact_orders.net_revenue = 0` → revenue comes from `fact_us_shipment_economics`.
- **COGS ~65% coverage**: `has_cogs=false` → margin shown "unverified".
- **Returns**: reference-only — NOT subtracted from an order's P&L.
- **Timezone**: all timestamps/`date_key` are ICT (`Asia/Ho_Chi_Minh`).
- **Shopee fees only**; other platforms' fee columns are NULL.
- **Status timeline**: RETAIL customers only. `acquisition_source` always NULL. `customer_code` not in serving (search by id/phone/email).

## Source research (full schema inventory)
- `../../plans/reports/researcher-01-260529-2223-order-schema-inventory.md`
- `../../plans/reports/researcher-02-260529-2223-customer-schema-inventory.md`
- `../../plans/reports/researcher-03-260529-2223-integration-techstack.md`
