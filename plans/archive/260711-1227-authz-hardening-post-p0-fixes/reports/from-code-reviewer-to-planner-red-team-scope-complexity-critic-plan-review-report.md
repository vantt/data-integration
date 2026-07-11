# Red-Team Review: Scope & Complexity Critic — Authz Hardening Plan

Reviewer role: Scope & Complexity Critic (YAGNI enforcer) + Contract Verifier
Plan: `plans/260711-1227-authz-hardening-post-p0-fixes/`
Verification method: grep-verified against live codebase at `D:\Vantt\app\data-integration\crm\src`, not assumed from plan text.

---

## Finding 1: `TaskService.__init__`'s required `authz` param breaks 8 existing test construction sites, undeclared in Phase 2 scope

- **Severity:** Critical
- **Location:** Phase 2, section "Implementation Steps" step 2 / "Related Code Files"
- **Flaw:** Phase 2 mandates `authz: AuthorizationService` as a constructor param with **no default** ("required, no default... deliberate deviation from this file's usual `Optional[...] = None` convention"). `TaskService`'s current signature (`crm/src/application/task_service.py:64-70`) is `__init__(self, task_repo, cache_repo, db=None, party_repo=None)` — all params after position 2 already have defaults. Phase 2's "Related Code Files" list for this change covers only `task_service.py`, `composition.py`, the 2 route handlers, and 2 templates. It does not list, grep, or account for any of the 8 existing test call sites that construct `TaskService(...)` without an `authz` argument.
- **Failure scenario:** Every listed test raises `TypeError: __init__() missing 1 required positional argument: 'authz'` the moment Phase 2 lands, failing the full suite — directly contradicting Phase 2's own Success Criteria bullet "Full CRM test suite green."
- **Evidence:**
  - `crm/src/tests/test_task_claim_action_types_snapshot.py:49,67,80,113` — 4 call sites, e.g. `svc = TaskService(task_repo, cache_repo, db=None)`
  - `crm/src/tests/test_task_kind.py:155,231` — `svc = TaskService(task_repo, cache_repo, db=None)`
  - `crm/src/tests/test_claim_context_snooze_r14.py:71` — `return TaskService(task_repo, cache_repo, db=None), task_repo`
  - `crm/src/tests/test_task_service_title_fallback.py:33` — `svc = TaskService(task_repo, cache_repo, db=None, party_repo=party_repo)`
  - `crm/src/tests/test_activity_disposition_api_routes.py:134` — `task_svc = TaskService(task_repo, MagicMock(), db=db)`
  - Total: 8 call sites, 5 files, all unaccounted for in Phase 2's file list.
- **Secondary defect:** a required param with no default cannot syntactically follow existing default-valued params (`db=None`, `party_repo=None`) in the same signature — Python raises `SyntaxError: non-default argument follows default argument`. The plan's example call sites (e.g. `composition.py:328`'s current positional call `TaskService(sqlite_repos["task"], sqlite_repos["cache"], db, sqlite_repos["party"])`) would need `authz` inserted earlier than `db`/`party_repo` to be legal, which silently shifts every positional caller's arguments by one slot unless every call site is rewritten to keyword args — a second class of breakage the plan does not mention.
- **Suggested fix:** Either (a) give `authz` a default of `None` and fail closed inside `unclaim_customer_actions()` when `self._authz is None` (contradicts the plan's stated "no silent-skip" design goal, but is syntactically safe and backward compatible), or (b) explicitly enumerate and update all 8 test call sites plus reorder the signature with keyword-only enforcement (`*`) and audit every remaining caller for correctness.

## Finding 2: `resolve_actions_and_tasks()`/`bulk_resolve()`'s new required `party_id`+`authz` params break 19 existing test call sites, undeclared in Phase 3 scope

- **Severity:** Critical
- **Location:** Phase 3, section "Implementation Steps" steps 3-5 / "Related Code Files"
- **Flaw:** Phase 3 adds `party_id: str` and `authz: AuthorizationService` as new **required** params to `resolve_actions_and_tasks()` (`activity_side_effects.py:44`) and threads the same through `bulk_resolve()` (`outcome_resolve_helpers.py:21`). Phase 3's "Related Code Files" lists only `activity_side_effects.py`, `outcome_resolve_helpers.py`, `screen_customer_360_activity.py` (verify-only), and the port/repository files — no test files. `crm/src/tests/test_outcome_bulk_resolve.py` calls `_bulk_resolve(...)` (imported directly as the alias for `outcome_resolve_helpers.bulk_resolve`) 19 times, none passing `party_id` or `authz`.
- **Failure scenario:** All 19 tests raise `TypeError: missing required positional argument` once Phase 3 lands, directly contradicting Phase 3's own Success Criteria bullet "full existing bulk-resolve test suite still green."
- **Evidence:** `crm/src/tests/test_outcome_bulk_resolve.py` — 19 call sites at lines 82, 85, 88, 94, 99, 107, 112, 119, 124, 133, 138, 143, 152, 158, 166, 184, 196, 207, 220, all of the shape `_bulk_resolve(["a1"], [], action_state=as_, task_svc=None)` or similar — zero pass `party_id`/`authz`. Import confirmed at `test_outcome_bulk_resolve.py:27` (`bulk_resolve as _bulk_resolve`).
- **Suggested fix:** Add `test_outcome_bulk_resolve.py` (and re-verify `test_bulk_resolve_endpoint.py`, which exercises the route layer and may be insulated) to Phase 3's "Related Code Files," and update all 19 call sites as part of this phase, not silently discovered later during "run tests."

## Finding 3: Phase 2's own example `notes_repo.add_note(...)` call contradicts its own composition-wiring instructions — internal contradiction, not just an "unresolved risk"

- **Severity:** High
- **Location:** Phase 2, "Implementation Steps" step 3 vs. "Related Code Files" / step 4
- **Flaw:** Phase 2's "Related Code Files" and step 4 instruct wiring `sqlite_repos["note"]` (i.e. `SQLiteNoteRepository`, `composition.py:248`) directly as `TaskService`'s `notes_repo`. `SQLiteNoteRepository` satisfies `NoteRepository(Protocol)` at `crm/src/domain/ports/tag_repository.py:98-101`, whose `add_note` signature is `add_note(self, note: Note) -> None` — it takes one fully-constructed `Note` domain entity. But step 3's example call is `self._notes_repo.add_note(..., party_id, body, author_user_id=actor_id, note_type="unclaim_reason", visibility="team")` — this is the `NoteService.add_note()` kwargs signature (`application/note_service.py:30-56`), not the raw repository Protocol's. The plan labels this a "Risk... wasn't 100% pinned during research" but it is not merely unpinned — the two instructions in the same phase document are mutually exclusive as written.
- **Failure scenario:** Implemented literally, `self._notes_repo.add_note(party_id, body, author_user_id=...)` against a `SQLiteNoteRepository` raises a `TypeError` (wrong signature) at the first unclaim-with-reason call, inside a try/except that (per step 3) swallows it — the ownership check still passes and the unclaim still happens, but the audit note silently never gets written. This defeats requirement #1's whole purpose ("Unclaiming requires selecting a reason... written to an audit note").
- **Evidence:** `crm/src/domain/ports/tag_repository.py:98,101`; `crm/src/adapters/outbound/sqlite/tag_note_repository.py:302` (`def add_note(self, note: Note) -> None`); `crm/src/application/note_service.py:30-56`; `composition.py:248` (`"note": SQLiteNoteRepository(db)`).
- **Suggested fix:** Decide explicitly at plan-time (not implementation-time) whether `TaskService` is injected with the raw `NoteRepository` (and must construct a `Note` entity itself) or a `NoteService` instance (and calls its friendlier `add_note(...)`). Update the wiring instruction and the example call to match.

## Finding 4: Phase 4's "existing caller" of `POST /tasks` appears to be dead/broken code, not a live regression risk — plan spends effort protecting a phantom consumer

- **Severity:** Medium
- **Location:** Phase 4, "Requirements" bullet 4 and "Risk Assessment" (both risks)
- **Flaw:** Phase 4 repeatedly frames `/tasks`'s "existing caller" (S07 Tasks Board's own "+ Tạo task" button) as a live regression surface requiring careful additive-only changes and explicit manual verification ("Existing S07 Tasks Board '+ Task' flow (if it exists as a separate caller) → unchanged behavior"). Grepping the actual templates shows: (a) zero templates currently `hx-post` to `/tasks` at all; (b) S07's own "+ Tạo task" button (`tasks_board.html:27-32`) opens `GET /tasks/modal/create`, whose handler (`screen_tasks_board.py:123-129`) renders `fragments/modal_create_task.html` — **a template file that does not exist on disk** (confirmed via Glob, only `modal_m05_create_task.html` exists). That GET route already 500s/raises `TemplateNotFound` before ever reaching a form that could POST to `/tasks`.
- **Failure scenario:** None from this plan directly — but the plan's own risk-mitigation effort (grepping for "OTHER existing callers," worrying about a `worklistRefresh` listener collision on "S07 Tasks Board's own page") is spent defending a caller that is not currently reachable through the UI, while the plan does not surface or flag the actual pre-existing bug (missing `modal_create_task.html`) it stumbled into during this research.
- **Evidence:** `Glob **/modal_*task*.html` → only `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html`; `Grep hx-post="/tasks"` across templates → no matches; `screen_tasks_board.py:123-129` references `"fragments/modal_create_task.html"`.
- **Suggested fix:** Verify at implementation time whether `GET /tasks/modal/create` is truly dead (confirm via a manual click, not just grep) — if confirmed dead, drop the "protect the existing caller" framing from Phase 4's risk assessment (it's testing against a caller that can't currently execute), and separately log the missing-template bug as its own tracked item (out of this plan's scope per user's stated hold-scope decision, but worth a one-line flag so it isn't lost).

## Finding 5: `TaskClaimWriter` Protocol's stale `-> bool` return-type annotation is not in Phase 2's file list

- **Severity:** Medium
- **Location:** Phase 2, "Related Code Files" (omission)
- **Flaw:** `screen_worklist.py:75-77` defines a `TaskClaimWriter(Protocol)` used to type the `task_claim` param, with `def unclaim_customer_actions(self, party_id: str) -> bool: ...`. Phase 2 changes the concrete return type to a 3-state `str`. The Protocol definition itself is never listed as a file to modify anywhere in Phase 2.
- **Failure scenario:** Not a runtime crash (Python `Protocol`s aren't structurally enforced without a type checker), but it's a real, verifiable contract-drift the plan misses while simultaneously claiming (Phase 1) that public interfaces "must be properly designed and stable." A future reader or a mypy/pyright run treats `task_claim.unclaim_customer_actions(...)` as returning `bool`, silently mismatching the real `"ok"|"not_found"|"forbidden"` value.
- **Evidence:** `crm/src/adapters/inbound/web/screen_worklist.py:75-77`.
- **Suggested fix:** Add this Protocol update to Phase 2's file list; trivial one-line fix, but currently invisible to whoever implements the phase from the plan alone.

## Finding 6: Phase 2 step 5's control-flow for `handle_unclaim_customer` isn't compatible with the current broad try/except — plan doesn't flag the restructuring needed

- **Severity:** Medium
- **Location:** Phase 2, "Implementation Steps" step 5
- **Flaw:** Current handler (`screen_worklist.py:527-538`) wraps the service call in `try: task_claim.unclaim_customer_actions(party_id) except Exception as exc: log.error(...)` and then **unconditionally** falls through to `_render_worklist_fragment(request)` (200) regardless of what happened inside the try. Step 5 says to check `result == "forbidden"` and return 403 "else... existing re-render path unchanged" but doesn't state where the 403 branch sits relative to the try/except — if a naive implementation keeps the existing broad `except Exception` (e.g. some future exception at the service layer, or a lazy read of `result` from outside the try scope), the forbidden/error case can silently fall through to a 200 success render, effectively bypassing the new authz check at the HTTP layer even though `TaskService` itself computed `"forbidden"` correctly.
- **Failure scenario:** A non-assignee's unclaim attempt returns 200 (worklist re-renders "successfully") instead of 403, even though the service-layer check fired — the exact bug class this phase exists to close, re-introduced by an underspecified control-flow patch.
- **Evidence:** `crm/src/adapters/inbound/web/screen_worklist.py:526-538` (current try/except-then-always-render shape).
- **Suggested fix:** Phase 2 should explicitly specify the new control flow (e.g. `result` must be read and branched on *inside* the try block or with the try narrowed to only the call itself), not leave it to implementation-time judgment for a security-relevant code path.

## Finding 7: Phase 1's own Risk Assessment concedes the abstraction doesn't fit uniformly — evidence against "properly structured" framing

- **Severity:** High
- **Location:** Phase 1, "Risk Assessment," second bullet
- **Flaw:** Phase 1's overview asserts `AuthorizationService` is "a small, real, hexagonal-architecture service" with "clean typed interface" designed so injection is consistent. Its own Risk Assessment then admits: "threading `AuthorizationService` through `resolve_actions_and_tasks()`... may prove awkward compared to `TaskService`'s clean constructor injection in Phase 2 — if so, inline construction... is an acceptable fallback." Phase 3 echoes this uncertainty verbatim ("prefer threading from composition if straightforward, fall back to inline construction only if it isn't"). A service whose own creator cannot commit to one injection pattern across its 2 (and only 2) known consumers is evidence the "single source of truth, stable interface" framing oversells the design's cohesion — the 2 consumers don't actually share an architectural shape (one is a DI-friendly class, the other a free function deep in a call chain), only a coincidental one-line boolean comparison.
- **Verdict on the premature-abstraction question:** For TODAY's scope alone, 2 inline `==`/`is not None` comparisons (2-4 lines total) in `task_service.py` and `activity_side_effects.py` would have been strictly simpler, equally correct, and equally testable (each is directly unit-testable in its existing surrounding test file) — the classic "wait for the 3rd duplication" heuristic would reject this extraction on its technical merits alone. However, the user explicitly requested centralization in preparation for future RBAC (documented in `plan.md`'s "Mid-plan design decision" note) — that is a legitimate, stated requirement that overrides the default YAGNI heuristic; per `review-audit-self-decision` rules this is a user decision, not something to silently reverse. The honest critique is therefore not "delete Phase 1" but: **the plan should not simultaneously claim the abstraction is architecturally clean AND admit in the same document that it doesn't cleanly fit one of its 2 consumers** — that combination should have prompted either simplifying `is_same_party`'s call site (e.g. resolve `authz` once in the route handler and pass the *decision*, not the service instance, down the call chain) or accepting a plain module-level function instead of a class for the free-function consumer.
- **Evidence:** Phase 1 `phase-01-authorization-service-foundation.md` Risk Assessment bullet 2; Phase 3 `phase-03-resolve-idor-fix.md` step 4.
- **Suggested fix:** Resolve the injection-pattern question at plan time, not "at implementation time" — pick one of: (a) module-level pure functions (`is_owner()`, `is_same_party()`) instead of a class, avoiding DI entirely for what is stateless logic; or (b) commit to threading a single composition-wired instance through both call chains and accept the extra plumbing in Phase 3.

## Finding 8: Scope grew from "4 items" to 5 phases + ~18 production files + a new class/port/Protocol member — proportionality concern

- **Severity:** Medium
- **Location:** `plan.md` Overview / all phases
- **Flaw:** The original ask (per `plan.md:19-24`) was 4 items: 1 ownership check, 1 IDOR fix, 1 routing fix, 1 test file. As executed, the plan touches: `authorization_service.py` (new), `test_authorization_service.py` (new), `composition.py`, `task_service.py`, `screen_worklist.py`, `screen_customer_360_panels.py`, `_wl_row.html`, `c360_insight_panel.html`, `task.py` (new constant), `action_state_port.py` (new Protocol method), `action_state_repository.py`, `activity_side_effects.py`, `outcome_resolve_helpers.py`, `screen_customer_360_activity.py` (verify), `screen_tasks_board.py`, `modal_m05_create_task.html`, plus (per Findings 1-2 above) at least 27 additional test call sites the plan itself doesn't yet account for. That's ~16 production files + 2 new files + 27+ latent test fixes, for what the user originally scoped as 2 narrow authz checks, 1 routing fix, and 1 test file.
- **Failure scenario:** Not a correctness bug, but a review/execution-cost risk: a 5-phase plan with this much surface area increases the chance further undiscovered breakage (see Findings 1-2) ships along with it, and the "hold scope, no expansion" framing in `plan.md:28` sits awkwardly next to the actual blast radius.
- **Evidence:** File counts derived directly from each phase's "Related Code Files" section plus Findings 1-2's grep results.
- **Suggested fix:** Not a call to cut Phase 1 (see Finding 7's verdict — user requirement stands), but the plan should be explicit in its own scope statement that "centralizing authorization" has a real, non-trivial fan-out (2 new required constructor/function params across 2 service layers, 1 new Protocol member, 1 new port implementation) rather than implying it's incidental plumbing to 2 one-line checks.

---

## Contract Verifier Verification Results

### `TaskService.__init__` (Phase 2 adds required `authz` param)
All call sites found via `grep -rn "TaskService\("`:
1. `crm/src/composition.py:328` — production, updated in Phase 2 (accounted for)
2. `crm/src/tests/test_activity_disposition_api_routes.py:134` — **not accounted for**
3. `crm/src/tests/test_claim_context_snooze_r14.py:71` — **not accounted for**
4. `crm/src/tests/test_task_service_title_fallback.py:33` — **not accounted for**
5. `crm/src/tests/test_task_kind.py:155` — **not accounted for**
6. `crm/src/tests/test_task_kind.py:231` — **not accounted for**
7. `crm/src/tests/test_task_claim_action_types_snapshot.py:49` — **not accounted for**
8. `crm/src/tests/test_task_claim_action_types_snapshot.py:67` — **not accounted for**
9. `crm/src/tests/test_task_claim_action_types_snapshot.py:80` — **not accounted for**
10. `crm/src/tests/test_task_claim_action_types_snapshot.py:113` — **not accounted for**

Total: 10 call sites, 1 of 10 covered by Phase 2's file list. **8 of 10 will break.**

### `TaskService.unclaim_customer_actions()` (bool → 3-state str)
All call sites found via `grep -rn "unclaim_customer_actions"`:
1. `crm/src/adapters/inbound/web/screen_worklist.py:531` — updated in Phase 2 (accounted for)
2. `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py:137` — updated in Phase 2 (accounted for)
3. `crm/src/adapters/inbound/web/screen_worklist.py:77` — `TaskClaimWriter` Protocol stub, **not updated** (Finding 5)

Test files: zero matches for `unclaim_customer_actions` in `crm/src/tests/`. **Plan's claim "both known callers... being updated in this same phase" is accurate for production callers** — this specific claim checks out.

### `resolve_actions_and_tasks()` (Phase 3 adds required `party_id` + `authz`)
All call sites found via `grep -rn "resolve_actions_and_tasks"`:
1. `crm/src/application/activity_side_effects.py:246` — the sole caller, inside `execute_side_effects()`; `party_id` confirmed in scope as a keyword-only param (`activity_side_effects.py:97`) — updated in Phase 3 (accounted for)

No other production or test call sites found. This specific claim ("party_id already available at every call site") is accurate for the direct function.

### `bulk_resolve()` (Phase 3 threads `party_id` + `authz` through)
All call sites found via `grep -rn "bulk_resolve\("`:
1. `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py:478` (as `_bulk_resolve`) — production, `party_id` confirmed in scope as a path param on `handle_resolve_async` — updated in Phase 3 (accounted for)
2. `crm/src/tests/test_outcome_bulk_resolve.py` — **19 direct call sites** at lines 82, 85, 88, 94, 99, 107, 112, 119, 124, 133, 138, 143, 152, 158, 166, 184, 196, 207, 220 — **not accounted for in Phase 3's file list**

Total: 20 call sites, 1 of 20 covered. **19 of 20 will break** (Finding 2).

### `POST /tasks` (Phase 4 adds optional Form params + `return_to` handling)
- Templates: `grep -rn 'hx-post="/tasks"'` across `crm/src/adapters/inbound/web/templates/` → **zero matches**. No template currently posts to this route.
- `GET /tasks/modal/create` (`screen_tasks_board.py:123-129`, the presumed producer of a form that would post to `/tasks`) renders `"fragments/modal_create_task.html"`, which **does not exist** (`Glob **/modal_*task*.html` → only `modal_m05_create_task.html`).
- Tests: `grep -rn "handle_create_task|POST /tasks"` across `crm/src/tests/` → zero matches; no test exercises this handler today.
- Conclusion: the "existing caller" Phase 4 repeatedly protects against appears unreachable in the current codebase (Finding 4).

---

## Unresolved Questions

1. Is `GET /tasks/modal/create` confirmed dead in practice (e.g. does some other template reference `modal_create_task.html` under a different path, or was it recently deleted without updating the route)? Grep/Glob say no live reference exists, but a manual click-through would remove all doubt before Phase 4 treats it as a live regression surface.
2. Should `TaskService.notes_repo` be a raw `NoteRepository` (requiring `TaskService` to construct a `Note` entity itself) or a `NoteService` instance (matching the kwargs call already written in Phase 2's own pseudocode)? The plan currently instructs both, contradicting itself (Finding 3).
3. Given Finding 7's injection-pattern inconsistency, should `AuthorizationService` be a plain module (functions) instead of a class, sidestepping the DI question for both consumers?
