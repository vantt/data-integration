# Code Review — CRM Backup + Restore-Verify Tooling

**Reviewer:** code-reviewer · **Date:** 2026-06-24 · **Scope:** `crm/ops/backup_crm.py`, `crm/ops/restore_verify_crm.py`, `crm/entrypoint.sh`, `docker-compose.yml` (crm/crm_backups), `scripts/backup/backup.sh` + `backup.ps1` (disabled legs)

**Method:** read all changed files; empirically reproduced FTS5 shadow-table behavior, checksum determinism, and online-backup page-copy semantics in a throwaway SQLite (results inline). Live testing already covered: real prod backup (7572 parties, gate passed, no downtime), drill PASS + 4 negative tampers. This review focuses on what live testing did NOT exercise.

---

## Verdict (TL;DR)

The **backup half is sound and trustworthy as-is.** The gate logic is correct, the online-backup snapshot is page-consistent, and the FTS5 shadow-table concern (item 1) turns out to be a *non*-issue within a single backup run (proven below). 

The **restore-verify drill has one HIGH defect that makes part of it vacuous**: Gate B's "write→read→delete round-trip" hits a **non-existent endpoint** (`POST /api/tags` does not exist) and silently soft-skips — so the write path the docstring claims to prove is **never actually tested**. The drill still PASSes, giving false assurance on writability. The 4 negative tampers only exercise Gate A (file integrity), not the write path, so this gap was invisible in live testing.

**Must-fix before fully trusting in production:**
1. **[HIGH]** Fix the drill write-probe endpoint (or remove the false claim). Currently vacuous.
2. **[HIGH]** Restore an automated/scheduled CRM backup — the disabled `crm_data` leg leaves CRM with **no scheduled backup** (on-demand only).

Everything else is MEDIUM/LOW (hardening / nice-to-have).

---

## CRITICAL

None. No data-loss, isolation-breach, or prod-mutation path found. Isolation of the drill is genuinely solid (see HIGH-3 for the one residual gap).

---

## HIGH

### H1 — Gate B write round-trip is vacuous: wrong endpoint, silently skipped
`crm/ops/restore_verify_crm.py:182-195` (`_write_delete_roundtrip`) POSTs to `/api/tags`. **No such route exists.** Verified the only tag-write routes are:
- `POST /api/parties/{id}/tags` (`customer360_handler.py:197`)
- `POST /settings/tags` (`screen_management.py:456`)
- `POST /customers/{party_id}/tags` (`screen_modals_party.py:302`)

A POST to `/api/tags` returns 404 → falls into the bare `except Exception` (line 192) → prints `write-probe skipped … read-path verified` → returns. The docstring (lines 12-14, 183) claims a write→read→delete round-trip "proves the restored schema is writable", but **no write ever happens**. The drill PASSes regardless. The negative tampers don't catch this because they only target Gate A integrity, never the write path.

Impact: a restored DB that is read-only / has a broken write path / failed a write-affecting migration would still PASS the drill. This is the single biggest trust gap.

**Fix:** point the probe at a real write endpoint and make a missing/!2xx response a HARD fail (not a soft-skip). E.g. POST to `/api/parties/{id}/tags` for a known party_id pulled from the snapshot, assert 200/201, then DELETE and assert. Note `require_api_token` is *bypassed* when `CRM_API_TOKEN` is unset (`auth_dependency.py:8`), so the ephemeral app needs no token — good — but the route must be correct. Do **not** keep a catch-all `except: skip` that turns any failure into a pass.

### H2 — No scheduled CRM backup after this change (operational regression)
`scripts/backup/backup.sh:152` removed `crm_data` from the auto-backup loop; `backup.ps1:100-105` disabled the raw copy. The new `backup_crm.py` is **on-demand only** (CLI / `docker exec`); nothing schedules it. Net effect: until a cron/Task-Scheduler/Dagster trigger is wired, **CRM has zero automated backups.** The old (WAL-unsafe) copy was at least running on a schedule.

This is correct *design* (raw WAL copy was unsafe) but an operational hole. Severity HIGH because silent backup stoppage is exactly the "zombie-run" failure class the alert code (`_alert`) was written to prevent — yet there's nothing to alert on if nothing runs.

**Fix:** wire `python -m crm.ops.backup_crm --data-dir /data --dest /backups` into the existing scheduler (Task Scheduler on the host calling `docker exec crm …`, or a Dagster schedule). Track "last successful backup age" and alert if it exceeds N hours. Document the trigger in the runbook.

### H3 — Prod-untouched assertion uses size+mtime only; one isolation gap is real but bounded
`restore_verify_crm.py:123-126` fingerprints prod via `stat -c %s-%Y /data/crm.db` (size + mtime seconds). This is weaker than a checksum:
- A same-size in-place page overwrite within the same wall-clock second would not change size or mtime-seconds → undetected. In practice the drill never mounts `crm_data` into the ephemeral container (verified: `gate_b_functional` mounts only `dest:/data`, lines 138-143; no `crm_data`, no `caddy_net`, distinct name/port), so prod can only change via *normal prod traffic*, not via the drill. The fingerprint is a smoke-detector for "did I accidentally touch prod", and for that it's adequate-but-coarse.

Residual real gap: the assertion only covers `crm.db`, not `cache.db`, and not the WAL/SHM sidecars. Low practical risk given the isolation, but the claim "prod is never touched" is asserted more narrowly than stated.

**Fix (cheap):** add `crm.db-wal` to the fingerprint, or upgrade to a content hash via `docker exec crm sha256sum /data/crm.db`. Acknowledge in the docstring that the guarantee is "drill never mounts prod volume" (the real guarantee) rather than relying on mtime.

---

## MEDIUM

### M1 — FTS5 shadow tables ARE profiled, but it's safe within a backup run (documented so nobody "fixes" it wrongly)
`_user_tables` (`backup_crm.py:42-47`) filters `type='table' AND name NOT LIKE 'sqlite_%'`. **FTS5 shadow tables are `type='table'` and are NOT named `sqlite_*`** — verified they all pass the filter: `crm_party_search`, `crm_party_search_{data,idx,docsize,config,content}` all get profiled. The `_data`/`_idx` shadow tables hold serialized B-tree **blobs** whose byte layout is insert-order-dependent (verified: same logical FTS content inserted in different order → different `_data` checksum).

**Why this is NOT a bug here:** the gate compares the *live source* against an *online-backup snapshot of that same source*. `src.backup(dst)` copies pages verbatim (verified: source `_data` checksum == snapshot `_data` checksum after `.backup()`). So within one backup run the shadow blobs are byte-identical and the gate matches. Gate A in the drill compares the restored file against the *snapshot* profile stored in the manifest — also the same bytes. So no false-diff in the current flow. Live testing confirming a pass is consistent with this.

**Latent risk to flag, not fix now:** if anyone ever changes the gate to compare a snapshot against a *separately rebuilt* index (e.g. re-running `search_index.py` then comparing), the `_data` checksum will diverge for identical logical content and produce spurious FAILs. Also FTS5 `'optimize'`/`'merge'` commands rewrite `_data` — verified they change the blob. Recommend: **skip FTS5 shadow tables and the FTS5 main virtual table from content checksum** (keep them in the page-level snapshot, which is what actually restores them), and checksum only real base tables. Detect via `sqlite_master.sql LIKE '%USING fts5%'` for the main vtable and the `_data/_idx/_docsize/_config/_content` suffix family. This makes the manifest stable and intent-clear. Low urgency because current flow is safe.

### M2 — TOCTOU between source profile and snapshot under concurrent writes
`backup_crm.py:205-211`: order is `_checkpoint` → `profile_db(source)` → `_snapshot(source→dst)` → `profile_db(dst)` → gate. The source is profiled at instant T1; the snapshot is taken at T2 > T1. Under live write traffic, a commit between T1 and T2 means the snapshot legitimately differs from the T1 profile → the gate raises `snapshot != source` and **the whole backup FAILS** (for crm.db). This is a *false negative* (a perfectly good snapshot rejected), not a corruption risk.

The inverse (a write that makes a stale snapshot spuriously "match") is not possible here — the checksum is content-based, so any divergence is caught; it just over-rejects rather than under-rejects. Fail-closed is the safe direction, but on a busy CRM this could make backups flaky.

**Why live test passed:** the real run happened to have no conflicting commit in the T1→T2 window (millisecond window on a 7572-row DB). On a busier moment it can fail.

**Fix options:** (a) profile the source *from the snapshot's own consistent read transaction* — i.e. snapshot first, then compare snapshot against a `BEGIN IMMEDIATE`/deferred-read snapshot of source taken at the same logical point; or (b) accept the fail-closed behavior but **retry once** on a gate mismatch (re-snapshot) before declaring failure, since a second attempt is very likely to land in a quiet window; or (c) document that the gate is "snapshot self-consistent + integrity ok" and treat a source/snapshot delta as a *retryable* condition rather than a hard FAIL. At minimum, log the specific diff so a flaky failure is diagnosable.

### M3 — `_resolve_backup_volume` picks `prefixed[0]` blindly
`restore_verify_crm.py:68-76`: `prefixed = [n for n in names if n.endswith("_crm_backups")]; return prefixed[0]`. If two compose projects each have a `*_crm_backups` volume (e.g. `data-integration_crm_backups` and a stale `data-integration2_crm_backups`), `prefixed[0]` is whichever Docker lists first — nondeterministic, and could select the wrong project's backups. Then the drill verifies the wrong CRM's data and reports PASS.

**Fix:** prefer the volume matching the actual compose project name (derive from repo dir name `REPO.name`, i.e. `data-integration_crm_backups`), and `_fail` with the candidate list if >1 match remains. Don't silently `[0]`.

### M4 — Rotation `_rotate(keep-1)` before write: safe but can over-delete on the boundary
`backup_crm.py:187` calls `_rotate(dest, keep - 1)` *before* writing the new backup, reasoning "make room for the new one so final count == keep". Logic check: with keep=7, it keeps 6 existing, then writes 1 → 7. Correct in the happy path. But if the new backup then FAILS on source-of-truth (line 224 raises), you've already deleted the 7th-oldest and are left with 6 good + 1 failed-dir. Not catastrophic (6 good remain), but the failed dir persists (manifest written at line 223 before raise) and isn't cleaned up, so it counts toward the next rotation and can displace a good backup over time. The shell scripts handle this (they remove failed dirs); `backup_crm.py` does not.

**Fix:** rotate *after* a successful write, not before; or on source-of-truth failure, `shutil.rmtree(out_dir)` before re-raising so failed dirs never accumulate. The disk pre-flight (2× headroom, line 153) already guarantees room for one more, so rotating after is safe.

### M5 — `migration_head` ordering relies on lexical version strings
`backup_crm.py:66-74` selects `MAX(version)` from `schema_migrations` where `version` is now the full filename TEXT (`migrations.py:118`, e.g. `0026_consent_contact_enum.up.sql`). `ORDER BY version DESC` is lexical. Works while prefixes are zero-padded 4-digit (`0001`..`9999`). Crosses a correctness boundary at `10000_`, and any non-padded or differently-prefixed migration name would mis-sort. Cosmetic today (head is informational, not gated), but flag it.

**Fix:** none required now; if migration count could exceed 9999 or naming changes, sort by numeric prefix. Document the assumption.

---

## LOW

### L1 — Drill imports private `backup_crm._tables_match` (underscore coupling)
`restore_verify_crm.py:116` calls `backup_crm._tables_match(...)`. Reaching into another module's underscore-private API couples the drill to backup internals; a rename breaks the drill silently at runtime (it's only exercised when a tamper or real diff occurs). Promote `_tables_match` and `profile_db` to the module's documented public surface (drop the underscore on `_tables_match`, or expose a thin public `compare_profiles`).

### L2 — `latest_backup()` can select a failed/partial backup
`restore_verify_crm.py:80-86` picks `stamps[-1]` (lexical max) regardless of manifest `ok`/`partial`. A source-of-truth failure still leaves a timestamped dir with a manifest (backup_crm.py:223), so the drill could target a known-bad backup. Gate A would then correctly fail it, but the operator sees a confusing failure on the "latest" rather than the drill skipping to the last good one. Consider: read each candidate's manifest and pick the newest with `crm.db.ok == true`.

### L3 — `latest_backup` mounts volume without `:ro`
`restore_verify_crm.py:81` mounts `{BACKUP_VOL}:/b` (rw) for a read-only `ls`; `export_backup` correctly uses `:ro` (line 92). Add `:ro` to `latest_backup` for consistency and defense-in-depth.

### L4 — `image_digest` recorded as `None`
`backup_crm.py:196`: `os.environ.get("CRM_IMAGE_DIGEST")` — this env var is not set in the compose `crm` service (verified: not present in docker-compose.yml crm env). So every manifest records `image_digest: null`, and the drill's intent to "boot the same image the backup was taken under" can't be asserted. The drill instead uses `docker inspect crm` for the *current* prod image (line 239), which may differ from the image at backup time. Either set `CRM_IMAGE_DIGEST` in the crm service env, or drop the field to avoid implying a guarantee that isn't there.

### L5 — Windows host-bind `dest:/data` for the ephemeral container + Defender
`restore_verify_crm.py:48` `TMP_HOST = REPO/"app_data"/"crm_verify_tmp"` is a Windows host path bind-mounted into the ephemeral container (line 139 `dest:/data`). SQLite over a 9p/host-bind on Windows is exactly the locking class the project moved *away* from (memory: crm_data is a named volume specifically to avoid Windows filesystem lock issues). The ephemeral boot runs migrations (entrypoint Step 1) which write to this host-bind crm.db. Risk: intermittent SQLite lock/`disk I/O error` under Defender scanning → flaky drill failures unrelated to backup correctness. Live test passed, but this is a known-flaky surface. Consider exporting into a named volume instead of a host bind, or add `app_data/crm_verify_tmp` to Defender exclusions and document it.

### L6 — `entrypoint.sh` runs migrations in VERIFY_MODE → mutates restored DB after Gate A
`crm/entrypoint.sh:22-23` skips reverse_etl + sync_parties under `CRM_VERIFY_MODE=1` (correct — those rewrite the DBs). But Step 1 migrations (line 15) still run and **write** to the restored crm.db. This is intentional/documented ("validates the schema head") and ordering is safe because Gate A runs pre-boot (`restore_verify_crm.py` docstring lines 9-11, gate_a before gate_b). Just confirming: do not move Gate A after boot, or the sha256/integrity check will fail on the migration-mutated header. Fine as-is; flag so it isn't accidentally reordered. (Edge: if a restored backup is at an *older* migration head than the current image's migration files, the verify boot will silently apply newer migrations — meaning the drill proves "old backup + new migrations boots", not "backup boots as-is". Acceptable, but the printed `head=` is the pre-migration head, which is slightly misleading after boot.)

---

## Item-by-item response to review focus

1. **Gate correctness / FTS5:** `_tables_match` is sound. FTS5 shadow tables are profiled but safe within a single run (page-copy keeps blobs identical) — proven. Views are excluded (type='view'). No WITHOUT ROWID / virtual-table breakage of `SELECT *`/COUNT observed. `wal_checkpoint(PASSIVE)` is **not** a no-op for assurance: it's belt-and-suspenders only — the online-backup API already reads committed WAL pages, so the checkpoint is a pure optimization (correctly documented as such, lines 109-111). It does not give *false* assurance. → See M1.

2. **Concurrent writes / TOCTOU:** real, but fail-*closed* (over-rejects, never accepts a stale match, because checksums are content-based). Not a corruption risk; a flakiness risk. → M2.

3. **Drill prod-safety:** isolation is genuinely real — ephemeral container never mounts crm_data/caddy_net, distinct name+port. The only weaknesses are the coarse size+mtime fingerprint (H3) and `prefixed[0]` (M3). No path found where the drill writes prod crm_data.

4. **Error handling / partial states:** rotation ordering (M4) can leak failed dirs; cleanup of temp dirs + ephemeral container is solid (atexit + SIGINT/SIGTERM handlers, lines 231-233; `_cleanup` removes container + temp paths). `_tamper` value-branch is correct (picks a non-id column, falls back to row-delete on type error, lines 205-212) — but moot for trust since the negative tests only validate Gate A, not the (broken) write path.

5. **Auto-backup gap:** confirmed — CRM now has no scheduled backup. → H2.

6. **DRY/KISS/edge:** private-import coupling (L1), Windows host-bind (L5), `data-integration` hardcoding (M3), image-digest None (L4) all confirmed.

---

## Must-fix before trusting in production
1. **H1** — Fix Gate B write-probe endpoint + make it hard-fail. The drill currently does not verify writability despite claiming to.
2. **H2** — Schedule `backup_crm.py` + alert on backup-age. No automated CRM backup currently runs.

## Nice-to-have (hardening)
- H3 (fingerprint cache.db + wal / use content hash), M1 (skip FTS5 from checksum to future-proof), M2 (retry-on-gate-mismatch for busy-DB flakiness), M3 (project-name-aware volume resolve), M4 (rotate after success / clean failed dirs), L1–L6.

---

## Unresolved questions
1. **Scheduling intent for H2:** is the new backup meant to be triggered by host Task Scheduler (`docker exec crm python -m crm.ops.backup_crm`) or by a Dagster schedule? That choice changes where the backup-age alert should live.
2. **Was the write round-trip ever expected to pass?** If the drill's live PASS was read as "write path verified", the team should re-run after H1 — current PASS does not cover writes.
3. **`CRM_IMAGE_DIGEST`** — is pinning the backup-time image a real requirement (L4), or should the field be dropped?

**Status:** DONE
**Verdict:** The backup half is trustworthy as-is (gate logic correct, FTS5 concern empirically cleared, snapshot consistent). The restore-verify drill is **partially trustworthy** — file-integrity (Gate A) and isolation are solid and proven, but Gate B's write verification is **vacuous** (wrong endpoint, silent skip) so "restores to a *writable* CRM" is unproven. Two must-fixes before full trust: **H1** (fix the drill write-probe to a real endpoint + hard-fail) and **H2** (restore an automated, alerted CRM backup — currently none runs on a schedule).
