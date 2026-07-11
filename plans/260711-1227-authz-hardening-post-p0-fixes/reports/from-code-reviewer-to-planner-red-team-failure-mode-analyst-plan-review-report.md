# Red-Team Review: Authz Hardening + Post-P0 Fixes Plan

Reviewer role: Failure Mode Analyst / Flow Tracer
Plan: `plans/260711-1227-authz-hardening-post-p0-fixes/`
Scope: plan.md + 5 phase files + 2 research reports, verified against `crm/src/` on disk.

---

## Finding 1: Ownership check is bypassed whenever `actor_id` is falsy — defeats Phase 2's entire purpose

- **Severity:** Critical
- **Location:** Phase 2, "Implementation Steps" step 3 (`phase-02-unclaim-ownership-and-audit-trail.md:51`)
- **Flaw:** The spec'd guard is:
  > "If `actor_id` and not `self._authz.is_owner(existing.assignee_user_id, actor_id)` → return `"forbidden"`"
  i.e. `if actor_id and not is_owner(...):`. When `actor_id` is falsy (`None` or `""`), the whole condition short-circuits to `False` — the forbidden branch is skipped and the unclaim **proceeds unconditionally**, regardless of who actually owns the claim. `AuthorizationService.is_owner()` itself fails closed on empty/None inputs (`phase-01...md:46-48`), but that safety is never reached because the outer `if actor_id` gate filters it out first.
- **Failure scenario:** Any request where `request.state.current_user` is `None` reaches `unclaim_customer_actions` with `actor_id=""`. `cf_access_middleware.py:4` documents this is not a corner case: *"If CF_ACCESS_AUDIENCE is unset → bypass (dev/LAN mode, current_user = None)"* — the exact LAN-trust mode this plan repeatedly cites as the reason no RBAC exists. Under that mode every unclaim request has `actor_id=""`, so the ownership check added by this phase is a complete no-op — any staff (or any unauthenticated LAN caller) can unclaim any other rep's customer, exactly the gap Phase 2 exists to close. Requirement text ("Only `assignee_user_id == current_user.user_id` may unclaim; mismatch → 403") is contradicted by the spec'd code.
- **Evidence:** `crm/src/adapters/inbound/http/cf_access_middleware.py:1-4,164` (bypass sets `current_user=None`); `phase-01-authorization-service-foundation.md:46-48` (`is_owner` fails closed only if reached); `phase-02-unclaim-ownership-and-audit-trail.md:51` (the vulnerable gate); route handlers (`screen_worklist.py:527-538`, `screen_customer_360_panels.py:130-140`) confirmed to have **no** 401/uid-presence guard planned before calling unclaim, unlike the sibling claim handler `handle_c360_claim_customer` which does check `if not uid: return 401` (`screen_customer_360_panels.py:117-119`) — a precedent the plan cites for styling but not for this guard.
- **Suggested fix:** Drop the `actor_id and` prefix — always call `is_owner()` and let it fail closed on missing actor_id (it already does). Additionally add an explicit `if not uid: return 401` in both route handlers before calling `unclaim_customer_actions`, matching the claim-handler precedent the plan already references.

---

## Finding 2: `authz` required-constructor-param change will crash 9 test instantiations across 5 files not listed in either phase's file list — and contradicts the phase's own rollback claim

- **Severity:** Critical
- **Location:** Phase 2, "Related Code Files" + "Implementation Steps" step 2 (`phase-02...md:35,48`) vs. "Risk Assessment" (`phase-02...md:75`)
- **Flaw:** Phase 2 mandates `authz: AuthorizationService` as a **required, no-default** constructor param on `TaskService` ("deliberate deviation from this file's usual `Optional[...] = None` convention", step 2). Grep confirms `TaskService(...)` is instantiated in **9 places across 5 test files**, none of which appear anywhere in Phase 1's or Phase 2's "Related Code Files" sections (which list only `composition.py`):
  - `test_task_service_title_fallback.py:33`
  - `test_task_kind.py:155,231`
  - `test_task_claim_action_types_snapshot.py:49,67,80,113`
  - `test_claim_context_snooze_r14.py:71`
  - `test_activity_disposition_api_routes.py:134`
  None pass `authz`. Every one of these will raise `TypeError: __init__() missing 1 required positional argument: 'authz'` the moment Phase 2 lands, unless fixed as a byproduct — but the plan never asked anyone to touch these files.
- **Failure scenario:** Phase 2 is cooked, its own success criterion "Full CRM test suite green" (`phase-02...md:69`) is checked against a suite that was never updated for these 9 sites — the suite fails immediately at collection/execution, not from the new authz logic but from a signature break in unrelated pre-existing tests. This directly contradicts Phase 2's own Risk Assessment / Rollback line: *"Rollback: additive constructor param (defaults `None`, backward compatible)"* (`phase-02...md:75`) — that claim is **false** for `authz` (only true for `notes_repo`). The mis-classification of the change as "backward compatible" is almost certainly why the file list omitted these 9 sites — the risk section describes a safer change than the implementation steps actually specify.
- **Evidence:** `grep -n "TaskService(" crm/src -r` → 10 hits total (1 in composition.py, 9 in tests), verified above; `phase-02...md:48` ("required, no default"); `phase-02...md:75` ("defaults `None`, backward compatible").
- **Suggested fix:** Either (a) enumerate and update all 9 test call sites in Phase 2's file list, or (b) give `authz: Optional[AuthorizationService] = None` a default and fail closed inside the method (`if self._authz is None or not self._authz.is_owner(...): return "forbidden"`) — safer for an authz-critical class anyway, since it removes the temptation for the `if actor_id and ...` bypass pattern seen in Finding 1.

---

## Finding 3: Same required-param pattern breaks ~19 direct test call sites in `test_outcome_bulk_resolve.py`, not enumerated in Phase 3's file list

- **Severity:** High
- **Location:** Phase 3, "Related Code Files" (`phase-03-resolve-idor-fix.md:30-37`) vs. Implementation Steps 3-4
- **Flaw:** Phase 3 adds `party_id: str` and `authz: AuthorizationService` as **required** new params to `resolve_actions_and_tasks()`, and Phase 3's own step 6 says "Grep for any OTHER caller ... to confirm no other route/test needs updating beyond what's listed above" — phrased as a TODO for implementation time, not something already verified. Grepping now: `crm/src/tests/test_outcome_bulk_resolve.py` calls `_bulk_resolve(...)` directly **19 times** (lines 82-220) with the old signature (`action_ids, task_ids, action_state=, task_svc=, ...` — no `party_id`, no `authz`). This file is not in Phase 3's "Related Code Files" list.
- **Failure scenario:** Same as Finding 2 — Phase 3's success criterion "full existing bulk-resolve test suite still green" (`phase-03...md:55`) will fail immediately once `bulk_resolve`/`resolve_actions_and_tasks` require the new params, because this 19-call test file was never scheduled for update.
- **Evidence:** `grep -c "_bulk_resolve(" crm/src/tests/test_outcome_bulk_resolve.py` → 19; `crm/src/tests/test_activity_disposition_api_routes.py:451,463,477,498,514,529,543` also call `execute_side_effects(...)` directly (7 sites) — if the authz instance for `resolve_actions_and_tasks` ends up threaded onto `execute_side_effects`'s own signature (a plausible resolution of the ambiguity in Finding 5), these 7 sites break too and are equally absent from the file list.
- **Suggested fix:** Add `test_outcome_bulk_resolve.py` and `test_activity_disposition_api_routes.py` to Phase 3's Related Code Files, and decide the `execute_side_effects` signature question up front (see Finding 5) so the full blast radius is known before implementation starts.

---

## Finding 4: Audit-note write will silently no-op — repository/service layering mismatch, masked by the mandated try/except

- **Severity:** High
- **Location:** Phase 2, Architecture (`phase-02...md:31,37`) vs. Implementation Steps 3-4 (`phase-02...md:53,55`)
- **Flaw:** Phase 2's composition wiring plan is to inject `sqlite_repos["note"]` — the raw `SQLiteNoteRepository` — as `TaskService`'s `notes_repo`. That object satisfies `NoteRepository.add_note(self, note: Note) -> None` (`crm/src/domain/ports/tag_repository.py:98,101`, verified concrete impl at `crm/src/adapters/outbound/sqlite/tag_note_repository.py:302`) — it takes **one `Note` domain object**, not kwargs. But Implementation Step 3 (`phase-02...md:53`) specifies calling it as `self._notes_repo.add_note(...)` with `party_id=`, `body=`, `author_user_id=`, `note_type=`, `visibility=` — that kwarg shape only exists on `NoteService.add_note()` (`crm/src/application/note_service.py:30-56`, an application-layer wrapper that builds the `Note` entity, sets `note_id`/`created_at`, and calls the repo). If implemented literally against the raw repo, this call raises `TypeError: add_note() got an unexpected keyword argument 'party_id'`.
- **Failure scenario:** Step 3 also mandates wrapping the note write in "try/except-log (never let the audit-note write block the actual unclaim)". Combined with the signature mismatch above, every unclaim will **succeed** (state change happens) while the audit-note write **always throws and is silently swallowed** — the core Phase 2 requirement "A successful unclaim writes an audit note" (`phase-02...md:21`) is never actually met in production, and nothing in the test suite would catch it if tests mock `notes_repo` as a bare `MagicMock()` (which accepts any kwargs silently).
- **Evidence:** `crm/src/domain/ports/tag_repository.py:98-101`; `crm/src/adapters/outbound/sqlite/tag_note_repository.py:302`; `crm/src/application/note_service.py:30-39`; `phase-02...md:31` ("`TaskService` gains a constructor-injected `notes_repo`"), `:37` ("add `sqlite_repos[\"note\"]`"), `:53` (kwarg call shape). Note: the plan's own Risk Assessment (`phase-02...md:73`) already flags this as unresolved ("verify... whether `TaskService` should call a raw repository method or go through `NoteService`'s own validation") — this finding adds the concrete failure mode (silent swallow via the mandated try/except) that the plan doesn't spell out.
- **Suggested fix:** Inject a `NoteService` instance (or thread the repo but call `Note(...)` construction inline in `TaskService`) — resolve this before implementation, not during it, and add an explicit test asserting a real `Note` row is written (not just "no exception raised").

---

## Finding 5: Phase 2/3 "no file overlap, safe to run in parallel" claim depends on an unresolved design choice that, if resolved the way the plan prefers, causes a `composition.py` collision

- **Severity:** Medium
- **Location:** plan.md "Dependencies" (`plan.md:47`) vs. Phase 3 Implementation Step 4 (`phase-03...md:44`)
- **Flaw:** plan.md asserts: *"No file overlap between phases 2 and 3 ... safe to run in parallel once Phase 1 lands."* Phase 2 modifies `composition.py` to construct `AuthorizationService()` and wire it into `TaskService(...)` (`phase-02...md:37,55`). Phase 3's own step 4 says the `authz` instance needed inside `activity_side_effects.py` "needs to be either passed in from the caller chain (ultimately from wherever `execute_side_effects`/`resolve_actions_and_tasks` are invoked from a route handler, which should have DI access to the composition-wired instance) or instantiated inline ... **prefer threading from composition if straightforward**, fall back to inline construction only if it isn't." The stated preference is the one that touches `composition.py` again.
- **Failure scenario:** If two agents/sessions cook Phase 2 and Phase 3 concurrently (as the plan explicitly permits) and Phase 3's implementer follows the plan's stated preference ("thread from composition"), both phases edit `composition.py` in the same window — merge conflict or, worse, a silent overwrite if one branch is merged without rebasing on the other. The plan's blanket "no file overlap" claim is not actually guaranteed by anything in the phase specs; it's contingent on an implementation choice the plan itself nudges toward the collision-causing option.
- **Evidence:** `plan.md:47`; `phase-03-resolve-idor-fix.md:44` ("prefer threading from composition if straightforward").
- **Suggested fix:** Pin the design decision now (inline `AuthorizationService()` construction inside `activity_side_effects.py`, since the class is stateless — the plan itself says this is "cheap to construct on demand") rather than leaving it as a preference to be decided independently by whoever implements Phase 3, and update the plan text to remove the "prefer threading from composition" framing if going inline.

---

## Finding 6: Phase 4's risk analysis targets a caller that is already dead code — the "verify, don't assume" step wasn't actually performed against the codebase

- **Severity:** Medium
- **Location:** Phase 4, "Risk Assessment" (`phase-04-no-party-task-creation-fix.md:54`) and Implementation Step 4 (`phase-04...md:41`)
- **Flaw:** Phase 4's risk section hedges: *"if S07 Tasks Board's own page also happens to have a `worklistRefresh`-listening element (unlikely, but unverified)"* and step 4 says *"Grep for any OTHER existing caller of `POST /tasks` (S07 Tasks Board's own '+ Task' button, if separate from M05) ... verify, don't assume."* Tracing the actual flow: S07's "+ Tạo task" buttons (`tasks_board.html:27-33,85-90`) call `GET /tasks/modal/create`, whose handler (`screen_tasks_board.py:123-129`) renders `"fragments/modal_create_task.html"`. That template **does not exist anywhere in the repo** (`glob **/fragments/modal_*.html` and `grep -rn modal_create_task crm/` both confirm — only the Python reference exists, no `.html` file). Opening that modal today almost certainly raises `jinja2.TemplateNotFound` → 500. There is also **zero test coverage** for `handle_create_task`/`make_tasks_board_router` (`grep -rl handle_create_task crm/src/tests/` → no hits).
- **Failure scenario:** The plan's risk section reasons about protecting a "live" S07 caller that cannot currently be reached through the UI at all. This isn't a blocker for Phase 4's own changes (which are additive/optional-param-safe regardless), but it means: (a) the plan's stated verification step was written up without actually being executed, undermining confidence in other "verify at implementation time" deferrals in this same plan (there are several — Finding 4, Finding 5, and Phase 3's stale-cache risk all use this same "verify later" pattern); (b) if someone later fixes the missing template as a separate task, Phase 4's new `return_to`/field-forwarding logic on `/tasks` will suddenly get exercised by a second, previously-inert caller with no test coverage protecting it.
- **Evidence:** `crm/src/adapters/inbound/web/screen_tasks_board.py:123-129`; `crm/src/adapters/inbound/web/templates/tasks_board.html:27-33,85-90`; glob for `fragments/modal_create_task.html` → no match; grep `modal_create_task` across `crm/` → only the two Python references, no template.
- **Suggested fix:** Note the missing-template bug explicitly in the plan (even if out of scope) so it isn't rediscovered as a surprise later, and don't rely on "verify at implementation time" as the resolution mechanism for risks that determine whether a design decision (e.g. combining `closeModal`+`worklistRefresh` triggers) is safe — verify before finalizing the phase spec.

---

## Finding 7: Stale `TaskClaimWriter` Protocol left declaring the old `bool` return type

- **Severity:** Medium
- **Location:** Phase 2, "Related Code Files" (missing `screen_worklist.py:75-77`'s Protocol block)
- **Flaw:** `screen_worklist.py:75-77` declares:
  ```python
  class TaskClaimWriter(Protocol):
      def claim_customer_actions(self, party_id: str, actions: list, assignee_id: str) -> tuple: ...
      def unclaim_customer_actions(self, party_id: str) -> bool: ...
  ```
  This is the structural type used for the `task_claim` param threaded into `make_worklist_router`. Phase 2 changes `TaskService.unclaim_customer_actions`'s real signature and return type (`party_id`, `actor_id`, `reason` params; `str` return) but never mentions updating this Protocol declaration.
- **Failure scenario:** Python `Protocol` structural typing isn't enforced at runtime, so nothing crashes — but the type contract silently diverges from the real implementation. If this repo runs `mypy`/`pyright` in CI (worth confirming), this becomes a type-check failure; if not, it's stale documentation that will mislead the next person reading `screen_worklist.py` to believe `unclaim_customer_actions` still returns `bool` and takes only `party_id`.
- **Evidence:** `crm/src/adapters/inbound/web/screen_worklist.py:75-77`; absent from `phase-02-unclaim-ownership-and-audit-trail.md`'s "Related Code Files" list (`:33-43`).
- **Suggested fix:** Add this Protocol update to Phase 2's file list; update the signature to match the real `unclaim_customer_actions(party_id, actor_id=None, reason=None) -> str`.

---

## Flow Tracer Verification Results

### Trace 1 — Do BOTH unclaim route handlers get identical ownership behavior via `TaskService`?

**Traced path:**
- `PATCH /worklist/customers/{party_id}/unclaim` → `handle_unclaim_customer` (`screen_worklist.py:527-538`) → `task_claim.unclaim_customer_actions(party_id)` where `task_claim = services["task"]` (composition.py).
- `PATCH /customers/{party_id}/unclaim` → `handle_c360_unclaim_customer` (`screen_customer_360_panels.py:131-140`) → `task_svc.unclaim_customer_actions(party_id)` where `task_svc` is the **same** `services["task"]` singleton.

**Result:** CONFIRMED both routes delegate to the identical `TaskService` instance/method — the "single write path" claim structurally holds. However, current code (pre-Phase-2) discards the return value entirely on both sides (`try: task_claim.unclaim_customer_actions(party_id) except Exception: log.error(...)`, no result inspection, no return-on-exception — falls through to re-render regardless). Post-Phase-2, both routes are specified to add symmetric `result`-branching logic (steps 5-6) — this part is genuinely parity-safe **if** implemented as specified. The asymmetry that does exist: neither handler is spec'd to add a 401 guard for missing `uid` before calling unclaim (see Finding 1), despite the sibling claim handler (`screen_customer_360_panels.py:117-119`) already having that exact pattern available to copy. And because the ownership check itself is bypassed when `actor_id` is falsy (Finding 1), "identical behavior" in practice means both routes are **identically unprotected** under LAN-trust/no-CF-Access conditions, not identically protected.

### Trace 2 — Do BOTH resolve paths (`execute_side_effects` step 7 AND `/reason/resolve-async`) get the IDOR fix?

**Path A — `execute_side_effects` step 7:**
`_run_side_effects` closure (`screen_customer_360_activity.py:73-83`) → `execute_side_effects(activity, actor_id, party_id=activity.party_id, ...)` (`activity_side_effects.py:93`, `party_id: str` required kwarg) → step 7 internally (`activity_side_effects.py:246-249`) calls `resolve_actions_and_tasks(resolve_action_ids, remaining_task_ids, action_state, task_svc, contact_outcome, actor_id)`. `party_id` is in scope in the enclosing function (it's a parameter to `execute_side_effects` itself) and can be threaded into the internal call with no new plumbing needed outside `activity_side_effects.py`. **CONFIRMED** — plan's claim holds for this path.

**Path B — `/reason/resolve-async`:**
`handle_resolve_async(request, party_id: str, ...)` (`screen_customer_360_activity.py:417-431`, `party_id` is a route path param, in scope) → `_bulk_resolve(action_ids=..., task_ids=..., action_state=..., task_svc=..., actor_id=..., contact_outcome=...)` (`screen_customer_360_activity.py:478-485`) → `bulk_resolve()` (`outcome_resolve_helpers.py:21-67`) → `resolve_actions_and_tasks(...)` (`outcome_resolve_helpers.py:64-67`). **Current** `bulk_resolve()` signature does **not** accept `party_id` at all — it needs to be added and threaded through, which the plan correctly identifies as required work (not an already-solved gap). `party_id` is available at the call site (`screen_customer_360_activity.py:478`) as a pure pass-through. **CONFIRMED** — plan's claim holds for this path too, and correctly scopes the work needed.

**Gap found (see Finding 3):** both paths' *test* call sites (`test_outcome_bulk_resolve.py`, 19 direct calls; `test_activity_disposition_api_routes.py`, 7 direct `execute_side_effects()` calls) are not enumerated in Phase 3's file list and will break once the new required params land.

### Trace 3 — Will the `/tasks` `return_to=stay` change affect S07 Tasks Board's existing usage?

**Traced path:** Searched all templates for `hx-post="/tasks"` or equivalent — none found. The only form posting to `/customers/{party_id}/tasks` is M05 (`modal_m05_create_task.html:43`), which Phase 4 changes to conditionally target `/tasks` only when `party_id` is empty. S07's own "+ Tạo task" / "+ Tạo task mới" buttons (`tasks_board.html:27-33,85-90`) instead `hx-get="/tasks/modal/create"`, rendering `screen_tasks_board.py:123-129`'s `"fragments/modal_create_task.html"`.

**FAILED (in the sense of: the assumed live flow doesn't exist) — actual flow found:** `fragments/modal_create_task.html` does not exist in `crm/src/adapters/inbound/web/templates/` (confirmed via `Glob **/fragments/modal_*.html` — 9 hits, none named `modal_create_task.html` — and `grep -rn modal_create_task crm/` — only the two Python references in `screen_tasks_board.py`, no template file). S07's own task-creation entry point is dead/broken code today; `POST /tasks` (`screen_tasks_board.py:131-163`) currently has **no reachable UI caller** and **no test coverage**. The plan's risk framing ("if S07 Tasks Board's own page also happens to have a `worklistRefresh`-listening element... unverified") is answered trivially (no such listener exists in `tasks_board.html`), but the underlying assumption that this is a protected live flow is false — see Finding 6.

---

## Unresolved Questions

1. Does this repo run `mypy`/`pyright` in CI? If yes, Finding 7's stale `Protocol` becomes a build-blocking issue, not just documentation drift — worth confirming before Phase 2 starts.
2. Should `AuthorizationService` be threaded via DI at all for a stateless, zero-IO class, or is inline `AuthorizationService()` construction at every call site (Phase 1's own stated fallback) simply the right default — avoiding both the `composition.py` collision (Finding 5) and the required-param test breakage (Findings 2, 3) in one move?
3. Is there a decision-owner sign-off needed on Finding 1 (the `actor_id`-truthy bypass) before this ships as "closes an IDOR-shaped gap" — as specified, Phase 2 does not close the gap under the LAN-trust deployment mode this codebase is documented to run in.
