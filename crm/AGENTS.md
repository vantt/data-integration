# CRM Sub-project — Agent Rules

Internal CRM OLTP sub-project. Read global `AGENTS.md` at repo root first — this file adds CRM-specific constraints only.

## Architecture & Clean Code Rules

### Hexagonal architecture — mandatory

**Every repository adapter must have a port.**
Before writing `class SQLiteXxxRepository`, create `crm/src/domain/ports/xxx_repository.py` with a `typing.Protocol` defining the public API. Services accept the Protocol type, never the concrete class. Check `domain/ports/` first — don't add a port that already exists.

**Single composition root.**
`crm/src/composition.py` is the ONLY place that imports concrete adapter classes and wires them to ports. All other code (`application/`, `adapters/inbound/`) depends on protocols/ports only. Never import a concrete SQLite or DuckDB adapter outside `composition.py`.

**No duplicate wiring.**
Each service or composite adapter is instantiated exactly once in `composition.py`. If two screens need the same combined service object, share one instance — don't construct identical objects twice.

**Cross-cutting composites.**
When 2+ screens need methods from multiple services (e.g., Profile + Tag + CustomField), use `_XxxComposite` in `composition.py` as a thin delegating adapter. Instantiate once; pass the same instance to all screens that need it. Do NOT add cross-cutting logic to `_XxxComposite` — it only delegates.

### Screen boundaries — typed protocols required

Every `make_xxx_router(svc: Any, ...)` parameter typed `Any` is a bug waiting to happen. For each service parameter passed into a screen factory:

1. Define a `typing.Protocol` in the same file (or in `screen_modal_shared.py` if shared across modals) that lists exactly the methods the screen calls.
2. Use the Protocol as the type annotation: `def make_xxx_router(templates, my_svc: MySvc, ...)`.
3. The Protocol lives in the **adapter layer** (`adapters/inbound/web/screens/...`), not in `domain/ports/`. It describes what the screen needs, not what the repo stores.

**Split read/write when access patterns differ.**
If a screen only reads, give it a narrower read-only protocol (e.g., `TaskQuerier` with `list_by_party`). If another screen also writes, give it `TaskCreator` separately. Never force a screen to accept a fat service interface just because another screen needs the write methods.

### Code placement rules

| Code type | Where it lives |
|---|---|
| Standalone CLI / ops scripts | `crm/ops/` |
| Functions imported by app code | proper module under `crm/src/` |
| Domain entities (pure dataclasses) | `crm/src/domain/entities/` |
| Port protocols | `crm/src/domain/ports/` |
| Business logic | `crm/src/application/` |
| HTTP/web handlers | `crm/src/adapters/inbound/` |
| DB adapters | `crm/src/adapters/outbound/` |

**Never mix library code into a CLI script.** If a CLI script contains a function (`render_html`, `parse_x`) that the app imports, extract that function to a proper `src/` module first; the CLI becomes a thin wrapper.

### Service & repository discipline

- Services (`application/`) accept **port protocols**, return **domain entities**. No HTTP, no SQLite, no template imports.
- Repositories (`adapters/outbound/`) accept a `sqlite3.Connection` or similar — not a service. Don't call services from repos.
- When adding a method to a service, verify the method name matches what the repository port actually exposes. A typo in a method name (`list_targets_by_campaign_and_status` vs `list_targets`) is a silent runtime bug.
- `domain/ports/` must not contain duplicate protocol definitions. If a port for `XxxRepository` exists in `xxx_repository.py`, do not redeclare it in `profile_repository.py` or elsewhere.

---

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
├── src/                        # FastAPI app (hexagonal) — Python port
│   ├── domain/                 # entities, ports
│   ├── application/            # services
│   ├── adapters/inbound/web/   # Jinja2/HTMX screens + fragments
│   ├── adapters/outbound/sqlite/  # crm.db + cache.db queries
│   └── adapters/outbound/duckdb/  # olap.duckdb read-only queries
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

Full convention for the Python UI layer: see AGENTS.md §Surface ID convention above and source banners in each template file. When creating or editing any Jinja2 template:

1. Add `{# @surface ID · Name ... #}` as **line 1** of the file (source banner).
2. Add `data-surface="ID"` on the **outermost element** of each top-level surface root.
3. Partials (HTMX fragments): banner only — no nested `data-surface` marker.
