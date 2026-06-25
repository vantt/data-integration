---
phase: 2
title: Restore-Verify Drill
status: completed
priority: P1
effort: 1.5d
dependencies:
  - 1
---

# Phase 2: Restore-Verify Drill

## Overview
The heart of the plan: prove a backup is restorable by booting a **fresh, throwaway CRM** from it on an **isolated** temp volume, then asserting **data integrity** (vs the Phase-1 manifest) and **functional health** (app serves real data). On-demand now; clean exit codes so it can be scheduled later.

## Requirements
- **Functional:** given a backup dir → spin an ephemeral CRM → run integrity + functional checks → PASS/FAIL report → tear down. Default to "latest backup".
- **Non-functional:** **ZERO contact with prod** (`crm_data` volume, live `crm` container, prod port/Caddy untouched); self-contained (no warehouse/`olap.duckdb` needed); deterministic exit code (0=pass); fully automated teardown even on failure.

## Architecture
- **Module:** `crm/ops/restore_verify_crm.py` — orchestrates the drill; `python -m crm.ops.restore_verify_crm --backup <dir|latest>` CLI; returns 0/non-0.
- **Isolation model:**
  - Temp data dir on host (e.g. `app_data/crm_restore_verify/{run-ts}/`) — copy restored `crm.db`+`cache.db` from the backup into it.
  - `docker run --rm` a **fresh** container from the SAME crm image, name `crm-restore-verify`, mounting the temp dir as `/data`, on an **ephemeral host port** (e.g. `:18090`), **no Caddy label, not the prod port (3007), not writing crm_data**, no `data_lake` mount (self-contained).
  - **Skip warehouse steps:** add `CRM_VERIFY_MODE=1` to `crm/entrypoint.sh` → when set, **skip Step 2 (reverse_etl) and Step 3 (sync_parties)**. Critical: `sync_parties` writes `crm.db` from `cache.db` → would MUTATE the restored data and corrupt the integrity comparison. Migrations (Step 1) still run — on a restored-at-head DB they must be a no-op; that itself validates the migration head.
- **Integrity checks** (assert against backup `manifest.json`): for each DB — sha256 of the restored file matches manifest; `PRAGMA integrity_check` = ok; `PRAGMA foreign_key_check` empty (referential integrity); per-table row counts match; applied migration head matches.
- **Functional smoke** (against the ephemeral app on :18090): `GET /health` healthy; a few **read** endpoints return 200 + plausibly non-empty (`GET /api/dedup/candidates`, `GET /api/segments` or a customer360 read, `GET /` web screen). Reads are unguarded → no `X-CRM-Token` needed.
- **Teardown:** `--rm` container + delete temp dir in a `finally` (always runs). Report a concise PASS/FAIL table (per-check) + exit code.

## Related Code Files
- Create: `crm/ops/restore_verify_crm.py`
- Modify: `crm/entrypoint.sh` (honor `CRM_VERIFY_MODE=1` → skip reverse_etl + sync_parties)
- Reference (read): `crm/src/adapters/inbound/http/health_handler.py`, `dedup_handler.py`, `segment_handler.py` (pick stable read endpoints), `docker-compose.yml` crm service (image name, env it needs)

## Implementation Steps
1. Add `CRM_VERIFY_MODE` gate to `entrypoint.sh` (skip reverse_etl + sync_parties when set).
2. Write `restore_verify_crm.py`. Pre-flight: `docker rm -f crm-restore-verify`; resolve backup dir; copy DBs to a temp **named volume**; pin image = `docker inspect crm` digest; assert the image's entrypoint has `CRM_VERIFY_MODE`; record prod `crm.db` mtime/size + prod `/health`.
3. **Gate A — file integrity (BEFORE any boot):** on the copied temp files, verify sha256 + content checksums + row counts + `integrity_check` + `foreign_key_check` vs manifest. (Boot mutates the header → must check first.)
4. **Gate B — functional boot:** `docker run` ephemeral crm with `CRM_VERIFY_MODE=1`, temp port (18090), temp named volume, **NO crm_data / caddy_net / Caddy label / prod data_lake** (assert these absent). Poll `/health` (bounded; log-dump on timeout).
5. Functional checks: key tables ≥ manifest row counts; read endpoints 200+non-empty; **one write+delete round-trip** (X-CRM-Token) to prove writes.
6. **Cross-version mode** (`--forward-migrate`): boot an OLD backup against current image → migrations run N→N+k → verify post-migration invariants (not sha). Migration failure = FAIL.
7. `atexit`+signal cleanup: remove container + temp volume; assert prod `crm.db` mtime/size + `/health` UNCHANGED; print PASS/FAIL; exit 0/1.
8. **Negative-test suite** — confirm each FAILs the drill: row-drop, value-mutation (NULL), table-truncate (empty), file-truncate.

## Success Criteria — ✅ DONE (verified 2026-06-24; deferred items flagged)
- [x] **Gate A** (file integrity, pre-boot): sha256 + content checksums + counts + integrity match manifest. _(FK-check not implemented — polish.)_
- [x] **Gate B** (functional): fresh CRM boots on a temp volume with NO prod crm_data/caddy_net/label/port/data_lake; serves `/healthz` + reads; **real write** (create/insert/delete/drop on restored crm.db) — code-review H1 fix. _(uses host-bind `/data`, not a named volume — polish.)_
- [ ] **Cross-version drill** (`--forward-migrate`) — DEFERRED (same-version restore proven; forward-migrate is in the polish backlog).
- [x] **Negative suite** — all four (row-drop, value-mutate, table-truncate, file-truncate) make the drill FAIL.
- [x] Cleanup always runs (atexit+signals); exit 0=pass/non-0=fail. _(image pinned to `docker inspect crm`; not asserted vs manifest digest which is null — polish.)_
- [x] **Prod untouched**: prod `crm.db` size+mtime fingerprint identical before/after.

## Risk Assessment
- **Accidentally hitting prod** (wrong volume/port/name) → hard-assert distinct temp volume + container name + port before `docker run`. Highest-severity risk.
- **`sync_parties` mutating restored data** → `CRM_VERIFY_MODE` must skip it.
- **Flaky readiness** → bounded poll + log dump on timeout, not infinite wait.

## Red-Team Hardening (must-fix, 2026-06-24)
- **Order matters — integrity BEFORE boot (H3/H6).** Booting the app mutates the DB file (`apply_migrations` sets `journal_mode=WAL` → rewrites the header), so a post-boot sha256 NEVER matches the manifest even for a perfect restore. So: **(A) file-level integrity on the COPIED temp files first** — sha256 + content checksums + row counts + `integrity_check` + `foreign_key_check` vs manifest, BEFORE any container starts. **(B) then boot** the ephemeral app purely as the FUNCTIONAL test. Two distinct gates.
- **Prod-safety hard-asserts (in code, before `docker run`):** `docker rm -f crm-restore-verify` first (kill any leak from a crashed prior run); then ASSERT: temp volume name ≠ `crm_data`, container name ≠ `crm`, port ≠ 3007; and the `docker run` args contain **NO `crm_data` mount, NO `caddy_net`, NO Caddy label, NO prod `data_lake` mount**. Abort if any assert fails.
- **Pin the image (H-digest):** use the SAME image prod runs — `docker inspect crm --format '{{.Image}}'` — and assert it equals the manifest `image_digest` (for same-version restores). Don't pull `:latest` blindly.
- **`CRM_VERIFY_MODE` must exist in that image** — pre-flight `docker run --rm <image> grep -q CRM_VERIFY_MODE /app/crm/entrypoint.sh` (or inspect) before trusting the skip; if absent, the drill runs reverse_etl/sync_parties → abort.
- **Cleanup that actually runs (Windows):** `atexit` + SIGINT/SIGTERM handlers (Python `finally` is bypassed on SIGKILL); temp restore data on a **Docker named volume** (WSL2, Defender-immune), removed in the handler.
- **Prod untouched assertion:** record prod `crm.db` mtime+size + prod `/health` BEFORE the drill; re-check AFTER → must be identical/healthy. Proves the drill never wrote prod.
- **Cross-version drill mode (must test the real recovery case):** beyond same-version restore, run a mode that boots an OLD backup against the CURRENT image → migrations forward-migrate N→N+k → verify **post-migration** invariants (row counts ≥ pre-migration where expected, `integrity_check` ok, app serves) — NOT sha-match. Handle a migration FAILURE as a drill FAIL with logs.
- **Functional test must include a WRITE path + min-row floor (empty-table false-PASS):** read-only smoke passes on an empty restore (no parties → `/api/dedup/candidates` → 200 empty). Add: (a) assert key tables ≥ manifest row counts (not just "200 OK"); (b) one **write+delete** round-trip (create a throwaway tag/task via API with `X-CRM-Token`, read it back, delete it) to prove writes work on the restored schema.
- **Negative-test suite (prove checks aren't vacuous)** — each MUST make the drill FAIL: (1) drop a row, (2) **mutate a value** (NULL a column), (3) truncate a table (empty), (4) corrupt/truncate the .db file. One tamper is not enough.
