# Phase 01 — Rename `sapo_assets.py` → `sapo_v2_assets.py`

**Priority:** Low (naming consistency) | **Status:** ✅ DONE (2026-06-24)

> **Completion note:** Renamed via `git mv`; `key_prefix=["sapo"]` left untouched (family namespace future-proofs Sapo v3). Updated imports in `definitions.py`, `asset_checks/__init__.py`, smoke test + 4 doc/comment refs. Validated: `py_compile` OK on all 6 files; renamed module imports with **unchanged asset key** `sapo/ingest_sapo_v2_orders_batch_asset`; `grep` source-clean. Side note: `orchestration/config/ingestion_sla.yaml` has a UTF-8 BOM that stricter PyYAML rejects (pre-existing, prod tolerates it) — separate minor item, not addressed here.
**Context:** [plan](plan.md) · [audit report](../reports/full-stack-health-audit-datapipeline-to-crm-260624-1119-report.md)

## Overview
Module holds only Sapo **v2** assets (all functions already `ingest_sapo_v2_*`, `key_prefix=["sapo"]`). Filename `sapo_assets.py` is stale vs the `source_system = sapo_v2` convention. Rename file + all import sites.

## Key insight (why safe)
- Asset keys derive from `@asset` decorators (`key_prefix` + function name), **NOT** the filename → renaming the file does **not** change asset keys → **no cursor/state loss, no re-materialization**.
- The internal `import run_sapo_v2_*` lines at top of the module are unaffected (they import sibling `ingestion/` entry scripts, not this file).
- **Risk:** Dagster loads all assets as one unit — any missed attribute ref crashes startup. All runtime call sites MUST update in the same commit (atomic).

## Related code files

**Rename (git mv):**
- `orchestration/assets/sapo_assets.py` → `orchestration/assets/sapo_v2_assets.py`

**Modify — runtime (blocking, atomic):**
- `orchestration/definitions.py` — import L31; module list L46; attr refs L82, L96, L180–184, L223 (`sapo_assets.` → `sapo_v2_assets.`)
- `orchestration/asset_checks/__init__.py` — import L31; refs L37–42
- `orchestration/asset_checks/__tests__/test_check_factories_smoke.py` — imports/refs L161,164,174,178,190,193,209,212,226,229

**Modify — comments/docs (non-blocking, do for accuracy):**
- `orchestration/ops/dlt_metrics.py:3`
- `orchestration/assets/hug_assets.py:3`
- `orchestration/docs/README.md:29`
- `docs/development/contributing.md:442`

## Implementation steps
1. `git mv orchestration/assets/sapo_assets.py orchestration/assets/sapo_v2_assets.py`
2. Update `definitions.py` import + all `sapo_assets.` attribute refs → `sapo_v2_assets.`
3. Update `asset_checks/__init__.py` import + refs.
4. Update smoke test imports/refs.
5. Update the 4 comment/doc references.
6. Validate (see below).
7. If `data_platform` container bakes orchestration code (Dockerfile.dataplatform) → `docker compose up -d --build data_platform`; if volume-mounted → restart only.

## Todo
- [ ] git mv file
- [ ] definitions.py (import + 7 ref blocks)
- [ ] asset_checks/__init__.py
- [ ] smoke test
- [ ] 4 doc/comment refs
- [ ] validate + (rebuild/restart) container

## Success criteria
- `grep -rn "sapo_assets" orchestration/` → 0 hits (only `sapo_v2_assets`).
- `python -m py_compile orchestration/assets/sapo_v2_assets.py orchestration/definitions.py orchestration/asset_checks/__init__.py` → exit 0.
- `dagster definitions validate` → "Definitions validated".
- Asset-checks smoke test passes.
- Dagster UI: all `sapo/ingest_sapo_v2_*` assets present with **same keys** (no orphaned/duplicated assets, cursors intact).

## Risks / mitigation
- **Missed ref → startup crash** → mitigate with `grep` success-criterion before restart.
- **Asset key change (if a decorator were edited by mistake)** → do NOT touch decorators/`key_prefix`; rename is file + imports only.
- Low blast radius overall; fully revertible via `git mv` back.
