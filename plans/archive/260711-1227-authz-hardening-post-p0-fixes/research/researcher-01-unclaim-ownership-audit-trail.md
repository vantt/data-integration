# Research: Unclaim Handlers, Ownership/Role System, & Audit Trail

**Phase 6 — Authz/Audit Hardening (Post-P0 Fixes)**  
Research date: 2026-07-11  
Scope: Pure data-gathering; no design opinions, no recommendations

---

## 1. Unclaim Handlers — Route Paths & Port Method Resolution

### Finding 1.1: Two separate route registrations, same port method
**Route 1 — Worklist:**
- Path: `PATCH /worklist/customers/{party_id}/unclaim` (screen_worklist.py:526)
- Handler: `handle_unclaim_customer()` (line 527–538)
- Calls: `task_claim.unclaim_customer_actions(party_id)` (line 531)
- Parameter type: `task_claim` wired from `services["task"]` (composition.py, see section 6)
- UI trigger: "Trả việc" button in worklist claimed-task row (_wl_row.html:unclaimed queue section, wrapped in `t.source == 'action_queue_claim'` check)
- Response: re-renders entire worklist fragment via `hx-target="#worklist-container" hx-swap="outerHTML"`

**Route 2 — Customer 360:**
- Path: `PATCH /customers/{party_id}/unclaim` (screen_customer_360_panels.py:130)
- Handler: `handle_c360_unclaim_customer()` (line 131–140)
- Calls: `task_svc.unclaim_customer_actions(party_id)` (line 137)
- Parameter type: `task_svc` wired from same `services["task"]` (composition.py)
- UI trigger: "Trả việc" button in c360 insight panel (c360_insight_panel.html, shown when `customer_claim is defined and customer_claim`)
- Response: re-renders insight panel via `hx-target="#tab-panel" hx-swap="innerHTML"`

### Finding 1.2: Both routes call identical port method
**Port method signature** (application/task_service.py):
```python
def unclaim_customer_actions(self, party_id: str) -> bool:
    """Cancel the per-customer claim task, returning all actions to the unclaimed queue."""
    # Fetches existing claim task for party_id, sets status=cancelled + completed_at
```

**Conclusion:** Both routes are separate HTTP entry points on different URL paths, but they delegate to the identical `TaskService.unclaim_customer_actions(party_id)` port method. No current authorization check on either route — party_id is passed via URL path parameter with zero ownership validation.

---

## 2. Ownership/Role System

### Finding 2.1: Role entity exists, permission checking does not
**Role constants** (domain/entities/app_user.py:13–17):
```python
ROLE_SALES = "sales"
ROLE_CARE = "care"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
VALID_ROLES = [ROLE_SALES, ROLE_CARE, ROLE_MANAGER, ROLE_ADMIN]
```

**AppUser entity** (domain/entities/app_user.py:24–39):
- `user_id: str` (UUID)
- `email: str`
- `full_name: str`
- `role: str` — one of VALID_ROLES
- `is_active: bool`
- `created_at`, `updated_at`: UTC ISO-8601
- `lark_user_id: Optional[str]` — CF Access JWT custom.sub
- `staff_id: Optional[int]` — Sapo account_id bridge

**Role status in v1** (app_user.py:28–29):
> "Role is informational in v1 (auth deferred — LAN-trust model)."

**Permission checking:** No permission helper, no `is_admin()`, no `is_manager()` logic found in:
- `crm/src/domain/entities/` (searched all files)
- `crm/src/adapters/inbound/web/` (no middleware enforcing role checks on unclaim routes)

**Conclusion:** Role field exists and is stored but unused for access control. No built-in permission system — all routes trust LAN + current_user identity. Plan must decide: allow admin override of assignee-only check, or assignee-only with zero override.

---

## 3. Current User Derivation Pattern

### Finding 3.1: Two patterns, both read request.state.current_user

**Pattern A — screen_worklist.py:321–323 (local helper function):**
```python
def _current_user_id(request: Request) -> str:
    user = getattr(request.state, "current_user", None)
    return user.user_id if user else ""
```
Used throughout worklist handlers (line 330, 346, 358, 442, 480).

**Pattern B — screen_customer_360_panels.py:117 (nested getattr):**
```python
uid = getattr(getattr(request.state, "current_user", None), "user_id", "")
```
More defensive but equivalent; used in c360 claim handler + activity log draft context (line 271).

**Underlying assumption:** `request.state.current_user` is an `AppUser` instance (or None) populated by auth middleware before handlers run.

**Concrete usage examples in worklist:**
- Line 442 (assign-me): `uid = _current_user_id(request)` → returns empty string if not authenticated → checked `if not uid: return 401`
- Line 480 (claim action): `uid = _current_user_id(request)` → same pattern
- Line 367–373 (mark task done): no uid check, operates on task_id directly

**Conclusion:** Consistent pattern; extract via `request.state.current_user.user_id` (handle None → empty string). No current_user check on unclaim handlers — fix must add this.

---

## 4. Outcome Reason Pattern — Existing Structure for Reuse

### Finding 4.1: Reason enum and UX requirements already defined

**Valid reasons** (domain/entities/activity.py:60–78):
```python
VALID_OUTCOME_REASONS = [
    "budget", "timing", "product_fit", "competitor",
    "stock", "trust", "no_need", "other",
    "still_stocked", "wait_promo", "irritation",
    "do_not_contact",
]
```

**Enforcement rule** (activity.py:80):
```python
REASON_REQUIRED_OUTCOMES: set[str] = {"refused"}
```
Outcome `refused` requires a reason to be recorded.

**Where reasons are collected:** Not found in templates yet (call cockpit reason rail not inspected). The spec structure exists; unclear which UI widget collects it (dropdown? chips? radio?).

**How to reuse:** For unclaim, could add new required outcome list like:
```python
REASON_REQUIRED_OUTCOMES_UNCLAIM: set[str] = {"unclaimed"}  # or similar
```
And follow same Activity side-effect pattern: store `outcome_reason` in `crm_activity` or lightweight event log (see section 5).

**Conclusion:** Reason pattern + constants exist; UI widget pattern (dropdown vs radio vs chips) not yet verified in call cockpit code. Copy the same enum structure for unclaim reasons if needed.

---

## 5. Audit Trail Options — No Dedicated Audit Table; Lightweight Event Pattern Available

### Finding 5.1: No audit_log or history_log table
**Migrations scanned:** crm/migrations/ contains 45+ migration files (0001–0045_*).  
**Table names found:**
- `crm_party`, `crm_party_identity`, `crm_activity_log`, `crm_task`, `crm_app_user`
- `crm_note` (added migration 0010)
- `crm_action_state`, `crm_action_dismissal` (B5, migration 0015/0038)
- No `audit`, `history_log`, `_log` (except `activity_log` and `action_dismissal` which serve different purposes)

**Closest existing lightweight event pattern:** `crm_note` table + `NoteService.add_note()`

### Finding 5.2: NoteService as lightweight event store

**Signature** (application/note_service.py:30–56):
```python
def add_note(
    self,
    party_id: str,
    body: str,
    author_user_id: Optional[str] = None,
    note_type: str = "general",
    pinned: bool = False,
    visibility: str = "team",
    source_activity_id: Optional[str] = None,
) -> Note:
```

**Port interface** (domain/ports/tag_repository.py):
```python
class NoteRepository(Protocol):
    def add_note(self, note: Note) -> None: ...
```

**Existing note_types:** "general", "outcome" (inferred from side-effects.py:187 `note_type=save_as_note.get("note_type") or "outcome"`). Migration 0010 added note_type + pin_visibility columns.

**How it works:** Notes are party-scoped (party_id FK), timestamped (created_at), author-tracked (author_user_id), and can link to source activity (source_activity_id). Soft-delete supported (soft_delete_note method).

**Fit for unclaim audit trail:** Could add new note_type = "unclaim_reason" or similar, store reason + actor_id + party_id in a single note row. Lightweight, no new table needed. Downside: mixed with customer-facing notes unless visibility/type filtering used.

**Alternative:** Add a minimal `crm_task_claim_audit` table (1 migration) to record:
- `claim_id` (task_id of the claim task)
- `action` (claimed | unclaimed)
- `reason` (nullable)
- `actor_user_id`
- `occurred_at`

**Conclusion:** No dedicated audit table currently exists. NoteService can record lightweight events if visibility/type isolation acceptable. Otherwise, minimal migration adds 4-5 columns to a new audit table.

---

## 6. IDOR Fix — Party ID Resolution in `resolve_actions_and_tasks()`

### Finding 6.1: resolve_actions_and_tasks current state (no party_id checking)

**Current signature** (application/activity_side_effects.py:44–51):
```python
def resolve_actions_and_tasks(
    action_ids: list[str],
    task_ids: list[str],
    action_state,
    task_svc,
    contact_outcome: Optional[str],
    actor_id: Optional[str] = None,
) -> None:
```

**Current behavior** (line 72–90):
- Takes raw `action_ids` list
- Takes raw `task_ids` list
- Calls `action_state.snooze(aid, ...)` or `action_state.dismiss(aid, ...)` without resolving party_id
- Calls `task_svc.transition_status(tid, ...)` without checking task ownership

**IDOR risk:** If an attacker passes action_id or task_id lists from a different party/customer, they can dismiss/snooze that customer's actions or complete another user's tasks.

### Finding 6.2: Party ID resolution for action_ids

**Method exists in adapter layer:**  
`SQLiteActionStateRepository._resolve_party_and_action_type()` (action_state_repository.py:81–118)

**Signature & implementation:**
```python
def _resolve_party_and_action_type(self, action_id: str) -> Optional[tuple[str, str]]:
    """Look up (party_id, action_type) for action_id via cache-join pattern.
    Checks wh_action_queue + wh_sku_action_queue. Returns None if action not found
    or party not yet linked."""
    # Tries two branches:
    # 1. cache.wh_action_queue + wh_party_seed join + crm_party_identity (lines 90–97)
    # 2. cache.wh_sku_action_queue + same pattern (lines 99–107)
```

**Problem:** This method is **private** (prefixed with `_`) and **not exposed by ActionStatePort protocol** (domain/ports/action_state_port.py:7–20, only defines `dismiss()`, `snooze()`, `reopen()`).

**To expose for application layer:** Must extend ActionStatePort with new method:
```python
def resolve_party_id(self, action_id: str) -> Optional[str]:
    """Resolve the party_id for an action_id, or None if not found."""
```
Then SQLiteActionStateRepository implements it by calling its existing `_resolve_party_and_action_type(action_id)[0]`.

### Finding 6.3: Party ID resolution for task_ids

**Task entity has party_id field** (domain/entities/task.py:76):
```python
party_id: Optional[str] = None  # FK → crm_party (nullable)
```

**To resolve in application layer:**  
`resolve_actions_and_tasks()` already receives `task_svc` parameter (wired from `TaskService` in composition.py).  
`TaskService.get_task(task_id: str) -> Optional[Task]` (signature found in worklist.py:60) returns full Task entity with party_id.

**No new port needed:** `task_svc` is already a parameter; call `task_svc.get_task(task_id)` to fetch party_id. Sufficient to pass already-available port.

### Finding 6.4: Port parameter type hints

**Current state:** `action_state` and `task_svc` in `resolve_actions_and_tasks()` have no type hints (line 47–48).

**Inferred types from composition.py wiring:**
- `action_state` is `SQLiteActionStateRepository` (satisfies `ActionStatePort` protocol)
- `task_svc` is `TaskService` (satisfies implicit task service protocol)

**For type safety:** Add protocol type hints:
```python
def resolve_actions_and_tasks(
    action_ids: list[str],
    task_ids: list[str],
    action_state: ActionStatePort | None,
    task_svc: TaskServiceProtocol | None,  # create TaskServiceProtocol if not exists
    ...
) -> None:
```

### Finding 6.5: Composition wiring

**Where action_state is wired** (composition.py):
```python
app.include_router(make_worklist_router(
    ...
    action_state=sqlite_repos["action_state"],  # SQLiteActionStateRepository
    task_claim=services["task"],  # TaskService
))
```

Both are passed to router factory; router passes them to handlers that call `resolve_actions_and_tasks()` (indirectly via execute_side_effects).

**Conclusion for IDOR fix:**
1. Extend `ActionStatePort` protocol with `resolve_party_id(action_id: str) -> Optional[str]`
2. In `resolve_actions_and_tasks()`, add pre-checks: resolve each action_id to party_id and verify it matches expected `party_id` parameter (add new param)
3. For tasks: call `task_svc.get_task(task_id).party_id` (already available; no new port needed)
4. Reject (log + skip) any action/task with mismatched or unresolvable party_id

---

## Unresolved Questions

1. **Call cockpit UI widget for outcome_reason:** Which template collects outcome reasons (dropdown? chips? radio buttons?)? Needed to match UI pattern for unclaim reasons.
2. **NoteService visibility isolation:** If recording unclaim reasons as notes, how to prevent team-facing notes from leaking system-only audit entries? Visibility field alone sufficient, or need new note_type enum value?
3. **Task claim context — who can unclaim:** Should only the assignee (task.assignee_user_id) be allowed to unclaim, or any role? Current code has no check.
4. **Task claim context — return reason requirement:** Should unclaim ALWAYS require a reason, or only when status transitions to "cancelled" (already set by unclaim method)? If so, modify TaskService.unclaim_customer_actions to accept reason parameter.

---

## File:Line Summary

- **screen_worklist.py**
  - Line 526–538: `handle_unclaim_customer` (PATCH /worklist/customers/{party_id}/unclaim)
  - Line 321–323: `_current_user_id` helper

- **screen_customer_360_panels.py**
  - Line 130–140: `handle_c360_unclaim_customer` (PATCH /customers/{party_id}/unclaim)
  - Line 117: current_user extraction pattern

- **app_user.py**
  - Line 13–17: Role constants
  - Line 24–39: AppUser entity (role field at line 33)

- **activity.py**
  - Line 60–78: VALID_OUTCOME_REASONS
  - Line 80: REASON_REQUIRED_OUTCOMES

- **task_service.py**
  - unclaim_customer_actions method signature (no line available, grep confirmed)

- **action_state_repository.py**
  - Line 81–118: `_resolve_party_and_action_type` (private; must be exposed)

- **activity_side_effects.py**
  - Line 44–51: `resolve_actions_and_tasks` signature
  - Line 72–90: resolve logic (no party_id checks)

- **composition.py**
  - Wiring: task_claim=services["task"], action_state=sqlite_repos["action_state"]

- **Templates**
  - c360_insight_panel.html: "Trả việc" button → `/customers/{party_id}/unclaim`
  - _wl_row.html: "Trả việc" button → `/worklist/customers/{pid}/unclaim`

- **Domain ports**
  - action_state_port.py (line 7–20): ActionStatePort protocol — does not expose resolve_party_id
  - task_repository.py: TaskRepository protocol — has get_by_id (not used in activity_side_effects)

- **Note service**
  - note_service.py (line 30–56): add_note signature
