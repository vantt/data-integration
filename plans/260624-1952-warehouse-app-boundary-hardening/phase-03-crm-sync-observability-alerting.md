---
title: "CRM Sync Observability & Alerting"
description: "Add Lark alerting + persisted crm_etl_run health record + morning digest surfacing + hug best-effort alert-on-failure + tighten CatalogException skip."
status: pending
priority: P1
effort: 3h
branch: main
tags: [crm, observability, alerting, lark, sqlite]
created: 2026-06-24
---

# Phase 03 — CRM Sync Observability & Alerting

## Context Links

- Plan: `plans/260624-1952-warehouse-app-boundary-hardening/plan.md`
- Research: `plans/reports/from-research-to-planner-boundary-hardening-findings-260624-1952-report.md`
- Admin handler: `crm/src/adapters/inbound/http/admin_handler.py`
- Reverse ETL run: `crm/sync/reverse_etl_warehouse_to_crm.py`
- Identity resolver IO: `crm/src/hug/identity_resolver_io.py`
- Cache schema: `crm/sync/cache_schema.sql`
- Lark client (orchestration): `orchestration/notifications/lark_client.py`
- Morning digest: `orchestration/ops/morning_digest.py`

---

## Overview

**Priority:** P1 (fail-loud failures are already in place; this phase makes them _observable_).

**Current status:** Pending.

**Brief description:** The reverse-ETL pipeline and warehouse read layer already raise exceptions
loudly on schema mismatch. The gap is that those loud failures are invisible: no Lark alert fires,
no durable record is written, and the morning digest has no CRM sync section. Additionally, four
best-effort hug sub-steps swallow exceptions silently into `log.error()` — failures never leave the
container logs. One CatalogException catch (`identity_resolver_io.py:98-103`) conflates a legitimate
pre-data absence with a mart rename, creating a genuine silent-skip risk.

This phase closes all five gaps with minimal new surface area.

---

## Key Insights

1. **CRM has no `requests` dep.** `crm/src/requirements.txt` lists FastAPI, uvicorn, duckdb, pydantic —
   no `requests`. `orchestration/notifications/lark_client.py` imports `requests` at module level
   (with a graceful `ImportError` stub). Importing `lark_client` directly from CRM would require
   adding `requests` to CRM's deps or causing a silent import error → thin local notifier is correct.

2. **Cross-package import is an active coupling violation.** CRM is a separate deployable
   (`crm/src/` with its own requirements, its own Docker image). Importing from `orchestration.*`
   inside CRM creates a hard dependency on the orchestration package's install path — fragile in Docker
   and violates the boundary-hardening goal of this entire plan. A thin CRM-local copy is the right call.

3. **`lark_client.py` is 110 lines total; the alert-relevant portion is ~35 lines.** The thin CRM copy
   does NOT need the stub path, the Lark card builder, or the HMAC signer — just `urllib.request`
   (stdlib, zero new dep) + the same env-var names. `urllib.request` is already transitively available
   in the CRM image (Python stdlib).

4. **`_state` is router-closure-scoped (`admin_handler.py:197`)** — process-local, lost on restart.
   The persisted `crm_etl_run` table in `cache.db` provides the durable equivalent. Home = `cache.db`
   (not `ingestion_health.db`) because: (a) CRM's Python runtime already owns `cache.db` writes
   (`reverse_etl_warehouse_to_crm.py:148`), (b) `ingestion_health.db` is owned by the orchestration
   container and uses `asset_key`+`run_id` as PK — forcing CRM's run-level record into that PK scheme
   is a category mismatch, (c) Go reads `cache.db` RO already for other tables.

5. **`wh_sync_run` gives per-mart-per-run grain** (`cache_schema.sql:130-138`). `crm_etl_run` gives
   the missing **run-level** summary: one row per `/admin/refresh` invocation, with step that failed,
   end status, and duration. Together they provide complete observability without duplication.

6. **Morning digest reads only `ingestion_health.db`** (`morning_digest.py:628-653`). To include CRM
   sync freshness the digest must read `cache.db` (separate SQLite, different container volume).
   Path: env var `CRM_CACHE_DB_DIGEST_PATH` passed to the orchestration container (mount same
   `crm_data` volume read-only), read with `sqlite3` read-only in a new helper `_read_crm_etl_last_run()`.

7. **CatalogException discrimination:** DuckDB's `CatalogException` message for a missing table reads
   `"Table with name mart_hug_optin does not exist!"`. For a column mismatch it raises
   `duckdb.BinderException` (not `CatalogException`). So the current catch already only fires on
   "table absent" — but it would also fire if the schema was renamed to e.g. `main_sapo.mart_hug_optin`
   (schema mismatch = `CatalogException`). The discrimination: check `information_schema.tables` first;
   only swallow `CatalogException` when the table is confirmed absent in the schema.

---

## Requirements

### Functional

1. **F1 — CRM Lark alert on critical step failure.** When `_reverse_etl_run` or `_sync_parties_run`
   raises (outer `except` at `admin_handler.py:279`), fire a Lark card via CRM-local notifier.
   Fields: service=CRM, step=`reverse_etl|sync_parties`, error=first 200 chars of `str(exc)`,
   duration_ms, started_at (ICT).

2. **F2 — CRM Lark alert on best-effort sub-step failure.** When any of `_hug_resolve_run`,
   `_hug_voucher_issue_run`, `_hug_voucher_redeem_run`, `_hug_customer_push_run`,
   `_rebuild_search_index_run` raises (currently only `log.error`), also fire a Lark card.
   Color = orange (non-blocking). These remain best-effort (no re-raise).

3. **F3 — Persisted `crm_etl_run` table in `cache.db`.** One row per `/admin/refresh` invocation.
   Schema: `(run_id TEXT PK, status TEXT, started_at TEXT, finished_at TEXT, duration_ms INTEGER,
   error_step TEXT, error TEXT, serving_version TEXT)`. Written at both success and failure paths in
   `_run_refresh`. `serving_version` NULL initially (populated in Phase 05).

4. **F4 — Morning digest CRM section.** `compose_and_send_digest` reads last `crm_etl_run` row from
   `cache.db` (RO) via `CRM_CACHE_DB_DIGEST_PATH` env var. Adds one digest field:
   `"🔄 CRM sync"` → status emoji + age of last successful run + last error step if any.
   Gracefully absent when env var unset or file not found.

5. **F5 — CatalogException discrimination in `identity_resolver_io.py`.** Before swallowing
   `CatalogException`, confirm the table is genuinely absent via `information_schema.tables`. If the
   table exists (i.e. CatalogException was from something else — schema rename, column access), re-raise
   and let the caller handle it. Only return `[]` when table is confirmed absent.

### Non-functional

- **NF1** — CRM notifier must never raise (same contract as `lark_client.py`: degrade to `log.error`
  on network error or when `LARK_ALERT_WEBHOOK` unset).
- **NF2** — `crm_etl_run` insert must be best-effort from the perspective of the refresh flow: if the
  insert fails, log and continue — never abort a successful run because of a health-record write failure.
- **NF3** — No new Python package added to `crm/src/requirements.txt` (use stdlib `urllib.request`).
- **NF4** — Morning digest CRM read must be read-only (`check_same_thread=False`, no WAL writes).
- **NF5** — `cache.db` write is single-writer Python (reverse_etl process); `crm_etl_run` insert
  happens inside the same `try/finally` block that already owns the connection, so no new locking surface.

---

## Architecture

### New Component: `crm/src/notifications/lark_notifier.py`

Thin CRM-local notifier. Uses stdlib `urllib.request` only.

```
Data in:  LARK_ALERT_WEBHOOK (env), LARK_ALERT_SECRET (env), title (str), fields (dict), color (str)
Data out: HTTP POST to Lark webhook (or log.warning stub when LARK_ALERT_WEBHOOK unset)
```

Signature mirrors `orchestration/notifications/lark_client.py:send_lark_card()` so if the dep
constraint is ever relaxed the call sites need zero changes.

**Why not symlink or shared module?** CRM and orchestration have separate Python environments, separate
Docker images, separate sys.path roots. Symlinks break across container boundaries. A 50-line stdlib-only
copy is cheaper than the coupling.

### `crm_etl_run` Table (added to `cache_schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS crm_etl_run (
    run_id          TEXT PRIMARY KEY,
    status          TEXT NOT NULL,          -- ok | error
    started_at      TEXT NOT NULL,          -- UTC ISO8601
    finished_at     TEXT,
    duration_ms     INTEGER,
    error_step      TEXT,                   -- which step raised (null on ok)
    error           TEXT,                   -- str(exc) truncated to 500 chars
    serving_version TEXT                    -- null until Phase 05 populates it
);
```

Retention: 30-day trim aligned with `wh_sync_run` trim (same `finally` block).

### Data Flow

```
POST /admin/refresh
  → _run_refresh(started_at)
      ├── _reverse_etl_run()          ← CRITICAL; on Exception:
      │       log.error                           ├── _notify_lark("reverse_etl", exc)  [NEW]
      │       re-raise ──────────────────────────────► outer except:279
      │                                               ├── _notify_lark("refresh", exc)  [NEW]
      │                                               └── _write_crm_etl_run(status="error", ...)  [NEW]
      ├── _hug_resolve_run()          ← best-effort; on Exception:
      │       log.error + _notify_lark("hug_resolve", exc)  [NEW — non-blocking orange]
      ├── _hug_voucher_issue_run()    ← same pattern
      ├── _hug_voucher_redeem_run()   ← same pattern
      ├── _hug_customer_push_run()    ← same pattern
      ├── _sync_parties_run()         ← CRITICAL; on Exception:
      │       re-raise → outer except:279 (same as above)
      ├── _rebuild_search_index_run() ← best-effort; same pattern
      └── [on success] _write_crm_etl_run(status="ok", ...)  [NEW]

identity_resolver_io.fetch_new_optins()
  → try query mart_hug_optin
  → except CatalogException:
       check information_schema.tables for mart_hug_optin   [NEW]
       if absent: return []  (legitimate pre-data state)
       if present: re-raise  (unexpected — schema issue)

Morning digest (orchestration container):
  → build_digest_rows() [existing]
  → _read_crm_etl_last_run(path=CRM_CACHE_DB_DIGEST_PATH) [NEW]
  → compose_card_fields(..., crm_run=...) [NEW field appended]
```

### File Ownership

| File | Action | Owner |
|------|--------|-------|
| `crm/src/notifications/lark_notifier.py` | **CREATE** | phase-03 |
| `crm/src/adapters/inbound/http/admin_handler.py` | **MODIFY** | phase-03 |
| `crm/sync/cache_schema.sql` | **MODIFY** | phase-03 |
| `crm/sync/reverse_etl_warehouse_to_crm.py` | **MODIFY** (add crm_etl_run write) | phase-03 |
| `crm/src/hug/identity_resolver_io.py` | **MODIFY** | phase-03 |
| `orchestration/ops/morning_digest.py` | **MODIFY** | phase-03 |

No other phase touches these files concurrently (phase-01/02 own `transformation/`; phase-04/05
own `serving/bootstrap_serving_views.py`, `crm_sync.py`).

---

## Related Code Files

### Modify

- `crm/src/adapters/inbound/http/admin_handler.py` — add `_notify_lark()` calls at outer except
  (:279) and inside each best-effort except block (:220, :232, :243, :252, :265); add `_write_crm_etl_run()` helper
- `crm/sync/cache_schema.sql` — append `crm_etl_run` DDL after `wh_sync_run` (:138)
- `crm/sync/reverse_etl_warehouse_to_crm.py` — add `crm_etl_run` INSERT at success path (:213) and in
  `_run_step` exception path — NO, `crm_etl_run` is run-level (one per `/admin/refresh`), NOT step-level;
  the write belongs in `admin_handler._run_refresh`, not in `reverse_etl_warehouse_to_crm.run()` directly
- `crm/src/hug/identity_resolver_io.py` — tighten `CatalogException` handler (:98-103)
- `orchestration/ops/morning_digest.py` — add `_read_crm_etl_last_run()` and CRM field in
  `compose_card_fields()`

### Create

- `crm/src/notifications/lark_notifier.py` — thin CRM-local Lark alert (stdlib-only)

### Delete

None.

---

## Implementation Steps

### Step 1 — Create `crm/src/notifications/lark_notifier.py`

Create `crm/src/notifications/__init__.py` (empty) and `crm/src/notifications/lark_notifier.py`.

Key design:
- `send_alert(title: str, fields: dict, color: str = "red") -> None`
- Reads `LARK_ALERT_WEBHOOK` and `LARK_ALERT_SECRET` from env at call time (not module load).
- When unset: `log.warning("[LARK-STUB] ...")` — never raises.
- HTTP via `urllib.request.urlopen` with a 5s timeout.
- HMAC signing identical to `orchestration/notifications/lark_client.py:27-33` (copy the 6-line
  `_sign` function verbatim — it's pure stdlib `hmac` + `hashlib`).
- Card payload: same minimal JSON structure as `lark_client.py:74-95`.
- Max 200 lines total; target ~80.

### Step 2 — Add `crm_etl_run` DDL to `cache_schema.sql`

Append after the `wh_sync_run` block (`cache_schema.sql:138`):

```sql
-- crm_etl_run: run-level summary for each /admin/refresh invocation.
-- One row per invocation; complements wh_sync_run (per-mart grain).
CREATE TABLE IF NOT EXISTS crm_etl_run (
    run_id          TEXT PRIMARY KEY,
    status          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    duration_ms     INTEGER,
    error_step      TEXT,
    error           TEXT,
    serving_version TEXT
);
```

Schema is applied idempotently via `su.apply_schema()` → `reverse_etl_warehouse_to_crm.py:152`.
No migration needed.

### Step 3 — Wire alerting + crm_etl_run write in `admin_handler.py`

3a. Add import at top of `admin_handler.py`:
```python
from notifications.lark_notifier import send_alert
```
(CRM's server runs from `crm/src/` as the Python root — `notifications.lark_notifier` resolves.)

3b. Add `_write_crm_etl_run(cache_path, run_id, status, started_at_iso, finished_at, duration_ms, error_step, error)` helper function: opens `cache.db` with WAL, inserts into `crm_etl_run`, closes. Best-effort wrapper: catch + log on failure.

3c. In `_run_refresh` outer except block (:279-291): after `log.error`, call:
```python
send_alert(
    title="CRM Sync Failed",
    fields={
        "step": "reverse_etl or sync_parties",
        "error": str(exc)[:200],
        "duration": f"{duration_ms}ms",
        "started": iso_start,
    },
    color="red",
)
_write_crm_etl_run(cache_path=..., status="error", error_step=_failed_step, error=str(exc)[:500], ...)
```

3d. Track `_failed_step` variable inside `_run_refresh`: set to the step name string just before each
`await asyncio.wait_for(...)` call for critical steps. Reset to `None` after each critical step succeeds.

3e. In each best-effort except block (:220, :232, :243, :252, :265): add after `log.error`:
```python
send_alert(
    title="CRM Sub-step Failed (non-blocking)",
    fields={"step": "<step_name>", "error": str(<exc_var>)[:200]},
    color="orange",
)
```

3f. At success path after `log.info("admin: refresh ok ...")` (:269): call `_write_crm_etl_run(..., status="ok", error_step=None, error=None, ...)`.

3g. Add retention trim for `crm_etl_run` alongside the `wh_sync_run` trim in
`reverse_etl_warehouse_to_crm.py:204-211`:
```python
cache_conn.execute("DELETE FROM crm_etl_run WHERE finished_at < datetime('now','-30 days')")
```

Note: `_write_crm_etl_run` needs the `cache_db` path. `admin_handler.py` currently does not import
`config.py`. Add the import:
```python
from sync.config import cache_db_path as _cache_db_path
```

### Step 4 — Tighten `CatalogException` in `identity_resolver_io.py`

Replace `:98-103`:

```python
except duckdb.CatalogException:
    # Only suppress when the table is genuinely absent (pre-first-ingest state).
    # A schema-level rename also raises CatalogException — detect and re-raise that.
    absent = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'mart_hug_optin'"
    ).fetchone()[0] == 0
    if absent:
        log.info("fetch_new_optins: mart_hug_optin not in serving db yet — 0 rows")
        return []
    raise  # table exists but query still failed — surface the real cause
```

### Step 5 — Morning digest CRM section

5a. In `orchestration/ops/morning_digest.py`, add helper after the existing `_check_db_staleness()` function (~:624):

```python
def _read_crm_etl_last_run() -> Optional[dict]:
    """Read last crm_etl_run row from cache.db (read-only).

    Returns dict with keys: status, started_at, finished_at, duration_ms,
    error_step, error — or None if path unset / file missing / table absent.
    """
    import sqlite3 as _sqlite3
    path = os.getenv("CRM_CACHE_DB_DIGEST_PATH")
    if not path or not os.path.exists(path):
        return None
    try:
        con = _sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = con.execute(
                "SELECT status, started_at, finished_at, duration_ms, error_step, error "
                "FROM crm_etl_run ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        finally:
            con.close()
        if row is None:
            return None
        return dict(zip(
            ["status","started_at","finished_at","duration_ms","error_step","error"], row
        ))
    except Exception as exc:
        logger.warning(f"morning_digest: could not read CRM sync health: {exc}")
        return None
```

5b. In `compose_and_send_digest` (~:626), after `rows, kpi_data = build_digest_rows(...)`:
```python
crm_run = _read_crm_etl_last_run()
```

5c. In `compose_card_fields()`, add `crm_run: Optional[dict] = None` parameter and append the field
after the KPI line:
```python
if crm_run:
    age_min = ... # compute from crm_run["finished_at"] vs now
    em = "✅" if crm_run["status"] == "ok" else "❌"
    crm_line = f"{em} last sync {age_min} phút trước"
    if crm_run.get("error_step"):
        crm_line += f" · lỗi bước: {crm_run['error_step']}"
    fields["🔄 CRM sync"] = crm_line
```

---

## Todo List

- [ ] Create `crm/src/notifications/__init__.py`
- [ ] Create `crm/src/notifications/lark_notifier.py` (stdlib-only, ~80 lines)
- [ ] Add `crm_etl_run` DDL to `crm/sync/cache_schema.sql`
- [ ] Add `_write_crm_etl_run()` helper to `admin_handler.py`
- [ ] Add `send_alert()` call at outer except `:279` (critical failure)
- [ ] Add `send_alert()` call in each of the 5 best-effort except blocks
- [ ] Add `_failed_step` tracking variable for critical steps
- [ ] Add retention trim for `crm_etl_run` in `reverse_etl_warehouse_to_crm.py`
- [ ] Tighten `CatalogException` handler in `identity_resolver_io.py:98-103`
- [ ] Add `_read_crm_etl_last_run()` to `morning_digest.py`
- [ ] Add `CRM_CACHE_DB_DIGEST_PATH` env var to orchestration service in `docker-compose.yml`
- [ ] Add CRM sync field to `compose_card_fields()` in `morning_digest.py`

---

## Success Criteria

| # | Observable outcome |
|---|--------------------|
| SC1 | After a forced reverse-ETL failure, a Lark card with `color=red` and `"CRM Sync Failed"` appears within 30s |
| SC2 | `SELECT * FROM crm_etl_run` in `cache.db` shows one row per `/admin/refresh` invocation with correct status/error |
| SC3 | After 24h (morning digest run), the Lark card contains a `"🔄 CRM sync"` field showing last run age |
| SC4 | Forcing `_hug_resolve_run` to raise produces an orange Lark card but does NOT abort the refresh (sync_parties still runs) |
| SC5 | Renaming `mart_hug_optin` to `mart_hug_optin_v2` in the test DB causes `fetch_new_optins` to re-raise (not silently `[]`) |
| SC6 | With `mart_hug_optin` absent from the DB, `fetch_new_optins` returns `[]` (existing behavior preserved) |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `notifications` import fails in CRM container (sys.path issue) | Low | High | Confirm CRM's server entrypoint sets `crm/src/` as root; add an import smoke test |
| `_write_crm_etl_run` opens cache.db while reverse_etl holds it open | Low | Medium | Write happens _after_ `reverse_etl_warehouse_to_crm.run()` completes (which closes the connection at `finally:216`); no simultaneous open |
| Morning digest fails when `crm_etl_run` table not yet created (first boot) | Low | Low | `sqlite3.OperationalError` caught by the outer `except Exception` in `_read_crm_etl_last_run` → returns `None` gracefully |
| CatalogException re-raise breaks pre-deploy environments where schema truly changed | Low | Medium | The `information_schema` check is the guard; re-raise only when table IS present — schema renames cause table absent → still returns `[]` |
| LARK_ALERT_WEBHOOK not set in CRM container | Likely (pre-config) | None | `send_alert` degrades to `log.warning` — zero functional impact; set env to activate |
| `crm_etl_run` cache.db path unknown to orchestration container | Medium | Low | Mitigation: mount `crm_data` volume RO into `data_platform` container, set `CRM_CACHE_DB_DIGEST_PATH`; document in docker-compose |

---

## Security Considerations

- `send_alert` reads `LARK_ALERT_WEBHOOK` and `LARK_ALERT_SECRET` from env at call time — no secret
  stored in code or logged.
- Error message in Lark card truncated to 200 chars — prevents PII or full stack traces leaking into
  the chat channel via exception messages.
- `crm_etl_run.error` column truncated to 500 chars at insert.
- Morning digest reads `cache.db` via `?mode=ro` URI — no write surface from orchestration container.

---

## Next Steps

- **Phase 05 depends on this:** when the `serving_version.json` marker is introduced, populate
  `crm_etl_run.serving_version` from the marker read at the start of `_run_refresh` (value available
  before ETL runs). This field is schema-ready (NULL until Phase 05).
- **`docker-compose.yml`** needs two additions (not in scope of this phase but must not block):
  1. `LARK_ALERT_WEBHOOK` + `LARK_ALERT_SECRET` env vars forwarded to the `crm` service (same `.env` values).
  2. `crm_data` volume mounted read-only into `data_platform` service; `CRM_CACHE_DB_DIGEST_PATH` set to its path.

---

## Unresolved Questions

1. **`admin_handler.py` import path for `sync.config`:** the file imports from `adapters.*` and `hug.*`
   using paths relative to `crm/src/`. `sync.config` lives at `crm/sync/config.py`. Confirm that
   `crm/sync/` is on `sys.path` inside the CRM server process, or add the import differently (e.g.
   call `os.environ.get("CRM_CACHE_DB", "./data/cache.db")` inline to avoid the path ambiguity). [VERIFY before implementing Step 3]

2. **Lark `orange` color validity:** `lark_client.py` documents `red|orange|yellow|green|blue|grey`.
   Lark's card API accepts `orange` — verify against current Lark Custom Bot API to confirm
   `orange` is a valid template value; fallback to `yellow` if not.

3. **`_write_crm_etl_run` placement:** decided it lives in `admin_handler.py`. Alternative: move to a
   new `crm/sync/health_recorder.py` module (mirrors `orchestration/ops/ingestion_health.py` pattern)
   to keep `admin_handler.py` lean. Worth doing if `admin_handler.py` grows > 200 lines after changes.
