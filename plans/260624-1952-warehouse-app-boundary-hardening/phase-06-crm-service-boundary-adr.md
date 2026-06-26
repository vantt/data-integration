# Phase 06 — CRM Service-Boundary ADR

**Plan:** [Warehouse ↔ App Boundary Hardening](./plan.md)
**Tier:** 3 — Prep (design only, zero runtime change)
**Priority:** P2 · **Status:** Pending · **Effort:** ~3h

---

## Context Links

- Plan overview: `plans/260624-1952-warehouse-app-boundary-hardening/plan.md`
- Research findings: `plans/reports/from-research-to-planner-boundary-hardening-findings-260624-1952-report.md`
- ADR convention + index: `docs/decisions/README.md`
- Reference ADR format: `docs/decisions/005-dual-duckdb.md`
- Freshness SLA source of truth: `docs/analytics-handbook/semantic/freshness.md`
- CRM docker-compose: `docker-compose.yml:167–212`
- CRM data reader (de-facto contract): `crm/sync/duckdb_reader.py`
- Reverse-ETL orchestration: `crm/sync/reverse_etl_warehouse_to_crm.py:145–168`
- HTTP handler surface: `crm/src/adapters/inbound/http/` (14 files)
- Phase 02 output (to be created): `docs/analytics-handbook/contracts/crm-warehouse-consumption-contract.md`

---

## Overview

**What this phase does:** Author three documentation artifacts that formally record the CRM/warehouse relationship without touching any code or container configuration:

1. **ADR-015** (`docs/decisions/015-crm-service-boundary.md`) — architectural decision record keeping warehouse-as-platform and treating CRM as a formally-bounded independent service that *consumes* a stable published contract.
2. **Consumption-contract spec** (`docs/analytics-handbook/contracts/crm-warehouse-consumption-contract.md`) — machine-readable-enough prose spec of every data dependency CRM has on the warehouse.
3. **Readiness checklist** (embedded in ADR-015, Hệ quả section) — conditions that make a *future* physical split cheap; each maps to the phase that delivers it.

**What this phase does NOT do:** split services, move containers, migrate databases, change volume mounts, or create new infra. This is design synthesis, not implementation.

---

## Key Insights

1. **CRM already has a de-facto consumption contract** — `duckdb_reader.py` pinned column lists (`_DIM_CUSTOMERS_BASE_COLS` :61-72, `_DIM_CUSTOMERS_INSIGHT_COLS` :39-56, `_MART_PRODUCT_HEALTH_COLS` :75-85, `_MART_CUSTOMER_TIER_COLS` :88-108, `_MART_ACTION_QUEUE_COLS` :114-121, `_DIM_PRODUCTS_COLS` :125-133, `_FACT_ORDERS_COLS` :139-148, `_MART_DEADSTOCK_TARGET_COLS` :353-383). The contract spec just makes this *explicit and human-readable*.

2. **CRM's single inbound data dependency** is `olap.duckdb` at path `CRM_OLAP_PATH=/app/var/data_lake/serving/olap.duckdb` (`docker-compose.yml:179`). After Phase 04 adds `main_marts` aliases to `sapo_export_latest.duckdb`, repointing to the snapshot removes the live-parquet coupling. The fallback path already references `sapo_export_latest.duckdb` (`duckdb_reader.py:175–186`).

3. **CRM owns two databases:** `crm.db` (application state, named volume `crm_data`) and `cache.db` (same volume, `CRM_CACHE_DB=/data/cache.db`). Nothing in the warehouse writes these; ownership boundary is already clean.

4. **CRM HTTP surface is LAN-only via Caddy** (`crm.lan.fwg.vn`, `caddy_net`, `docker-compose.yml:198-212`). Auth: `X-Refresh-Token` guards `POST /admin/refresh`; `X-CRM-Token` guards `/api/*` mutations; `GET /admin/status` has no auth (LAN-only, acceptable). 13 handler modules + auth_dependency.

5. **No shared writable volume.** The data_lake mount is `:ro` (`docker-compose.yml:204`). The only coupling is a *read path* on `olap.duckdb`. Phase 04 resolves this by giving CRM a self-contained snapshot file.

6. **The monorepo cost is near-zero today.** CRM code lives in `crm/`, sync scripts in `crm/sync/`, migrations in `crm/migrations/`. There is no interleaving with warehouse Python. YAGNI: don't split what already has clean directory boundaries.

7. **ADR next sequence: 015** — `docs/decisions/014-source-system-combined-identifier.md` confirmed by glob. ADR-015 confirmed available.

---

## Requirements

### Functional

- F1. ADR-015 written in Vietnamese headers per project convention; status `Accepted`; cites `file:line` for all behavioral claims.
- F2. ADR records: (a) current state, (b) the decision (keep monorepo + bounded service), (c) the rationale (YAGNI + cost analysis), (d) consequences (readiness checklist), (e) split triggers (concrete, observable).
- F3. Consumption-contract spec covers: source file, marts consumed, pinned columns per mart, freshness SLA, trigger mechanism, CRM-owned datastores, HTTP surface summary.
- F4. Readiness checklist maps each condition to the phase that delivers it; phases 01-05 cover all items.
- F5. Contract spec location decided and justified (see Architecture section).
- F6. ADR-015 filename = `015-crm-service-boundary.md` (domain slug, no plan/phase numbers).
- F7. README.md in `docs/decisions/` updated with ADR-015 entry.

### Non-functional

- NF1. No code changes, no docker-compose changes, no volume changes.
- NF2. ADR < 120 lines; contract spec < 150 lines. KISS.
- NF3. All behavioral claims cite `file:line`.
- NF4. Contract spec must be durable: column names come from `duckdb_reader.py` constants, not hand-invented.

---

## Architecture

### Current state (before any phase)

```
Dagster pipeline
    │
    ├─► dbt build ──► parquet ──► olap.duckdb (glob views, live parquet deps)
    │                                   │
    │                           [CRM mounts :ro]
    │                           CRM_OLAP_PATH=/app/var/data_lake/serving/olap.duckdb
    │                                   │
    └─► crm_sync asset ──POST /admin/refresh──► CRM container
                                                   ├─ crm.db     (owned)
                                                   └─ cache.db   (owned)
```

**Problem:** `olap.duckdb` views reference parquet via glob; Metabase also holds a read connection → potential lock contention. CRM's data dependency is not formally documented; a dbt rename silently breaks a sync run.

### Designed boundary (after phases 01–05 complete)

```
Dagster pipeline
    │
    ├─► dbt build (contract:enforced) ──► parquet
    │       │
    │       └─► build_standalone_export ──► sapo_export_latest.duckdb
    │                (+ main_marts aliases)  (self-contained, no parquet glob)
    │                        │
    │               serving_version.json (phase 05)
    │                        │ poll
    └─► CRM container (independent restart cadence)
            │  reads sapo_export_latest.duckdb  (CRM_OLAP_PATH or fallback)
            ├─ crm.db     (owned, crm_data volume)
            └─ cache.db   (owned, crm_data volume)
            │
            HTTP surface (LAN only via Caddy):
            POST /admin/refresh   (X-Refresh-Token)
            GET  /admin/status    (no auth, LAN only)
            /api/*                (X-CRM-Token)
            /hug/*                (internal)
            + 9 domain handlers
```

**Why this is the split-ready shape:** CRM reads from a versioned self-contained file (not live parquet), polls a version marker (not a Dagster push), owns its two databases, and has no shared writable volume with the warehouse. A physical split would change: the volume mount path (env var swap) and the network route (make version file accessible over HTTP). That's it.

---

## Documents to Create

| File | Action | Notes |
|---|---|---|
| `docs/decisions/015-crm-service-boundary.md` | Create | ADR-015, Vietnamese headers |
| `docs/analytics-handbook/contracts/crm-warehouse-consumption-contract.md` | Create | New `contracts/` sub-dir |
| `docs/decisions/README.md` | Amend | Add ADR-015 to Mục lục under new section "App Boundaries" |

**Why `docs/analytics-handbook/contracts/` for the consumption spec, not `docs/decisions/`?**
ADRs record *decisions* (why we chose X). The consumption spec is a *living contract* (what data CRM needs, updated when `duckdb_reader.py` changes). Mixing static decisions with living specs muddies the ADR index. `docs/analytics-handbook/contracts/` co-locates it with semantic/, freshness.md, and other "what the data means" references — the logical home for CRM's data dependency inventory. New `contracts/` subdir is cheap to create and signals future contracts for other consumers (hug, Evidence, Rill).

**No code changes.** All `crm/` source files, `docker-compose.yml`, `duckdb_reader.py`, and orchestration files are read-only for this phase.

---

## ADR-015 Content Outline

The person executing this phase writes `docs/decisions/015-crm-service-boundary.md` following this structure (must match `005-dual-duckdb.md` format exactly):

```
# ADR-015: CRM service boundary — warehouse-as-platform with formally-bounded consumer

> **Trạng thái:** Accepted
> **Ngày:** {execution date}
> **Tham chiếu:** [plan.md](../../plans/260624-1952.../plan.md),
>   [duckdb_reader.py](../../crm/sync/duckdb_reader.py),
>   [docker-compose.yml:167-212](../../docker-compose.yml)

## Bối cảnh
- Current coupling: CRM reads olap.duckdb (live parquet glob) via :ro volume mount.
  No formal contract; dbt renames silently break sync until MissingColumnError fires.
  CRM trigger = best-effort fire-and-forget POST (crm_sync.py, never fails pipeline).
- Coupling cost today: LOW (single :ro path, clean dir boundaries, no shared writes).
- Split cost today: HIGH (would need snapshot export + version signaling + network path,
  none of which exist yet).
- Context: phases 01-05 of the boundary-hardening project deliver all pre-conditions.

## Quyết định
Keep warehouse and CRM in the same monorepo and same docker-compose.
Treat CRM as a formally-bounded independent service:
  - consumes a published, versioned snapshot (sapo_export_latest.duckdb post-phase-04)
  - via a stable column contract (duckdb_reader.py pinned lists)
  - triggered by a durable version poll (phase-05 serving_version.json)
  - owns its databases exclusively (crm_data volume)

## Lý do
1. YAGNI: no current driver justifies split cost (no DuckDB write contention from CRM,
   no independent deploy cadence requirement, no CRM load threatening pipeline).
2. Cost delta: after phases 01-05, the only remaining split cost is an env-var path
   swap + making serving_version.json network-accessible. Low; worth deferring.
3. Monorepo keeps cross-cutting changes (schema renames, new marts) atomic:
   one commit updates duckdb_reader.py + dbt model contract together.
4. Formal boundary gives 90% of the split's safety benefits at 0% of the ops cost.

## Hệ quả
### Readiness checklist (conditions for a cheap future split)
| Condition | Delivered by |
|---|---|
| dbt model contracts enforced (column-level schema guard at build time) | Phase 01 |
| Curated CRM exposure + published consumption-contract spec | Phase 02 |
| Lark alert on CRM refresh failure; persistent crm_etl_run health record | Phase 03 |
| CRM reads sapo_export_latest.duckdb (self-contained, no parquet glob) | Phase 04 |
| CRM polls serving_version.json (durable, self-healing trigger) | Phase 05 |
| No shared writable volume between warehouse and CRM | Already true |

All six conditions met → a physical split requires only:
  (a) change CRM_OLAP_PATH to a network-accessible URL or remote-mounted path
  (b) expose serving_version.json endpoint or file share

### Immediate consequences (this ADR)
- docs/analytics-handbook/contracts/ created; crm-warehouse-consumption-contract.md
  is the canonical record of what CRM reads; updated whenever duckdb_reader.py changes.
- ADR-015 added to docs/decisions/README.md under "App Boundaries".

## Khi nào xem xét lại
Split drivers (concrete, observable — YAGNI governs until one appears):
  1. DuckDB read-lock contention measurably degrades CRM refresh (>30s delay caused
     by warehouse writer holding exclusive lock during bootstrap_serving_views).
  2. CRM team needs deploy cadence independent of warehouse pipeline (multi-engineer,
     feature-flagged releases that cannot be coordinated in one compose file).
  3. CRM memory/CPU load (2g/1cpu limit, docker-compose.yml:173-174) threatens pipeline
     stability on shared host, requiring process isolation.
Until a driver is observed → keep monorepo.
```

---

## Consumption-Contract Spec Content Outline

`docs/analytics-handbook/contracts/crm-warehouse-consumption-contract.md`:

```markdown
# CRM ← Warehouse Consumption Contract

> Living document. Update when duckdb_reader.py column constants change.
> Source of truth for column lists: crm/sync/duckdb_reader.py

## Source file
After phase-04: sapo_export_latest.duckdb  (self-contained snapshot, no parquet deps)
Fallback (current): olap.duckdb via CRM_OLAP_PATH
Schema prefix: main_marts.*
Connection: read_only=True, TimeZone=Asia/Ho_Chi_Minh (duckdb_reader.py:160-161)

## Marts consumed + pinned columns
[table per mart, columns from duckdb_reader.py constants, file:line citation for each]

mart: main_marts.dim_customers  (two fetch modes)
  insight cols (duckdb_reader.py:39-56): customer_key, customer_id, value_group,
    customer_status, next_purchase_signal, predicted_next_purchase_date,
    avg_days_between_orders, avg_order_spend, discount_sensitivity, cancel_rate,
    last_purchased_sku, top_affinity_product, second_affinity_product,
    channel_preference, lifetime_contribution_margin, is_margin_negative
  base cols (duckdb_reader.py:61-72): customer_key, customer_id, customer_code,
    display_name (aliased from full_name), phone, email, customer_group,
    first_order_date, source_contact_quality, contact_quality

mart: main_marts.mart_product_health  (duckdb_reader.py:75-85)
mart: main_marts.mart_customer_tier   (duckdb_reader.py:88-108)
mart: main_marts.mart_customer_action_queue  (duckdb_reader.py:114-121)
mart: main_marts.dim_products         (duckdb_reader.py:125-133)
mart: main_marts.fact_orders          (duckdb_reader.py:139-148, incremental by date_key)
mart: main_marts.dim_deadstock_target (duckdb_reader.py:353-383)

## Freshness SLA (from docs/analytics-handbook/semantic/freshness.md)
dim_customers:  available by 07:00 ICT (sapo_batch_asset SLA 28h)
fact_orders:    available by 07:00 ICT (sapo_webhook_consumer SLA 12h)
mart_product_health / mart_customer_tier / mart_customer_action_queue: derived,
  available when dim_customers + upstream economics marts complete (07:30–08:30 ICT)

## Trigger mechanism
Phase-05 target: CRM polls serving_version.json; self-triggers refresh on new version.
Current: Dagster crm_sync asset fires POST /admin/refresh after build_serving_db completes
  (orchestration/assets/crm_sync.py, deps=[build_serving_db]).

## CRM-owned datastores (warehouse does NOT write these)
crm.db   — application state, Go service, crm_data named volume
cache.db — reverse-ETL cache (SQLite WAL), crm_data named volume
  schema: cache_schema.sql; health audit: wh_sync_run table (30-day trim)

## CRM HTTP surface (LAN-only, caddy_net, crm.lan.fwg.vn)
Auth model: X-Refresh-Token (POST /admin/refresh) | X-CRM-Token (/api/* mutations)
           unauthenticated: GET /admin/status, GET /health

Handlers (crm/src/adapters/inbound/http/):
  admin_handler, health_handler, insight_handler, json_api_mirror_handler,
  dataquality_handler, activity_handler, task_handler, conversation_handler,
  dedup_handler, customer360_handler, segment_handler, campaign_handler,
  auth_dependency (shared), __init__

## Invariants (never violated by warehouse changes)
- Warehouse never writes to crm_data volume
- Column renames in dbt models must be paired with updates to duckdb_reader.py constants
  (MissingColumnError fires within the same sync run — detected before data corruption)
- date_key is always ICT YYYYMMDD integer — do NOT recompute from ordered_at in CRM
- net_revenue is VAT-inclusive (embedded, not gross) — do NOT subtract VAT again
- realized_margin_pct is H010-corrected — use this, not gross_margin_pct
```

---

## Implementation Steps

1. **Verify ADR slot** — confirm `docs/decisions/014-source-system-combined-identifier.md` is the highest ADR; confirm 015 is available. (Already verified by glob.)

2. **Create `docs/analytics-handbook/contracts/` directory** — create `crm-warehouse-consumption-contract.md` from the outline above. Populate all column lists verbatim from `duckdb_reader.py` constants (cite `file:line` for each block). Do not paraphrase — copy column names exactly to make future diff of reader vs spec trivial.

3. **Write `docs/decisions/015-crm-service-boundary.md`** — follow the outline above; Vietnamese section headers; blockquote header with Trạng thái / Ngày / Tham chiếu. Keep under 120 lines.

4. **Amend `docs/decisions/README.md`** — add a new section `### App Boundaries` with entry `- [ADR-015: CRM service boundary — warehouse-as-platform](./015-crm-service-boundary.md)`.

5. **Cross-check** — verify every column name in the contract spec matches the current constant in `duckdb_reader.py`. Any mismatch = copy error; fix before committing.

6. **No other files changed.** Confirm by reviewing git diff before commit.

---

## Todo List

- [ ] Verify `docs/decisions/015-crm-service-boundary.md` slot is free (done in pre-read)
- [ ] Create `docs/analytics-handbook/contracts/` dir
- [ ] Write `docs/analytics-handbook/contracts/crm-warehouse-consumption-contract.md`
- [ ] Populate all 8 mart column lists verbatim from `duckdb_reader.py` with `file:line` citations
- [ ] Write `docs/decisions/015-crm-service-boundary.md` (Vietnamese headers, ≤120 lines)
- [ ] Amend `docs/decisions/README.md` — add ADR-015 under new "App Boundaries" section
- [ ] Verify column names in spec match reader constants exactly
- [ ] Confirm git diff shows only 3 files touched (two new, one amended)

---

## Success Criteria

- `docs/decisions/015-crm-service-boundary.md` exists, status Accepted, all behavioral claims cite `file:line`, Vietnamese headers match project convention.
- `docs/analytics-handbook/contracts/crm-warehouse-consumption-contract.md` exists, lists all 8 marts with column names matching `duckdb_reader.py` constants.
- `docs/decisions/README.md` contains ADR-015 entry under "App Boundaries".
- Zero code files modified; zero docker-compose changes; zero new Python modules.
- A reviewer reading ADR-015 can identify exactly when a physical split becomes justified, without guessing.
- A developer renaming a dbt mart column can check the contract spec to know which CRM file must also change.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Contract spec column list drifts from `duckdb_reader.py` immediately after writing | Medium | Low (doc only, no runtime) | Step 5 explicit cross-check; note in spec header "update when duckdb_reader.py changes" |
| ADR content is too abstract to be actionable (readiness checklist items vague) | Low | Medium | Each checklist row names the phase file explicitly; split triggers are phrased as observable conditions, not adjectives |
| `contracts/` subdir placement causes confusion (wrong home for doc) | Low | Low | Justified in "Documents to Create" section above; README in contracts/ can clarify scope |
| Phase 04/05 not yet done when ADR-015 is authored (CRM still reads olap.duckdb) | High | None (this is expected) | ADR-015 describes the *target* state and the readiness checklist; current state explicitly noted in Bối cảnh |

---

## Security Considerations

- `GET /admin/status` has no auth. Acceptable: LAN-only (`caddy_net`), status payload exposes sync timestamps and step names but no customer data. ADR-015 should note this as a known gap to address if CRM ever moves outside LAN.
- `X-Refresh-Token` and `X-CRM-Token` are shared secrets from `.env`; not baked into the tracked `docker-compose.yml` (`${CRM_REFRESH_TOKEN:?}` pattern at `:184`, `${CRM_API_TOKEN:?}` at `:186`). Contract spec should document auth model so a future split knows what to replicate.
- The consumption-contract spec should not include secret values — header names only (`X-Refresh-Token`, `X-CRM-Token`).

---

## Next Steps

- **Depends on (to be executed first):** Phase 02 (consumption-contract spec references the exposures file created there); Phase 04 (ADR-015 "target state" is the snapshot path); Phase 05 (ADR-015 trigger mechanism section describes version-poll).
- **This phase is the synthesis phase** — it can be drafted using phase 02/04/05 *plans* as input, but the final version should be updated once those phases are executed to reflect actual file paths and snapshot naming.
- **After this phase:** no immediate follow-on. The readiness checklist in ADR-015 is the long-term tracker; revisit when a split driver appears (per Khi nào xem xét lại).

---

## Unresolved Questions

1. **`mart_deadstock_target` mart name** — `_MART_DEADSTOCK_TARGET_COLS` at `duckdb_reader.py:353-383` is pinned, but the mart name (`dim_deadstock_target`? `mart_deadstock_targets`?) needs verification against the actual dbt model before the contract spec names it. Check `transformation/models/marts/` for the canonical SQL filename.
2. **`main_marts` alias availability in sapo_export_latest.duckdb** — Phase 04 adds these aliases to the standalone export; until Phase 04 ships, the contract spec's "source file" section must note that `main_marts.*` schema prefix requires olap.duckdb (not the snapshot). Clarify in the spec with a conditional note.
3. **`/admin/status` auth posture** — noted as LAN-acceptable in current design. If this ADR is reviewed by a security-minded team member, they may want a token added. Flag as a split-trigger pre-condition or a P3 hardening item?
