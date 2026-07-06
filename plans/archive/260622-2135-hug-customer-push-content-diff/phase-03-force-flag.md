# Phase 3 — Force/Full-Resync Flag

## Context Links
- File to modify: `crm/src/hug/customer_push.py` (same file as Phase 2)
- Caller chain: `admin_handler.py:160–176` → `push_run()` (no args)
- Existing watermark pattern: `hug_resolver_watermark.json`, `hug_voucher_watermark.json` — JSON files in `CRM_DATA_DIR`

## Why This Is Not Optional

If D1 is reset/re-provisioned (wrangler d1 execute, CF incident, schema migration), the
local store still holds content strings from the prior push. The diff sees zero changed rows
→ skips → D1 stays empty permanently. No automatic recovery until a row's content actually
changes. This is a silent data-loss risk, not a corner case.

## Design

### Two activation paths (both must work)

**1. `force: bool` parameter on `run()`** (already added in Phase 2 signature)

Used by:
- Tests (Phase 4)
- Future CLI tooling
- Any caller that imports `customer_push` directly

**2. Environment variable `HUG_CUSTOMER_PUSH_FULL=1`**

Used by:
- Ops recovery without code deploy: set env var in Docker, restart container, wait for next cron
- `_hug_customer_push_run()` in `admin_handler.py` passes no args — env var is the only
  runtime override path without changing `admin_handler.py`

### Resolution in `run()`

```python
_force = force or os.environ.get("HUG_CUSTOMER_PUSH_FULL", "").strip() == "1"
```

Evaluated once at the top of the diff-decision block (after edge_rows are built).
When `_force` is True: `changed = edge_rows`, skip loading state, push all rows,
update state for all ok_rows. Store still updated — so after a forced resync the store
reflects D1's actual state and normal diff resumes on the next run.

### State Update on Force Run

Force does NOT skip the state update. After a successful forced push, `_update_push_state`
writes the full set of ok_rows → store is now in sync with D1 again. Failed batches in a
force run are still not stored (same crash-safety rule).

### Log Distinguishability

- Normal no-change skip: `"customer_push: no content change across %d rows — skipping push"`
- Normal partial push: `"customer_push: %d/%d rows changed — pushing"`
- Force run: `"customer_push: force=True — pushing all %d rows"`

This makes it trivially grep-able in container logs to confirm a force run completed.

## `admin_handler.py` — No Changes Required

`_hug_customer_push_run()` at lines 160–176 calls `push_run()` with no args. The env-var
path means ops can trigger a force resync without touching admin_handler.py or deploying code:

```bash
# In docker-compose.yml or docker exec:
HUG_CUSTOMER_PUSH_FULL=1 <restart or next cron fires>
```

After the resync confirms in logs, unset the var for normal operation.

## Risk: Leaving `HUG_CUSTOMER_PUSH_FULL=1` Set Permanently

If the env var is left set, every run pushes all rows — identical to pre-diff behavior.
No data corruption. Performance regression only. Mitigated by clear ops runbook: unset after
confirming one successful resync in logs.

## Rollback

Force flag does not need rollback — it is a one-time operational lever. Reverting the
entire feature (Phase 2+3) means removing the diff logic from `run()`; the state DB file
can be left in place harmlessly.

## Success Criteria

- `run(force=True)` pushes all edge_rows regardless of store contents
- `HUG_CUSTOMER_PUSH_FULL=1` env var triggers same full push via `_hug_customer_push_run()`
- After a force run, store is updated for ok_rows; next run operates in diff mode (no force)
- Log line contains "force=True" when either activation path is used
