# detailView

Read-only web app that shows the **complete warehouse insight for ONE order or ONE customer**.
Operational apps (Sapo, MISA, Shopee) fragment this across screens and can't compute margin,
RFM, lifecycle, segmentation — the OLAP warehouse already does. Search by code/id → full detail page.

- **Stack:** FastAPI + Jinja2 + HTMX (no build step, single small container)
- **Data:** opens `data_lake/serving/olap.duckdb` with `read_only=True` (same DB Metabase reads; zero lock risk)
- **No auth** (LAN-only, behind Caddy at `detailview.local`)

## Architecture — hexagonal (ports & adapters)

```
app/
├── domain/           # pure: Order/Customer aggregates, value objects, ports.py (Protocols)
├── application/      # use-case services (orchestrate ports; no SQL/HTTP)
├── adapters/
│   ├── inbound/web/  # FastAPI routes + Jinja2 templates + HTMX + static
│   └── outbound/duckdb/  # read-only connection + repositories + SQL  (ONLY place with SQL)
├── composition.py    # wires adapters → ports (DI)
├── config.py         # env settings (OLAP_DB_PATH, APP_TZ, port)
└── main.py           # FastAPI factory + /healthz + thin /api/*
```

`domain/` and `application/` import **no** framework/DB (enforced by `tests/test_architecture.py`),
so the DuckDB adapter could be swapped (e.g. Postgres) without touching domain or UI.

## Endpoints
| Path | Purpose |
|---|---|
| `GET /` | Home (search) |
| `GET /search?mode=order\|customer&q=` | Resolve → HTMX redirect / dropdown / not-found |
| `GET /orders/{order_code}` | Order detail (sidebar + 8 tabs, HTMX) |
| `GET /orders/{order_code}/tab/{tab}` | Order tab partial |
| `GET /customers/{customer_id}` | Customer detail (sidebar + 4 tabs) |
| `GET /customers/{customer_id}/tab/{tab}` | Customer tab partial |
| `GET /api/orders/{code}`, `/api/customers/{id}` | Thin JSON mirror |
| `GET /healthz` | Liveness + required-view presence |

## Run in Docker (recommended — parquet is mounted)
Part of the root `docker-compose.yml` as service `detail_view`:
```bash
docker compose up -d --build detail_view
# → http://detailview.local  (Caddy)  or  http://localhost:3005
```

## Run locally (Windows dev)
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:OLAP_DB_PATH="D:\vantt\app\data-integration\app_data\data_lake\serving\olap.duckdb"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```
> Note: the serving views read parquet at the **container** path. On a bare Windows host without
> that parquet, `/healthz` and `/` work, but detail/search data renders only inside Docker (or
> against a host where the export parquet exists).

## Test
```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests -q
```

## Docs
- [docs/PRD.md](docs/PRD.md) — product + hexagonal architecture spec
- [docs/UI_SPECS.md](docs/UI_SPECS.md) — UI/UX spec + ASCII layouts (input for `claude design`)
- [docs/plan.md](docs/plan.md) — build plan & decisions
