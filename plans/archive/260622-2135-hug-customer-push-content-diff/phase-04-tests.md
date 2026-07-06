# Phase 4 — Test Matrix Extension

## Context Links
- File to extend: `crm/src/tests/test_hug_customer_push.py` (verified, 254 lines)
- Existing fixtures: `_make_cache_db()`, `_make_crm_db()`, `tmp_dir` (lines 39–95)
- Existing mock style: `patch("urllib.request.urlopen", side_effect=fake_urlopen)` (line 174)
- `post_signed` / `push_enabled` / `admin_secret` observed via env monkeypatch + urlopen mock

## New Fixture

```python
@pytest.fixture()
def state_db(tmp_dir):
    """Path to a fresh hug_push_state.db (does not exist yet — created by run())."""
    return str(pathlib.Path(tmp_dir) / "hug_push_state.db")
```

Inject `state_db` path into `run(state_db=state_db)` for all new tests. This keeps each
test isolated and avoids touching the real `CRM_DATA_DIR`.

## Test Cases

### D1 — First run bootstraps store and pushes all rows

**Scenario:** `state_db` file does not exist. Two customers in cache.db.

**Setup:** `_make_cache_db` with 2 rows; `_make_crm_db` empty; env `HUG_WORKER_URL` + `HUG_ADMIN_SECRET` set.

**Assert:**
- `urlopen` called (at least 1 batch)
- `result["skipped"]` is falsy
- `result["ok"] == 2`
- `state_db` file now exists
- `SELECT COUNT(*) FROM hug_customer_push_state` == 2
- Both rows have `content` matching `"{tier}|{recency_days}|{value_group}|{is_contactable}"`

---

### D2 — Second run, no change → zero API calls

**Scenario:** Store already populated from D1. Same cache.db rows (no changes).

**Setup:** Run D1 first (or manually seed `hug_push_state.db`). Then call `run()` again with
the same cache/crm/state paths.

**Assert:**
- `urlopen` NOT called (mock assert_not_called)
- `result == {"skipped": True, "reason": "no-change"}`

---

### D3 — One row's tier changed → exactly that row pushed, store updated

**Scenario:** Store has 2 rows. Recreate cache.db with customer_id=1 `strategic_tier` changed
from "LIVE_CORE" to "SECOND_ORDER"; customer_id=2 unchanged.

**Setup:** Run D1 to populate store. Recreate cache.db with changed tier for cid=1.
Call `run()` again.

**Assert:**
- `urlopen` called exactly once (1 batch, 1 row)
- POST body `rows` list has exactly 1 entry with `customer_id == "1"` and `tier == "SECOND_ORDER"`
- `result["ok"] == 1`, `result["total"] == 1`
- State for cid=1 updated to new content string
- State for cid=2 unchanged (old content still present)

---

### D4 — Batch failure does NOT update store for that batch's rows

**Scenario:** 2 rows in changed set. `urlopen` returns HTTP 500 for the first (and only) batch.

**Setup:** `state_db` empty (first run). `fake_urlopen` returns a response with `status=500`.
The `post_signed` call must be made to read the status — mock `post_signed` directly to return
`{"ok": False, "error": "HTTP 500", "status": 500}` for simplicity (avoids urlopen JSON parsing).

**Approach:** patch `hug.customer_push.post_signed` directly (imported at line 39 of customer_push.py)
to return failure. This is cleaner than mocking urlopen for error-path tests.
VERIFIED: real `post_signed` returns `{"ok": False, "error": "http 500"}` on HTTP error
(NO `status` key) and never raises (`d1_transport.py`). Mock must match this shape —
do NOT include a `status` key. `_push_batches` only reads `result["ok"]`.

**Assert:**
- `result["failed"] == 2`, `result["ok"] == 0`
- `state_db` file exists but `SELECT COUNT(*) FROM hug_customer_push_state == 0`
  (no rows stored because no batch succeeded)
- Next call to `run()` with same data retries — `post_signed` called again (no skip)

---

### D5 — `force=True` bypasses store and pushes all rows

**Scenario:** Store fully populated (all rows match current content). Call `run(force=True)`.

**Setup:** Run D1 to populate store. Call `run(force=True, ...)` with same cache/crm/state.

**Assert:**
- `urlopen` (or `post_signed`) called — at least 1 batch
- `result["skipped"]` is falsy (not a no-change skip)
- All rows pushed (`result["ok"] == 2`)
- Log contains "force=True" (use `caplog` fixture with `propagate=True`)

---

### D6 — `HUG_CUSTOMER_PUSH_FULL=1` env var triggers force run

**Scenario:** Same as D5 but via env var, not `force=True` param.

**Setup:** `monkeypatch.setenv("HUG_CUSTOMER_PUSH_FULL", "1")`. Call `run()` (no force kwarg).

**Assert:** same as D5 — all rows pushed despite store being current.

---

### D7 — New customer not in store is included in push alongside unchanged customers

**Scenario:** Store has 1 row. Cache.db now has 2 rows (second is new, not in store).

**Assert:**
- Only the new customer is pushed (1 row, not 2)
- Existing customer is skipped (content unchanged)
- `result["ok"] == 1`, `result["total"] == 1`

---

## Mocking Notes

- For tests that need HTTP success: use existing `fake_urlopen` pattern (line 161–172).
  Return `resp.status = 200` and mock `__enter__`/`__exit__`. The `post_signed` layer
  checks `response.status` to determine ok/fail.
- For tests that need HTTP failure (D4): patch `hug.customer_push.post_signed` directly
  to return `{"ok": False, "error": "HTTP 500", "status": 500}`. Avoids re-implementing
  the HTTP response mock for error cases.
- Use `monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")` and
  `monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")` for all push-enabled tests,
  consistent with existing C5 test (line 156–158).

## Existing Tests — No Changes

C1–C8 are unaffected. The new `state_db` param has a default of `None` (resolves to
`_push_state_db_path()`). Existing tests that call `run(cache_db=..., crm_db=...)` without
`state_db` will attempt to open `./data/hug_push_state.db` — which will not exist in the
test environment, so the state will bootstrap empty and the push will proceed normally.
However, this leaves a file on disk in `./data/`. To prevent that side effect, existing
integration tests (C5, C6) should add `state_db=str(pathlib.Path(tmp_dir) / "state.db")`
to their `run()` calls. This is a 1-line addition, not a behavioral change.

## Success Criteria

- All 7 new tests pass (D1–D7) plus all 8 existing tests (C1–C8) — no regressions
- D2 verifies zero `urlopen`/`post_signed` calls (the core correctness claim)
- D4 verifies crash-safe store update (failed batch leaves store unmodified)
- Coverage: `_open_push_state`, `_load_push_state`, `_content_str`, `_update_push_state`,
  force-flag env-var path all exercised

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| D1 reset divergence (store says pushed, D1 empty) | Low (CF incident / wrangler re-apply) | High (silent data loss at edge) | Force flag (Phase 3); ops runbook |
| `hug_push_state.db` not volume-mounted in Docker | ~~Low~~ RESOLVED | — | VERIFIED: `crm_data:/data` named volume mounts whole dir (`docker-compose.yml:181,197`); state persists across restarts |
| Content string collision (two configs hash to same str) | Impossible with pipe-separated concat of 4 distinct-type fields | N/A | N/A |
| `recency_days` bumps at ICT midnight → full 7.5k push | Expected/accepted | Low (1 full push/day is fine) | Accepted; noted in out-of-scope |
| Failed batch + new run re-pushes rows that D1 already has | Harmless (D1 upsert is idempotent) | None | No action needed |

## Rollback Plan

This feature is purely additive. Rollback = revert `customer_push.py` to pre-diff version
(single file change). `hug_push_state.db` can be left in place — the reverted code ignores it.
No migration needed in either direction.

## Out of Scope (Known Gaps — Do Not Implement)

- Deletion of customers who drop out of `wh_customer_tier` from D1 (current full push also
  never deletes; no regression introduced)
- Once-per-day forced full push at ICT midnight when recency_days bumps for all customers
  (accepted — recency_days bump triggers the diff naturally; the one daily full push is correct)
- Dashboard/monitoring for push skip rate (can be derived from logs via grep "no-change")
