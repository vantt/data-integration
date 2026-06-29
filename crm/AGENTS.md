# CRM Sub-project — Agent Rules

Internal CRM OLTP sub-project. Read global `AGENTS.md` at repo root first — this file adds CRM-specific constraints only.

## Boundary rule

Python app, migrations, Python sync, and SQLite data files live ONLY under `crm/`. Never cross-write into `ingestion/`, `transformation/`, `orchestration/`, `detailView/`, or any other sub-project.

## Stack

| Layer | Choice |
|---|---|
| App | Python — FastAPI + Jinja2/HTMX, uvicorn |
| Reverse-ETL | Python — reads `olap.duckdb` read-only |
| DB owned | `crm.db` — SQLite WAL (Docker named volume `crm_data`) |
| DB cache | `cache.db` — warehouse read-cache, ATTACHed read-only |

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
├── app/                        # FastAPI app (hexagonal)
│   ├── domain/                 # entities, ports
│   ├── application/            # services
│   ├── adapters/inbound/web/   # Jinja2/HTMX screens + fragments
│   └── adapters/outbound/sqlite/  # crm.db + cache.db queries
├── migrations/                 # SQL migration files
├── sync/                       # Python reverse-ETL (warehouse → cache.db)
└── docs/                       # UI spec, conventions
```

## Hug Database Table Ownership

Two SQLite databases serve the Hug subsystem. Changes to either schema must be
coordinated between the two.

| Database | Tables | Owner | Written by |
|----------|--------|-------|------------|
| `hug.db` | `hug_token`, `hug_customer_push` | Hug package | CLI mint tool (`hug_mint.py`), claim station handler |
| `crm.db` | `crm_hug_campaign`, `crm_hug_campaign_history`, `crm_hug_voucher_allocation`, `crm_identity_link` | CRM server | `HugCampaignRepositoryAdapter`, `HugVoucherRepositoryAdapter` |

**Why split?** `crm_hug_*` tables are owned by the CRM server (campaign admin UI,
voucher attribution screen). They live in `crm.db` to avoid coupling the Hug token
lifecycle (a separate, offline-capable process) to the CRM migration chain.
`hug.db` is written only by Hug-specific tooling; the CRM server reads it via a
separate connection (`hug_conn`) solely for token claim/mint screens.

## Plans & design

Full schema design and phase breakdown: `plans/260613-1133-internal-crm-oltp-schema/plan.md`

## Surface ID convention (`data-surface`)

Every UI surface defined in `docs/ui-spec/` has a stable ID (S01–S13, P01–P06, M01–M14, C01–C06). These IDs are injected as `data-surface="<ID>"` attributes into the root HTML element of each surface's `.templ` function. This lets you instantly locate a surface in both DevTools and source code.

**Spec index:** `docs/ui-spec/00-overview.md`

| Prefix | Spec folder | Template files |
|--------|------------|----------------|
| S (screen) | `docs/ui-spec/screens/` | one `XXXPage()` templ per screen |
| P (panel) | `docs/ui-spec/panels/` | `PXXXPanel()` templs in `customer_360.templ` |
| M (modal) | `docs/ui-spec/modals/` | `ModalXxx()` templs in `modals.templ`, `management_modals.templ` |
| C (component) | `docs/ui-spec/components/` | shared templs, mostly in `layout.templ` |

### Rule — MANDATORY when creating or editing a surface

1. **New screen** (`XXXPage` templ that calls `@AppShell`): add `data-surface="SXX"` to the `<div class="crm-page page-enter">` root element.
2. **New panel** (`PXXPanel` HTMX fragment): add `data-surface="PXX"` to the outermost HTML element. If the panel has conditional roots (if/else), wrap the entire body in `<div data-surface="PXX">...</div>`.
3. **New modal** (`ModalXxx` templ): add `data-surface="MXX"` to the `<div class="modal-scrim">` root element.
4. **New shared component** (`CXX`): add `data-surface="CXX"` to the component's root element.
5. **Before assigning a new ID**: check `docs/ui-spec/00-overview.md` to pick the correct ID and avoid collisions.

**Search pattern:** `grep -r 'data-surface="S01"' crm/src/` to instantly find any surface's template code.

### Python port (Jinja2 templates)

Full convention for the Python UI layer: **`docs/ui-conventions.md`** — surface map, banner template, `data-surface` rationale. When creating or editing any Jinja2 template:

1. Add `{# @surface ID · Name ... #}` as **line 1** of the file (source banner).
2. Add `data-surface="ID"` on the **outermost element** of each top-level surface root.
3. Partials (HTMX fragments): banner only — no nested `data-surface` marker.
4. When delegating UI work to sub-agents, tell them to read `docs/ui-conventions.md` first.
