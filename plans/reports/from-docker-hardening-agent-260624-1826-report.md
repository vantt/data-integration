# Docker Hardening Report — 2026-06-24

**Scope:** `docker-compose.yml`, `Dockerfile.evidence` (repo root only). No containers recreated. Static validation only.

---

## Task 1 — Remove redundant `.env.docker` file mount from `data_platform` ✅ DONE

**Grep result:** No Python code in `ingestion/`, `orchestration/`, or `scripts/` reads `/app/.env.docker` as a file path. All matches were comments or error message strings (e.g. `"Set via .env.docker (container) or .env.local (host)."`). Zero `open()`/`load()`/`dotenv()` calls against that path.

**Change applied** (`docker-compose.yml`, `data_platform.volumes`):
- Removed: `- ./.env.docker:/app/.env.docker:ro`
- Retained: `env_file: .env.docker` (the injection mechanism — untouched)
- Retained: `docker-compose.yml`, `Dockerfile.*` read-only mounts (those are for self-inspection/backup scripts, separate concern)

**Blast radius reduction:** Secrets no longer appear as a readable file at a predictable container path. An app-level exploit can still read env vars but can't `cat /app/.env.docker` to dump them all in one shot.

---

## Task 2 — Resource limits on all services ✅ DONE

Added `mem_limit` + `cpus` at the service level (Compose Spec top-level syntax — accepted without `--compatibility` flag, `docker compose config` exit 0 confirms).

| Service | mem_limit | cpus | Rationale |
|---|---|---|---|
| data_platform | 8g | 4 | Dagster + dbt + DuckDB + Playwright — most demanding service |
| metabase | 4g | 2 | JVM heap (typically 1-2g) + DuckDB driver queries |
| crm | 2g | 1 | FastAPI + SQLite + DuckDB read queries |
| evidence | 2g | 1 | Node.js Evidence build (can spike during `npm run build`) |
| rill | 2g | 1 | Go binary, generally lightweight but DuckDB queries may spike |
| detail_view | 2g | 1 | FastAPI + DuckDB read-only — retiring soon |
| fileserver | 512m | 0.5 | Caddy static file serving — minimal resource needs |

`docker compose config` **exit code 0** after changes. Compose rendered `mem_limit` values in bytes (e.g., `8589934592` = 8g) confirming correct parsing.

---

## Task 3 — Non-root USER ✅ PARTIAL (evidence only; rill skipped)

### evidence — DONE

**Dockerfile.evidence** updated:
1. `RUN useradd -r -u 1001 -g node app` — reuse the existing `node` group from `node:20-slim` base image; uid 1001 avoids conflict with uid 1000 (node) already in the image.
2. `RUN mkdir -p pages sources scripts && chown -R 1001:node /app` — ensures non-root owns `/app` before the user switch, so the runtime CMD (`cp`, `npm run sources`, `npm run build`) can write to `/app/sources/datalake/` and `/app/build/`.
3. `USER 1001` added before `EXPOSE 3000`.

Volume mounts for evidence are all `:ro` or bind-mounted source directories owned by host — these are read-only from the container's perspective; no write permission issue.

### rill — SKIPPED ⚠️

**Rationale:**
- Base image `rilldata/rill:v0.85.3` was not pulled locally; its internal USER/entrypoint is unknown.
- Two writable bind mounts: `./rill:/app/rill` and `./app_data/rill:/app/rill/.rill`. On Windows host + WSL2 9p driver, bind-mounted NTFS paths present as uid/gid 0 inside the container. A non-root user (e.g. uid 1001) would get EACCES on those mounts.
- Rill is a Go binary that may also write SQLite state or cache files to WORKDIR.
- Risk of silent startup failure is high; skipped per "if can't be proven safe, SKIP + flag" constraint.
- **To enable later:** inspect running container with `docker exec rill id` + `ls -la /app/rill`, then add `USER` only if rill runs as non-root already or after verifying mount ownership.

### data_platform — SKIPPED ⚠️

Writes to bind-mounted named volumes (`monitoring_db`, bind mounts for `dagster_home`, `data_lake`, `backups`, `input_source`) currently owned by root. Non-root would break dbt writes, DuckDB writes, Dagster run history, and backup scripts. Not safe without a full uid/gid migration of all those directories.

### crm — SKIPPED ⚠️

Writes to named volume `crm_data` (SQLite crm.db + cache.db) and bind-mounted `./crm/src`. Named volumes created as root; non-root would need explicit `chown` in Dockerfile and volume ownership migration on existing containers. Out of scope for static validation.

### metabase — already non-root ✅

`Dockerfile.metabase` already has `RUN groupadd -r metabase && useradd -r -g metabase metabase` and `USER metabase`. No change needed.

### detail_view — SKIPPED (retiring)

Per task spec.

---

## Files Modified

- `D:\Vantt\app\data-integration\docker-compose.yml` — Task 1 (mount removal) + Task 2 (resource limits)
- `D:\Vantt\app\data-integration\Dockerfile.evidence` — Task 3 (non-root user)

---

**Status:** DONE_WITH_CONCERNS
**Per-task:**
- Task 1 (remove .env.docker mount): DONE — mount removed, grep confirmed no code reads `/app/.env.docker`
- Task 2 (resource limits): DONE — all 7 services have mem_limit + cpus, compose config exit 0
- Task 3 (non-root USER): PARTIAL — evidence hardened; rill/data_platform/crm skipped (bind-mount ownership risk); metabase already non-root; detail_view skipped (retiring)

**compose config valid:** YES (exit code 0)

---

## Unresolved Questions

- rill non-root: pull image + `docker inspect rilldata/rill:v0.85.3 --format '{{.Config.User}}'` to check if base image already runs non-root. If yes, no Dockerfile change needed.
- data_platform/crm non-root: requires deciding on a uid strategy and `chown`-ing existing named volumes — out of scope for this hardening pass but tracked as future hardening.
