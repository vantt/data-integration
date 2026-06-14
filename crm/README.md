# Internal CRM (OLTP)

Embedded SQLite WAL CRM for ~10 sales/care staff. Enriches and standardizes warehouse insights to drive re-sell: golden customer records, activity log, conversations, segments, campaigns, Sapo write-back. OLAP stays untouched — this app only reads the warehouse as a cache source.

## Folder layout

```
crm/
├── app/                        # Go hexagonal single-binary
│   ├── cmd/server/             # main entrypoint
│   └── internal/
│       ├── domain/             # entities, value objects, business rules
│       ├── ports/              # inbound + outbound interfaces
│       └── adapters/
│           ├── inbound/http/   # chi HTTP handlers
│           └── outbound/
│               ├── sqlite/     # crm.db + cache.db queries (sqlc)
│               └── sapo/       # Sapo API write-back client
├── migrations/                 # golang-migrate SQL files
├── sync/                       # Python reverse-ETL scripts (warehouse → cache.db)
├── data/                       # runtime SQLite files (gitignored)
├── AGENTS.md
└── README.md
```

## Stack

| Layer | Choice |
|---|---|
| App | Go, chi router, sqlc, golang-migrate |
| DB (owned) | SQLite WAL — `crm.db` |
| DB (cache) | SQLite WAL — `cache.db` (warehouse read-cache, ATTACH read-only) |
| Reverse-ETL | Python — reads `olap.duckdb` read-only, writes `cache.db` |

## Admin refresh endpoint

Dagster triggers the reverse-ETL + syncparties on demand via
`POST /admin/refresh` (header `X-Refresh-Token: $CRM_REFRESH_TOKEN`) after the
warehouse serving layer updates. Fire-and-forget: the refresh runs async on a
background goroutine and the POST returns `202 {"status":"accepted",...}`
immediately, `409 {"status":"busy"}` if a refresh is already running, `401` on
bad token. Poll `GET /admin/refresh/status` for the last run's outcome
(`{"state":"idle|running|ok|error",...}`).

## Design & phases

→ `plans/260613-1133-internal-crm-oltp-schema/plan.md`
