# Red-Team: Prod-Safety Review — CRM Backup + Restore-Verify Drill
**Plan:** `plans/260624-2010-crm-backup-checkpoint-restore-verify/`
**Date:** 2026-06-24 | **Reviewer:** adversarial (hostile posture)
**Scope:** phase-01 + phase-02; grounding in `docker-compose.yml` + `crm/entrypoint.sh`

---

## 0. Attack Surface Summary

The drill touches production in five real coupling points:
1. **Phase 1** runs code *inside* the live `crm` container (`docker exec crm …`)
2. **Phase 1** writes to `app_data/crm_backups/` which lives on the same host volume tree as `app_data/data_lake/` (DuckDB warehouse, Dagster home)
3. **Phase 2** copies from that backup dir into a temp dir and mounts it as the ephemeral container's `/data`
4. **Phase 2** `docker run` is supposed to be ephemeral, but several failure modes leave it touching or mimicking prod
5. Both phases run unattended from a Python script — Python signal handling on Windows (Docker Desktop) has known gaps

---

## 1. Volume / Container / Port Collisions

### 1a. Stale container from a previous run
Plan says `docker run --rm … --name crm-restore-verify`. `--rm` only fires on **normal exit**. If the drill previously crashed (OOM, SIGKILL, host restart, Ctrl-C without signal propagation), the container remains. The next run's `docker run --name crm-restore-verify` fails with "name already in use" and the drill aborts — but the *stale* container is still running, still bound to `:18090`, and if it previously loaded from `crm_data` (see §1c) it is still serving stale prod data with no monitoring.

**Mitigation required:** In `restore_verify_crm.py`, before `docker run`, always execute `docker rm -f crm-restore-verify 2>/dev/null || true`. Assert the container is gone before proceeding.

### 1b. Port 18090 already in use
Nothing in the plan checks whether `:18090` is free. On Windows/Docker Desktop, port binding failure surfaces only at runtime. The drill will fail to start the ephemeral app, time out on `/health`, report FAIL — but **the prod CRM on :3007 is unaffected**. The risk here is a false-negative FAIL that gets ignored, not a prod corruption. Still: the drill must `docker run` with `--publish` and catch "port already allocated" explicitly, or use a dynamic free-port selection + assertion.

**Mitigation required:** pre-flight `netstat -ano | findstr :18090` (Windows) or `ss -ltn | grep 18090` (Linux/Docker) before `docker run`; fail with a clear diagnostic, not a silent timeout.

### 1c. Ephemeral container accidentally mounting `crm_data` named volume (HIGHEST SEVERITY)
The plan's proposed `docker run` mount is *not finalized in the plan text* — it says "mounting the temp dir as `/data`". The exact flag must be a **bind-mount to the host temp dir**, e.g. `-v /host/path/crm_restore_verify/RUN-TS:/data`. If the implementer instead writes `-v crm_data:/data` (copy-paste from `docker-compose.yml`) or omits the mount entirely (the CRM image's entrypoint expects `/data` and will create it inside the container from `crm_data` if CRM_DATA_DIR defaults to the volume), the ephemeral CRM boots from the LIVE `crm_data` volume and `sync_parties` (Steps 2-3 in `entrypoint.sh`) **writes to prod crm.db**.

Concrete bad path:
- `CRM_VERIFY_MODE` not yet implemented (Phase 1 must land first; if Phase 2 is tested before the gate is in `entrypoint.sh`), entrypoint runs all steps
- Step 3 (`sync_parties`) writes `crm_party` rows derived from `cache.db` → `crm.db`
- If `cache.db` in prod has fresh data and the ephemeral container wrote duplicates or deletions, prod `crm.db` is now corrupt

**Mitigation required:**
- The `docker run` must explicitly assert that NO volume flag references `crm_data`; add an assertion in code: `assert 'crm_data' not in docker_run_cmd`
- The bind mount path must be constructed from a runtime temp dir, not any constant from the compose file
- The `CRM_VERIFY_MODE` gate must be merged to `entrypoint.sh` *before* any Phase 2 test run; add a gate check in `restore_verify_crm.py`: pull the image, inspect `docker inspect <image>` for the `entrypoint.sh` commit, or run `docker run --rm <image> grep CRM_VERIFY_MODE /app/entrypoint.sh` as a pre-flight and abort if not found

### 1d. Caddy routing to the ephemeral container
The prod `crm` service has label `caddy: crm.lan.fwg.vn`. The ephemeral container **must not** carry that label. The plan says "no Caddy label" but doesn't assert it. If any wrapper script or developer adds a label (or copies the compose service definition), Caddy will load-balance prod traffic to the ephemeral container. On `--rm` teardown, Caddy gets a dead upstream but may have already routed a write request to the ephemeral app (which writes to the temp volume, losing the mutation).

The ephemeral container *does not need to join `caddy_net` at all* — it only needs the Python script on the host (or inside data_platform) to reach `:18090`. If it doesn't join `caddy_net`, Caddy never sees it.

**Mitigation required:** Do NOT pass `--network caddy_net` to the `docker run`. Use `--network none` or a dedicated `--network crm_restore_verify_net` (ephemeral, created + destroyed by the drill). Assert in code that neither `caddy_net` nor any Caddy label appears in the run args.

---

## 2. `CRM_VERIFY_MODE` Skip Failure Modes

### 2a. Env var not honored (gate not in entrypoint.sh yet)
Phase 2 depends on Phase 1 shipping the entrypoint gate. If the drill runs before that commit is in the image (e.g. image was built once, Phase 1 code was updated but image not rebuilt), `entrypoint.sh` runs all four steps including reverse_etl + sync_parties. On a temp volume this is still safe because the DBs are copies — BUT see §1c above if the volume is wrong.

**Mitigation required:** `restore_verify_crm.py` must verify the gate exists in the image it uses before `docker run`:
```sh
docker run --rm <image> grep -q CRM_VERIFY_MODE /app/entrypoint.sh || exit 1
```

### 2b. `CRM_VERIFY_MODE` set but reverse_etl still reads `olap.duckdb` (prod coupling)
Looking at `docker-compose.yml` (prod crm service, line 204): `- ./app_data/data_lake:/app/var/data_lake:ro`. The prod `crm` container mounts the ENTIRE data lake read-only. `entrypoint.sh` Step 2 (`reverse_etl_warehouse_to_crm`) reads `olap.duckdb` at `CRM_OLAP_PATH=/app/var/data_lake/serving/olap.duckdb`.

The drill's proposed `docker run` intentionally omits the `data_lake` mount ("no `data_lake` mount — self-contained"). This is correct design. BUT:
- If `CRM_VERIFY_MODE` is NOT set (see §2a), and `data_lake` is NOT mounted, Step 2 fails gracefully (the `if … else echo WARN` path in entrypoint.sh) — OK.
- **If `data_lake` IS accidentally mounted** (implementer copies the prod compose volumes verbatim), reverse_etl runs against the live warehouse file — a **read-only** operation but it adds a reader lock on `olap.duckdb` during the drill. DuckDB with concurrent readers is fine unless a writer (Dagster) is also active; this project's own memory note says "DuckDB not for concurrent writes" and "always read_only=True". A read-only mount + read_only open is safe — but it is an unnecessary prod coupling that should be asserted away.

**Mitigation required:** Assert no `data_lake` mount in the drill's `docker run` args. The ephemeral CRM must start with `CRM_OLAP_PATH` pointing to a nonexistent path (or not set) so that if `CRM_VERIFY_MODE` fails to gate, reverse_etl gracefully fails rather than reading prod.

### 2c. `sync_parties` writes crm.db — sha256 check timing
Phase 2 plan correctly says: add assertion that crm.db sha256 is unchanged after boot. But the plan does not specify *when* that check runs relative to the app being healthy. If the check runs before Step 3 finishes (race: the health poll may return 200 before sync_parties completes because the HTTP server starts in Step 4, after Steps 2-3), the check would pass on a pre-mutation sha256. Then sync_parties mutates it, and the subsequent row-count check compares against a stale manifest.

On a temp volume this is a test validity issue (the integrity check is vacuous) not a prod safety issue. But it erodes confidence in the drill.

**Mitigation required:** Take the sha256 snapshot of the temp dir's crm.db **after the drill's tear-down**, not during uptime. Or: add a sleep + explicit check that sync_parties has exited (inspect container process list).

---

## 3. Backup-Time Interference with Prod

### 3a. `docker exec crm python -m crm.ops.backup_crm` inside live container
The plan uses SQLite online-backup API (`src.backup(dst)`) opened with `sqlite3.connect("file:{path}?mode=ro", uri=True)`. This is the correct WAL-safe approach. However:

- **WAL checkpoint contention:** SQLite's online-backup with a concurrent writer means the backup may iterate multiple passes to get a consistent snapshot. Under heavy write load (e.g. a large `sync_parties` run or a Dagster-triggered `/admin/refresh`) the backup retries indefinitely. The plan does not mention a `backup()` call with a progress/page callback or a timeout. A stuck backup holds a read lock on the WAL.
- **Read lock + writer starvation:** `mode=ro` + WAL means writers are not blocked, but WAL grows unbounded while a long-running read is active. If the backup takes minutes (large crm.db), WAL grows, checkpointing is deferred, next writes are slower.

This is a **performance coupling**, not data corruption. But a backup scheduled during peak ingest could noticeably slow the live app.

**Mitigation required:** Add a `pages` argument to `src.backup(dst, pages=100)` with `sleep(0.1)` between batches (yields writer checkpoints). Or: document that backup should run during a quiet window (add to runbook). Monitor WAL size before/after as a success criterion.

### 3b. Backup destination shares host filesystem with Dagster + data lake
`app_data/crm_backups/` lands in the same Windows host directory tree as `app_data/data_lake/` (the DuckDB warehouse). If the disk fills:
- Dagster cannot write run logs → ops silently fails
- DuckDB writes to `olap.duckdb` can fail mid-transaction → mart corruption (DuckDB is write-lock sensitive)
- CRM's `cache.db` write (from reverse_etl) can fail → partial cache

The plan has a disk pre-flight check in `backup_crm.py` (abort if free < snapshot × safety factor). But:
- The pre-flight measures free space *before* starting the backup. If rotation's old dirs are large, and the new backup fills the gap before rotation runs, the host can still hit 0.
- On Windows, Docker Desktop's WSL2 virtual disk auto-grows but has a hard ceiling (typically the set max size). The disk pre-flight inside Docker `exec` sees the container's filesystem, which maps to the WSL2 vdisk — the same vdisk shared by ALL Docker data including `crm_data`, `monitoring_db`, and all other named volumes. Filling it crashes everything.

**Mitigation required:**
- Pre-flight must check free space on the WSL2/Docker vdisk, not just the bind-mount path.
- Rotation must run *before* the new backup is written (not after), so old dirs are cleared to make room.
- Add a hard disk limit: refuse to start if `free_space < 2 × source_size` (not just `1 × + 1 GB`).
- Consider writing backups to a separate host volume or network path (out of scope for now, but note the risk).

### 3c. Backup writes through the container's `/backups` bind-mount to `app_data/crm_backups/`
Phase 1 modifies `docker-compose.yml` to add `- ./app_data/crm_backups:/backups` to the `crm` service. This means **every `docker compose up -d crm`** now exposes the backup directory inside the live container. Any code path inside crm that has a path traversal bug or an accidental `open('/backups/…', 'w')` call could corrupt backup files. The surface is small but the exposure is permanent once the mount is added.

**Mitigation required:** Mount `/backups` read-write only during backup runs, not permanently. Use `docker run --rm -v ./app_data/crm_backups:/backups crm python -m crm.ops.backup_crm` (one-off exec) instead of adding it to the compose service definition. This avoids permanently exposing the backup tree inside the live container.

---

## 4. Teardown Failures

### 4a. Python `finally` + Windows signal handling
The plan relies on `finally` in Python for guaranteed cleanup. On Windows (where the drill runs), Python's signal handling for SIGINT/Ctrl-C is different from POSIX. Specifically:
- `subprocess.Popen` for `docker run` → Ctrl-C sends SIGINT to the Python process but the `docker run` subprocess may not receive it (Docker Desktop on Windows uses named pipes, not PTY). The subprocess continues running.
- Python's `finally` block *does* run on KeyboardInterrupt — but only if the exception propagates to the `try`. If the `docker run` is called with `subprocess.run(..., check=True)` and the Python process is killed (not just Ctrl-C), `finally` does not run.

Result: the temp volume dir and the `crm-restore-verify` container both remain after an aborted drill. Over repeated aborts, temp dirs accumulate in `app_data/crm_restore_verify/` — potentially gigabytes of SQLite copies — and the stale container consumes port 18090.

**Mitigation required:**
- Register a signal handler for SIGINT + SIGTERM that calls the cleanup function, then re-raises.
- Use `atexit.register(cleanup)` in addition to `try/finally`.
- Add a startup check that cleans up any dirs in `app_data/crm_restore_verify/` older than N hours.
- Add the temp volume dir to `.gitignore` and document manual cleanup in the runbook.

### 4b. `--rm` container and bind-mount temp dir — deletion order
The plan deletes the temp dir in `finally`. If `docker rm` hasn't completed (async on Windows Docker Desktop) when `shutil.rmtree(temp_dir)` runs, Docker may still hold a filesystem handle on the bind-mount, causing the rmtree to fail on Windows (`PermissionError: [WinError 32] The process cannot access the file`). The temp dir is left behind.

**Mitigation required:** After `docker stop crm-restore-verify` + `docker rm crm-restore-verify`, poll `docker ps -a --filter name=crm-restore-verify` until the container is gone before attempting `rmtree`. Add `time.sleep(2)` + retry loop.

---

## 5. Image Drift (False Confidence)

### 5a. Drill tests backup against a different image than prod runs
The plan says "boot from the SAME crm image". But `docker-compose.yml` builds the image with `build: context: . dockerfile: Dockerfile.crm`. Unless the drill explicitly uses the currently-running prod image digest (not just the tag), it could use a stale local image. Example:

- Prod `crm` container was started 3 days ago from image `data-integration_crm:latest` at digest `sha256:abc`
- Developer ran `docker compose build crm` today (new code, new image at `data-integration_crm:latest` = `sha256:def`)
- Drill runs: `docker run data-integration_crm:latest` → uses `sha256:def`
- The backup was taken from a container running `sha256:abc`
- Migration head in the backup may be LOWER than what `sha256:def` expects
- Migrations run on the restored DB and either succeed (promoting to the new head — which means the drill tests a MIGRATED DB, not the backup state) or fail (drill aborts, backup falsely marked BAD)

This is the deepest false-confidence risk: the drill could PASS (new migrations ran and succeeded) while a real restore of prod (which must run the old image) would need different steps.

**Mitigation required:**
- Record the image digest at backup time in `manifest.json` (`image_digest: sha256:…`).
- Drill must use `docker inspect crm --format '{{.Image}}'` to get the RUNNING prod image digest, and pass `--image <digest>` to the `docker run` call.
- If the backup manifest's image_digest differs from the current prod image, the drill should WARN (not fail) and explicitly note that migrations will run in the drill but may not represent a same-version restore.

### 5b. Migration idempotency assumption
The plan states: "Migrations (Step 1) still run — on a restored-at-head DB they must be a no-op; that itself validates the migration head." But the plan never checks whether `apply_migrations` is actually idempotent. If migrations are tracked by filename/version in `schema_migrations` table and a developer added a migration without a guard (`CREATE TABLE IF NOT EXISTS`), the migration re-applies on a head DB → error → drill fails on a perfectly valid backup.

**Mitigation required:** Read `crm/src/adapters/outbound/sqlite/migrations.py` to verify that the applied-migrations table is checked before each migration is run (standard "skip if already applied" pattern). Add this as a success criterion in Phase 2.

---

## 6. Windows / Docker Desktop Specifics

### 6a. Named-volume copy for backup destination
Phase 1 uses `docker exec crm python -m crm.ops.backup_crm --data-dir /data --dest /backups`. The `/backups` bind-mount maps to `./app_data/crm_backups/` on the Windows host via WSL2 9p protocol. This is the same 9p mount that the memory note (`feedback_docker-wsl2-9p-mount-fix.md`) flagged as fragile (`mkdir /run/desktop/mnt/host/d: file exists` on WSL freeze). If WSL2 is in a degraded state, the bind-mount is unavailable inside the container but the backup script proceeds, creating an empty or partially-written backup dir that looks valid (rotation logic checks `[ -d "$dst" ] && [ "$(ls -A "$dst")" ]` — a sparse dir might pass this check).

**Mitigation required:** The backup script should verify the destination mount is writable before starting (write a `.probe` file, read it back, delete it). Fail hard if the probe fails.

### 6b. DuckDB-analog SQLite lock (dllhost / Windows Defender scanning)
The project's memory note (`project_docker_environments.md`) records that Windows Defender scanning of bind-mounted paths causes dllhost to hold file handles. The `crm_data` named volume avoids this by living inside the Docker VM — but `crm_backups` lives on the Windows host filesystem. On each backup write, a new `.db` file appears in `app_data/crm_backups/`. Windows Defender may scan the file, briefly holding a read lock. The Python backup script's `src.backup(dst)` writes to a fresh dst file — the lock on the new dst file by Defender could cause the backup to fail mid-write (write error on the destination).

**Mitigation required:** Either move `crm_backups/` to a Docker named volume (lives in WSL2 VM, outside Defender's reach), or add Defender exclusion for `app_data/crm_backups/` to the runbook. Note this in the Phase 3 runbook as a known risk on Windows.

### 6c. Restore drill's temp dir also on Windows host filesystem
Same issue: `app_data/crm_restore_verify/{run-ts}/` is on the Windows host. Defender scans newly-copied `.db` files. The `shutil.rmtree` in `finally` may fail if Defender still holds a handle (on Windows, files in use cannot be deleted). This causes the temp dir to persist even when the drill calls cleanup.

**Mitigation required:** Use a Docker named volume for the temp restore data instead of a host bind-mount. Create a temp named volume (`crm_restore_verify_{ts}`), copy backup files into it via a `docker run --rm` container, mount it in the drill container, then `docker volume rm crm_restore_verify_{ts}` in cleanup. This keeps all SQLite files inside the Docker VM (no Defender contact).

---

## 7. Additional Risks Not Covered by the Plan

### 7a. `backup.sh` (existing) still runs on schedule and still does raw `cp` of `crm_data`
The plan notes the existing `backup.sh` does a WAL-unsafe raw `cp` of the `crm_data` named volume. Phase 1 replaces this for CRM only. But `backup.sh` (scheduled via `setup-task-scheduler.ps1` or Dagster's `system_backup.py` op) still runs — and it still does `cp -a /app/var/crm_data …` (line ~152 in backup.sh). This means during scheduled backup windows, both the new Phase-1 backup AND `backup.sh` may run simultaneously, both reading `crm_data`, competing for WAL reader slots. The `backup.sh` path is unsafe (torn copy) and its continued existence undercuts the Phase-1 safety guarantee.

**Mitigation required:** Phase 1 implementation must disable or replace the `crm_data` copy step in `backup.sh`. The two backup mechanisms must not coexist silently.

### 7b. No prod-CRM uptime assertion after the drill
Phase 2 success criteria list "Prod CRM untouched throughout (verify live container uptime + crm_data unchanged)". But the plan has no concrete implementation for this check. Someone must add:
- `docker inspect crm --format '{{.State.Status}}'` == `running` before AND after the drill
- A sha256 of the live `crm.db` (via `docker exec crm sqlite3 /data/crm.db "SELECT sha256(…)"` or a pre/post `docker exec crm python -c "import hashlib; …"`) to assert the prod DB was not written to

Without this, the drill can PASS while silently having mutated prod (§1c scenario), and no one catches it.

**Mitigation required:** Add prod-health assertions as an explicit step in `restore_verify_crm.py`: record live crm.db size+mtime before drill; assert unchanged after drill.

---

## Top Prod-Safety Risks (Ranked)

1. **Ephemeral container accidentally mounts `crm_data` named volume** → `sync_parties` writes to live prod `crm.db`. Mitigation: hard assert `crm_data` not in `docker run` args; `CRM_VERIFY_MODE` gate must land in image before any drill test.

2. **`CRM_VERIFY_MODE` gate not yet in the running image** → entrypoint runs all steps against whatever `/data` is mounted. Even on a temp volume this is fine; against prod volume it is catastrophic. Mitigation: pre-flight `grep` inside the target image before `docker run`.

3. **Stale `crm-restore-verify` container + no Caddy exclusion** → stale container receives prod traffic if it somehow joins `caddy_net` and carries Caddy label. Mitigation: `docker rm -f` pre-flight; prohibit `caddy_net` and labels in drill's `docker run`.

4. **Disk exhaustion from `crm_backups/` on shared host volume** → Dagster + DuckDB writes fail, mart corruption possible. Mitigation: pre-flight must compare against 2× source size; rotate *before* write; move backups off the shared data_lake host path.

5. **Image digest drift** → drill tests a migrated DB (new image migrations ran on old backup), gives false PASS confidence. Mitigation: record image digest in manifest; drill must use the running prod image digest.

6. **Python `finally` unreliable on Windows for SIGKILL** → temp dirs + stale containers accumulate; port 18090 stays bound. Mitigation: `atexit` + signal handler + startup stale-dir sweep; use Docker named volumes for temp data.

7. **Windows Defender scanning backup dir** → `backup()` dst file locked mid-write, partial backup; `rmtree` fails silently in cleanup. Mitigation: move `crm_backups/` and restore temp dir into Docker named volumes (inside WSL2 VM).

8. **Existing `backup.sh` still does raw WAL-unsafe `cp` of `crm_data`** and may run concurrently with Phase-1 backup. Mitigation: remove/disable the `crm_data` copy in `backup.sh` as part of Phase 1.

9. **No prod uptime/integrity assertion** → the drill can pass while prod was silently mutated (§1c); no canary catches it. Mitigation: record pre/post `crm.db` mtime + size; assert unchanged after drill completes.

---

**Status:** DONE
**Top prod-safety risks:** see ranked list §above; risks 1-3 can cause silent prod mutation and are the highest severity — they must be hardened before any Phase 2 test run against a real machine.
