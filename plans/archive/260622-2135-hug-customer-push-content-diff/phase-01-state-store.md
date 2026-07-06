# Phase 1 — State Store Design

## Context Links
- Source: `crm/src/hug/customer_push.py` (verified)
- Cache schema owner: `crm/sync/cache_schema.sql` (verified — Python sole-writer comment on line 4)
- Hug db schema: `crm/src/hug/db.py` (verified — token lifecycle only, no push state)
- Config: `crm/src/hug/config.py` — `hug_db_path()` returns `{CRM_DATA_DIR}/hug.db`

## Decision: Dedicated `hug_push_state.db`

### Options Evaluated

**Option A — New table in `cache.db`**
- `cache_schema.sql:4`: "Python is the SOLE writer. Go ATTACHes this file read-only."
- `customer_push.py:96–112`: `_load_tier_rows` opens cache.db as `file:...?mode=ro` (URI read-only)
- Problem: adding a `mode=rw` connection to cache.db from customer_push breaks the SOLE-WRITER contract (Go ATTACHes read-only; opening rw from Python's push path while Go might be reading is safe only if no write race, but it muddies the ownership boundary). Also requires altering cache_schema.sql — a file owned by the sync layer, not the hug layer.
- Verdict: **rejected** — violates stated ownership boundary.

**Option B — New table in `hug.db`**
- `hug.db` is opened rw by `hug/db.py:connect()` for token lifecycle.
- `customer_push.py` currently has zero dependency on `hug.db` — adding it creates a new import coupling.
- `hug.db` schema (`_SCHEMA` in `hug/db.py:22–46`) is described as "single embedded schema applied idempotently" — KISS note warns against migration chain.
- Problem: push_state is logically about the push operation (edge sync state), not the token lifecycle. Mixing them conflates two distinct concerns. If hug.db is absent (pre-deploy, edge not yet deployed), customer_push would fail to open it even though D1 push is also gated-off.
- Verdict: **rejected** — wrong ownership; latent coupling.

**Option C — Dedicated `hug_push_state.db`** ← RECOMMENDED
- New file: `{CRM_DATA_DIR}/hug_push_state.db`
- Opened rw exclusively by `customer_push.py` (sole writer, no other reader).
- Zero impact on cache.db ownership or hug.db schema.
- Schema applied idempotently via `CREATE TABLE IF NOT EXISTS` on first connection (no migration file needed — KISS).
- Path resolution mirrors `_cache_db_path()` / `_crm_db_path()` pattern already in customer_push.py.
- Windows/Docker path: `os.path.join(os.environ.get("CRM_DATA_DIR", "./data"), "hug_push_state.db")` — identical pattern to existing helpers; works on both OSes.
- Rollback: simply delete the file → next run bootstraps from empty → one full push (correct, same as today).

### Schema (applied in `customer_push.py`, no separate .sql file)

```sql
CREATE TABLE IF NOT EXISTS hug_customer_push_state (
    customer_id  TEXT PRIMARY KEY,
    content      TEXT NOT NULL,
    pushed_at    TEXT NOT NULL
)
```

- `content`: raw concat string `"{tier}|{recency_days}|{value_group}|{is_contactable}"` (not a hash — KISS, debuggable, benchmarked ~1.5ms for 7.5k string-compares, negligible)
- `pushed_at`: ISO-8601 UTC text, matches repo convention (see `cache_schema.sql:5`)
- No WAL pragma needed — single writer, no concurrent readers; default journal is fine for a tiny state file. Add `PRAGMA synchronous=NORMAL` and `PRAGMA busy_timeout=3000` for robustness.

## SQLite Connection Pattern

New private helper in `customer_push.py`:

```python
def _push_state_db_path() -> str:
    default_dir = os.environ.get("CRM_DATA_DIR", "./data")
    return os.path.join(default_dir, "hug_push_state.db")
```

Open rw (NOT URI mode=ro) with `CREATE TABLE IF NOT EXISTS` applied on each open. Caller opens, uses, closes within `run()` scope — no long-lived connection. Tests inject the path via a new `state_db` param on `run()`.

## Crash Safety Guarantee

Store is updated ONLY for rows belonging to **successfully-pushed batches** (determined by `_push_batches` returning per-batch ok/fail). A crash mid-push leaves the store with the last committed batch's state → next run retries only the un-stored rows. This is idempotent because D1 upsert is `ON CONFLICT DO UPDATE`.

## File Ownership

- `hug_push_state.db` — created and owned by `customer_push.py` (Python sole writer)
- No Go reader, no external dependency
- Must be volume-mounted alongside crm.db / cache.db in Docker compose (same `CRM_DATA_DIR` volume — no config change needed)

## Success Criteria

- File is created on first `run()` call when `CRM_DATA_DIR` exists
- Schema applied idempotently (re-running `run()` with existing DB does not error)
- File persists across container restarts (same volume as crm.db)
