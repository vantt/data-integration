# CRM Sub-project — Agent Rules

Internal CRM OLTP sub-project. Read global `AGENTS.md` at repo root first — this file adds CRM-specific constraints only.

## Boundary rule

Go app, migrations, Python sync, and SQLite data files live ONLY under `crm/`. Never cross-write into `ingestion/`, `transformation/`, `orchestration/`, `detailView/`, or any other sub-project.

## Stack

| Layer | Choice |
|---|---|
| App | Go — chi router, sqlc, golang-migrate |
| Reverse-ETL | Python — reads `olap.duckdb` read-only |
| DB owned | `data/crm.db` — SQLite WAL |
| DB cache | `data/cache.db` — warehouse read-cache, ATTACHed read-only |

## Conventions

**TIMESTAMPTZ discipline** — store UTC ISO-8601 (TEXT in SQLite); display Asia/Ho_Chi_Minh (ICT) at serving layer. Never store local time.

**Money** — VND as INTEGER (no decimals).

**JSON** — use SQLite JSON1 extension; store as TEXT column typed `JSON`.

**Table prefixes** — `crm_*` for owned tables; `wh_*` for warehouse-cache tables in `cache.db`.

**Per-connection PRAGMAs** (set on every connection open):
```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
```

**Cross-DB boundary** — NO foreign keys across `crm.db` ↔ `cache.db` ATTACH boundary. Link by `customer_id` value only (soft reference).

## Folder layout

```
crm/
├── app/cmd/server/             # Go main
├── app/internal/domain/        # entities, rules
├── app/internal/ports/         # interfaces
├── app/internal/adapters/inbound/http/
├── app/internal/adapters/outbound/sqlite/
├── app/internal/adapters/outbound/sapo/
├── migrations/                 # SQL migration files
├── sync/                       # Python reverse-ETL
└── data/                       # runtime SQLite (gitignored)
```

## Plans & design

Full schema design and phase breakdown: `plans/260613-1133-internal-crm-oltp-schema/plan.md`
