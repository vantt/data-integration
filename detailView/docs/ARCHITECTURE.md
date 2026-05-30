# detailView — Architecture & Data-Quality Mechanism

Technical reference for the `detailView` app: how the hexagonal architecture is structured, how
it stays **reactive to OLAP data changes**, and how **data-quality insight is derived from the
warehouse** (not hard-coded). Read alongside `PRD.md` (product) and the audit/design reports in
`../../plans/reports/researcher-260530-*`.

---

## 1. What this app is (and is not)

A **read-only window** onto the OLAP serving warehouse: given one order code or one customer id,
render the *complete* computed business insight for that entity. It owns **no** business logic that
isn't presentation/derivation — all metrics (margin, RFM, coverage…) are computed upstream by dbt.
Its job is to **assemble, present, and tell the truth about** that data — including the data's own
quality and freshness.

Design consequence: the app must (a) always reflect the **latest** pipeline output, and (b) **react
to changes in the data's shape** (new columns/views, coverage shifts) without code edits where
possible. The architecture below is built around those two properties.

---

## 2. Hexagonal architecture (ports & adapters)

**Dependency rule:** dependencies point *inward*. The domain knows nothing about FastAPI, Jinja, or
DuckDB. Adapters depend on the domain (via ports), never the reverse. Enforced by
`tests/test_architecture.py` (regex bans `import duckdb|fastapi` under `domain/` + `application/`,
plus a smoke-query that exercises real SQL against an empty DB).

```
app/
├── domain/                 PURE — no framework/DB imports
│   ├── order.py            OrderDetail aggregate + parts + quality_flags()
│   ├── customer.py         CustomerDetail aggregate + parts + quality_flags()
│   ├── shared.py           Money/Badge/DataQualityFlag/DataQualitySummary, enums
│   └── ports.py            Protocols (the hexagon's "ports")
├── application/
│   └── services.py         use-cases: OrderService, CustomerService, SearchService
├── adapters/
│   ├── inbound/  (driving)  translate HTTP/HTMX → application calls
│   │   └── web/             FastAPI routes, Jinja2 templates, HTMX, static
│   └── outbound/ (driven)   implement domain ports against the warehouse
│       └── duckdb/          read-only connection + repositories + SQL + capability/DQ adapters
├── config.py               Settings.from_env() — paths derived from OLAP_DB_PATH
├── composition.py          the ONLY place wiring adapters → ports (DI)
└── main.py                 FastAPI factory; exception handler; /healthz, /api/*
```

### Ports (driven) and their adapters

| Port (`domain/ports.py`) | Purpose | Adapter (`adapters/outbound/duckdb/`) |
|---|---|---|
| `OrderRepository` | full single-order aggregate by code | `order_repository.py` |
| `CustomerRepository` | full single-customer aggregate by id | `customer_repository.py` |
| `SearchPort` | resolve order (code/id/shipment) + customer (id/phone/email) | `search.py` |
| `CapabilityPort` | introspect serving **schema + freshness** (`view_exists`, `has_column`, `data_version`, `freshness`, `known_tables`) | `capability_adapter.py` |
| `DataQualityPort` | system-level **coverage metrics** (`coverage_metrics() → DataQualitySummary`) | `dataquality_adapter.py` |

**Driving (inbound):** `adapters/inbound/web/` (HTML+HTMX) and `/api/*` JSON. The web adapter is the
only place that knows about HTTP; it calls application services and renders domain objects.

**Composition root** (`composition.py`) builds the DuckDB adapters from `Settings`, injects them into
the application services + capability/DQ, and exposes a frozen `Services` object. `main.create_app()`
is the sole caller.

---

## 3. Request flow

```
GET /orders/{code}                         GET /orders/{code}/tab/{tab}   (HTMX lazy)
  → web route                                → web route (HX-Request)
  → OrderService.get_detail(code)            → same; renders only the tab partial into #tab-panel
  → OrderRepository.get_by_code (outbound)
       header (core)  ─ required
       economics/items/costs/payments/       ← OPTIONAL collections: guarded (missing view → [])
       returns/shipments
  → maps rows → OrderDetail (domain)
  → route resolves quality_flags = order.quality_flags(capability)
  → route adds base context: data_health (DataQualityPort), caps, data_version
  → Jinja renders Precision templates
```

Search: header `hx-get /search?mode=&q=` → `SearchService.resolve()` → `HX-Redirect` on single hit,
results dropdown on many, inline hint on none.

---

## 4. Reactivity to data changes (the core requirement)

The serving layer is **rolling self-refresh**: each `olap.duckdb` view is
`SELECT * FROM read_parquet(<glob>) WHERE filename = max(filename)`, so it resolves to the newest
parquet **at query time**. Combined with the app's **per-request, read-only** DuckDB connect (open →
query → close, no pool, no ORM cache), **every page already shows the latest pipeline output with zero
cache-invalidation**. This is the cheapest possible reactivity for *data values*.

What is NOT free is reacting to **schema/shape** changes and surfacing **freshness**. The
`CapabilityPort` adapter handles those with deliberately small caches:

| Concern | Source | Cache | Why |
|---|---|---|---|
| Per-record values (a row's `has_cogs`, amounts…) | per-request DuckDB read | **none — always fresh** | the whole point; rolling views are query-time |
| Schema (views/columns present) | `information_schema.columns` | **5 min** TTL | schema only changes on a manual `bootstrap_serving_views.py` run — rare |
| `data_version` token | max parquet basename across rolling dirs (filesystem) | **60 s** TTL | pipeline runs ~daily; used for "data as-of" + cache-busting |
| System coverage metrics | `mart_data_quality` (1-row view) | **5 min** TTL | aggregate KPIs; recomputed each pipeline run |

`data_version` = lexically-max `"{table}_{YYYYMMDDHHMMSS}.parquet"` (monotone). It is a single scalar
"data as-of" usable for the UI freshness strip and as an HTTP cache key.

---

## 5. Data-quality insight — derived, not hard-coded

The app's most important "insight" property: **quality caveats reflect the real state of the OLAP**
and **self-heal** when the pipeline improves. Every hint falls into one of four categories — only two
of them are data-driven, and that is intentional (YAGNI):

| Category | Example | Source | Self-heals? |
|---|---|---|---|
| **A. Per-record data flag** | "Margin unverified — no MISA COGS match" | row field `has_cogs` (from `fact_order_economics`) | yes (per order) |
| **B. Capability / coverage-driven** | carrier-link note · "acquisition not tracked" | `CapabilityPort.has_column/view_exists` · `DataQualityPort` rates | **yes, automatically** |
| **C. Domain / business rule** | "Returns are reference-only, not in order P&L" · "Status timeline RETAIL-only" | domain logic (`is_retail`, accounting rule) | n/a (stable truth) |
| **D. UX helper copy** | "Each row is traceable to its source…" · "carrier codes are in Shipments above" | static template copy explaining the UI | n/a (not a data claim) |

**Why not make everything data-driven?** Categories C and D are *not* claims about what data exists —
forcing them through a port would be over-engineering. Only **B** (assertions about the data's
existence/coverage) earns a capability/quality port.

### Self-healing examples (category B)

- **Carrier link:** `Shipment` shows a copy-only tracking code + a note "no carrier URL map". That note
  is emitted by `order.quality_flags(cap)` **only when** `not cap.has_column("fact_fulfillments",
  "carrier_url")` and `not cap.view_exists("dim_carriers")`. The day the pipeline adds either, the note
  **disappears with no code change**.
- **Acquisition source:** `customer.quality_flags(cap, dq)` emits "Acquisition source not tracked" only
  when `dq.acq_source_null_rate_pct` is missing or `> 95%`. If acquisition data starts arriving, the
  flag self-silences.

### The "Data health" surface

`DataQualityPort.coverage_metrics()` reads the single-row `mart_data_quality` view and merges it with
capability signals into a `DataQualitySummary` (data_version, as-of, coverage rates, `stale_views`,
`has_carrier_link_map`). A slim strip in `base.html` renders "data as-of … · COGS X% covered · stale:
…", giving users **real OLAP insight** about what they're looking at. Live today this surfaces, e.g.,
COGS coverage ≈29% (margins widely unverified) and `dim_product_category` stale ~4 months.

`mart_data_quality` is a dbt model (`transformation/models/marts/sales/mart_data_quality.sql`,
grain = 1 row). It joins the order/customer/fulfillment/return facts each pipeline run and is exposed
to serving by `bootstrap_serving_views.py` (auto-discovered — no script edit).

---

## 6. Resilience

| Failure | Behavior |
|---|---|
| Serving DB briefly RW-locked (view bootstrap) | connection retries 3× / 0.2s backoff |
| Missing **optional** view (e.g. `fact_fulfillments`) | repository guard → empty collection; page still renders |
| Missing **core** view (order header / customer profile) | returns `None` → graceful 404 page |
| Any other DuckDB error (binder, IO, parse) | global FastAPI exception handler → `partials/_503.html` (503), not a raw stack trace |
| Schema drift (column added/removed/retyped) | `row_coercion` returns `None` → renders "—"; capability cache picks up new columns within 5 min |

---

## 7. Operational constraints (must-know)

- **DuckDB is single-writer.** The app only ever opens `read_only=True`. `read_only` connections still
  take a shared lock → the serving-view **bootstrap (RW) requires stopping ALL readers** (Metabase
  **and** detail_view) briefly. See `[[feedback_duckdb_view_rebuild]]`.
- **Adding a mart → serving view** is: write the dbt model with `location="{{ get_rolling_location() }}"`
  + `unique`/`not_null` test → `run_dbt.py --select <model>` (pre-create the `rolling/<model>` dir) →
  re-run `bootstrap_serving_views.py` (auto-discovers the folder). No serving-script edit.
- **Timezone:** all `TIMESTAMPTZ`/`date_key` are ICT (`Asia/Ho_Chi_Minh`); the connection sets the
  session TZ; `pytz` + `tzdata` are runtime deps.
- **Fonts/assets** are vendored locally (offline/LAN-safe) — no CDN at runtime.

---

## 8. Extending the app (playbook)

- **New entity field** → add to the domain dataclass + the outbound `.sql` + mapper. Templates bind to it.
- **New self-healing caveat** → add a `DataQualityFlag` in the relevant `quality_flags()` gated on a
  `CapabilityPort`/`DataQualityPort` signal. Never hard-code a data-state claim in a template.
- **New coverage metric** → add a column to `mart_data_quality.sql` + `DataQualitySummary`; surface in
  the data-health strip.
- **New tab** → add to the `OrderTab`/`CustomerTab` enum + route map + a partial; tab bar buttons must
  all carry `onclick="dvActivateTab(this, url)"` (every tab, so re-click works).

---

## 9. Key files

| Concern | File |
|---|---|
| Domain aggregates + flags | `app/domain/order.py`, `customer.py`, `shared.py` |
| Ports | `app/domain/ports.py` |
| Use-cases | `app/application/services.py` |
| DuckDB read connection | `app/adapters/outbound/duckdb/connection.py` |
| Repositories + SQL | `app/adapters/outbound/duckdb/*_repository.py`, `queries/*.sql` |
| Capability / data-quality | `app/adapters/outbound/duckdb/capability_adapter.py`, `dataquality_adapter.py` |
| Composition / app factory | `app/composition.py`, `app/main.py` |
| Web (routes/templates) | `app/adapters/inbound/web/` |
| System DQ mart | `transformation/models/marts/sales/mart_data_quality.sql` |
