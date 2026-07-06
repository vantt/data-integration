---
phase: 6
title: "Automated Restore-Verify (drill-runner sidecar)"
status: completed
priority: P2
effort: "1.5d"
dependencies: [1, 2, 5]
---

# Phase 6: Automated Restore-Verify (drill-runner sidecar)

## Overview
Make the restore drill run **inside this system** on a schedule (no external host scheduler). A tiny single-purpose sidecar holds the Docker socket and exposes an HTTP trigger; a Dagster weekly schedule calls it; the sidecar spins the ephemeral CRM and runs the drill. Closes the "auto-verify" gap while keeping the Docker-socket blast radius minimal + auditable.

## Why a sidecar (not socket on data_platform)
- HTTP-ifying alone can't avoid the socket for the drill — the drill MUST spin a container, so *something* behind the endpoint needs Docker access.
- Putting the socket on `data_platform` (runs dlt/dbt/Sapo code) = huge blast radius. A dedicated **single-purpose** sidecar that only runs the drill = small, auditable surface, no public route, token-gated.

## Architecture
```
crm_restore_verify_schedule (weekly, Dagster)
  → crm_restore_verify asset  --HTTP POST /run-drill (token)-->  crm_drill_runner sidecar [has /var/run/docker.sock]
      --docker run-->  crm-restore-verify (ephemeral CRM from latest backup)  → PASS/FAIL
  ← asset reds on FAIL  → health_alert_failure_sensor alerts
```

## Components
1. **`Dockerfile.drillrunner`** — `python:3.12-slim` + docker CLI; runs a tiny FastAPI (`crm/ops/drill_runner_server.py`) exposing `POST /run-drill` (token-gated via `DRILL_TOKEN`) that subprocess-runs `restore_verify_crm.py` and returns `{status, exit_code, tail}`.
2. **`docker-compose.yml` → new service `crm_drill_runner`**: build the Dockerfile; mounts `/var/run/docker.sock:/var/run/docker.sock` + `./crm:/app/crm:ro` + the `crm_backups` volume; on `caddy_net` (Dagster reaches it by name); **NO Caddy label, NO published port** (internal only); `mem_limit: 512m`; `DRILL_TOKEN=${DRILL_TOKEN:?...}` from root `.env`.
3. **Drill rework (`crm/ops/restore_verify_crm.py`)** for sibling-container correctness (named volumes resolve on the host daemon; host binds don't translate from a socket-mounted container):
   - Restore the backup into a **named volume `crm_verify_data`** (helper `alpine cp` from `crm_backups` → `crm_verify_data`), not a host bind.
   - `docker run -v crm_verify_data:/data ...` for the ephemeral CRM.
   - Gate A integrity: read restored DBs via a helper container mounting `crm_verify_data` (reuse `backup_crm.profile_db`).
   - This mode also works when run from the host, so it replaces the current host-bind path (DRY).
4. **Bake the `CRM_VERIFY_MODE` entrypoint into the crm image** (rebuild `crm`) → drop the runtime entrypoint-mount + CRLF/LF hack entirely. The gate becomes permanent + the drill stops mounting `entrypoint.sh`.
5. **Dagster** — `crm_restore_verify` asset **`deps=[crm_backup]`** (fail-loud, POST to the sidecar) added to the **daily** `crm_backup_job`. So each daily run = backup → immediately verify the just-made backup is recoverable; a failed verify reds the run + alerts. (Decision 2026-06-26: daily + chained after backup — "a backup isn't trusted until proven restorable".) The drill **cleans up** its ephemeral container + clears the `crm_verify_data` volume every run.

## Related Code Files
- Create: `Dockerfile.drillrunner`, `crm/ops/drill_runner_server.py`
- Modify: `crm/ops/restore_verify_crm.py` (named-volume mode), `docker-compose.yml` (new service + `crm_verify_data` volume), `orchestration/assets/crm_sync.py` (`crm_restore_verify` asset), `orchestration/definitions.py` (job + schedule), `.env` (`DRILL_TOKEN`)
- Rebuild: `crm` image (bake entrypoint gate)

## Implementation Steps
1. Rework `restore_verify_crm.py` to named-volume mode; verify it still PASSes + negatives still caught (from host first).
2. Bake the entrypoint gate into the crm image; rebuild `crm`; confirm prod CRM healthy + drill no longer needs the entrypoint mount.
3. Write `drill_runner_server.py` + `Dockerfile.drillrunner`.
4. Add the `crm_drill_runner` service + `crm_verify_data` volume + `DRILL_TOKEN`; bring it up; test `POST /run-drill` (token) end-to-end from `data_platform`.
5. Add the `crm_restore_verify` asset + weekly schedule; verify definitions import clean; restart `data_platform`.
6. Trigger the Dagster job manually once → confirm PASS in the Dagster UI; confirm a FAIL (tamper) reds the run + alerts.

## Success Criteria
- [x] Daily Dagster `crm_backup_job` runs `crm_backup → crm_restore_verify` (deps-chained); drill PASSes via the sidecar (verified 2026-06-26, backup `20260626-020014`, 50251+78860 rows match manifest).
- [x] A tampered backup makes the drill FAIL (non-vacuous) — `value` tamper caught at Gate A (sha256 mismatch); `crm_restore_verify` reds → failure sensor alerts.
- [x] Docker socket mounted ONLY on the single-purpose `crm_drill_runner` (no public route, token-gated `X-Drill-Token` → 401 on bad token); NOT on `data_platform`.
- [x] Drill uses the `crm_verify_data` named volume (no host-bind translation); `CRM_VERIFY_MODE` gate baked into the crm image (no runtime entrypoint mount).
- [x] Prod CRM untouched (fingerprint stable across the drill) + stays healthy across the crm rebuild; ephemeral container + verify volume cleaned each run.

## Outcome (2026-06-26)
Built + verified live, zero downtime. One real bug found in verification: the drill runs INSIDE the socket-mounted sidecar, so the ephemeral CRM's *host-published* port was unreachable as `localhost` from the sidecar (Gate B "never healthy" despite the app being up). Fixed by joining `caddy_net` and reaching the ephemeral by container name (no published port) in sidecar mode; host/dev mode keeps the published-port path. Captured as a lesson.

## Risk Assessment
- **Docker socket = root on host** (even isolated). Mitigate: single-purpose sidecar, no public route, token-gated, documented. Accepted trade-off for in-system orchestration.
- **crm image rebuild** could break prod CRM startup. Mitigate: rebuild + recreate with the existing verified entrypoint logic; health-check before/after; rollback = previous image.
- **Sibling-container path translation** — the reason for named volumes; the top correctness risk if missed.
