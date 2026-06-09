# detailView Hexagonal Architecture Audit

**Date:** 2026-05-30  
**Scope:** Read-only audit — no code changes  
**Focus:** Hexagonal fitness for a read-only OLAP business-insight window

---

## 1. Boundary Integrity

### Import discipline

The architecture test (`tests/test_architecture.py:17`) enforces a single regex:

```python
_FORBIDDEN = re.compile(r"^\s*(import|from)\s+(duckdb|fastapi)\b", re.MULTILINE)
```

Applied to all `.py` files under `app/domain/` and `app/application/`. Verified by reading all files in those dirs — passes cleanly.

**Boundaries hold:** domain and application layers import zero infrastructure. SQL only lives in `adapters/outbound/duckdb/queries/*.sql`. FastAPI only in `adapters/inbound/web/`. Mappers (`customer_mappers.py`, `order_mappers.py`) live in the outbound adapter and carry no duckdb import; they are pure dict→dataclass functions.

### Gaps in the architecture test

| Gap | Risk | Severity |
|-----|------|----------|
| Regex tests `domain/` + `application/` only; does not test that inbound adapters avoid direct duckdb imports | Low (web layer has no reason to, but not enforced) | Low |
| Only blocks `duckdb` and `fastapi`; `httpx`, `requests`, `sqlalchemy`, etc. are unchecked | Acceptable for current deps | Info |
| `runtime_checkable isinstance` check (`test_repositories_satisfy_ports`) uses `:memory:` — confirms structural match but does not execute any SQL | Test passes even if all queries are broken | Medium |
| No test confirms `composition.py` is the *only* place wiring adapters to services | Not a gap today, but could regress | Low |

**Verdict:** Boundary integrity is solid. The architecture test should add a smoke-query assertion (`test_repositories_satisfy_ports` calls `get_by_code("NONEXISTENT")` and expects `None`) to close the silent-SQL-failure gap.

---

## 2. Data-Knowledge Leaks into the View Layer

### Classification table

Every caveat/note in templates that encodes pipeline knowledge, classified by type:

| Location | Text | Classification | Flag? |
|----------|------|----------------|-------|
| `_shipments.html:190` | "no carrier link map in the serving layer yet" | **Hard-coded system-truth** (C) | YES |
| `_financial.html:69` | "no MISA COGS match for this order" | Driven by `f.has_cogs` boolean | OK (A) |
| `_financial.html:55` | `COGS <span>MISA</span>` label hard-coded | Source-system name baked into template | Minor (C) |
| `_financial.html:62` | "service · payment · infra · voucher · tax" hard-coded in waterfall label | Shopee fee breakdown structure baked in | Minor (C) |
| `_financial.html:19-21` | "US CrossBorder order. Domestic net_revenue = 0" | Driven by `f.is_us` boolean | OK (A) |
| `_line_items.html:105` | "No per-line COGS — cost of goods is recorded at order level only" | Always shown; structural system fact | Smell (C) |
| `_returns.html:106` | "Reference only — returns are not deducted from this order's P&L" | Always shown when returns exist; semantic fact | Minor (C) |
| `_fulfillment.html:36-38` | "Per-leg carrier codes and live status are in Shipments above" | Layout annotation, not data-knowledge | OK |
| `_status_timeline.html:16-21` | "RETAIL only. Monthly status snapshots computed for retail customers only" | Driven by `customer.timeline_available` → `is_retail` property | OK (A) |
| `_overview.html:123-129` | COGS partial-coverage caveat with computed `cov_pct` | Driven by `cogs_order_count < total_orders_count` | OK (A) |
| `customer.py:140` | `DataQualityFlag("acq_unknown", "Acquisition source not tracked", "info")` | **Hard-coded unconditional** — emitted for every customer regardless of data | YES (C) |
| `customer.py:141` | `DataQualityFlag("nightly_sync", "Profile syncs nightly (not real-time)", "info")` | **Hard-coded system-truth**, same for every customer | YES (C) |
| `_operations.html:49` | `s.country not in ("", "Việt Nam", "Vietnam")` | Country filter for domestic suppression hard-coded | Minor (C) |
| `order_detail.html:152` | `badge("same person", "neutral")` — recipient=buyer assumed | Inferred structural assumption; no separate parties object | Minor (C) |

### Most problematic smells

1. **Carrier link map** (`_shipments.html:190`): "no carrier link map in the serving layer yet" is a permanent hard-coded disclaimer. When the pipeline adds `dim_carriers` with URLs, this text must be edited manually; there is no `has_carrier_link_map` flag flowing from data.

2. **`acq_unknown` + `nightly_sync`** (`customer.py:140-141`): Always emitted unconditionally for every customer. If the pipeline adds acquisition-source tracking (e.g. via a `utm_source` column), the caveat will keep showing "not tracked" until someone edits the domain — a staleness-by-design problem.

3. **`no per-line COGS`** (`_line_items.html:105`): Always shown. If per-line COGS is added to `fact_sales`, this caveat stays visible forever.

4. **"MISA" source system name** in waterfall labels: baked into template strings, not from `CostRow.source_system`. If the pipeline renames or adds a second COGS source, template must be manually updated.

---

## 3. Reactivity to Data Changes

### Connection strategy

- **Per-request connect/close** via `read_only_connection()` context manager (`connection.py:61-67`). No connection pool, no persistent handle.
- **DuckDB read_only=True** — safe alongside Metabase and dbt/Dagster writer. Short retry loop (3 attempts, 0.2s linear backoff) handles the bootstrap window lock. This is correct and sufficient for a low-concurrency internal tool.
- **No caching** at any layer (no Redis, no in-process TTL, no HTTP `Cache-Control` headers).
- **Session timezone** set at connect time (`SET TimeZone='Asia/Ho_Chi_Minh'`): correct per pipeline architecture.

### Freshness — where design helps

| Mechanism | Benefit |
|-----------|---------|
| Per-request connect | DuckDB re-reads parquet on each new connection; views auto-reflect new data |
| `read_only=True` | Can't corrupt serving layer; Dagster writer and reader coexist |
| SQL in external `.sql` files (via `sql_loader.py`) | Query changes don't require Python redeployment |
| `lru_cache` on `load_sql()` | SQL text cached per-process — fine; SQL changes require restart (expected) |
| No ORM/session state | No stale object cache to invalidate |

### Freshness — where design hurts

| Mechanism | Cost |
|-----------|------|
| Full aggregate per tab request | Every tab click re-executes all child queries for the aggregate (e.g., `order_tab` re-fetches all 6 queries including header, line items, costs, etc. even if only the "Items" tab was clicked) |
| No ETag/304 | HTMX tab loads always re-fetch; identical data is re-queried and re-rendered |
| No partial loading | `CustomerRepository.get_by_id()` executes 4 queries in sequence under one connection; `OrderRepository.get_by_code()` executes 6. All are executed even when only the sidebar is needed |

### The missing-view guard (search.py)

`search.py:49-53` wraps `resolve_order` in `try/except Exception` → falls back to `_resolve_order_fallback()` which omits `fact_fulfillments`. This is an excellent capability-aware pattern: the adapter degrades gracefully when a view doesn't exist, without crashing the user's search.

This pattern is **not generalized**: `order_repository.py` and `customer_repository.py` have no equivalent guard. A missing `fact_fulfillments`, `fact_order_economics`, or `mart_customer_status_snapshot_monthly` would surface as an unhandled DuckDB exception, propagating to FastAPI as a 500.

---

## 4. Resilience

### Error propagation map

| Failure mode | Current behavior | Impact |
|---|---|---|
| DuckDB file locked at bootstrap | Retry 3×, then `IOException` propagates up | Routes have no try/except → FastAPI 500 |
| Missing view (e.g. `fact_fulfillments`) | search: graceful fallback; repos: unhandled exception → 500 | Inconsistent |
| Schema drift (column removed) | `row.get("col")` → `None` → coercion → `None` in domain → renders as "—" | Silent degradation — good |
| Schema drift (column added) | Ignored; no impact | Good |
| Schema drift (column type changed) | `row_coercion.py` tries multiple coercions; returns `None` on failure | Silent degradation |
| DB file not found | `duckdb.IOException` → unhandled → 500 | Bad |
| Query parse error (SQL syntax) | Unhandled exception → 500 | Bad |

### The 500 problem

Routes (`routes.py`) call `order_service.get_detail()` / `customer_service.get_detail()` with no `try/except`. Service calls `repo.get_by_code()`. Repo opens a DuckDB connection and runs 6 queries. Any unhandled `duckdb.IOException` or `duckdb.BinderError` propagates as an uncaught exception through FastAPI, which returns a 500 with a stack trace.

A `_503.html` template exists (`partials/_503.html`) but is **never rendered** — there is no exception handler wired to use it. It is currently dead code.

The healthz endpoint (`main.py:26-44`) correctly catches exceptions and returns 503 JSON — but this only protects the liveness probe, not real user requests.

---

## 5. Port Granularity & Cohesion

### Current port design

```
OrderRepository.get_by_code(order_code) → OrderDetail | None
CustomerRepository.get_by_id(customer_id) → CustomerDetail | None
SearchPort.resolve_order(query) → str | None
SearchPort.resolve_customer(query) → list[CustomerHit]
```

### Critique

**`OrderRepository.get_by_code` executes the full aggregate** (`order_header.sql` + 5 child queries) on every single call — including every HTMX tab click. The 4 tabs (Financial, Items, Operations, Context) all call `order_service.get_detail()`, which re-runs all 6 queries. Only the tab-specific slice is used; the rest is thrown away.

| Port concern | Issue |
|---|---|
| Port is too coarse-grained | One method loads the entire aggregate; tab routes only use a slice |
| No tab-level port | There is no `get_financial(order_code)` or `get_line_items(order_code)` port; only the fat aggregate |
| `CustomerRepository.get_by_id` same problem | 4 queries per call; tab endpoints only use one sub-section |
| `SearchPort` is well-sized | Two focused methods, each returns a minimal type |

**Note:** The coarse port is not wrong at this scale. DuckDB is fast; the 6 queries run in a single connection under 10–50ms. The overhead of refactoring to per-section ports would exceed the gain at current traffic levels (YAGNI). The smell is real but the urgency is low.

### `composition.py` wiring

Clean. `build_services()` is a single function with explicit injection. No global state, no service locator, no magic. `Services` is a frozen dataclass. App factory (`create_app`) is the sole caller. This is the correct pattern.

---

## 6. Prioritized Recommendations

Priority: **P0** = fix now (correctness/resilience), **P1** = do soon (data-truth risk), **P2** = do when justified.

### P0 — Global exception handler for web routes

**Problem:** Any DuckDB error (lock, missing view, binder error) → unhandled exception → FastAPI 500 with stack trace.  
**Fix:** Register a FastAPI exception handler in `main.py` or `web.py`:

```python
@app.exception_handler(Exception)
async def db_error_handler(request, exc):
    return templates.TemplateResponse("partials/_503.html", {"request": request}, status_code=503)
```

The `_503.html` template already exists and is designed for this. Wire it. One-liner fix.

### P0 — Architecture test: add smoke-query to port satisfaction check

**Problem:** `test_repositories_satisfy_ports` only checks `isinstance`, not that queries execute.  
**Fix:** Call `DuckDbOrderRepository(":memory:").get_by_code("NONEXISTENT")` — expects `None`, not an exception. Exercises the actual SQL against an empty DB.

### P1 — Replace unconditional `acq_unknown` + `nightly_sync` flags with capability-driven logic

**Problem:** `customer.py:140-141` emits these flags unconditionally. If the pipeline adds acquisition tracking or real-time sync, the caveats persist until a developer notices.  
**Pattern:** Add `has_acquisition_source: bool` column to `dim_customers`. Emit `acq_unknown` only when `not has_acquisition_source`. Similarly, `nightly_sync` could be driven by a pipeline metadata flag or simply removed if the sync cadence changes.  
**Benefit:** Caveats become self-healing — when data improves, the flag disappears automatically.

### P1 — Introduce a `CapabilityPort` (or extend domain flags) for the carrier link smell

**Problem:** `_shipments.html:190` hard-codes "no carrier link map in the serving layer yet". When `dim_carriers` is added with tracking URLs, this requires a template edit.  
**Fix (KISS approach):** Add a `has_carrier_url: bool` field to `Shipment`. SQL: `CASE WHEN dc.tracking_url IS NOT NULL THEN TRUE ELSE FALSE END`. Template renders a link when `True`, shows the copy-only note when `False`. Zero new ports needed; reuses existing mapper.

**Rejected alternative:** A separate `CapabilityPort` protocol that queries schema metadata. Over-engineered for a single field.

### P1 — Generalize the missing-view guard from `search.py` to repositories

**Problem:** `search.py` catches exceptions and degrades; `order_repository.py` and `customer_repository.py` do not.  
**Fix:** Wrap child-query fetches (`fetch_all_dicts` calls for optional collections like `fact_fulfillments`, `fact_order_returns`) in try/except that returns `[]` on failure, logging the view name. Core queries (header, profile) remain uncaught — a missing core view should return `None` (not found), not 500.

### P2 — Per-tab port methods (only if latency becomes observable)

**Problem:** Every tab click re-fetches the full aggregate.  
**Fix:** Add `get_financials(order_id)`, `get_line_items(order_id)`, etc. to `OrderRepository`. Each tab route calls the matching method.  
**Hold until:** Query latency > 200ms or CPU becomes a concern. Current DuckDB performance on parquet makes this premature.

### P2 — Remove `_value_metrics.html` duplication

`partials/customer/_value_metrics.html` duplicates significant content from `_overview.html`. If it is no longer fetched standalone, consider consolidating. Check HTMX routes before removing.

### P2 — Widen `_REQUIRED_VIEWS` in healthz

`main.py:23` checks only `fact_orders`, `fact_order_economics`, `dim_customers`. Missing: `fact_fulfillments`, `fact_order_costs`, `fact_payments`, `dim_channels`, `mart_customer_status_snapshot_monthly`. Extend to surface degraded state before users hit 500s.

---

## Summary

| Dimension | Rating | Key Finding |
|---|---|---|
| Boundary integrity | **A** | No infra leaks. Architecture test enforces this. |
| Data-knowledge leaks | **B−** | Most caveats are data-driven. Two unconditional domain flags + one hard-coded template string are genuine smells. |
| Reactivity | **A−** | Per-request DuckDB connect = always-fresh. No cache to invalidate. Full-aggregate reload per tab is the main inefficiency. |
| Resilience | **C** | `_503.html` exists but is dead code. No global exception handler. Missing-view guard is inconsistent across adapters. |
| Port design | **B** | Ports are clean and minimal. Aggregate granularity is acceptable at current scale (YAGNI). |

---

## Unresolved Questions

1. Is `_value_metrics.html` fetched standalone via any HTMX route, or only `include`d from `_overview.html`? If the latter, it is pure duplication and can be removed.
2. What is the actual query latency (p50/p99) for `get_by_code` on production parquet? This determines urgency of per-tab port refactor.
3. Does `dim_carriers` with tracking URLs exist in the pipeline plan? If yes, P1 carrier-link fix has a concrete schema to target.
4. The `_demo_stub.py` is in `adapters/inbound/web/` — is it reachable at any route in production, or dead code? If dead, remove it to reduce confusion.
5. `order_mappers.py:138` hard-codes `us_price_incl_vat=None` with comment "out of read-only scope". If US line-item pricing is needed, where does it come from, and is there a ticket?
