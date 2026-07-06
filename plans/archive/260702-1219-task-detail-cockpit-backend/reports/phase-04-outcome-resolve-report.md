# Phase 04 — Outcome Bulk-Resolve + Async-Resolve Report

## Status: DONE

## Summary

Closed the two remaining Phase-4 backend gaps for the CRM Call Cockpit:
1. **Outcome bulk-resolve** — extended `handle_log_activity` with two new form fields that dismiss action_ids and complete task_ids from the cockpit outcome bar after a call.
2. **Async-resolve (A-S14-026)** — new `POST /customers/{party_id}/reason/resolve-async` endpoint that logs an outbound contact via Zalo/email and resolves the rail item without a call.
3. **Helper module** extracted (`outcome_resolve_helpers.py`) for pure-logic testability (no FastAPI dependency).
4. **Wiring gap fixed** in `composition.py`: `action_state` was not previously passed to `make_customer_360_router`.
5. **Contract documented** in `S14-implementation-notes.md` § 11 for the future ui-port step.

---

## Files Changed

| File | Change |
|---|---|
| `crm/src/adapters/inbound/web/screens/customer360/outcome_resolve_helpers.py` | **NEW** — `parse_id_list()` + `bulk_resolve()` (no FastAPI dep) |
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` | `register_activity_routes()` — new `action_state=` param; `handle_log_activity` — new `resolve_action_ids` + `resolve_task_ids` form fields + bulk-resolve call; new `handle_resolve_async` endpoint |
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py` | Pass `action_state=action_state` to `register_activity_routes()` |
| `crm/src/composition.py` | Add `action_state=sqlite_repos["action_state"]` to `make_customer_360_router()` call in `_register_web_routes()` |
| `crm/docs/ui-spec/notes/S14-implementation-notes.md` | Appended § 11 — Outcome bulk-resolve + async-resolve contract |
| `crm/src/tests/test_outcome_bulk_resolve.py` | **NEW** — 23 pure-logic unit tests |

---

## py_compile Result

```
OK: outcome_resolve_helpers.py
OK: screen_customer_360_activity.py
OK: screen_customer_360.py
OK: composition.py
OK: test_outcome_bulk_resolve.py
```

All five changed/new Python files compile cleanly.

---

## Test Output

```
crm/src/tests/test_outcome_bulk_resolve.py — 23 passed in 0.05s
```

Full suite (excluding 3 pre-existing FastAPI-import collection errors):
```
4 failed (pre-existing), 603 passed, 42 skipped
```
Zero new failures introduced.

---

## Endpoint Contract

### 1. Outcome bulk-resolve (extended existing endpoint)

```
POST /customers/{party_id}/log-activity
```

New form fields (both optional, default `""`):

| Field | Description |
|---|---|
| `resolve_action_ids` | Comma-separated action_ids → `action_state.dismiss()` for each |
| `resolve_task_ids` | Comma-separated task_ids → `task_svc.transition_status(tid, "done")` for each |

- `skip_task_id` guard prevents double-resolution when `complete_task=1` and `task_id` overlap with `resolve_task_ids`.
- Response: unchanged — `HX-Redirect: /customers/{party_id}?tab=timeline`.
- Per-item errors logged at WARNING; never fail the whole request.

### 2. Async-resolve (new endpoint, A-S14-026)

```
POST /customers/{party_id}/reason/resolve-async
```

| Form field | Default | Description |
|---|---|---|
| `channel` | `""` | `"zalo"` → `activity_type="chat"`, `"email"` → `activity_type="email"` |
| `action_id` | `""` | Optional — single action_id to dismiss |
| `task_id` | `""` | Optional — single task_id to mark done |
| `note` | `""` | Optional free-text logged in activity body |

- Logs `direction="out"`, `outcome="async_sent"` activity, then resolves the given id.
- Returns **204 No Content** — HTMX targets the specific rail item only (`hx-swap="outerHTML"`). Cockpit panel not re-rendered (preserves call state per §9 invariant).

### Helper module

`crm/src/adapters/inbound/web/screens/customer360/outcome_resolve_helpers.py`
- `parse_id_list(raw: str) → list[str]`
- `bulk_resolve(action_ids, task_ids, action_state, task_svc, skip_task_id="", actor_id="") → None`
