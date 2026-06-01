# Plan — `detailView` Order & Customer Insight App

**Created:** 2026-05-29 22:23 | **Branch:** main | **Status:** AWAITING APPROVAL (build gated)

## Goal
Lightweight read-only web app surfacing the COMPLETE insight the OLAP warehouse holds
for ONE order and ONE customer. Solves info fragmentation across Sapo/management apps:
warehouse already computes economics, RFM, segmentation that source apps can't show.

## Scope (v1)
- Two detail screens: **Order Detail** (`/orders/{order_code}`), **Customer Detail** (`/customers/{customer_id}`).
- Floating header w/ search box → resolve order code / customer id|phone → open detail page.
- Reads `app_data/data_lake/serving/olap.duckdb` `read_only=True` (same DB Metabase reads, zero lock risk — empirically verified).
- No auth. LAN-only behind Caddy (`detail.lan.fwg.vn`). Runs as a Docker Compose service like metabase/rill.

## Decisions (confirmed)
| # | Decision | Choice |
|---|---|---|
| 1 | Stack | FastAPI + Jinja2 + **HTMX now** (tab/search partial loads). No Node build. |
| 2 | App name | folder `detailView/`; docker service/container `detail_view`; Caddy `detail.lan.fwg.vn`; port `3005:8000` |
| 3 | Architecture | **Hexagonal** — pure domain ⟂ ports ⟂ adapters (DuckDB driven, Web/JSON driving) |
| 4 | DB access | `read_only=True`, mount `:ro`, query `fact_*`/`dim_*`/`mart_*` only (hide `int_*`) |
| 5 | Frontend design | skeleton only now (semantic HTML + CSS vars); `claude design` styles later |

## Phases
- **A — Discover** ✅ DONE — 3 schema/integration reports in `plans/reports/researcher-0{1,2,3}-*`.
- **B — Design** ✅ THIS PACKAGE — [PRD.md](./PRD.md) + [UI_SPECS.md](./UI_SPECS.md).
- **C — Build** ⛔ AWAITING APPROVAL:
  - C1. Scaffold `detailView/` hexagonal skeleton + domain models + ports.
  - C2. DuckDB outbound adapter (connection + order/customer repositories + SQL).
  - C3. Application services (get order/customer detail, search, lazy tab loaders).
  - C4. FastAPI inbound web adapter: pages + HTMX tab partials + search; optional JSON API.
  - C5. Frontend skeleton: floating header, 2/1 two-column layout, tab shells (unstyled).
  - C6. Docker: `Dockerfile.detailview` + compose service + `:ro` mount + Caddy labels.
  - C7. Monorepo registration: README, docs/README, AGENTS.md, docs/architecture/overview, .env.docker.
  - C8. Smoke test (real DB), basic unit tests on domain/services.

## Data caveats the UI MUST honor (from research)
- US orders: `fact_orders.net_revenue=0` → use `fact_us_shipment_economics` (flag "US CrossBorder").
- COGS missing ~35% → show `has_cogs` flag; margin "unverified" when false.
- Returns NOT in order P&L (`return_amount` reference-only).
- `date_key`/TIMESTAMPTZ are ICT (Asia/Ho_Chi_Minh).
- Shopee fees only; non-Shopee fee cols NULL.
- Status timeline = RETAIL only; `acquisition_source` always NULL; `customer_code` not in serving (search by id/phone/email).

## Parallelization plan for Build (Stage C)
- dev-A (backend/domain+adapter+services): owns `detailView/app/domain/*`, `application/*`, `adapters/outbound/*`, `tests/*`.
- dev-B (web/frontend skeleton): owns `adapters/inbound/web/*` (routes, templates, static).
- lead (me): composition root, Dockerfile, docker-compose + monorepo registration (shared/infra files) + integration.
- File-ownership boundaries prevent conflicts; api contract = application service signatures (defined C1).

## Open questions (non-blocking; default chosen)
1. Expose a JSON API (`/api/...`) alongside HTML? **Default: yes, thin** (cheap, future SPA-ready, hexagonal-clean).
2. Show non-RETAIL customers' Status Timeline tab? **Default: hide tab w/ "RETAIL only" notice** for others.
3. Surface `int_*` intermediates (e.g. US line prices, Shopee fee detail)? **Default: no** (end-user marts only).
