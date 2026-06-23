# Infra & Docker Config Audit — 2026-06-23

**Scope:** docker-compose.yml, docker-compose.override.yml, Dockerfile.*, caddy/, caddy-global/, env files, .gitignore, .dockerignore, loose root scripts, detailView service.

---

## CRITICAL

### C1 — Cloudflare API Token Exposed in Plaintext Backups
**File:** `app_data/backups/202606*/config/.env.docker` (all 7 daily backups)
**Token value:** `cfut_REDACTED_ROTATE_THIS_TOKEN` (present in every backup file)
**Risk:** The backup script copies `.env.docker` verbatim to `app_data/backups/`. While `app_data/` is gitignored, the token exists in 7 plaintext copies on the Windows filesystem. Any filesystem backup (OneDrive, Windows Backup, shadow copies), logs exfil, or directory traversal vulnerability on the Windows host exposes a live Cloudflare DNS-management API token. This token controls ACME DNS-01 certificate issuance — compromise = subdomain takeover / cert issuance for any `*.lan.fwg.vn`.
**Direction:** Rotate the token. Exclude `.env.docker` from the backup script's config copy step (copy a sanitized manifest instead), or encrypt the backup archive. Add `app_data/backups/` exclusion audit to the backup rotation script.

---

### C2 — `CRM_REFRESH_TOKEN` Hardcoded Default in Tracked `docker-compose.yml`
**File:** `docker-compose.yml:171`
```
- CRM_REFRESH_TOKEN=change-me-crm-refresh
```
**Risk:** The `POST /admin/refresh` endpoint on the CRM service (`:8090`) is protected only by this token. It is baked into the tracked compose file as a literal default. Any team member who clones the repo knows the default. If the operator never overrides it in `.env.docker`, the endpoint is effectively unprotected on the LAN — Dagster uses it to trigger reverse-ETL, but so could anyone on the network.
**Verification:** `.env.docker` line 102-103 does override this value, so the running container is not using the default. The risk is onboarding/restore scenarios where someone runs `docker compose up` without first configuring `.env.docker`.
**Direction:** Remove the fallback literal from `docker-compose.yml`. Use `${CRM_REFRESH_TOKEN}` (no default) so Docker Compose fails loudly if the variable is unset. Document the required var in `.env.docker.example` (it's present there as a comment only at line 94-95).

---

## HIGH

### H1 — `CRM_DEV_RELOAD=1` Hardcoded in Base `docker-compose.yml` (Runs in Prod)
**File:** `docker-compose.yml:174`
```
- CRM_DEV_RELOAD=1
```
**Also:** `docker-compose.override.yml:6` (duplicated — override is redundant)
**Risk:** `crm/entrypoint.sh:38-40` shows `CRM_DEV_RELOAD=1` enables `uvicorn --reload --reload-dir /app/crm/src`. This means the production container runs with the live-reload watcher active: higher CPU/memory, reduced performance, and non-deterministic process behavior (file watchers can misbehave or miss changes under volume mounts). More importantly, this signals the base compose was configured for development and may have other dev-mode assumptions that reach production.
**Direction:** Remove `CRM_DEV_RELOAD=1` from `docker-compose.yml`. Keep it only in `docker-compose.override.yml` (which should be excluded from the production deploy command `docker compose -f docker-compose.yml up -d`). The override file comment already says "Production: use `docker compose -f docker-compose.yml up -d`" — but the base file contradicts this.

### H2 — `metabase` and `rill` Mount `data_lake` Read-Write — Shared DuckDB Write Risk
**File:** `docker-compose.yml:64` (metabase), `docker-compose.yml:85` (rill)
```
- ./app_data/data_lake:/app/var/data_lake        # no :ro
```
**Risk:** `olap.duckdb` sits at `data_lake/serving/olap.duckdb`. `data_platform` (Dagster) writes to it. `metabase` and `rill` mount the same directory without `:ro`. DuckDB is single-writer; a concurrent write attempt from metabase or rill during a Dagster serving rebuild causes a lock error or corruption. In practice, metabase opens DuckDB read-only via the DuckDB JDBC driver, but the OS-level mount gives the container write permission — there is no defense-in-depth if the driver misbehaves or an admin runs a raw DuckDB command inside the metabase container.
**Note from memory:** DuckDB lock storms have already occurred in this project (see `feedback_duckdb_not_for_concurrent-write.md`).
**Direction:** Add `:ro` to the `data_lake` mount for `metabase` and `rill`. The overlay `monitoring_db:/app/var/data_lake/monitoring` named volume will still allow monitoring writes within metabase's container if needed.

### H3 — `dagster dev` Running in Production
**File:** `docker-compose.yml:45`
```
dagster dev -h 0.0.0.0 -p 3001 -f orchestration/definitions.py
```
**Risk:** `dagster dev` is the development server. Dagster documentation explicitly states `dagster dev` should not be used in production — it auto-reloads on code changes, lacks production stability, and may expose the Dagster UI without authentication on port 3000 (internal) and through Caddy at `etl.lan.fwg.vn`. The Dagster UI allows triggering arbitrary pipeline runs, viewing logs with credentials from env vars, and managing schedules.
**Direction:** For production, use `dagster-webserver` + `dagster-daemon` as separate processes (or a supervisor approach). At minimum, add authentication to the Caddy route for `etl.lan.fwg.vn`.

### H4 — `HUG_ADMIN_SECRET` Referenced in Compose but Missing from `.env.docker.example`
**File:** `docker-compose.yml:178`
```
- HUG_ADMIN_SECRET=${HUG_ADMIN_SECRET}
```
**Risk:** There is no entry for `HUG_ADMIN_SECRET` in `.env.docker.example` or `.env.example`. This var controls the POST `/hug/token/upsert` endpoint on the Cloudflare Worker (`hug.fjp.vn`). If an operator sets up from the example template, `HUG_ADMIN_SECRET` will be an empty string — the CRM will push upserts with no secret, or the Worker will reject them silently. No documentation in examples warns about this required variable.
**Direction:** Add `HUG_ADMIN_SECRET=your_hug_admin_secret_here` to `.env.docker.example` with a clear description.

### H5 — `CLOUDFLARE_API_TOKEN` Not in `.env.docker.example` / `.env.example`
**File:** `caddy-global/docker-compose.yml:24` references `${CLOUDFLARE_API_TOKEN}`, but neither `.env.docker.example` nor `.env.example` documents it.
**Risk:** New operators won't know this token is required. The caddy-global compose reads from `--env-file .env.docker` but that's not documented. During initial setup, the Caddy DNS-01 challenge will silently fail, causing certificate issuance failures for all services.
**Direction:** Add `CLOUDFLARE_API_TOKEN=your_cloudflare_zone_token_here` to `.env.docker.example` under a `[CADDY-GLOBAL]` section.

---

## MEDIUM

### M1 — 5 Services Lack Healthchecks in Compose/Dockerfile
**Files:** `Dockerfile.dataplatform`, `Dockerfile.metabase`, `Dockerfile.rill`, `Dockerfile.evidence` — no HEALTHCHECK instruction. `docker-compose.yml` has no `healthcheck:` blocks for these services.
**Only `Dockerfile.crm` and `Dockerfile.detailview` have HEALTHCHECK.**
**Risk:** `restart: unless-stopped` restarts on crash, but Docker cannot report "unhealthy" status. Dependent services that restart after `data_platform` won't know if it's ready. Dagster startup takes 20-30s (dbt parse, bootstrap) — no readiness signal means dependent callers (CRM reverse-ETL trigger) may race.
**Direction:** Add `HEALTHCHECK` to `Dockerfile.dataplatform` (dagster webserver `/server_info`), `Dockerfile.metabase` (`/api/health`), and `Dockerfile.evidence` (HTTP 200 on preview port).

### M2 — `Dockerfile.rill` Uses `rilldata/rill:latest` (Mutable Tag)
**File:** `Dockerfile.rill:1`
```
FROM rilldata/rill:latest
```
**Risk:** `latest` is re-pulled on rebuild, making the build non-reproducible. A breaking Rill release will silently reach production on next `docker compose build`.
**Direction:** Pin to a specific version tag (e.g., `rilldata/rill:v0.49.0`). Update deliberately.

### M3 — All Service Ports Bind to `0.0.0.0` (All Interfaces) Without Host Restriction
**File:** `docker-compose.yml` — all ports use `"3000:3001"`, `"3001:3000"`, etc. format.
**Risk:** On a Windows host connected to LAN, ports 3000-3007 are reachable from any LAN device directly, bypassing Caddy auth/TLS. Dagster UI (3000), Metabase (3001), Rill (3002), Fileserver (3004), DetailView (3005), Evidence (3006), CRM (3007) are all directly accessible on LAN without any authentication layer.
**Mitigation in place:** Caddy provides HTTPS + basic_auth for fileserver. Rill, Evidence, Metabase have no application-level auth on direct port access.
**Direction:** Restrict sensitive ports to `127.0.0.1:`: e.g. `"127.0.0.1:3001:3000"` for metabase. Services only need to be reachable via Caddy reverse proxy, not directly from LAN.

### M4 — `bootstrap_serving_views.py` Opens `olap.duckdb` Read-Write During Serving
**File:** `scripts/provisioning/bootstrap_serving_views.py:96`
```python
con = duckdb.connect(SERVING_DB_PATH)  # no read_only=True
```
**Risk:** This script runs at `data_platform` startup (via `bootstrap_reporting.py` in the compose command). When run while Metabase has the DB open for reading, this can cause a write-lock contention on `olap.duckdb`. Metabase docs/memory note recommends always `read_only=True` on serving DBs.
**Direction:** Confirmed the script *creates* the views — it must be read-write. But add documentation comment explaining why it's intentionally RW and that Metabase must be stopped first (consistent with existing memory note `feedback_duckdb_view_rebuild.md`). Consider adding a lock-wait loop or explicit stop/start ordering.

### M5 — `check_*.py` Scripts Committed to Git (Tracked)
**Files:** `check_parquet_date_range.py`, `check_sapo_channel_mapping.py`, `check_sapo_order_history_log.py`, `check_sapo_order_payload.py`, `check_sapo_order_sources.py`, `check_sapo_order_text_partition.py`, `check_sapo_raw_orders.py`, `check_sapo_shopee_gap.py`, `check_shopee_orders_history.py` — all tracked by git.
**Risk:** Ad-hoc analysis scripts committed to main repo. They contain hardcoded local paths (e.g. `D:/Vantt/app/data-integration/app_data/...`), business-specific queries, and schema assumptions that will silently break as the schema evolves. They are not excluded from the Docker build context (`.dockerignore` has no `check_*.py` exclusion), adding unnecessary KB to every build.
**Direction:** Move to `scripts/analysis/` or `poc/` (already gitignored), or add to `.gitignore` and `.dockerignore`. At minimum, add `check_*.py` and `_tmp_*.py` to `.dockerignore`.

### M6 — `_tmp_gift_check.py` at Repo Root (Untracked, Not Gitignored)
**File:** `_tmp_gift_check.py` (untracked per git status)
**Risk:** Temporary analysis script not in `.gitignore`. Will remain as noise until manually deleted. Contains hardcoded absolute Windows path `D:/Vantt/app/data-integration/...`.
**Direction:** Add `_tmp_*.py` to `.gitignore`. Delete file.

### M7 — Metabase Runs H2 Embedded Database in Production
**File:** `.env.docker:75` → `MB_DB_TYPE=h2`
**Risk:** H2 is a single-file Java embedded DB. It has no concurrent-safe backup mechanism — a file copy while Metabase is running can produce a corrupt snapshot. Corruption (disk full, unclean shutdown) means total loss of all dashboards, questions, and users. H2 is officially unsupported by Metabase for production.
**Direction:** Migrate to Postgres backend for Metabase (already commented out in `.env.docker.example`). At minimum, include the Metabase H2 file in the existing backup rotation (`app_data/backups/`) which currently backs up `config/` but may not back up `app_data/metabase_data/metabase.db.mv.db`.

---

## LOW

### L1 — `plans/` and `docs/` Not Excluded from Docker Build Context
**Files:** `.dockerignore` — no exclusion for `plans/` (8.2MB) or `docs/` (3.9MB).
**Risk:** Every `docker compose build` sends ~12MB of planning docs and reports to the Docker daemon unnecessarily. Minor build context bloat, no security impact.
**Direction:** Add `plans/` and `docs/` to `.dockerignore`.

### L2 — `ingestion/.dlt/config.toml` Contains Real Google Sheets URLs (Tracked)
**File:** `ingestion/.dlt/config.toml:25-27`
```toml
marketing_spend = "https://docs.google.com/spreadsheets/d/1wQpT4lCZWrPE7fnbRNTKiNDRFzVT2u_WhN-9uY9u3lc/..."
targets = "https://docs.google.com/spreadsheets/d/1ZHt2iAD88OGgSRopVOkqEgusja-JpP4XqtiH4anhax4/..."
```
**Risk:** Real spreadsheet IDs committed to git. These are not credentials, but expose internal business data URLs. Anyone with repo access can directly access the sheets if sharing is set to "anyone with the link."
**Direction:** Verify sheets are access-controlled (require Google auth). If OK, low impact. Otherwise restrict sharing and use `.env` for URLs.

### L3 — `ingestion/.dlt/config.toml` Contains `REPLACE_ME` Facebook/Messenger Placeholders (Tracked)
**File:** `ingestion/.dlt/config.toml:29-35`
```toml
[sources.facebook_ads]
access_token = "REPLACE_ME_OR_SET_ENV_VAR"
```
**Risk:** Not a live secret, but signals these source configs are incomplete. If someone accidentally pastes a real token here instead of using env vars, it will be committed.
**Direction:** Add a pre-commit hook or comment warning to use env vars only. Add `.dlt/secrets.toml` pattern to the gitignore (already has `ingestion/.dlt/secrets.toml.sample` pattern but the actual `secrets.toml` path should be verified as gitignored — it is via `ingestion/.gitignore`).

### L4 — `caddy-global` Uses `docker.sock` Mount Without Explicit Read-Only
**File:** `caddy-global/docker-compose.yml:28`
```
- /var/run/docker.sock:/var/run/docker.sock
```
**Risk:** Required for caddy-docker-proxy to read container labels. But this grants the Caddy container full Docker API access (equivalent to root on the host). If Caddy is compromised, the attacker has host-level control.
**Direction:** This is an accepted architectural constraint of caddy-docker-proxy. Document the risk. Consider socket proxy (e.g., `tecnativa/docker-socket-proxy`) to expose only read-only label endpoints.

### L5 — No Resource Limits on Any Service
**File:** `docker-compose.yml` — no `mem_limit`, `cpus`, or `deploy.resources` on any service.
**Risk:** A runaway Dagster pipeline or DuckDB query can consume all RAM, causing OOM kills of other services (Metabase, CRM). On Windows/Docker Desktop, this affects the WSL2 VM memory ceiling.
**Direction:** Add `mem_limit` on at least `data_platform` (the heaviest consumer). Example: `mem_limit: 6g`.

### L6 — `Dockerfile.dataplatform` Runs as Root
**File:** `Dockerfile.dataplatform` — no `USER` directive. Container runs as root.
**Risk:** All services except `metabase` (which has `USER metabase`) run as root inside containers. Privilege escalation from a compromised container is easier as root.
**Direction:** Add non-root `USER` to `Dockerfile.dataplatform`, `Dockerfile.crm` (already runs as default Python image user — verify), `Dockerfile.detailview`, `Dockerfile.evidence`, `Dockerfile.rill`.

---

## Summary Table

| ID | Severity | Title |
|----|----------|-------|
| C1 | CRITICAL | Cloudflare API token in plaintext backup files |
| C2 | CRITICAL | CRM refresh token hardcoded default in tracked compose |
| H1 | HIGH | `CRM_DEV_RELOAD=1` active in base compose (prod runs dev mode) |
| H2 | HIGH | metabase + rill mount data_lake read-write (DuckDB lock risk) |
| H3 | HIGH | `dagster dev` running in production |
| H4 | HIGH | `HUG_ADMIN_SECRET` undocumented in env examples |
| H5 | HIGH | `CLOUDFLARE_API_TOKEN` undocumented in env examples |
| M1 | MEDIUM | 5 services lack Docker healthchecks |
| M2 | MEDIUM | Rill uses `latest` image tag (non-reproducible builds) |
| M3 | MEDIUM | All ports bind to 0.0.0.0 — services accessible direct on LAN |
| M4 | MEDIUM | `bootstrap_serving_views.py` opens olap.duckdb read-write at startup |
| M5 | MEDIUM | `check_*.py` ad-hoc scripts tracked in git + in build context |
| M6 | MEDIUM | `_tmp_gift_check.py` at repo root, not gitignored |
| M7 | MEDIUM | Metabase using H2 embedded DB in production (no crash-safe backup) |
| L1 | LOW | `plans/` and `docs/` not excluded from Docker build context |
| L2 | LOW | Real Google Sheets URLs in tracked `config.toml` |
| L3 | LOW | `REPLACE_ME` Facebook token placeholders in tracked config |
| L4 | LOW | `docker.sock` full-access mount in caddy-global |
| L5 | LOW | No resource limits on any service |
| L6 | LOW | Most containers run as root |

---

## Unresolved Questions

1. **C1 rotation urgency:** Has the Cloudflare token `cfut_RKOf...` already been rotated since the backup was made, or is it the current live token? If live, rotate immediately.
2. **M3 LAN exposure intent:** Are `etl.lan.fwg.vn`, `bi.lan.fwg.vn`, etc. intended to be accessible on LAN without Caddy auth (trusted LAN)? If yes, M3 drops to LOW. If the host is on a shared office network, it's HIGH.
3. **H3 dagster-webserver auth:** Is the Dagster UI at `etl.lan.fwg.vn` intended to be open to all LAN users, or should it require auth? Dagster OSS has no built-in auth — requires external (Caddy basic_auth or VPN).
4. **backup script scope:** Does the existing backup script in `scripts/` back up `app_data/metabase_data/`? If not, a Metabase H2 crash has no recovery path.

---

## FIXES APPLIED 260623

### Applied

| Finding | Status | Change | File:Line |
|---------|--------|--------|-----------|
| C2 | APPLIED | Replaced `CRM_REFRESH_TOKEN=change-me-crm-refresh` with `${CRM_REFRESH_TOKEN:?CRM_REFRESH_TOKEN must be set in .env.docker}` — fails loudly if unset | `docker-compose.yml:171` |
| H1 | APPLIED | Removed `CRM_DEV_RELOAD=1` from base compose; kept only in `docker-compose.override.yml` | `docker-compose.yml:174` (line removed) |
| H2 | APPLIED | Added `:ro` to `data_lake` mounts for `metabase` and `rill` | `docker-compose.yml:64,85` |
| H4 | APPLIED | Added `HUG_ADMIN_SECRET` with description to `.env.docker.example` | `.env.docker.example` (new section) |
| H5 | APPLIED | Added `CLOUDFLARE_API_TOKEN` under `[CADDY-GLOBAL]` section in `.env.docker.example` | `.env.docker.example` (new section) |
| M1 | APPLIED | Added `HEALTHCHECK` to `Dockerfile.dataplatform` (`/server_info`), `Dockerfile.metabase` (`/api/health`), `Dockerfile.evidence` (HTTP 200 on port 3000); added `curl` to each image's apt install | `Dockerfile.dataplatform`, `Dockerfile.metabase`, `Dockerfile.evidence` |
| M5 | APPLIED | Added `check_*.py`, `_tmp_*.py` to `.dockerignore` | `.dockerignore` |
| M6 | APPLIED | Added `_tmp_*.py` and `_tmp_*.sh` to `.gitignore` (covers `_tmp_gift_check.py`) | `.gitignore` |
| L1 | APPLIED | Added `plans/` and `docs/` to `.dockerignore` | `.dockerignore` |
| L1+ | APPLIED | Added `.pytest_cache/`, `.mypy_cache/`, `node_modules/` exclusions to `.dockerignore` | `.dockerignore` |

**YAML validation:** `CRM_REFRESH_TOKEN=test docker compose config -q` exits 0 — compose is valid.

**`.env.docker.example` update:** `CRM_REFRESH_TOKEN` example value changed from `change-me-crm-refresh` to `your_strong_random_token_here` with generation hint.

### Deferred

| Finding | Status | Reason |
|---------|--------|--------|
| C1 | DEFERRED — user action | Token rotation requires Cloudflare dashboard action + `.env.docker` update. Backup exclusion needs `scripts/` backup script edit (out of file ownership scope). User must: (1) rotate token at Cloudflare, (2) update `.env.docker`, (3) restart caddy-global. |
| H3 | DEFERRED — HIGH RISK | `dagster dev` → production migration plan documented below. Do not change compose command without coordinated restart + testing. |
| M2 | DEFERRED — LOW RISK | Pin `rilldata/rill:latest` to a specific version. Requires checking current running version (`docker exec rill rill version`), testing, then pinning in `Dockerfile.rill:1`. No urgency. |
| M3 | DEFERRED — needs user decision | Restrict ports to `127.0.0.1:` requires confirming LAN exposure intent (Unresolved Q2). |
| M4 | DEFERRED — doc only | Add comment to `scripts/provisioning/bootstrap_serving_views.py:96` explaining intentional RW. Not a compose/Dockerfile change. |
| M7 | DEFERRED — needs planning | Metabase H2 → Postgres migration. Requires `docker-compose.yml` postgres service addition + data export/import. High-effort, plan separately. |
| L2 | DEFERRED | Google Sheets URLs are not credentials. Verify sheets require Google auth; if so, no action needed. |
| L3 | DEFERRED | `REPLACE_ME` placeholder — not a live secret. Low priority. |
| L4 | DEFERRED | `docker.sock` in caddy-global is an architectural constraint of caddy-docker-proxy. Accepted risk; socket proxy would require architectural change. |
| L5 | DEFERRED | Resource limits (`mem_limit`) need profiling data to set correctly. Add `mem_limit: 6g` to `data_platform` once memory baseline is known. |
| L6 | DEFERRED | Non-root USER in Dockerfiles. Requires verifying path/permission compatibility in each image. Multi-image change; plan separately. |

### Deferred Plan — H3: dagster dev → Production Migration

**Risk:** Changing the `data_platform` compose `command:` while stack is live will trigger container recreation and a 20-60s downtime. If `dagster-webserver` or `dagster-daemon` have different startup behaviors, schedules/sensors may miss runs.

**Steps when ready:**
1. Stop schedules/sensors in Dagster UI to prevent mid-migration run state corruption.
2. Replace the `dagster dev ...` portion of the `command:` chain in `docker-compose.yml` with two separate approaches — either:
   - **Option A (supervisor in single container):** Install `supervisord`, add a `supervisord.conf` that starts both `dagster-webserver -h 0.0.0.0 -p 3001 -f orchestration/definitions.py` and `dagster-daemon run -f orchestration/definitions.py`. Single container, no compose restructuring.
   - **Option B (split services):** Add `dagster_daemon` service in compose pointing at same volumes, running `dagster-daemon run`. `data_platform` runs only `dagster-webserver`. Cleaner separation but requires two containers sharing `dagster_home`.
3. Add Caddy `basic_auth` to the `etl.lan.fwg.vn` route (or restrict to VPN/SSH tunnel) before exposing the webserver externally — Dagster OSS has no auth.
4. Test: confirm `/server_info` responds, sensors auto-start, and the healthcheck passes.
5. Re-enable schedules/sensors.

**Recommendation:** Option A (supervisord) is lower disruption for a single-host stack. Option B is cleaner for future scaling.
