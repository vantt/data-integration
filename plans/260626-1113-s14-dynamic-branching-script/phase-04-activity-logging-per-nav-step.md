# Phase 04 — Terminal-outcome logging (per-step path capture DEFERRED)

**Status:** pending  
**Effort:** ~0h for PoC (no new logging code)  
**Blockers:** Phase 03  
**File ownership:** none new for PoC.

---

## Decision (2026-06-26): do NOT log per nav step to crm_activity

Original design logged one `crm_activity` row per navigation step (fine-grained outcome in free-text `body`). **Rejected** — 3 problems:
1. **Timeline pollution** — one call = 3–4 rows; `crm_activity` is the human-facing touchpoint timeline (C360 renders it). A call is ONE meaningful touchpoint, not one-per-tap.
2. **Free-text `body` buries queryable signal** — `[node:… → outcome]` strings are the anti-pattern; the flywheel would need fragile parsing.
3. **Lossy** — body strings can't be cleanly backfilled into columns later.

### PoC (v1) — terminal outcome only, ZERO capture change
The branching nav is a **client-side UI concern** that ends in the SAME single outcome log used today: outcome bar → `s14OpenOutcome` → M08 modal → `ActivityService.log_activity` → ONE `crm_activity` row (canonical `contact_outcome`). crm_activity is **already ready**; the PoC adds NO logging code. The interpreter endpoint (Phase 02) resolves the next node and returns the fragment — it does NOT write activity.

### Flywheel (deferred, WS-C — OUT of v1)
Path + fine-grained outcomes (`interested`, `objection_price`, …) are **flywheel analytics data** → a dedicated **structured** table `crm_script_nav_event` (party_id, script_refreshed_at, node_id, outcome, occurred_at), separate from the operational timeline. Build when the flywheel matters, NOT now. The mapping reference below documents the outcome vocabulary for that future table.

---

## (Reference for the deferred nav-event table — not built in v1)

> The data-flow + mapping below is retained as the spec for `crm_script_nav_event` when WS-C is built. It is NOT implemented in the PoC.

---

## Data Flow

```
POST /api/parties/{party_id}/script-nav
  { current_node_id: "reached_interest_check", outcome: "interested" }
  │
  ├─ _resolve_next_node(...)  →  (terminal=False, next_node={"id": "pitch_reorder", ...})
  │
  └─ activity_log.log_activity({
       "party_id":      party_id,
       "activity_type": "call",
       "direction":     "out",
       "outcome":       <canonical_outcome>,       # see mapping table below
       "body":          "[node:reached_interest_check → interested → pitch_reorder]",
       "occurred_at":   ""   # let service fill utc_now()
     })
     └─ ActivityService inserts crm_activity row
     └─ last_contact_repo.upsert(...) fires if outcome is canonical (activity_service.py:58-68)
```

---

## Outcome Mapping (nav step → `contact_outcome`)

`crm_activity.contact_outcome` is constrained to `reached|no_answer|callback|refused` (migration 0013). Script-specific fine-grained outcomes must be mapped before writing.

```python
_SCRIPT_TO_CONTACT_OUTCOME = {
    "reached":          "reached",
    "no_answer":        "no_answer",
    "callback":         "callback",
    "refused":          "refused",
    "interested":       "reached",
    "objection_price":  "reached",
    "objection_need":   "reached",
    "objection_timing": "reached",
    "purchased":        "reached",
}

def _canonical_outcome(script_outcome: str) -> str:
    return _SCRIPT_TO_CONTACT_OUTCOME.get(script_outcome, "reached")
```

Place this dict and helper in `script_nav_handler.py` — no new module needed.

---

## `body` Field Format

The `body` field of `crm_activity` is free-text (`TEXT` column, no constraint). Use a structured prefix that is grep-able for future analytics:

```
[node:{current_node_id} → {outcome} → {next_node_id_or_terminal}]
```

Examples:
- `[node:root → reached → reached_interest_check]`
- `[node:reached_interest_check → interested → pitch_reorder]`
- `[node:pitch_reorder → purchased → terminal]`
- `[node:root → no_answer → terminal]`

This format is parseable with a simple regex if analytics ever queries it. It does not require a schema migration.

### Future migration path (not v1)

When nav-step volume justifies it, add `script_node_id TEXT` column to `crm_activity` via a new migration. The handler then writes `script_node_id=current_node_id` directly instead of embedding in `body`. The `body` prefix approach is a zero-migration interim.

---

## Wiring in `script_nav_handler.py`

The `wire_script_nav_router` factory signature (from Phase 02) gains one parameter:

```python
def wire_script_nav_router(
    party_repo: PartyRepository,
    approach_repo: ApproachScriptRepository,
    activity_log,          # ActivityService — same instance as screen_customer_360 uses
) -> None:
```

In `composition.py`, pass the existing `activity_service` instance (already wired for screen_customer_360 — locate its name in `composition.py` before writing).

**Verify in `composition.py`** before implementing: grep for `ActivityService` or `activity_service` to confirm the variable name and that it is already instantiated before the router wiring block.

```bash
grep -n "ActivityService\|activity_service\|activity_log" crm/src/composition.py
```

---

## Logging Only on Successful Nav (not on error responses)

Activity is written **only** when `_resolve_next_node` returns a valid result and the response is HTTP 200. On 403 (stop_state) or 404 (not found), no activity row is written. This prevents phantom rows from malformed requests.

---

## Terminal Step Logging

When `terminal=True` (outcome leads to `next: null`), still log the activity row — this is the most important event (records the final call outcome including `purchased`, `refused`, etc.). The `body` field uses `→ terminal` as the next node marker.

The `last_contact_repo.upsert` in `ActivityService` fires automatically for any row with a non-null `outcome` (`activity_service.py:58`). This keeps the `crm_last_contact` snapshot current without additional code.

---

## What Is NOT Logged Here

- The final M08 modal submission (existing `POST /customers/{party_id}/log-activity`) — that already writes its own `crm_activity` row via `handle_log_activity` (`screen_customer_360.py:509`). Nav-step rows and M08 rows are separate rows with distinct bodies. No deduplication needed for v1.
- Staff note text — notes go through M08 as today.

---

## Tests

| Test | Type | What to assert |
|------|------|----------------|
| Nav step writes `crm_activity` row | integration | After POST, query SQLite; row exists with `outcome=reached`, `body` contains `[node:root → reached →` |
| Terminal step writes row | integration | `body` contains `→ terminal` |
| Fine-grained outcome maps correctly | unit | `_canonical_outcome("interested") == "reached"` |
| Error response (404) writes no row | integration | Mock missing script; assert no new `crm_activity` row |
| `last_contact` upsert fires on terminal | integration | Query `crm_last_contact`; row updated after terminal step |

---

## Rollback

Remove the `activity_log.log_activity(...)` call from `script_nav_handler.py` (revert the TODO stub back to a comment). No DB migration to undo — rows already written to `crm_activity` are harmless orphans with distinct `body` format.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `activity_log` not available at nav step (wiring missed) | Low | Medium | `wire_script_nav_router` raises `RuntimeError` at startup if not wired (same pattern as Phase 02) |
| Double-logging: nav step + M08 for the same call | Certain | Low | Accepted by design — nav rows have `[node:...]` prefix, M08 rows have free-text body. Distinguish by `body` prefix in any future query |
| `crm_activity` SQLite contention from frequent nav steps | Very Low | Low | Single-writer constraint already known; nav steps are sequential per call, not concurrent |
