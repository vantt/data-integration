# Red-Team / Ops-Realism Review — CRM Backup-Checkpoint + Restore-Verify Plan
**Date:** 2026-06-24  
**Plan:** `plans/260624-2010-crm-backup-checkpoint-restore-verify/`  
**Reviewer role:** Hostile adversarial reviewer + grizzled SRE  
**Scope:** Operational realism; read-only — no edits  

---

## Attack 1 — Real-incident restore gap: you can't fetch the backup from a dead host

### What the plan says
Phase 3 runbook restores from `app_data/crm_backups/` on the host. Backups land at `./app_data/crm_backups/{YYYYMMDD-HHMMSS}/` (Phase 1 architecture, `/backups` volume mount). The existing `backup.ps1`/`backup.sh` also writes to a local directory (`D:\_1.FWG_PARA\1.Projects\dev\dataware_house\backups` by default, or wherever `BACKUP_ROOT` is configured). All of it is local.

### The real disaster scenario
Host dies. Disk fails. Windows goes corrupt. Docker Desktop refuses to start. The crm_data named volume lives inside the Docker Desktop WSL2 VM — it's not directly readable from Windows even when the host is alive (this was already noted in memory: "crm_data is a Docker named volume, not on Windows filesystem"). In a real host-lost event:

1. The `app_data/crm_backups/` directory is on the same Windows `D:` drive that just died.
2. The existing `backup.sh` BACKUP_ROOT is also local (possibly `D:\...` per the `.ps1` default).
3. The new Phase-1 backups and the old `backup.sh`/`backup.ps1` crm_data copies are **both on the same physical host as the thing that broke**.
4. There is **no offsite, no remote, no secondary location** mentioned anywhere in this plan.

**Operational failure:** on a single-disk Windows host, both the prod volume and the backup are on the same drive. A real hardware DR event (not a soft "container crashed" event) = unrecoverable. The runbook says "restore from `app_data/crm_backups/`" — that path is on a dead machine.

The plan calls this a "DR pilot" repeatedly. It is not DR. It is a recovery-from-soft-corruption tool. That distinction must be explicit.

**Specific plan fix required:**
- Phase 3 runbook must have a section titled "What this runbook does NOT cover" that explicitly states: this procedure assumes the host is alive and the `app_data/crm_backups/` directory is accessible. It does NOT protect against host/disk loss.
- A stub section must name the offsite gap and the minimum to close it (e.g. Windows Task Scheduler robocopy to a NAS or external drive, or Cloudflare R2 upload post-backup). Even a comment "copy latest backup to `\\NAS\crm_backups\` after each run" closes the risk.
- Without this, the word "DR" in the plan title and overview is misleading and will give operators false confidence.

---

## Attack 2 — Two competing backup systems: dual crm_data copies, zero reconciliation

### What exists
`backup.ps1` Step 3 (lines 100-122) does `docker run --rm -v crm_data:/crm_src:ro alpine cp -a /crm_src/. /crm_dst/` — a raw filesystem copy of the live volume **while the container is still down** (because `.ps1` stops containers at Step 1). It lands at `{BACKUP_DIR}/crm_data/`.

`backup.sh` (line 152) loops `for vol_name in data_lake dagster_home input_source crm_data` — same raw copy, but hot (container running). This lands at `{BACKUP_DIR}/app_data/crm_data/`.

The new plan creates a **third** copy mechanism: `crm/ops/backup_crm.py` using SQLite online-backup API, landing at `app_data/crm_backups/`.

After this plan is implemented there will be **three** locations with crm_data copies:
1. `app_data/backups/{ts}/crm_data/` (from `backup.ps1` — raw, stopped-container, WAL-safe when stopped)
2. `app_data/backups/{ts}/app_data/crm_data/` (from `backup.sh` in Docker — raw `cp`, hot, WAL-unsafe per the plan's own L56/L68 citation)
3. `app_data/crm_backups/{ts}/` (from new `backup_crm.py` — SQLite online-backup API, consistent)

**Operational failure:** in an incident, an operator reads the runbook and is told to restore from `app_data/crm_backups/`. A panicking second operator finds `app_data/backups/` from the nightly `backup.ps1` and restores from there. These are **different formats** (one is consistent SQLite snapshot, the other is raw filesystem including WAL/SHM files). The raw one may be 1 hour newer but corrupted. Nobody knows which is authoritative.

The plan's own overview says the existing raw copy has a "WAL-unsafe — L56/L68" gap but **does not retire or reconcile** the existing mechanism. It adds a new one alongside.

**Specific plan fix required:**
- Phase 1 must explicitly declare the relationship to the existing `backup.ps1/backup.sh` crm_data copy: either (a) retire it — remove crm_data from `backup.sh` loop + remove `backup.ps1` Step 3, and document why; or (b) keep it as a secondary raw emergency copy with explicit "do not use for restore" warning.
- Phase 3 runbook must have ONE authoritative restore source with a clear hierarchy: "Only restore from `app_data/crm_backups/` (consistent snapshots). The `app_data/backups/*/crm_data/` copies are emergency-only raw dumps and may be inconsistent."
- Without this, the DRY violation actively worsens incident response.

---

## Attack 3 — Restoring an old backup after schema migrations

### What the plan says
Phase 2 drill: "Migrations (Step 1) still run — on a restored-at-head DB they must be a no-op; that itself validates the migration head." The manifest records `migration_head`.

### The real failure mode
Scenario: backup was taken at migration `v012`. Code is now at `v020`. There are 8 new migrations, some of which ADD NOT NULL columns with no default, ALTER tables with data-dependent transforms, or DROP columns.

Restoring the `v012` backup into a container running `v020` code means `apply_migrations()` will run `v013`–`v020` against the restored data. This is the **standard migration path** and is theoretically fine — but:

1. The plan has **zero coverage** of what happens when a migration fails mid-restore. `entrypoint.sh` hard-fails on migration error (correct) — but the runbook says "confirm migrations OK" without specifying what to do when they're NOT OK. What's the rollback? Which backup do you try next?

2. The Phase 2 drill **only drills the latest backup** (implicitly: "default to latest backup"). A 3-month-old backup is never drilled. Nobody knows if it's actually restorable until they need it in an incident. 

3. The plan's keep-N is 7 (default). At 1 backup/day, retention is 7 days. This is not documented as an explicit RTO/RPO decision. If the corruption is discovered 8 days later, all backups are post-corruption. There's no policy stated.

4. The manifest stores `migration_head` but the restore drill only checks "applied migration head matches" — it checks that the restored DB shows the same head as at backup time (i.e., migrations were NOT run forward). This is correct for the drill test, but it means the drill never exercises the forward-migration path that a real old-backup restore would take. **The drill does not test the most likely real recovery scenario.**

**Specific plan fix required:**
- Phase 3 runbook must have a "migration mismatch" section: what to do if `apply_migrations()` fails during restore (try older backup, get a dev to write a compensating migration, etc.).
- Phase 2 drill should include an optional `--target-migration <head>` flag or a test mode that restores a backup from `v012` code snapshot and then runs `v020` migrations against it — proving forward migration works. At minimum, document this gap explicitly.
- RPO/RTO and retention must be stated explicitly: "7 backups × 1/day = 7-day RPO max. If corruption is silent for >7 days, all backups are lost." Add a recommendation to keep at least 1 weekly backup separately (CRM_BACKUP_KEEP_WEEKLY).

---

## Attack 4 — Verification ≠ usable app: read-only smoke is not "working CRM"

### What the plan says
Phase 2 functional smoke: `GET /health`, `GET /api/dedup/candidates`, `GET /api/segments`, `GET /` web screen. "Reads are unguarded → no X-CRM-Token needed."

### What the CRM actually does
The CRM is a reverse-ETL + operational tool. The **business-critical workflows** that the team actually uses include:
- **Write operations:** creating/updating crm_party records, tagging customers, creating tasks, updating segments.
- **Hug campaign dispatch:** creates campaign records, fires webhook to Zalo/email. Pure reads won't catch a broken write path.
- **Dedup merge:** mutates crm.db (merges party records). Read-only check of `/api/dedup/candidates` tells you candidates exist but says nothing about whether merging them would succeed.
- **Voucher generation / consent recording:** write paths to crm.db.
- **sync_parties** is intentionally skipped in `CRM_VERIFY_MODE=1` — correct for isolation, but it means the verified CRM has zero crm_party rows (or only what was in crm.db at backup time, not what sync_parties would produce). A "passing" drill could show an empty parties list and still PASS all checks.

If `sync_parties` didn't run, `GET /api/dedup/candidates` and `GET /api/segments` may return empty lists (no parties = no candidates, no segment members). The drill SUCCESS criteria says "return 200 + plausibly non-empty." If the backup itself was taken after a wipe or during a slow period, "plausibly non-empty" fails to detect an empty-table restore.

**Operational failure:** drill PASSES. Operator declares CRM restored. Business tries to create a task or fire a hug campaign → 500 error or silent failure on write path. CRM is "up" but not usable.

**Specific plan fix required:**
- Add at minimum one **write smoke test** to the drill: POST a test crm_party (or a test tag), verify it persists, DELETE it. Clean up after. No token needed if writes are also unguarded, or add a test token env var.
- Document explicitly: "A passing drill proves reads work. Writes are not verified. Manual validation of write paths is required before declaring full operational recovery."
- The "plausibly non-empty" criterion needs a minimum threshold (e.g., "≥100 parties in crm_party table") derived from the manifest row count, not just 200 status.

---

## Attack 5 — Dagster-wireable claim: not actually wireable with the current architecture

### What the plan says
"pure callable + CLI, clean exit codes — so scheduling is a later wiring step, not a rewrite." The module is `crm/ops/backup_crm.py` importable from a future Dagster op.

### The architectural reality
`docker-compose.yml` shows:
- `data_platform` (Dagster) container does NOT have a Docker socket mounted. There is no `- /var/run/docker.sock:/var/run/docker.sock` in its volumes.
- The new backup runs **inside the `crm` container** via `docker exec crm python -m crm.ops.backup_crm`. 
- A Dagster op in `data_platform` would need to either: (a) call `docker exec crm ...` — which requires Docker socket access, or (b) call the crm backup module directly — which requires the crm Python package to be installed in data_platform (it's not; they're separate images).
- The existing `system_backup.py` Dagster op runs `bash backup.sh` directly because that script runs **inside data_platform** and copies the `crm_data` volume that is mounted read-only at `/app/var/crm_data:ro` in the data_platform container. The new backup CANNOT use this path (it needs WAL-safe API, not raw cp).
- Dagster-via-HTTP: the CRM has no backup-trigger API endpoint. The plan doesn't add one.

So "callable from Dagster later" requires one of:
- Docker socket in data_platform (security risk, currently absent)
- A new HTTP endpoint on the CRM (scope change)
- Re-architecting backup to run from data_platform using the read-only crm_data mount (which brings back the WAL/SHM problem the plan is explicitly designed to avoid)

The "callable + CLI" claim is true for manual `docker exec`, but the Dagster-wiring path is architecturally blocked by current container topology.

**Specific plan fix required:**
- Remove or qualify "so it can wire into Dagster later" — replace with an honest assessment: "To wire into Dagster, one of: (a) add Docker socket to data_platform (security consideration), (b) add HTTP backup-trigger endpoint to CRM, (c) accept a read-only mount + WAL-safe copy from data_platform (evaluate feasibility). The current architecture does not support direct Dagster wiring without one of these changes."
- Phase 4 handoff (warehouse DR) should not inherit this claim uncritically.

---

## Attack 6 — Missing operational monitoring: backups silently stop and nobody knows

### What the plan says
Nothing. There is no monitoring, alerting, or backup-freshness check anywhere in the plan. Phase 1 has a clean exit code. That's it.

### The real failure
The zombie-run incident (documented in `from-reliability-agent-zombie-run-stuck-sensor-fix-260624-1656-report.md`) shows that scheduled tasks in this system silently fail and run empty for extended periods before anyone notices. The `backup.sh` already runs on Windows Task Scheduler — there is no mention of whether it has succeeded recently or whether any human has checked.

Specifically:
- `CRM_BACKUP_KEEP=7` means 7 backups. If the backup job silently stops running (container restart, Docker Desktop restart loses the schedule, Windows Task Scheduler misfires), you will have 7 old backups all older than 7 days — and zero way to know until an incident. The rotation guard removes old backups on success; if no backup runs, rotation never fires, and you end up with the last 7 backups aging silently.
- There is no Lark/webhook notification on backup failure (the existing `system_backup.py` sends a Lark card on SUCCESS but not on failure — see lines 103-116 where the `try/except` swallows notification failures silently. A FAILURE raises `Failure()` which Dagster catches and marks the run failed, but only if someone is watching Dagster UI).
- The `backup_crm.py` module has no notification path at all (not even the Lark card `system_backup.py` has).
- There is no monitoring endpoint or Dagster sensor checking "is the latest crm backup younger than 24h?"

**Specific plan fix required (must-fix):**
- Phase 1 `backup_crm.py` MUST emit a failure notification (Lark or at minimum stderr + non-zero exit clearly bubbling to whoever calls it). On-demand is fine for now, but failure must be loud, not silent.
- Phase 3 runbook must include a "how do I know backups are running?" section: check `ls -lt app_data/crm_backups/` and verify the newest is <24h old. Trivial to add, critical to not omit.
- Nice-to-have/future: a Dagster sensor that checks backup age and alerts if >48h (consistent with the pattern used elsewhere in the system).

---

## Summary Table

| # | Finding | Severity | Category |
|---|---------|----------|----------|
| 1 | All backups local-only — host/disk loss = total data loss | **Must-fix** | DR gap |
| 2 | Three competing crm_data backup mechanisms, no authoritative hierarchy | **Must-fix** | DRY / operator confusion |
| 3 | Old backup + forward migration path never drilled; RPO unstated | **Must-fix** | Completeness |
| 4 | Drill is read-only smoke; write paths and empty-data false-PASS undetected | **Must-fix** | Verification gap |
| 5 | Dagster-wiring claim architecturally blocked by current container topology | **Must-fix** (correct claim) | False premise |
| 6 | No alerting on backup failure; silent stop risk documented by prior incidents | **Must-fix** | Observability |

---

**Status:** DONE

**Must-fix before implementation (ranked — highest consequence first):**
- **[1] Offsite gap:** Add explicit "What this does NOT cover" section to Phase 3 runbook. Name minimum viable offsite path (NAS copy, R2 upload). Do NOT call it DR without this caveat. Zero implementation cost — just honest docs.
- **[2] Dual/triple backup reconciliation:** Phase 1 must declare the authority hierarchy and deprecation plan for existing `backup.ps1`/`backup.sh` crm_data raw copies. Operator confusion during an incident is high-stakes.
- **[5] Dagster-wiring claim:** Correct the "callable from Dagster later" framing to name the 3 architectural options and their trade-offs. The claim as written is false.
- **[6] Silent failure:** `backup_crm.py` must emit a failure notification (Lark card or loud log). Add a "verify backups are running" check to Phase 3 runbook. Mirrors the lesson from the zombie-run incident.
- **[4] Write-smoke gap:** Add one write+delete test to Phase 2 drill. Document explicitly that reads passing ≠ writes working. Add minimum row-count threshold derived from manifest (not just "200 OK").
- **[3] Old-backup + migration:** Add migration-failure handling to Phase 3 runbook. State RPO explicitly (7 days). Acknowledge the drill never tests the forward-migration path.

**Defer / future (nice-to-have, not blockers):**
- Dagster sensor for backup age alerting (>48h = alert). Consistent with system patterns but scheduling is explicitly out of scope for this plan.
- Weekly long-retention backup (1/week, keep 4) alongside daily (keep 7) for >7-day silent corruption scenarios.
- `--target-migration` test mode in Phase 2 drill to simulate old-backup + forward-migration restore.
- Encryption / PII sanitization (explicitly deferred to `260624-1958-pipeline-hardening-followups` — correct call, just confirm the two plans don't conflict on `backup.sh` layout).
- HTTP backup-trigger endpoint on CRM (enables cleaner Dagster wiring without Docker socket).
