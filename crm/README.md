# Internal CRM (OLTP)

Embedded SQLite WAL CRM for ~10 sales/care staff. Enriches and standardizes warehouse insights to drive re-sell: golden customer records, activity log, conversations, segments, campaigns, Sapo write-back. OLAP stays untouched — this app only reads the warehouse as a cache source.

## Folder layout

```
crm/
├── app/                        # FastAPI app (hexagonal)
│   ├── domain/                 # entities, ports
│   ├── application/            # services
│   ├── adapters/inbound/web/   # Jinja2/HTMX screens + fragments
│   └── adapters/outbound/sqlite/  # crm.db + cache.db queries
├── migrations/                 # SQL migration files (applied by app on startup)
├── sync/                       # Python reverse-ETL (warehouse → cache.db)
├── AGENTS.md
└── README.md
```

## Stack

| Layer | Choice |
|---|---|
| App | Python — FastAPI + Jinja2/HTMX, uvicorn |
| DB (owned) | SQLite WAL — `crm.db` (Docker named volume `crm_data`) |
| DB (cache) | SQLite WAL — `cache.db` (warehouse read-cache, ATTACHed read-only) |
| Reverse-ETL | Python — reads `olap.duckdb` read-only, writes `cache.db` |

## Admin refresh endpoint

Dagster triggers the reverse-ETL on demand via
`POST /admin/refresh` (header `X-Refresh-Token: $CRM_REFRESH_TOKEN`) after the
warehouse serving layer updates. Fire-and-forget: the refresh runs in a
background thread and the POST returns `202 {"status":"accepted",...}`
immediately, `409 {"status":"busy"}` if a refresh is already running, `401` on
bad token. Poll `GET /admin/refresh/status` for the last run's outcome
(`{"state":"idle|running|ok|error",...}`).

## Design & phases

→ `plans/260613-1133-internal-crm-oltp-schema/plan.md`
