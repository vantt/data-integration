# PRD — `detailView`: Order & Customer Insight App

**Owner:** Data Platform | **Date:** 2026-05-29 | **Status:** DONE — implemented and archived 2026-06-09

---

## 1. Problem & Motivation
Operational apps (Sapo, MISA, Shopee Seller Center) **fragment** order/customer info across
many screens, and many values they CANNOT compute (true margin, channel net profit, RFM,
lifecycle, segmentation). The OLAP warehouse already computes all of this. `detailView` gives a
**single, complete insight view** per order and per customer — read-only, instant lookup by code/id.

## 2. Goals / Non-Goals
**Goals**
- One URL per entity → full computed insight (financial, fulfillment, behavior, segmentation).
- Sub-second lookup by `order_code` or `customer_id`/`phone`.
- Zero operational burden: 1 small container, reads existing serving DB, no new data pipeline.
- Clean hexagonal architecture so DuckDB can be swapped (e.g. Postgres) without touching domain/UI.

**Non-Goals (v1)**
- No auth/RBAC (LAN-only). No write-back to source systems. No dashboards/aggregations (Metabase owns that).
- No list/browse/search-results grid beyond resolving a single entity. No mobile-native app.
- No editing of warehouse data; no new dbt models (consume marts as-is).

## 3. Users & Use Cases
- **Ops/CS staff**: look up an order by code to see full money + fulfillment + returns at a glance.
- **Sales/account owner**: look up a customer to see value tier, RFM, lifecycle, order history.
- **Analyst/manager**: verify a single order's economics (margin, fees, COGS coverage) with source traceability.

## 4. Functional Requirements
### 4.1 Search (floating header, every page)
- FR-1: Segmented input `[ Order | Customer ]` + text field. Enter → resolve → redirect to detail page.
- FR-2: Order resolved by `order_code` (exact, case-insensitive). Customer resolved by `customer_id` (exact) OR `phone` (normalized) OR `email`; if multiple match → show small disambiguation list (HTMX partial).
- FR-3: Not found → inline friendly empty state, no crash.

### 4.2 Order Detail (`/orders/{order_code}`)
- FR-4: Sidebar summary (always visible): codes, status/payment/fulfillment badges, money headline (net revenue or US revenue, gross profit + margin %, channel net profit), customer mini-card (links to customer page), channel, seller, key dates, data-quality flags.
- FR-5: Tabs (HTMX lazy-loaded): **Financial**, **Line Items**, **Cost Ledger**, **Payments**, **Fulfillment**, **Returns**, **Channel & Staff**, **Timeline**. Tab set + fields per [UI_SPECS.md](./UI_SPECS.md) §Order.
- FR-6: US orders → Financial tab pulls revenue from `fact_us_shipment_economics`, badge "US CrossBorder", and shows `has_unpriced_sku` warning.
- FR-7: COGS unverified (`has_cogs=false`) → margin fields show "unverified" badge.

### 4.3 Customer Detail (`/customers/{customer_id}`)
- FR-8: Sidebar profile card: name, contact, address, geo region, badges (customer_type, value_group, lifecycle_stage), loyalty points, headline LTV, total orders, first/last order, recency, tenure.
- FR-9: Tabs (HTMX lazy-loaded): **Value Metrics**, **Behavior (RFM/segmentation)**, **Status Timeline**, **Order History**. Per UI_SPECS §Customer.
- FR-10: Status Timeline only for `customer_type='RETAIL'`; otherwise tab shows "RETAIL only" notice.
- FR-11: Order History rows link to `/orders/{order_code}`.

### 4.4 Cross-cutting
- FR-12: All timestamps rendered ICT (`Asia/Ho_Chi_Minh`); money formatted VND.
- FR-13: Health endpoint `/healthz` (DB reachable, view present). Optional JSON API mirror under `/api/*`.
- FR-14: Hide `int_*` intermediate views; query only `fact_*`/`dim_*`/`mart_*`.

## 5. Non-Functional Requirements
- NFR-1 (perf): detail page < 800 ms p95 on local DB; per-tab query small (single entity).
- NFR-2 (concurrency): `read_only=True` connection; safe alongside live Metabase. Module-level connection guarded by `threading.Lock` (DuckDB read share) OR per-request connect (decide in C2 by benchmark; default per-request for simplicity).
- NFR-3 (footprint): image ≤ ~250 MB (`python:3.11-slim`). Idle RAM < 150 MB.
- NFR-4 (portability): forward-slash paths; works Windows-dev & Linux-container. `OLAP_DB_PATH` env-driven.
- NFR-5 (resilience): bootstrap_serving_views.py brief RW lock → retry connect w/ small backoff.
- NFR-6 (maintainability): every source file < 200 LOC; SQL isolated in outbound adapter only.

## 6. Architecture — Hexagonal (Ports & Adapters)
**Principle:** domain knows nothing about FastAPI, Jinja, or DuckDB. Dependencies point inward.

```
                ┌──────────────────── DRIVING (inbound) ────────────────────┐
   HTTP/HTMX ─► │ web adapter (FastAPI routes + Jinja2 templates + HTMX)     │
   JSON     ─► │ api adapter (optional /api/*)                              │ ─┐
                └───────────────────────────────────────────────────────────┘  │ calls
                                                                                 ▼
                ┌──────────────── APPLICATION (use-cases) ──────────────────┐
                │ GetOrderDetail · GetCustomerDetail · SearchEntity ·        │
                │ GetOrderTab/GetCustomerTab (lazy loaders)                  │
                └───────────────────────────────────────────────────────────┘
                        │ depends on PORTS (interfaces) only ▲ returns DOMAIN
                        ▼                                    │
   ┌──── DOMAIN (pure) ────┐        ┌──────── PORTS (Protocols) ───────────┐
   │ Order, Customer       │ ◄───── │ OrderRepository, CustomerRepository, │
   │ value objects, flags, │        │ SearchPort                            │
   │ display rules         │        └───────────────────────────────────────┘
   └───────────────────────┘                         ▲ implemented by
                                                      │
                ┌──────────────── DRIVEN (outbound) ────────────────────────┐
                │ duckdb adapter: connection(read_only) + repositories + SQL │ ─► olap.duckdb
                └───────────────────────────────────────────────────────────┘
```

### 6.1 Layers & responsibilities
| Layer | Package | Responsibility | May import |
|---|---|---|---|
| Domain | `app/domain/` | Entities, value objects (Money, Flag, badges), display/derivation rules. **Pure Python.** | stdlib only |
| Ports | `app/domain/ports.py` | `Protocol` interfaces for repositories + search. Return domain objects. | domain |
| Application | `app/application/` | Use-case services orchestrating ports; no SQL, no HTTP. | domain, ports |
| Inbound adapter | `app/adapters/inbound/web/`, `.../api/` | FastAPI routers, Jinja2 render, HTMX partials, request/response mapping. | application, domain |
| Outbound adapter | `app/adapters/outbound/duckdb/` | DuckDB read-only connection, SQL → domain mapping. **Only place with SQL.** | domain, ports, duckdb |
| Composition | `app/composition.py`, `app/main.py` | Wire adapters to ports (DI), build FastAPI app. | all |
| Config | `app/config.py` | Settings from env (`OLAP_DB_PATH`, port, tz). | stdlib/pydantic |

### 6.2 Domain model (aggregates)
- **OrderDetail**: `header` (codes, statuses, dates), `financial` (revenue waterfall + economics + flags), `line_items[]`, `cost_ledger[]` (grouped by category), `payments[]`, `returns[]`, `fulfillment`, `channel`, `staff`, `customer_ref`, `timeline`, `quality_flags` (has_cogs, is_us, has_returns, has_platform_fees).
- **CustomerDetail**: `profile`, `value_metrics` (LTV, AOV, totals, margin), `behavior` (RFM + 8 segments), `status_timeline[]` (RETAIL), `order_history[]`, `quality_flags`.
- **Money** VO (amount + currency=VND), **DataQualityFlag** VO (code, label, severity), **Badge** VO (kind, value, tone).
- Domain functions: `aov()`, `effective_revenue()` (US vs domestic), `margin_is_verified()`, badge mapping for value_group/lifecycle_stage.

### 6.3 Ports (signatures, indicative)
```python
class OrderRepository(Protocol):
    def get_by_code(self, order_code: str) -> OrderDetail | None: ...
    def get_tab(self, order_code: str, tab: OrderTab) -> TabData: ...   # optional granular load
class CustomerRepository(Protocol):
    def get_by_id(self, customer_id: str) -> CustomerDetail | None: ...
    def list_orders(self, customer_id: str) -> list[OrderSummary]: ...
class SearchPort(Protocol):
    def resolve_order(self, q: str) -> str | None: ...                 # → order_code
    def resolve_customer(self, q: str) -> list[CustomerHit]: ...       # id/phone/email
```

### 6.4 Outbound adapter notes
- One module per repository; SQL kept in `queries/` (`.sql` files or constants) for readability.
- Join map per researcher-01 §3 / researcher-02 §3. Map rows → domain dataclasses (no leaking DuckDB types).
- Connection: `app/adapters/outbound/duckdb/connection.py` resolves `OLAP_DB_PATH`, opens `read_only=True`, sets `SET TimeZone='Asia/Ho_Chi_Minh'`, retry/backoff on transient RW-lock.

## 7. Data Contract (source views)
Order: `fact_orders`, `fact_order_economics`, `fact_order_costs`, `fact_order_returns`, `fact_payments`, `fact_sales`, `fact_us_shipment_economics` + dims (`dim_products`, `dim_channels`, `dim_staff`, `dim_order_status`, `dim_payment_methods`, `dim_promotions`, `dim_geography`, `dim_branch_location`, `dim_date`, `dim_time`, `dim_customers`).
Customer: `dim_customers`, `mart_customer_status_snapshot_monthly`, + order facts for history/aggregates.
(Exact columns: see researcher-01 §2 and researcher-02 §2.)

## 8. Deployment & Integration
- `Dockerfile.detailview` (python:3.11-slim, install fastapi/uvicorn/duckdb/jinja2/pydantic-settings).
- Compose service `detail_view`: build context `.`, port `3005:8000`, `env_file: .env.docker`, network `caddy_net`, mount `./app_data/data_lake:/app/var/data_lake:ro`, labels `caddy: detail.lan.fwg.vn` + `reverse_proxy {{upstreams 8000}}`.
- Env: `OLAP_DB_PATH=/app/var/data_lake/serving/olap.duckdb`, `APP_TZ=Asia/Ho_Chi_Minh`, `DETAIL_VIEW_PORT=8000`.
- Registration: README.md (structure + stack), docs/README.md (component table), AGENTS.md (multi-project §6 + boundary rule), docs/architecture/overview.md (topology), .env.docker(+examples).

## 9. Risks & Mitigations
| Risk | Mitigation |
|---|---|
| RW lock during view bootstrap | retry + backoff on connect; surface 503 briefly |
| Misreading US/COGS caveats → wrong numbers | centralize caveat logic in domain; explicit flags + tests |
| Scope creep into dashboards | non-goal stated; defer aggregations to Metabase |
| Schema drift in serving views | adapter maps by column name; smoke test in CI/startup; `/healthz` checks key views |

## 10. Acceptance Criteria
- AC-1: `/orders/{valid_code}` renders all tabs with correct money + flags; US order shows US revenue + badge.
- AC-2: `/customers/{valid_id}` renders profile + 4 tabs; order history links resolve to order pages.
- AC-3: Search resolves order code and customer id/phone; not-found is graceful.
- AC-4: App connects `read_only` while Metabase live; no lock error. `/healthz` green.
- AC-5: Domain/application layers have NO import of duckdb/fastapi (architecture test).
- AC-6: Every source file < 200 LOC; runs in container at `detail.lan.fwg.vn`.

## 11. Open Questions
1. JSON API surface now or later? (default: thin `/api/*` now).
2. Non-RETAIL status timeline handling (default: hide w/ notice).
3. Connection strategy per-request vs shared+lock (decide by quick C2 benchmark).
