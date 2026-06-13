# Raw → Serving → Semantic Integration Report
**Scan date:** 2026-06-13 | **Purpose:** CRM integration contract — reverse-ETL read surfaces + Sapo write-back

---

## 1. Canonical Key Map

| Entity | Raw natural key | Surrogate key | Business code | Cross-system join key | Notes |
|---|---|---|---|---|---|
| Order | `entity_id` (VARCHAR, = `payload.id`) → mart `order_id` | `order_key` (MD5) | `order_code` (e.g. `260316A6VJXGMT`) | `order_code` joins Sapo ↔ Shopee ↔ MISA | `date_key` is ICT YYYYMMDD integer |
| Customer | `entity_id` (VARCHAR, = `payload.id`) → mart `customer_id` | `customer_key` (MD5) | `customer_code` (e.g. `KH000001`) | `customer_id` in Sapo; no cross-system key | PII: `phone`, `email` access-controlled |
| Product/SKU | `entity_id` (= `payload.id`) → `product_id` | `product_key` (MD5) | `sku` / `product_code` | `sku` joins `fact_order_items` ↔ `fact_inventory_snapshot` ↔ MISA | `variant_id` = Sapo level, `product_id` = parent level |
| Staff/Account | `entity_id` → `account_id` / `staff_id` | `staff_key` (MD5) | email | `seller_staff_key` (commission) vs `creator_staff_key` (audit trail) | |
| Channel | `source_id` (Sapo source_id or Suffix ID) | `channel_key` (MD5) | `channel_name` | `ref_order_sources.id` = seed SSoT | 3-level hierarchy: channel_format → platform → channel_name |
| Location | `location_id` | `location_key` (MD5) | `location_name` | `location_id` in orders/inventory | 3 active: 452566, 494912, 624127 |
| Fulfillment | `fulfillment_id` | — | — | `order_id` FK to fact_orders | |
| Return | `return_id` | — | `order_code` | `order_code` links to original order | |
| MISA voucher | — | `misa_sales_line_sk` (MD5) | `voucher_no` + `line_no` | `voucher_no` bridges to Sapo `order_code` | |

**Key rule (naming-conventions.md §2):** `_id` = system natural id (numeric/opaque), `_key` = MD5 surrogate, `_code` = alphanumeric business ref. The CRM MUST store both `customer_id` (natural, for Sapo API calls) and `customer_key` (for mart joins).

---

## 2. Sapo Write-back Surface

The entire ingestion layer (`ingestion/src/sapo/`) uses only GET requests (read-only). **No PUT, POST, or PATCH calls to the Sapo entity endpoints exist in the codebase today.** The only POST found is to the internal Cloudflare D1 ACK endpoint (`/ack-batch`), not to Sapo.

| Object | Write-back field | Confidence | Source | Notes |
|---|---|---|---|---|
| Customer — `tags` | Potentially writable via `PUT /admin/customers/{id}.json` | **UNKNOWN** | `docs/context/sapo-platform.md` mentions `tags: json` field in customer payload; Sapo generally supports PUT for entity update but no write endpoint is documented in SOURCES.md | Not implemented; no evidence for or against |
| Customer — `notes` | Same as tags (nested JSON field in payload) | **UNKNOWN** | `customers.py` schema shows `notes: json`; payload `description` field is text | Not implemented |
| Customer — `customer_group_name` | Potentially via `PUT /admin/customers/{id}.json` with `customer_group_id` | **UNKNOWN** | `customers.py` shows `customer_group_id`, `group_id`, `group_name` fields; no write code | Would require customer_group_id lookup before writing |
| Customer — `loyalty_customer` | Potentially readable/writable (Sapo loyalty API) | **UNKNOWN** | Field present in raw schema: `"loyalty_customer": {"data_type": "json"}` | Sapo loyalty API may be a separate endpoint not documented here |
| Order — `tags` | Potentially writable | **UNKNOWN** | `payload.tags: ["urgent"]` present in order schema | No write endpoint documented or implemented |
| Order — `note` | Potentially writable | **UNKNOWN** | `payload.note` text field present | No write code |
| Order — `assignee_id` | Potentially writable | **UNKNOWN** | `payload.assignee_id` present (people who closed the order) | Could support order routing from CRM |
| Order status fields | **NOT writable from CRM — Sapo owns status** | HIGH CONFIDENCE | Status transitions (`draft → finalized → completed / cancelled`) are driven by Sapo business logic; write-back would create bi-directional conflict risk | |

**Honest summary:** The Sapo API almost certainly supports `PUT /admin/customers/{id}.json` and `PUT /admin/orders/{id}.json` (this is standard Sapo/Shopify-style API design), but NO documentation of writable fields exists in this repo, and no write endpoint has been tested or implemented. Any CRM write-back to Sapo **requires explicit API validation against the live Sapo instance** before design commitment.

---

## 3. CRM Read Surfaces (Reverse-ETL candidates)

| Surface | Path / URL | Contents | Best for | Notes |
|---|---|---|---|---|
| **olap.duckdb** (primary) | `data_lake/serving/olap.duckdb` | Rolling self-refresh views over all mart Parquet snapshots — `fact_orders`, `dim_customers`, `fact_order_economics`, `mart_customer_action_queue`, `fact_fulfillments`, etc. | Real-time BI tool reads; reverse-ETL scheduler that can open DuckDB read-only | Must be opened `read_only=True`; views in schema `main_marts`; Evidence.dev already connects to this |
| **sapo_export_latest.duckdb** (portable) | `data_lake/serving/standalone/sapo_export_latest.duckdb` | Materialized copy of all olap.duckdb views into BASE TABLEs — no parquet path dependency | Distribution to external tools, AI assistants, or CRM if DuckDB file-based access is acceptable; offline analysis | GC keeps last 3 timestamped snapshots; served via Caddy fileserver at `http://<host>:3004` / `https://files.etl.lan.fwg.vn` |
| **Fileserver HTTP endpoint** | `http://evidence.lan.fwg.vn:3004` / `files.etl.lan.fwg.vn` | Serves standalone DuckDB files via HTTP | CRM download-and-query pattern (nightly pull) | |
| **mart_customer_action_queue** (actionable view) | `olap.duckdb → main_marts.mart_customer_action_queue` | Pre-computed queue of customers with actionable signals (`OVERDUE`, `AT_RISK`, `NEW_HIGH_VALUE`) | **Direct CRM input** — read this, don't re-derive | Only customers with active signal appear; not a full customer list |
| **dim_customers** | `olap.duckdb → main_marts.dim_customers` | Full customer profile with RFM, tiers, affinity SKUs, behavioral columns | CRM customer profile sync | Daily refresh, available by 07:00 ICT |
| **fact_orders** | `olap.duckdb → main_marts.fact_orders` | All orders with scope flags, channel, staff attribution, monetary amounts | Order history for CRM | Near-realtime via webhook, lag ~5 min |
| **fact_order_economics** | `olap.duckdb → main_marts.fact_order_economics` | Per-order P&L: net_revenue, cogs_amount, gross_profit, has_cogs | CRM profitability signals | ~65% COGS coverage; available 08:00 ICT |
| **Evidence.dev** | `http://evidence.lan.fwg.vn` (port 3006) | Static report pages built from olap.duckdb | Human-readable reporting; not machine-readable API | Connects to `main_marts` schema only |

**Recommended primary read surface for CRM reverse-ETL:** `olap.duckdb` opened `read_only=True` via DuckDB Python/JDBC driver, querying `main_marts.*` schema. The standalone export is a fallback if the CRM cannot mount the live file.

---

## 4. Cross-cutting Conventions (CRM must respect)

### 4.1 Timezone — ICT / TIMESTAMPTZ
- All timestamps stored as **TIMESTAMPTZ UTC-native** in the pipeline.
- `fact_orders.date_key` (INTEGER YYYYMMDD) is in **ICT (Asia/Ho_Chi_Minh, UTC+7)** — this is the calendar date the customer experiences.
- When querying KPI windows, use the `_yesterday_window_ict()` pattern or filter on `date_key` (ICT). Direct UTC WHERE clauses on `ordered_at` produce ~15% drift for orders created 17:00-24:00 UTC (= 00:00-07:00 ICT next day).
- Metabase DuckDB session is set to `TimeZone=Asia/Ho_Chi_Minh`; TIMESTAMPTZ auto-converts. The CRM must apply the same ICT interpretation.

### 4.2 VAT-inclusive pricing
- Sapo prices are **VAT-inclusive** (8% or 10% embedded). `$.total` = `total_collected` = cash after discount, VAT inside.
- CRM must never add 1.08 or 1.10 on top, and must never use `total_collected` as the P&L revenue line.
- Revenue waterfall the CRM should respect:

| Column | Formula | Use |
|---|---|---|
| `gross_revenue` | list price × qty before discount (VAT-in) | discount_rate denominator only |
| `total_collected` | `gross_revenue − discount_amount` (VAT-in) | cash reconciliation, customer invoice |
| `vat_amount` | embedded VAT (8/108 or 10/110 per item; 0 for ~60% orders) | tax reporting |
| `net_revenue` | `total_collected − vat_amount` | **P&L line — use this for margin** |
| `cogs_amount` | from MISA (VAT-exclusive) | gated on `has_cogs = true` |
| `gross_profit` | `net_revenue − cogs_amount` | gated on `has_cogs = true` |

### 4.3 Semantic columns — do NOT re-derive
These columns are pre-computed in marts. CRM must read, not re-compute:

| Column | Location | Rule |
|---|---|---|
| `scope_sales`, `scope_retail`, `scope_b2b` | `fact_orders` | Use pre-computed booleans; never re-derive via channel/customer_type filter |
| `is_active_order` | `fact_orders` | `status NOT IN ('CANCELLED','DRAFT')` — use this, not manual status filter |
| `has_cogs` | `fact_order_economics` | Gate ALL COGS/margin queries on this flag; `cogs_source` column is deprecated |
| `customer_tier` | `dim_customers` | Bronze/Silver/Gold/Platinum — pre-computed thresholds (1M/5M/10M VND total_spend) |
| `rfm_segment` | `dim_customers` | Pre-computed; do not re-derive RFM in CRM |
| `seller_staff_key` | `fact_orders` | Commission attribution (người chốt); `creator_staff_key` is audit trail only |
| `action_type`, `action_priority` | `mart_customer_action_queue` | CRM action signals — consume as-is |
| `realized_margin_pct` | `fact_order_economics` | Use `realized_*`, not `gross_margin_pct` — H010 fix only in realized_* |

### 4.4 Customer type limitation
`customer_type = 'WHOLESALE'` is unreliable for pre-2026 historical data (only ~3 live WHOLESALE records). CRM must not trust `customer_type` for historical B2B segmentation.

### 4.5 fact_payments is empty
`fact_payments` has 1 all-null placeholder row. Do not use for cash flow — use `payment_status` flag on `fact_orders` instead (unverified signal).

---

## 5. ADR Index

| ADR | Title | Relevance to CRM |
|---|---|---|
| ADR-001 | Pipeline 7-hop ELT pattern | CRM reads at Hop 7 only; never bypass to raw |
| ADR-002 | Immutable append-only data lake | Explains why CRM cannot mutate the lake; reverse-ETL is one-way read |
| ADR-003 | 2-level deduplication / src-stg-std 3-layer | Explains why `std_*` is the contract; CRM must not read `stg_*` directly |
| ADR-004 | 3-channel ingestion redundancy | Explains webhook + history_log + batch convergence; CRM gets the merged result |
| ADR-005 | Dual DuckDB (warehouse vs serving) | **Key for CRM:** read `olap.duckdb` (serving), never `sapo_warehouse.duckdb` |
| ADR-006 | Asset-level locking / concurrency | Explains single-writer DuckDB constraint; CRM must open read_only |
| ADR-007 | Hybrid job explicit dependencies | Explains why mart data is stale until 07:00–08:30 ICT |
| ADR-008 | Analytics-as-Code with Markdown blueprints | CRM dashboard blueprints should follow same pattern |
| ADR-009 | Collection organized by audience | Informs how CRM dashboards should be structured |
| ADR-010 | Dashboard owns questions (no sharing) | Each CRM view should own its queries |
| ADR-011 | Dashboard archetypes (Pulse/Cockpit/Exploratory) | CRM action screens = Cockpit archetype |
| ADR-012 | Technology stack | No reverse-ETL ADR exists — gap noted |
| ADR-013 | Explicit > Implicit heuristic | Prefer explicit filters over implicit assumptions in CRM queries |

**No ADR exists for reverse-ETL, write-back, OLTP app integration, or external CRM.**

---

## 6. Existing Integration Pattern

The only existing app reading from `olap.duckdb` beyond Metabase is **detailView** (`detail_view` Docker service at `detailview.lan.fwg.vn`) — a FastAPI + Jinja2 + HTMX read-only order/customer detail viewer. Its pattern is the closest analog to what the CRM should do:
- Opens `olap.duckdb` in `read_only=True` via Python duckdb library
- Queries `main_marts.*` schema
- No writes back to Sapo or to the lake

Evidence.dev connects to `olap.duckdb` via the `connection.yaml` pointing to `data_lake/serving/olap.duckdb`, schema `main_marts` only.

---

## Open Questions

1. **Sapo write-back API** — Does the Sapo instance expose `PUT /admin/customers/{id}.json`? What fields are actually writable (tags, notes, group, loyalty)? Requires live API test against `fwg.mysapogo.com`. This is the single biggest unknown for the 2-way sync requirement.

2. **Rate limit for write-back** — Standard tier is 40 req/min. If CRM writes enrichment for N customers in a batch, what is the safe cadence? No documentation.

3. **CRM write-back conflict strategy** — If CRM writes `customer_group` to Sapo and Sapo staff also changes it in the UI, the next batch ingestion will overwrite the CRM's value. Need a conflict resolution policy (last-write-wins? field-level ownership?).

4. **Reverse-ETL freshness vs CRM SLA** — `dim_customers` is available by 07:00 ICT daily. If CRM needs near-realtime customer profile (e.g., for same-day outreach), the current daily batch is insufficient. The webhook-driven `fact_orders` (5 min lag) is available, but `dim_customers` behavioral columns (RFM, tier, last_order_date) are daily only.

5. **PII handling** — `dim_customers.phone` and `email` are flagged as PII/sensitive in the data dictionary. Does the CRM Postgres need these columns? What access-control pattern applies in the new OLTP DB?

6. **mart_customer_action_queue status** — File scan confirms the mart is referenced in `entities.md` as `active`, but it was not verified as populated in `olap.duckdb`. Confirm the mart exists and has data before CRM onboarding.

7. **sapo_export_latest.duckdb HTTP delivery** — The fileserver serves the DuckDB file directly over HTTP. Is this acceptable for the CRM's deployment environment, or does the CRM need a query API layer?
