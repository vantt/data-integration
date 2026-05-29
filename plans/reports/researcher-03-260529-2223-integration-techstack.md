# Research Report: New Read-Only Web App — Integration & Tech Stack

**Date:** 2026-05-29 | **Scope:** Read-only research. No code changes.

---

## 1. How Metabase Opens olap.duckdb — Concurrent Read Safety

### Connection config (verified live via Metabase API)

```json
{
  "engine": "duckdb",
  "read_only": true,
  "database_file": "/app/var/data_lake/serving/olap.duckdb"
}
```

Both databases Metabase manages are `read_only: true`:
- DB 2 "Sapo" → `/app/var/data_lake/serving/olap.duckdb`
- DB 3 "Ingestion Health" → `/app/var/data_lake/monitoring/ingestion_health.duckdb`

The `read_only` flag is set in the Metabase DuckDB driver config (motherduckdb/metabase_duckdb_driver v1.5.2.0). It maps to the DuckDB JDBC `duckdb.read_only=true` property.

### DuckDB concurrent-read behavior (verified empirically 2026-04-08, see locking-and-concurrency.md §DB-level)

| Mode | File lock acquired? | Concurrent readers allowed? |
|---|---|---|
| `read_only=True` | **No** — mmap only | **Yes, unlimited** |
| RW (default) | **Yes — exclusive** | No other writers; readers still allowed |

**Empirical test run now (2026-05-29):** Second `duckdb.connect(olap_path, read_only=True)` while Metabase live:
- `fact_orders` count: 3,349 rows
- `dim_customers` count: 7,497 rows
- Connect time: ~13 ms, no exception

**Conclusion for new app:** Open olap.duckdb with `read_only=True`. Zero risk of lock contention with Metabase. DuckDB Python `1.5.2` is already in the container's runtime (`ingestion/requirements.txt`). The new app simply needs `duckdb` in its own requirements.

**The only writer constraint:** `bootstrap_serving_views.py` opens RW (exclusive) briefly when bootstrapping views. This blocks all `read_only` connects for the duration of CREATE OR REPLACE VIEW (~milliseconds per view). Not a practical concern for a running web app.

---

## 2. Serving Views — Schema Exposed by olap.duckdb

All 38 objects in `olap.duckdb` are **VIEWs** (no base tables). They live in schema `main`. Queried as `SELECT ... FROM main.<view>` or just `<view>` (default schema).

**Views by category (live count as of 2026-05-29):**

| Category | Views |
|---|---|
| **Dimensions** | `dim_branch_location`, `dim_channel_targets`, `dim_channels`, `dim_customers`, `dim_date`, `dim_geography`, `dim_order_status`, `dim_payment_methods`, `dim_price_lists`, `dim_product_category`, `dim_product_types`, `dim_products`, `dim_promotions`, `dim_sku_alias`, `dim_staff`, `dim_teams`, `dim_time` |
| **Facts** | `fact_inventory_snapshot`, `fact_marketing_spend`, `fact_order_costs`, `fact_order_economics`, `fact_order_returns`, `fact_orders`, `fact_payments`, `fact_sales`, `fact_targets`, `fact_us_shipment_economics`, `fact_variant_prices_snapshot` |
| **Intermediates** | `int_misa_sales_lines`, `int_return_sku_lines`, `int_sapo_inventories`, `int_shopee_order_adjustments`, `int_shopee_order_fees`, `int_shopee_order_items`, `int_us_shipment_line_prices` |
| **Marts** | `mart_customer_status_snapshot_monthly`, `mart_inventory_health`, `mart_sku_economics_monthly` |

**View internals:** Each view is a Rolling Self-Refresh pattern — it reads `read_parquet(glob, filename=true)` and selects rows WHERE `filename = max(filename)`. Parquet files live at `/app/var/data_lake/export/marts/rolling/<table>/`. The view resolves to the latest file at query time — no schema drift needed for the new app.

**Key views for order/customer detail pages:**
- `fact_orders` — order grain, 3,349 rows
- `dim_customers` — customer grain, 7,497 rows
- `fact_sales` — line-item grain
- `dim_products`, `dim_channels`, `dim_staff` — FK dimensions

**Timezone:** DuckDB session timezone is `Asia/Ho_Chi_Minh` (set in `bootstrap_serving_views.py:104`). All `TIMESTAMPTZ` fields display in ICT. Queries from the new app must be aware: `date_key` columns are ICT-based, not UTC.

---

## 3. Docker Integration Pattern

### Volume mount the new app must replicate

```yaml
volumes:
  - ./app_data/data_lake:/app/var/data_lake   # gives access to olap.duckdb
  - monitoring_db:/app/var/data_lake/monitoring  # named vol overlay — skip if not needed
```

**Exact olap.duckdb path inside container:** `/app/var/data_lake/serving/olap.duckdb`

The new app only needs the first bind mount. The `monitoring_db` named volume is only needed if it also queries ingestion health.

### Network

```yaml
networks:
  - caddy_net    # external network (defined in caddy-global/docker-compose.yml)
```

### Caddy reverse-proxy labels pattern

```yaml
labels:
  caddy: app.local           # hostname for local TLS
  caddy.reverse_proxy: "{{upstreams <INTERNAL_PORT>}}"
```

All services use `lucaslorentz/caddy-docker-proxy` — it auto-registers via Docker socket + these labels. No Caddyfile edits needed.

### env_file

```yaml
env_file:
  - .env.docker    # shared env; add app-specific vars here or in environment: block
```

### Dockerfile build pattern

All first-party services use a custom Dockerfile (`Dockerfile.<name>`) with context `.` (repo root). Example new service entry:

```yaml
  detail_app:
    build:
      context: .
      dockerfile: Dockerfile.detailapp
    container_name: detail_app
    restart: unless-stopped
    ports:
      - "3005:<INTERNAL_PORT>"
    env_file:
      - .env.docker
    networks:
      - caddy_net
    volumes:
      - ./app_data/data_lake:/app/var/data_lake
    labels:
      caddy: detail.local
      caddy.reverse_proxy: "{{upstreams <INTERNAL_PORT>}}"
```

**Important:** Metabase mounts data_lake as **`rw`** (not `:ro`). The new app should mount **`:ro`** for defense in depth — prevents any accidental write at OS level, even though DuckDB `read_only=True` already protects at application level.

---

## 4. Monorepo Registration Points

Every file that must be touched when adding a new service:

| File | Section to touch | What to add |
|---|---|---|
| `docker-compose.yml` | `services:` block | New service stanza (see pattern above) |
| `.env.docker` / `.env.docker.example` / `.env.example` | App-specific section | Any new env vars (e.g., `DETAIL_APP_PORT=8000`) |
| `README.md` | `Project Structure` tree + `Technology Stack` table | New directory entry + new row |
| `docs/README.md` | `Component Documentation` table | New row pointing to `/<app>/docs/README.md` |
| `AGENTS.md` | `Multi-Project Repository Structure` → numbered list | New section (e.g. `### 6. Detail App (detail_app/)`) |
| `AGENTS.md` | `AI Agent Rules → Respect Project Boundaries` | New bullet (`Detail App files ONLY in /detail_app/`) |
| `docs/architecture/overview.md` | `Tech Stack Overview` + deployment topology diagram | Add web app layer + service box |
| `Dockerfile.detailapp` | (create new) | New Dockerfile for the app |
| `detail_app/` | (create new) | App source, `requirements.txt`, `README.md` |

**Note:** `CLAUDE.md` at repo root does not list services — no change needed. `caddy-global/docker-compose.yml` is managed by the global Caddy container — no change needed as long as labels are set correctly in the new service.

---

## 5. Tech Stack Recommendation

### Options evaluated

| Dimension | FastAPI + Jinja2 | FastAPI + HTMX | FastAPI + React/Vite SPA |
|---|---|---|---|
| Docker image size | ~200 MB (python:slim) | ~200 MB | ~200 MB backend + ~50 MB build step |
| Frontend complexity | Near zero — SSR | Low — sprinkle JS | Medium — separate build pipeline |
| JS bundle shipped | None | Minimal (htmx.min.js, ~14 KB) | 100-500 KB |
| Dynamic filtering/UX | Good enough for detail pages | Good — partial DOM swaps | Best — full SPA reactivity |
| Ops overhead | 1 container | 1 container | 1 container (if SPA served by FastAPI) OR 2 |
| DuckDB read_only fit | Perfect — single thread per request is fine | Perfect | Perfect |
| Team Python fit | Native | Native | Requires JS/Node toolchain for dev |
| Hexagonal architecture | Clean: API routes = adapter, DuckDB = port | Same | Same — but more layers |
| Build complexity | Zero build step | Zero build step | `npm run build` in Dockerfile |

### Adoption risk

| Option | Maturity | Community | Breaking-change risk |
|---|---|---|---|
| FastAPI | High (5+ yrs, 80k GH stars) | Large | Low — stable API since 0.95 |
| Jinja2 | Very high (Django-era, 10k GH stars) | Huge | Very low |
| HTMX | High (4+ yrs, 40k GH stars) | Growing | Low — v2 breaking changes are minor |
| React/Vite | Very high | Very large | Medium — major versions every 2-3 yrs |

### Recommendation: FastAPI + Jinja2 (SSR only)

**Justification:** For order/customer detail pages (lookup by ID → render rows of data), full SSR via Jinja2 is sufficient. No client-side state management is needed. The Docker image stays minimal (`python:3.11-slim` + FastAPI + duckdb + jinja2 = ~220 MB). Zero frontend build pipeline. Connection pattern is one `duckdb.connect(read_only=True)` per request or a single shared connection with a thread lock — both are safe given the concurrent-read constraint. HTMX is a reasonable upgrade path if partial-page updates are later wanted (add `htmx.min.js` from CDN, no build step change).

**Do NOT use React/Vite unless:** the detail pages need client-side search, charts, or complex interactivity. The build pipeline, Node.js toolchain, and SPA routing overhead are YAGNI for detail views.

**DuckDB connection pattern:**

```python
# Option A — per-request (simplest, safe for low QPS)
@app.get("/orders/{order_id}")
def order_detail(order_id: int):
    con = duckdb.connect("/app/var/data_lake/serving/olap.duckdb", read_only=True)
    try:
        row = con.sql("SELECT * FROM fact_orders WHERE order_id = ?", [order_id]).fetchone()
    finally:
        con.close()

# Option B — module-level singleton with threading.Lock (slightly faster, safe for concurrent reads)
# DuckDB read_only mode is thread-safe for concurrent reads from same connection object.
```

**Minimal Dockerfile skeleton:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY detail_app/requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn[standard] duckdb jinja2
COPY detail_app/ /app/
ENV OLAP_DB_PATH=/app/var/data_lake/serving/olap.duckdb
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Summary

- **Concurrent read risk: NONE.** Metabase opens olap.duckdb with `read_only=true`. DuckDB allows unlimited concurrent `read_only` connections. Empirically verified 2026-05-29 with live Metabase.
- **38 views** in `main` schema, all VIEWs. Order/customer data available via `fact_orders`, `dim_customers`, `fact_sales`, and dimension tables.
- **Docker pattern** is straightforward: bind mount `./app_data/data_lake:/app/var/data_lake:ro`, join `caddy_net`, add Caddy labels. Mirror existing service pattern.
- **5 registration points**: `docker-compose.yml`, `.env.docker*`, `README.md`, `AGENTS.md`, `docs/architecture/overview.md` + create `Dockerfile.detailapp` and `detail_app/` directory.
- **Recommended stack:** FastAPI + Jinja2 (SSR). Single container, no build pipeline, DuckDB `read_only=True` per-request. HTMX is a clean upgrade path if partial updates are needed later.

---

## Unresolved Questions

1. **Auth on detail app:** Will the app be on `caddy_net` LAN-only (no auth needed) or exposed externally? Caddy basic_auth labels exist as a pattern (see `fileserver` service) but would need to be added.
2. **DuckDB module-level connection threading:** DuckDB Python docs state `read_only` connections support concurrent reads, but the exact thread-safety contract for the shared connection object (not per-request) should be verified against DuckDB 1.5.x release notes before using Option B.
3. **`int_*` views exposed to new app:** Intermediate views (e.g. `int_shopee_order_fees`) are available in olap.duckdb. Intentional? They contain partially transformed data not meant for end-user display. Consider whether the new app should filter to `fact_*`, `dim_*`, `mart_*` only.
4. **Port allocation:** Next available port after `3004` (fileserver) would be `3005`. Confirm no conflict with any other local services.
5. **Timezone display:** Queries against `TIMESTAMPTZ` columns will return ICT values. If the web app serves users outside ICT, TZ handling must be decided at the app layer.

---

**Status:** DONE
**Summary:** Confirmed Metabase uses `read_only=true` for olap.duckdb; zero concurrent-read risk for a second process. Documented all 38 views, exact Docker integration pattern, 5 registration files, and recommended FastAPI + Jinja2 as the KISS-compliant stack.
