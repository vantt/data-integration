# Phase 2 — Algorithm Changes in `customer_push.py`

## Context Links
- File to modify: `crm/src/hug/customer_push.py` (sole file changed in this phase)
- Verified current `run()`: lines 173–221
- Verified `_build_edge_rows`: lines 115–137 — output fields: `customer_id`, `tier`, `recency_days`, `value_group`, `is_contactable`
- Verified `_push_batches`: lines 140–170 — returns `{"total": N, "ok": N, "failed": N}`, tracks per-batch ok/fail
- Phase 1 state store: `hug_push_state.db` via new `_push_state_db_path()` helper

## Data Flow

```
cache.db (ro)  →  _load_tier_rows()  →  tier_rows
crm.db   (ro)  →  _load_crm_contactable_ids()  →  crm_contactable
                  _build_edge_rows()  →  edge_rows  (list[dict], ~7.5k)
                  ↓
hug_push_state.db (rw)
  _load_push_state()  →  store  {customer_id → content_str}
                  ↓
  content(r) = f"{r['tier']}|{r['recency_days']}|{r['value_group']}|{r['is_contactable']}"
  changed = [r for r in edge_rows if content(r) != store.get(r['customer_id'])]
                  ↓
  if not changed → log + return {skipped: True, reason: "no-change"}
                  ↓
  _push_batches(changed, url, secret)  →  per-batch ok/fail
                  ↓
  _update_push_state(conn, successfully_pushed_rows)
```

## New Private Functions

### `_push_state_db_path() -> str`
```
Returns os.path.join(os.environ.get("CRM_DATA_DIR", "./data"), "hug_push_state.db")
Mirrors existing _cache_db_path() / _crm_db_path() pattern (lines 54–57).
```

### `_open_push_state(db_path: str) -> sqlite3.Connection`
```
Opens hug_push_state.db read-write (plain sqlite3.connect, not URI mode=ro).
Applies PRAGMA busy_timeout=3000 and synchronous=NORMAL.
Applies CREATE TABLE IF NOT EXISTS hug_customer_push_state idempotently.
Returns connection — caller closes.
```

### `_load_push_state(conn: sqlite3.Connection) -> dict[str, str]`
```
SELECT customer_id, content FROM hug_customer_push_state
Returns {customer_id: content_str} dict.
Called once per run(); O(N) read, single query.
```

### `_content_str(row: dict) -> str`
```
Returns f"{row['tier']}|{row['recency_days']}|{row['value_group']}|{row['is_contactable']}"
Pure function — no I/O. Called for each edge_row in the diff loop.
```

### `_push_batches_with_state_update(...)` — OR modify `run()` inline

The preferred approach is to keep `_push_batches` unchanged (it is already tested via C5)
and handle state updates in `run()` by iterating batches manually OR by refactoring
`_push_batches` to yield per-batch results. **Simpler option (KISS)**: modify `_push_batches`
to accept an optional `on_batch_ok` callback `Callable[[list[dict]], None]` invoked after
each successful batch. This avoids duplicating the batch-split logic.

Alternatively — and more readable — change `_push_batches` return value to include
`ok_rows: list[dict]` (the rows from successfully-acked batches). `run()` then calls
`_update_push_state(conn, result["ok_rows"])`.

**Recommended**: return `ok_rows` from `_push_batches`. The function already tracks
`ok_count` per batch (lines 153–158); extending to accumulate `ok_rows` is a 2-line
addition, no signature breaking change for callers (dict return is additive).

### `_update_push_state(conn: sqlite3.Connection, ok_rows: list[dict], now_iso: str) -> None`
```
INSERT OR REPLACE INTO hug_customer_push_state (customer_id, content, pushed_at)
VALUES (?, ?, ?)
for each row in ok_rows.
Single executemany call — one transaction.
called only for ok_rows (rows from successful batches).
Rows from failed batches are NOT updated → store retains old content → retried next run.
```

## Modified `run()` Signature

```python
def run(
    cache_db: str | None = None,
    crm_db: str | None = None,
    state_db: str | None = None,   # NEW: injectable for tests
    force: bool = False,            # NEW: bypass content-diff (see Phase 3)
) -> dict[str, Any]:
```

Return value additions (backward-compatible — existing callers check `skipped`/`ok`/`failed`):
- `{"skipped": True, "reason": "no-change"}` — new early-return path (no API call)
- `{"skipped": False, "total": N, "ok": N, "failed": N}` — unchanged for actual pushes

## Modified `run()` Control Flow (pseudo-code, not actual code)

```
1. Early exits (unchanged): push_enabled(), secret check, cache.db exists
2. tier_rows = _load_tier_rows(cache_path)          # unchanged
3. crm_contactable = _load_crm_contactable_ids(...)  # unchanged
4. edge_rows = _build_edge_rows(tier_rows, crm_contactable)  # unchanged
5. state_path = state_db or _push_state_db_path()
6. state_conn = _open_push_state(state_path)
7. try:
8.   if not force:
9.     store = _load_push_state(state_conn)
10.    changed = [r for r in edge_rows if _content_str(r) != store.get(r["customer_id"])]
11.    if not changed:
12.      log.info("customer_push: no content change across %d rows — skipping push", len(edge_rows))
13.      return {"skipped": True, "reason": "no-change"}
14.    log.info("customer_push: %d/%d rows changed — pushing", len(changed), len(edge_rows))
15.  else:
16.    changed = edge_rows
17.    log.info("customer_push: force=True — pushing all %d rows", len(changed))
18.  url = worker_url() + _UPSERT_PATH
19.  result = _push_batches(changed, url, secret)      # returns ok_rows too
20.  now_iso = datetime.now(timezone.utc).isoformat()
21.  _update_push_state(state_conn, result["ok_rows"], now_iso)
22.  return {"skipped": False, **{k: v for k, v in result.items() if k != "ok_rows"}}
23. finally:
24.   state_conn.close()
```

## `_push_batches` Change (minimal)

Add `ok_rows: list[dict] = []` accumulator. When `result["ok"]` is truthy for a batch,
extend `ok_rows` with that batch's rows. Add `"ok_rows": ok_rows` to the returned dict.
No change to logging or existing return keys — fully additive.

## admin_handler.py Change

`_hug_customer_push_run()` at line 160–176 calls `push_run()` with no args. The logging
at lines 168–175 reads `result.get("ok", 0)` / `result.get("total", 0)` / `result.get("failed", 0)`.
The new `"no-change"` path returns `{"skipped": True, "reason": "no-change"}` — the existing
`if result.get("skipped"):` branch at line 168 already handles this correctly.
**No change needed to `admin_handler.py`.**

## Risk: Read-Write Open on `hug_push_state.db`

- `customer_push.py` is the sole writer and sole reader of this new file.
- No Go process reads it (Go has no knowledge of push state).
- No concurrent calls: admin_handler uses `_guard["running"]` single-flight (line 307–309) — only one refresh runs at a time.
- Conclusion: zero write contention risk.

## Risk: Windows vs Docker Path

- `os.path.join(os.environ.get("CRM_DATA_DIR", "./data"), "hug_push_state.db")` is identical
  to the pattern used by `_cache_db_path()` (line 54–57) which already works in both envs.
- Docker: `CRM_DATA_DIR` env var points to the volume mount — same directory as crm.db / cache.db.
- Windows native: resolves relative to CWD or explicit path — identical to existing behavior.

## Success Criteria

- Second consecutive run with no mart change: `result == {"skipped": True, "reason": "no-change"}`, zero `urlopen` calls
- First run on empty store: all rows pushed, store populated
- Changed-row run: only changed rows sent, store updated only for ok batches
- `ok` + `failed` counts in result reflect the changed subset, not the full 7.5k
