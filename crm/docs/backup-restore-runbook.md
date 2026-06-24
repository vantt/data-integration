# CRM Backup & Restore Runbook

**Principle:** an untested backup is not a backup. Backups are proven by the
restore-verify drill, not by their existence.

Tooling: `crm/ops/backup_crm.py` (verified snapshot) + `crm/ops/restore_verify_crm.py`
(restore drill). Authoritative for CRM — the raw `crm_data` copy in
`scripts/backup/{backup.sh,backup.ps1}` is **disabled/deprecated**; do not re-enable it.

## What is protected
- **`crm.db`** — source of truth (parties, tags, segments, tasks, campaigns, hug
  identity/voucher, consent, app users). Backed up + integrity-verified.
- **`cache.db`** — warehouse reverse-ETL snapshot. Backed up so a restore is
  self-contained, but it is **regenerable** (see "post-restore refresh").

## What is NOT protected (honest scope)
- This is a **local checkpoint, not full DR.** Snapshots live in the `crm_backups`
  Docker volume on the **same host** as prod → host/disk loss = total loss.
  **Minimal offsite step:** periodically copy a snapshot out and off-box, e.g.
  `docker run --rm -v <proj>_crm_backups:/b:ro -v "$PWD/offsite:/out" alpine cp -r /b/<ts> /out/`
  then sync `offsite/` to a NAS / R2 / S3.
- Warehouse (`olap.duckdb`, parquet lake, Dagster) — separate DR (see plan Phase 4).

## 1. Take a backup
```
docker exec crm python -m crm.ops.backup_crm --data-dir /data --dest /backups --keep 7
```
Writes `/backups/<YYYYMMDD-HHMMSS>/{crm.db, cache.db, manifest.json}` to the
`crm_backups` volume. The backup is a **gate**: it FAILS (non-zero + Lark alert) if
the snapshot does not byte-match the live source (counts + content checksums).

## 2. Verify a backup (the drill)
```
python crm/ops/restore_verify_crm.py                 # latest backup
python crm/ops/restore_verify_crm.py --backup <ts>
python crm/ops/restore_verify_crm.py --negative value   # self-test: must FAIL
```
- **PASS** = the backup booted a fresh, isolated CRM with data matching the manifest.
- The drill never touches prod (`crm` / `crm_data`); it asserts prod `crm.db` is
  unchanged before/after.

## 3. Real-incident restore (crm.db lost / corrupted)
> Causes downtime. Do it deliberately.
1. Pick + verify the backup first: `python crm/ops/restore_verify_crm.py --backup <ts>` → must PASS.
2. **Stop CRM:** `docker stop crm`
3. **Safety-copy current data** (so you can roll back):
   `docker run --rm -v <proj>_crm_data:/d -v "$PWD/app_data/crm_data_safety:/s" alpine cp -a /d/. /s/`
4. **Restore** the chosen snapshot into the `crm_data` volume:
   `docker run --rm -v <proj>_crm_backups:/b:ro -v <proj>_crm_data:/d alpine sh -c "rm -f /d/crm.db* /d/cache.db* && cp /b/<ts>/crm.db /b/<ts>/cache.db /d/"`
5. **Start CRM:** `docker compose up -d crm` → check `docker logs crm` (migrations OK) + `curl :3007/healthz` + spot-check the UI.
6. **Post-restore cache refresh (mandatory):** `cache.db` from the backup is *stale*.
   Trigger a fresh sync before relying on warehouse-derived views:
   `curl -X POST -H "X-Refresh-Token: $CRM_REFRESH_TOKEN" http://localhost:3007/admin/refresh`
7. **Rollback** if wrong: `docker stop crm` → restore the safety copy into `crm_data` → `docker compose up -d crm`.

> `<proj>` = compose project prefix (e.g. `data-integration`). Find it: `docker volume ls | grep crm_data`.

## 4. Retention / RPO
- `--keep 7` → max data-loss window = 7 × backup interval. Silent corruption older
  than retention is unrecoverable — keep a longer-retention offsite tier if needed.
- **Is it running?** Check the newest snapshot age:
  `docker run --rm -v <proj>_crm_backups:/b:ro alpine sh -c "ls -1 /b | tail -1"` —
  if older than your SLA, backups have silently stopped (investigate; alert on it).

## 5. Known follow-ups (not yet built)
- Scheduling (Dagster needs a CRM admin endpoint / socket / cron — not a trivial op).
- Cross-version restore drill (`--forward-migrate`: old backup → current schema).
- Offsite automation + backup-age alerting.
- Image-digest pinning assertion in the drill (manifest records it once `CRM_IMAGE_DIGEST` is set at backup time).
