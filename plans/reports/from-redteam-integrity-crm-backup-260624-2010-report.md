# Red-Team: CRM Backup / Restore-Verify Plan — Data-Integrity Attack Report

**Plan attacked:** `plans/260624-2010-crm-backup-checkpoint-restore-verify/` (plan.md + phase-01..04)  
**Grounding files read:** `crm/entrypoint.sh`, `crm/src/adapters/outbound/sqlite/migrations.py`, `scripts/backup/backup.sh`  
**Date:** 2026-06-24  
**Reviewer posture:** hostile, data-integrity only

---

## H1 — Source-Fidelity Gap: Manifest Computed FROM the Backup, Not Compared Against Live Source

**Hole (most dangerous).**  
Phase 1 writes `manifest.json` using the sha256 and row counts of the _backup files themselves_ at the moment of snapshot. There is **no comparison against the live source** at backup time. The manifest records what landed in the backup; it does not record what _should_ have landed.

**Concrete failure scenario.**  
Suppose `crm.db` has 12 000 party rows. The `sqlite3.Connection.backup()` call starts, but mid-flight the WAL contains un-checkpointed frames for 400 rows that are not yet visible to the read-only connection (see H2 below). The backup captures 11 600 rows. `manifest.json` records `crm_party: 11600`. Phase 2 restores, counts 11 600 rows, matches manifest — **PASS**. The data loss is invisible to every check in the plan.

**Why this slips past all proposed checks.**  
sha256 proves the backup file is intact since it was written. `integrity_check` proves internal B-tree consistency. Row counts match — because they were _measured from the backup_. FK check passes. Migration head matches. **None of these checks have access to ground truth.**

**Fix (Phase 1, manifest section).**  
Before calling `src.backup(dst)`, query the live source DB for row counts per table and record them separately in `manifest.json` as `source_row_counts`. After backup, compute `backup_row_counts`. Phase 2 must assert `backup_row_counts == source_row_counts`, not just `restored_row_counts == backup_row_counts`. Add the delta field explicitly: if `|source_total - backup_total| > 0` the backup script itself should WARN (or FAIL with a configurable tolerance). This closes the source-fidelity gap.

---

## H2 — WAL Consistency: Read-Only Open May Miss Un-Checkpointed Frames

**Hole.**  
Phase 1 opens each DB as `sqlite3.connect("file:{path}?mode=ro", uri=True)` then calls `src.backup(dst)`. The plan claims this is "page-consistent even under concurrent writes / WAL." That is _partially_ true but misleading.

**What SQLite's online backup API actually guarantees.**  
`Connection.backup()` uses the SQLite backup API, which takes a read-lock on the source and copies all pages. Under WAL, committed but un-checkpointed frames live in the `-wal` file. A reader opening `mode=ro` sees the WAL frames if `-shm` is available and readable; the backup API does copy WAL-modified pages as it reads them. However:

1. **`-shm` file and concurrent writes:** The `-shm` file (shared memory index into the WAL) is required for WAL to work with multiple processes. If the backup runs as a _separate process_ (`docker exec crm python …`) while the CRM uvicorn process is actively writing, Python's `sqlite3.backup()` in a `mode=ro` connection will snapshot a consistent point in time — but only the point in time when the backup _begins its first pass_. If the backup takes more than one pass (large DB), SQLite re-checks modified pages and re-copies them. That multi-pass behaviour is correct for _data_ but the plan does not specify a page-cache size that bounds passes; on a busy DB with high write throughput, the backup can spin many passes and still be consistent — but the plan gives no evidence the authors verified this in the WAL mode context.

2. **The real risk: `mode=ro` on a WAL DB that has no checkpoint.** If the WAL file has grown very large (e.g. 10 000 frames, no checkpoint ever run), the read-only connection must read through all WAL frames on every page lookup — this is slow but correct. **However**, if the WAL is corrupt or the `-wal` file is partially truncated (system crash mid-write), `mode=ro` open will fail or silently read stale data. The plan does not include a pre-backup `PRAGMA wal_checkpoint(PASSIVE)` or `PRAGMA wal_checkpoint(FULL)` health check on the live DB.

3. **The safety of skipping `wal_checkpoint(TRUNCATE)` before backup.** The plan explicitly avoids this (wisely — TRUNCATE blocks writers). But it also does _not_ verify that the WAL is accessible and un-corrupt before proceeding. A failed checkpoint from a prior crash could leave the WAL in a state where `integrity_check` passes on the live DB but the backup silently omits recent frames.

**Concrete failure scenario.**  
CRM crashes mid-write at 02:00. WAL is partially written. At 03:00 the backup job runs, opens `mode=ro`, SQLite auto-recovers the WAL on open (but only if it can acquire the write lock to roll back incomplete transactions — `mode=ro` prevents this). Result: `mode=ro` open succeeds but sees only the state _before the partial write_ — i.e. the backup silently omits the last N rows. `integrity_check` returns `ok` (the backed-up state is self-consistent). Row counts match manifest (measured from the same partial state). **PASS. Data lost.**

**Fix (Phase 1, backup mechanism).**  
Add a pre-backup health probe: open the DB read-write (briefly) with `PRAGMA wal_checkpoint(PASSIVE)` to flush as many WAL frames as possible without blocking, then verify `integrity_check=ok` on the live DB _before_ starting the backup. Record the checkpoint result in `manifest.json`. If checkpoint returns `busy_frames > 0` (frames it could not checkpoint because readers held them), log a warning — the backup may be slightly behind. If `integrity_check` fails on the live DB, abort the backup with a non-zero exit.

---

## H3 — Schema/Migration Drift on Restore: Old Backup + New Code = Mutated-Before-Verify

**Hole.**  
Phase 2 boots the restore container with the _current CRM image_ (same image tag as prod). `entrypoint.sh` step 1 runs `apply_migrations()` unconditionally before the app serves. If the backup was taken at migration head N=5 and code is now at N=8, migrations 6, 7, 8 run on the restored DB _before_ Phase 2's integrity checks execute.

**Concrete failure scenario.**  
Migration 0006 adds a `NOT NULL` column `consent_source` with a default. All existing rows get the default. The restored DB now has schema N=8. Phase 2 checks row counts — still matches manifest (row counts didn't change). sha256 of the _restored_ file does NOT match manifest (file was modified by migrations), but Phase 2's plan says "sha256 of the restored file matches manifest." This means Phase 2 **always FAILS sha256 on any backup older than the current head** — or worse, the plan author adds a carve-out "sha256 only checked if migration head matches" and the check becomes conditional and easy to misread.

**More dangerous variant.** Migration 0007 is destructive: `DROP TABLE hug_voucher_redemption; CREATE TABLE voucher_redemption ...` (rename with data migration). The data migration script has a bug and drops rows. Phase 2's row count check compares `restored_row_count` after migration against `manifest.json` `row_counts` from _before_ migration. They differ → FAIL. But the FAIL message says "row count mismatch" — ops assumes the backup is bad, uses an older backup, repeats, always fails. The real bug (broken migration) is never surfaced cleanly.

**The plan's stated mitigation** (phase-02, risk section): "Migrations (Step 1) still run — on a restored-at-head DB they must be a no-op." This is only true if the backup was taken at the current head. The plan does not handle the **cross-version restore** case at all.

**Fix (Phase 2).**  
- Record `image_tag` or `code_version` in `manifest.json` alongside `migration_head`.
- In `restore_verify_crm.py`, before running the drill, compare manifest `migration_head` against the image's current migration head. If they differ: (a) warn loudly that cross-version restore is in progress, (b) take a sha256 of the DB _before_ migrations run and record it, (c) run migrations, (d) take sha256 _after_ migrations and record both in the drill report. Never assert backup sha256 == restored sha256 across version boundaries — assert pre-migration sha256 matches manifest sha256 instead.
- Add a dedicated cross-version restore test case (restore a backup from migration N-3 against current head).

---

## H4 — cache.db Is Stale on Restore: "Correct Restore" ≠ "Correct App"

**Hole.**  
`cache.db` is a snapshot of warehouse state at backup time. On restore, it is potentially hours/days/weeks stale vs the live warehouse. The plan includes `cache.db` for "self-contained restore (no warehouse needed)" — but `CRM_VERIFY_MODE=1` skips `reverse_etl` and `sync_parties`. The functional smoke test hits `/api/segments`, `/api/dedup/candidates`, etc., which query `cache.db`. These return 200 with _stale data_. The plan declares **PASS**.

**This conflates two separate correctness properties:**  
1. `crm.db` is byte-identical to what was backed up (true, verifiable).  
2. The app is serving _current_ data to end-users (false — cache is stale by definition).

**Concrete failure scenario.**  
Real incident: prod `crm_data` volume corrupted. Ops restores from 48-hour-old backup. `crm.db` is intact — good. `cache.db` is 48 hours stale. Restore drill said PASS (it tested the 48-hour-old cache). Ops starts prod on the restored backup. `sync_parties` runs (not in verify mode now) and overwrites `crm_party` rows with 48-hour-old warehouse seeds, potentially undoing 48 hours of manual party edits. The plan's runbook (Phase 3) does not call this out as a mandatory post-restore step: "re-run reverse_etl + sync_parties after restore and before going live."

**Fix (Phase 3 runbook + Phase 2).**  
- Phase 2 drill should explicitly label the cache staleness in the PASS/FAIL report: "cache.db age: {backup_timestamp} (N hours old — will be refreshed on prod restart)."  
- Phase 3 runbook must include a mandatory step after real-incident restore: "After starting the container in normal mode (not VERIFY_MODE), confirm reverse_etl and sync_parties complete successfully before routing traffic." If reverse_etl cannot reach the warehouse, document the acceptable staleness window and how to verify it.
- Phase 1 manifest should record `cache_db_snapshot_time` explicitly (same as backup timestamp but make it a named field ops can read).

---

## H5 — Negative Test Sufficiency: Single Row Drop Does Not Cover Dangerous Corruption Classes

**Hole.**  
Phase 2 success criteria: "a deliberately tampered backup makes the drill FAIL (checks are not vacuous)." Implementation step 7: "corrupt a copy (drop a row / truncate a table) → confirm the drill FAILs."

One tamper type (row deletion) caught by row count check. Classes of corruption the proposed checks **do not catch**:

| Corruption class | Caught? | Why missed |
|---|---|---|
| Row deleted | Yes | Row count diff |
| Row inserted (extra data) | Yes | Row count diff |
| Row value mutated (VARCHAR field) | **No** | Row count unchanged; sha256 matches backup (manifest SHA is of backup, not source); integrity_check passes; FK check passes |
| Referential integrity broken via cascade delete | Depends | FK check catches dangling FKs but not if deleter cleaned up consistently |
| Partial WAL replay (missing frames, internally consistent) | **No** | H2 — self-consistent but stale |
| Migration table tampered (`schema_migrations` row deleted) | Yes | Migration head mismatch |
| Migration table tampered (version string changed) | **Possibly No** | If forged to match manifest exactly |
| `cache.db` completely replaced with empty DB | **No** | Row counts for an all-empty cache still match an empty-cache backup |
| Backup from wrong timestamp copied (older snapshot) | **No** | If that snapshot's manifest matches: all checks pass, old data silently restored |
| Encoding/collation corruption (TEXT stored as BLOB) | **No** | Row count, integrity_check, FK check all pass; only surfaced if functional smoke exercises that column |

**The most dangerous undetected class: silent value mutation.** A row count match plus sha256-of-backup-file match proves the backup is _self-consistent_ but does not prove any specific value is correct. An attacker (or a bug) that changes `crm_party.phone = NULL` for 500 rows leaves no trace in any proposed check.

**Fix (Phase 2, negative test suite).**  
Extend negative test coverage to at least:  
1. Mutate a value in a critical column (phone, email, tag_id) without changing row count — must detect via content hash or a spot-check query.  
2. Replace `cache.db` with a zero-row empty DB — drill should WARN (zero contacts in cache is suspicious, even if row count "matches" a backup that was also empty).  
3. Swap in an older backup's `crm.db` but keep the newer `manifest.json` — `backup_sha256 != manifest.sha256` should catch this, but verify the check order is correct.  

To detect value mutations: add per-table content checksums to the manifest. The simplest approach: `SELECT md5(group_concat(id || '|' || updated_at ORDER BY id)) FROM crm_party` — a single aggregate hash per critical table. SQLite lacks md5() natively but Python can compute it after a `SELECT *` ordered by PK. Add `table_content_hashes` to `manifest.json` for `crm_party`, `crm_tag`, `crm_segment`, `hug_campaign`. Phase 2 recomputes and compares. This closes the value-mutation hole without full row-by-row comparison.

---

## H6 — `apply_migrations` Opens DB Read-Write in entrypoint, Contradicts Backup's Read-Only Assumption

**Incidental structural hole (not a backup integrity hole per se, but affects restore correctness).**  
`migrations.py:apply_migrations()` does `sqlite3.connect(str(db_path))` — **read-write**, no `mode=ro`. It also sets `PRAGMA journal_mode=WAL`. On the restored DB (which was snapshotted in WAL mode), this is fine. But if the restore ever copies a non-WAL backup (e.g. someone backed up with `PRAGMA journal_mode=DELETE` and it was reverted), `apply_migrations` silently re-enables WAL, which writes a new `-wal` file. The post-migration sha256 of the DB file changes even if no schema changes were applied. The plan's risk note "verify head-match instead of assuming no-op" is insufficient because the WAL journal_mode pragma itself modifies the DB file header on first write, invalidating the sha256 check even for a perfectly matched migration head.

**Fix (Phase 2).**  
The sha256 integrity check must be taken _before_ entrypoint runs (before migrations, before journal_mode pragma). Capture `pre_boot_sha256` immediately after copying the backup to the temp dir, and compare it to `manifest.sha256`. Only after this pre-boot check passes, start the container. The current plan's flow (start container → run migrations → then check sha256) will always produce a sha256 mismatch if `PRAGMA journal_mode=WAL` rewrites the header on a fresh DB page.

Actually re-reading: Phase 2 says "sha256 of the _restored file_ matches manifest." If integrity checks run against the temp dir files _before_ `docker run`, this is fine. But the plan says checks run "inside the ephemeral container or via a mounted read of the temp DBs" (step 4) — after the container has already started (step 3: "poll /health until ready"). By then, migrations have run and WAL pragma may have written to the file. **The sha256 check as written is not order-safe.** The plan must explicitly run the file-level sha256 check on the copied files BEFORE `docker run`, not after.

---

## H7 — Rotation Deletes the Only Copy of a Partial Backup That Passed Disk Pre-flight But Failed Mid-Backup

**Minor operational hole.**  
The EXIT trap removes partial backup dirs (`BACKUP_DATA_OK=false`). But the disk pre-flight passes if there's _enough space for the snapshot_. Suppose crm.db is 500 MB, cache.db is 200 MB, free space = 750 MB. Pre-flight passes (700 MB needed + 1 GB margin... actually this would abort). But with a 100 MB safety margin (if someone changes the constant), pre-flight passes, crm.db backup succeeds, cache.db backup fails mid-write (disk fills). Trap deletes the partial dir. Now there's no backup at all — not even the good crm.db snapshot.

The existing `backup.sh` has the same design: `BACKUP_DATA_OK=false` wipes the entire partial dir even if crm.db was fully copied. For a two-DB backup, a more resilient design would set `BACKUP_DATA_OK=true` per-DB and only discard the truly-partial DB file.

**Fix (Phase 1).**  
Track success per-DB: `crm_db_ok`, `cache_db_ok`. On partial failure, keep the successfully-completed DB files and mark the manifest as `partial=true` — this is still usable for point-in-time recovery of the intact DB even if the other failed.

---

## Summary of Holes by Severity

| Rank | ID | Title | Severity |
|---|---|---|---|
| 1 | H1 | Manifest from backup, not source — silent data loss invisible | Critical |
| 2 | H2 | WAL partial/corrupt state not probed before backup | High |
| 3 | H3 | Cross-version restore mutates data before verification | High |
| 4 | H5 | Value-mutation corruption not detected by any check | High |
| 5 | H6 | sha256 checked after container start (post-migration write) — order is wrong | Medium |
| 6 | H4 | Stale cache.db conflated with "correct restore" in runbook | Medium |
| 7 | H7 | Partial backup of one DB discarded by rotation even if the other succeeded | Low |

---

**Status:** DONE

**Top integrity holes (most dangerous first):**

- **H1 — Source-fidelity gap [Critical]:** manifest records backup state, not live-source state; data loss passes all checks. Fix: query live source row counts before backup and record as `source_row_counts`; verify delta == 0 as part of backup success gate.
- **H2 — WAL health not probed before snapshot [High]:** a post-crash partially-corrupt WAL causes `mode=ro` to see stale state silently; `integrity_check` passes on the backed-up (self-consistent but incomplete) state. Fix: run `PRAGMA wal_checkpoint(PASSIVE)` + live `integrity_check` on source before backup starts.
- **H3 — Cross-version restore mutation before verification [High]:** restoring old backup with current image runs N+k migrations before Phase 2 checks run; sha256 will always mismatch and data may be structurally altered. Fix: sha256 the copied files _before_ `docker run`; handle cross-version explicitly in drill logic.
- **H5 — Value-mutation not covered by any check [High]:** row count + sha256-of-backup + integrity_check + FK check all pass when row values are silently corrupted. Fix: add per-table content checksums (`md5(group_concat(id||updated_at ORDER BY id))`) to manifest; negative test suite must include a value-mutation tamper.
- **H6 — sha256 checked post-container-start, after WAL pragma write [Medium]:** `PRAGMA journal_mode=WAL` in `apply_migrations` rewrites the DB file header; sha256 computed after container boot will not match the manifest even for a perfectly clean restore. Fix: check sha256 on copied temp files BEFORE `docker run`.
- **H4 — Stale cache.db declared correct [Medium]:** functional smoke PASS with stale cache data; runbook omits mandatory post-restore reverse_etl + sync_parties step. Fix: label cache age in drill report; add mandatory refresh step to Phase 3 runbook.
- **H7 — Partial backup rotation discards good crm.db if cache.db fails [Low]:** EXIT trap deletes entire partial backup dir even when one DB completed successfully. Fix: track per-DB success flags; keep completed DBs with `partial=true` manifest flag.
