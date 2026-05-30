# OLAP Data Quality Mechanism — Research & Design
**researcher-260530-1343-olap-dataquality-mechanism**
Date: 2026-05-30 | Scope: detailView read-only investigation + design

---

## Part 1 — Evidence: Schema Introspection

### 1.1 Views available (39 total in information_schema)
```
dim_branch_location, dim_channel_targets, dim_channels, dim_customers,
dim_date, dim_geography, dim_order_status, dim_payment_methods,
dim_price_lists, dim_product_category, dim_product_types, dim_products,
dim_promotions, dim_sku_alias, dim_staff, dim_teams, dim_time,
fact_fulfillments, fact_inventory_snapshot, fact_marketing_spend,
fact_order_costs, fact_order_economics, fact_order_returns, fact_orders,
fact_payments, fact_sales, fact_targets, fact_us_shipment_economics,
fact_variant_prices_snapshot, int_misa_sales_lines, int_return_sku_lines,
int_sapo_inventories, int_shopee_order_adjustments, int_shopee_order_fees,
int_shopee_order_items, int_us_shipment_line_prices,
mart_customer_status_snapshot_monthly, mart_inventory_health,
mart_sku_economics_monthly
```
`information_schema.columns` is fully queryable at runtime on the read-only connection. Column introspection is lock-free and fast (metadata, not parquet scan).

### 1.2 Carrier/tracking URL capability — confirmed absent
`fact_fulfillments` columns: `fulfillment_id, fulfillment_code, order_id, order_code, tracking_code, carrier_id, shipping_service, status, cod_amount, created_at, shipped_at`

**No** `*url*`, `*link*`, or `carrier_url` column exists. `dim_channels` and no `dim_carrier*` table exists either. The hard-coded note in `_shipments.html` ("no carrier link map in the serving layer yet") is **currently justified**. If a `carrier_url` column appeared on `fact_fulfillments` OR a `dim_carriers` view were created, the hint should self-silence.

### 1.3 acquisition_source — 100% NULL
```sql
SELECT acquisition_source, COUNT(*) FROM dim_customers GROUP BY 1
→ (None): 7497  -- every row
```
This is not a data quality gap that might heal itself — Sapo does not expose acquisition source in its API. The `acq_unknown` flag in `customer.py` is truthful but will never self-resolve without a new data source. It should remain as a **permanent informational flag**, not a data-driven signal.

---

## Part 2 — Evidence: Freshness Signals

### 2.1 Parquet filename as version token
Filenames follow: `{table_name}_{YYYYMMDDHHMMSS}.parquet`  
Example: `fact_orders_20260530071144.parquet`

The timestamp in the filename is **ICT** (the dbt pipeline timezone), embedded at export time. This is extractable without opening DuckDB — pure filesystem metadata.

**Max filename across all non-empty tables = data version token:**
```
mart_sku_economics_monthly_20260530071144.parquet  →  2026-05-30T07:11:44+07
```

The token has a stable format (`max(basename)` lexical sort = chronological sort because YYYYMMDDHHMMSS is lexicographically monotone). This gives a single scalar "data as-of" without any DB connection.

### 2.2 Per-domain freshness (observed today)
| Domain | Latest parquet mtime (ICT) |
|---|---|
| orders / financials | 2026-05-30 14:12:55 |
| customers | 2026-05-30 14:13:00 |
| fulfillments | 2026-05-30 14:12:48 |
| catalog (products, channels) | 2026-05-30 14:12:40 |
| dim_product_category | 2026-02-02 18:04:35 (**stale — 4 months**) |

`dim_product_category` has not been refreshed since 2026-02-02. The per-table freshness check would surface this automatically.

### 2.3 Max data timestamp inside fact_orders
```sql
SELECT MAX(order_timestamp) FROM fact_orders → 2026-05-30 10:18:03+07
SELECT MAX(updated_at)      FROM fact_orders → 2026-05-30 11:46:39+07
```
Pipeline ran at ~07:11 UTC+7, capturing orders up to ~10:18. Last updated_at is ~11:46 (some orders updated post-export). This is the "data as-of" from the data itself, complementary to filename timestamp.

### 2.4 Drift marker: `.known_tables.json`
- Location: `/app/var/data_lake/serving/.known_tables.json`
- Updated by `refresh_rolling.py` on every pipeline run (atomic `os.replace`)
- Contains: `{"tables": [sorted list of all observed rolling dirs]}`
- Drift detection: `refresh_rolling.py` prints `[!] SCHEMA_DRIFT: new table 'X'` when `current - known` is non-empty
- **The app can read this file directly** (plain JSON, no DuckDB lock) to know the current set of tables and compare against `information_schema.tables` to detect views that exist vs. are missing

---

## Part 3 — Evidence: Coverage / Quality Metrics (Live Queries)

| Metric | Value | Interpretation |
|---|---|---|
| `has_cogs` rate (fact_order_economics) | **29.3%** (983/3352) | 70.7% of orders have no MISA cost match — margin is widely unverified |
| `has_platform_fees` rate | **2.7%** (90/3352) | Shopee fee data is sparse — currently Shopee-only, most orders don't have it |
| `acquisition_source` NULL rate | **100%** (7497/7497) | Sapo doesn't expose acquisition channel — permanent gap |
| Fulfillment coverage | **94.5%** (3167/3352 orders) | 5.5% of orders have no shipment leg — normal for cancelled/warehouse orders |
| Return rate | **0.1%** (2/3352) | Very low; could be data gap or genuinely rare |
| US orders share | **35.4%** (1188/3352) | Significant — US crossborder logic is critical path |
| `carrier_id` NULL in fact_fulfillments | **18.8%** (663/3524) | Carriers not always captured (correlates with tracking_code NULL) |
| US `has_unpriced_sku` rate | **75.5%** (897/1188 US orders) | Most US orders have at least one SKU without a US price — systemic |

**Key insight:** `has_cogs=29.3%` and `has_platform_fees=2.7%` are real coverage metrics that can be queried per-entity. The existing `no_cogs` and `no_platform_fees` `DataQualityFlag` objects already consume per-order `has_cogs` and `has_platform_fees` booleans from the mapper — this path is **already data-driven**. The problem is:
1. The *system-level* rates (29.3%, 2.7%) are not surfaced anywhere
2. The `acq_unknown` and `nightly_sync` and carrier-link flags are **always-on hard-coded strings**

---

## Part 4 — Evidence: Caveat Inventory

### Hard-coded (always-on, never conditional):

| Location | Code | Label | Classification |
|---|---|---|---|
| `customer.py:140` | `acq_unknown` | "Acquisition source not tracked" | **Permanent** — 100% NULL, no data signal can change this without new ETL |
| `customer.py:141` | `nightly_sync` | "Profile syncs nightly (not real-time)" | **Permanent** — pipeline cadence, not a data signal; could become data-driven via pipeline schedule metadata |
| `_shipments.html:190` | *(inline text)* | "no carrier link map in the serving layer yet" | **Capability-driven** — should auto-silence if `carrier_url` column or `dim_carriers` view appears |
| `customer.py:143-144` | `timeline_retail` | "Status timeline: RETAIL customers only" | **Data-driven** — already reads `customer_type`; correct |

### Already data-driven (per-entity):

| Location | Code | Signal source |
|---|---|---|
| `order.py:240-241` | `no_cogs` | `financial.has_cogs` from DB |
| `order.py:244-245` | `no_platform_fees` | `financial.has_platform_fees` from DB |
| `order.py:238-239` | `unpriced_sku` | `financial.has_unpriced_sku` from DB |
| `order.py:242-243` | `has_returns` | `financial.has_returns` from DB |
| `customer.py:146-148` | `cogs_partial` | `cogs_order_count < total_orders_count` from DB |
| `_overview.html:102-128` | COGS coverage % | Computed from `cogs_order_count / total_orders_count` |

**Conclusion:** The per-entity quality flags are already well data-driven. The gaps are: (a) system-level coverage metrics not surfaced, (b) capability checks not queryable at runtime, (c) freshness/version not exposed.

---

## Part 5 — Design: Self-Healing Data Quality Mechanism

### 5.1 Architecture principles
- **Hexagon-clean:** two new driven ports, one new adapter, one optional dbt mart
- **YAGNI:** don't build a full observability platform; build exactly what the app needs
- **KISS:** no background threads, no pub/sub; use a short TTL in-process cache on the capability layer only
- **DRY:** one canonical capability adapter feeds both domain flag logic and the UI "data health" panel

### 5.2 New Driven Ports (signatures)

```python
# domain/ports.py additions

class CapabilityPort(Protocol):
    """Read-only introspection of the serving layer schema and freshness."""

    def view_exists(self, view_name: str) -> bool:
        """True if the view is present in information_schema."""
        ...

    def has_column(self, view_name: str, column_name: str) -> bool:
        """True if view_name has a column matching column_name."""
        ...

    def data_version(self) -> str:
        """Lexically-max parquet filename across all non-empty tables.
        Format: '{table}_{YYYYMMDDHHMMSS}.parquet'. Stable cache-busting token."""
        ...

    def freshness(self, view_name: str) -> datetime | None:
        """ICT datetime of the latest parquet for view_name, or None if empty."""
        ...

    def known_tables(self) -> frozenset[str]:
        """Tables listed in .known_tables.json. Lock-free JSON read."""
        ...


class DataQualityPort(Protocol):
    """Pre-aggregated coverage metrics over the full dataset.
    These are system-level rates, not per-entity flags."""

    def coverage_metrics(self) -> DataQualitySummary:
        """Returns system-wide coverage snapshot (cached, TTL ~5min)."""
        ...


@dataclass(frozen=True)
class DataQualitySummary:
    """Grain: entire dataset. Populated from mart_data_quality or direct queries."""
    data_version: str
    as_of: datetime
    total_orders: int
    cogs_rate_pct: float         # % of orders with has_cogs
    platform_fees_rate_pct: float
    fulfillment_coverage_pct: float
    return_rate_pct: float
    us_share_pct: float
    carrier_null_rate_pct: float  # % of fulfillments with no carrier_id
    acq_source_null_rate_pct: float  # informational — expected 100%
    stale_views: list[str]        # views where parquet mtime > threshold (e.g. 2 days)
    # Capability booleans derived from schema
    has_carrier_link_map: bool    # True if fact_fulfillments.carrier_url or dim_carriers exists
```

### 5.3 Self-Healing Flag Logic

Domain `quality_flags()` methods consume both ports. The domain is given both ports at construction time (injected by the application service):

```python
# domain/order.py (revised quality_flags)
def quality_flags(self, cap: CapabilityPort | None = None) -> list[DataQualityFlag]:
    flags: list[DataQualityFlag] = []
    if self.financial.is_us:
        flags.append(DataQualityFlag("is_us", "US CrossBorder revenue", "info"))
        if self.financial.has_unpriced_sku:
            flags.append(DataQualityFlag("unpriced_sku", "Some SKUs missing US price", "warn"))
    if not self.financial.has_cogs:
        flags.append(DataQualityFlag("no_cogs", "Margin unverified — no MISA COGS match", "warn"))
    if self.financial.has_returns:
        flags.append(DataQualityFlag("has_returns", "Has returns (reference only in P&L)", "info"))
    if not self.financial.has_platform_fees and self.financial.shopee_platform_fees is None:
        flags.append(DataQualityFlag("no_platform_fees", "No platform-fee data", "info"))
    # NEW: carrier link — auto-silences when capability arrives
    if cap and not cap.has_column("fact_fulfillments", "carrier_url") \
            and not cap.view_exists("dim_carriers"):
        flags.append(DataQualityFlag("no_carrier_link", "Tracking codes are copy-only — no carrier URL map", "info"))
    return flags

# domain/customer.py (revised quality_flags)
def quality_flags(self, cap: CapabilityPort | None = None,
                  dq: DataQualitySummary | None = None) -> list[DataQualityFlag]:
    flags = []
    # acq_unknown: only show if data confirms it's 100% NULL (or cap=None → always show)
    if dq is None or dq.acq_source_null_rate_pct > 95.0:
        flags.append(DataQualityFlag("acq_unknown", "Acquisition source not tracked", "info"))
    flags.append(DataQualityFlag("nightly_sync", "Profile syncs nightly (not real-time)", "info"))
    if not self.is_retail:
        flags.append(DataQualityFlag("timeline_retail", "Status timeline: RETAIL customers only", "info"))
    vm = self.value_metrics
    if vm.cogs_order_count is not None and vm.total_orders_count:
        if vm.cogs_order_count < vm.total_orders_count:
            flags.append(DataQualityFlag("cogs_partial", "Margin from partial COGS coverage", "warn"))
    return flags
```

**Self-healing behavior:**
- `no_carrier_link` disappears the moment `dim_carriers` view or `carrier_url` column is bootstrapped — no code change required
- `acq_unknown` self-silences if acquisition data ever starts arriving (rate drops below 95%)
- System-level stale_views list drives a new "data health" panel showing which domains are behind

### 5.4 Adapter Design: DuckDbCapabilityAdapter

```python
# adapters/outbound/duckdb/capability_adapter.py

import glob, json, os, threading
from datetime import datetime
from functools import lru_cache
import duckdb

_SCHEMA_CACHE_TTL_SECONDS = 300   # 5 min — schema changes are rare
_VERSION_CACHE_TTL_SECONDS = 60   # 1 min — data changes each pipeline run (~daily)

class DuckDbCapabilityAdapter:
    """Implements CapabilityPort. Schema info cached at process level with TTL."""

    def __init__(self, db_path: str, rolling_dir: str, known_tables_path: str):
        self._db_path = db_path
        self._rolling_dir = rolling_dir
        self._known_tables_path = known_tables_path
        self._lock = threading.Lock()
        self._schema_cache: dict | None = None
        self._schema_cache_ts: float = 0.0
        self._version_cache: str | None = None
        self._version_cache_ts: float = 0.0

    def _load_schema(self) -> dict:
        """Returns {view_name: set[column_names]}. Cached for _SCHEMA_CACHE_TTL_SECONDS."""
        import time
        now = time.monotonic()
        with self._lock:
            if self._schema_cache is None or (now - self._schema_cache_ts) > _SCHEMA_CACHE_TTL_SECONDS:
                schema: dict[str, set[str]] = {}
                with duckdb.connect(self._db_path, read_only=True) as conn:
                    rows = conn.execute(
                        "SELECT table_name, column_name FROM information_schema.columns"
                    ).fetchall()
                for table, col in rows:
                    schema.setdefault(table, set()).add(col)
                self._schema_cache = schema
                self._schema_cache_ts = now
            return self._schema_cache

    def view_exists(self, view_name: str) -> bool:
        return view_name in self._load_schema()

    def has_column(self, view_name: str, column_name: str) -> bool:
        schema = self._load_schema()
        return column_name in schema.get(view_name, set())

    def data_version(self) -> str:
        import time
        now = time.monotonic()
        with self._lock:
            if self._version_cache is None or (now - self._version_cache_ts) > _VERSION_CACHE_TTL_SECONDS:
                max_fn = _scan_max_filename(self._rolling_dir)
                self._version_cache = max_fn or "unknown"
                self._version_cache_ts = now
            return self._version_cache

    def freshness(self, view_name: str) -> datetime | None:
        td = os.path.join(self._rolling_dir, view_name)
        if not os.path.isdir(td):
            return None
        files = sorted(glob.glob(os.path.join(td, "*.parquet")))
        if not files:
            return None
        return datetime.fromtimestamp(os.path.getmtime(files[-1]))

    def known_tables(self) -> frozenset[str]:
        try:
            with open(self._known_tables_path, "r") as f:
                return frozenset(json.load(f).get("tables", []))
        except (OSError, ValueError):
            return frozenset()


def _scan_max_filename(rolling_dir: str) -> str | None:
    max_fn = None
    for t in os.listdir(rolling_dir):
        td = os.path.join(rolling_dir, t)
        if not os.path.isdir(td): continue
        files = sorted(glob.glob(os.path.join(td, "*.parquet")))
        if files:
            fn = os.path.basename(files[-1])
            if max_fn is None or fn > max_fn: max_fn = fn
    return max_fn
```

**What is cached vs always-fresh:**
| Data | Cache | Rationale |
|---|---|---|
| Schema (view/column lists) | 5 min TTL in-process | Schema changes require manual `bootstrap_serving_views.py` run — rare. 5 min is safe; schema drift is not a hot-path concern |
| `data_version` token | 1 min TTL | Pipeline runs ~daily; 1 min granularity is fine. Used for HTTP cache-busting only |
| Per-entity has_cogs, has_platform_fees etc. | Never (per-request DuckDB read) | These are row-level fields fetched in the existing per-request query — already always-fresh |
| DQ coverage metrics | 5 min TTL (see below) | These are aggregate queries; acceptable ~5 min staleness for system panel |

### 5.5 DataQuality Metrics: Lazy vs Precomputed (mart_data_quality)

**Option A: Direct aggregate queries at request time (lazy, TTL-cached)**
- Adapter runs `COUNT(*) WHERE has_cogs` etc. once per ~5 min, caches in process
- Pros: zero dbt/pipeline changes, always reflects current parquet
- Cons: first request after TTL expiry adds ~100-300ms latency; multi-worker deployments need a shared cache (Redis or on-disk JSON) to avoid N identical queries

**Option B: dbt mart `mart_data_quality` (precomputed each pipeline run)**
- One dbt model, grain: single row, refreshed every pipeline run
- Cols: `as_of_utc, total_orders, cogs_matched, cogs_rate_pct, platform_fees_rate_pct, fulfillment_coverage_pct, return_rate_pct, us_share_pct, carrier_null_rate_pct, acq_source_null_rate_pct`
- App reads it exactly like any other view — one cheap SELECT of 1 row
- Pros: zero query overhead per request; consistent with pipeline timing; single source of truth
- Cons: requires dbt model addition; metrics reflect pipeline-time state, not current parquet (lag = pipeline period, typically ~daily)

**Recommendation: Option B (mart_data_quality) for system-level metrics, Option A (live query + cache) for the `data_version` token and freshness timestamps.**

Rationale: System-level rates (COGS coverage, platform fee rate) are aggregate KPIs that belong in the mart layer — that's exactly what marts are for. The overhead of a 5-min TTL aggregate query running on every FastAPI worker startup is unjustified when dbt already computes these during the pipeline. The `data_version` token and per-view freshness are filesystem reads (fast, no DuckDB), so no mart needed.

**mart_data_quality schema (proposed):**
```sql
-- grain: 1 row, refreshed every pipeline run
SELECT
    NOW()                                                       AS as_of_utc,
    COUNT(*)                                                    AS total_orders,
    SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END)                  AS cogs_matched,
    ROUND(100.0 * SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END) / COUNT(*), 1) AS cogs_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN has_platform_fees THEN 1 ELSE 0 END) / COUNT(*), 1) AS platform_fees_rate_pct,
    -- fulfillment_coverage, return_rate, us_share via subqueries or separate CTEs
    ...
FROM fact_order_economics
```

### 5.6 Reactivity Strategy

The serving layer is already "always-latest at query time" by design (views glob max filename). The only reactivity gap is schema/capability info and the system DQ panel.

**Proposed:**
```
Per-request path (always-fresh):
  → DuckDB read for entity data (existing, untouched)
  → data_version token injected into HTML as <meta> or ETag header

Capability / schema (TTL-cached, 5 min):
  → DuckDbCapabilityAdapter._schema_cache refreshes after TTL
  → drives quality_flags() — no per-request DB hit
  → ETag for /health endpoint: "version={data_version}&schema={schema_hash}"

System DQ panel (mart_data_quality, pipeline-refresh):
  → One SELECT of 1 row, cached 5 min in adapter
  → Displayed in footer/side panel as "data as-of YYYY-MM-DD HH:MM ICT"
```

For the single-worker FastAPI container (current deployment), an in-process `threading.Lock` + monotonic timestamp is sufficient. No Redis needed.

HTTP caching: include `data_version` as an `ETag` or query param in HTMX tab URLs so browser doesn't serve stale HTML after a pipeline run. TTL = 1 min.

### 5.7 UI: "Data Health" Surface

**Proposed: small footer strip on every entity page + `/health` endpoint**

Footer strip (always visible):
```
Data as-of: 2026-05-30 07:11 ICT  ·  COGS: 29% covered  ·  [!] stale: dim_product_category (4 months)
```

Implementation: inject `DataQualitySummary` into Jinja context from the route handler (one call, cached). Template renders a `<div class="data-health-bar">` with:
- `as_of` from `mart_data_quality.as_of_utc` (converted to ICT)
- `cogs_rate_pct` — shows system coverage context for the per-order `no_cogs` warn
- stale views list (any view with freshness > 48h ago) — surface anomalies like `dim_product_category`

`GET /health` (JSON): returns `DataQualitySummary` as JSON for external monitoring / Dagster sensors.

---

## Part 6 — Migration Plan (Incremental, Low-Risk)

### Phase 1 — Capability port only (no dbt change, minimal risk)
1. Add `CapabilityPort` to `domain/ports.py` (Protocol, no impl yet)
2. Implement `DuckDbCapabilityAdapter` (new file, ~80 lines)
3. Wire into `composition.py` — add `capability: CapabilityAdapter` to `Services`
4. Modify `order.quality_flags()` to accept optional `cap: CapabilityPort | None = None`; add `no_carrier_link` self-healing flag; default `None` is backward-compatible
5. Modify `_shipments.html` to use the domain flag instead of the inline hard-coded note
6. **Test:** the carrier-link note still appears (capability absent) + disappears in a test stub where `has_column("fact_fulfillments","carrier_url")` returns True

### Phase 2 — Freshness + data_version in UI
1. Add `freshness()` and `data_version()` to `DuckDbCapabilityAdapter` (filesystem reads, no new DuckDB queries)
2. Inject `data_version` into all route responses as `<meta name="data-version">` and as HTMX `ETag`
3. Add a minimal `<div class="data-freshness">` partial showing "data as-of" from `data_version` token
4. Add `GET /health` JSON endpoint — no dbt dependency

### Phase 3 — mart_data_quality + system DQ panel
1. Add `mart_data_quality.sql` to dbt project (single-row aggregate, ~20 lines)
2. Implement `DuckDbDataQualityAdapter` reading from the mart view (1 SELECT, 5 min TTL)
3. Add `DataQualityPort` to domain ports; inject into customer.quality_flags for `acq_unknown` conditionalization
4. Add `data-health-bar` footer strip to `base.html`
5. Only build this after Phase 1+2 are stable

**YAGNI boundary:** Do not build per-table staleness alerting, per-pipeline-run comparison, or trend charting. Those belong in a dedicated observability tool, not this app.

---

## Unresolved Questions

1. **Multi-worker deployment:** if detailView ever runs >1 uvicorn worker, the in-process TTL cache is per-worker. Is a shared cache (on-disk JSON written by the pipeline) needed, or is per-worker acceptable (each worker converges independently after TTL)?

2. **`nightly_sync` flag:** can pipeline cadence be derived from the `data_version` timestamp gap (e.g. "last refreshed 6h ago → pipeline runs ~daily")? Or is this hardcoded-by-design since the pipeline schedule is configuration, not data?

3. **Return rate anomaly:** observed 0.1% return rate (2/3352 orders). Is this genuine (rare returns), or is `fact_order_returns` not fully populated (separate ingestion path from Sapo)? This affects whether `has_returns` on the order is trustworthy.

4. **mart_data_quality grain:** should it be a single aggregate row, or one row per domain (orders / customers / fulfillments)? Finer grain allows per-domain freshness comparisons but adds complexity.

5. **dim_product_category staleness (4 months):** is this intentional (static taxonomy) or a pipeline gap? If the latter, the stale-views check would surface it as a warning. Needs confirmation before building alerting.

6. **`acq_source_null_rate_pct` 95% threshold:** the suggested self-silencing threshold is 95%. This is arbitrary — if acquisition source starts being populated for new customers only (e.g., 10%), the flag should show "X% of customers have unknown acquisition". Should the flag label be dynamic ("Acquisition source: 90% unknown") rather than binary show/hide?

---

## Recommended Phased Plan

| Phase | Effort | Value | Risk |
|---|---|---|---|
| **1** — CapabilityPort + carrier-link self-healing | ~1 day | Eliminates first hard-coded caveat; proves the pattern | Very low |
| **2** — Freshness token + data-as-of UI strip | ~0.5 day | Users see when data was last refreshed; ETag for cache-busting | Very low |
| **3** — mart_data_quality + system DQ panel | ~1 day | Full system-level insight; COGS coverage context in UI | Low (new dbt model) |

Total estimated: ~2.5 dev-days. Phases are fully independent and each delivers standalone value.
