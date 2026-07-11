# Red-Team Security Review — Authz Hardening + Post-P0 Fixes Plan

Reviewer role: Security Adversary + Fact Checker
Plan: `plans/260711-1227-authz-hardening-post-p0-fixes/plan.md` + phases 1-5 + research/researcher-01, researcher-02

Posture: attacker-mindset review of a plan that fixes 2 IDOR-shaped gaps by introducing a new `AuthorizationService`. All findings are grep/read-verified against the current `crm/src` tree, not the plan's own claims.

---

## Finding 1: Phase 2's ownership guard is fail-OPEN, not fail-closed, when `actor_id` is empty

- **Severity:** Critical
- **Location:** Phase 2, section "Implementation Steps", step 3
- **Flaw:** The prescribed guard is:
  > "If `actor_id` and not `self._authz.is_owner(existing.assignee_user_id, actor_id)` → return `"forbidden"`"

  This is `if actor_id and not is_owner(...)`. When `actor_id` is falsy (`None` or `""`), the whole boolean expression short-circuits to `False` — the `"forbidden"` branch is **never entered**, and execution falls straight through to "Proceed with existing cancel logic". The unclaim succeeds with **zero ownership check** whenever the caller's `actor_id` is empty.
- **Failure scenario:** `_current_user_id(request)` (the function this phase's own route-handler step reuses, `screen_worklist.py:321-323`) returns `""` whenever `request.state.current_user` is `None` — i.e. whenever auth middleware fails to populate the user (misconfigured proxy, session desync, or a request that bypasses the LAN-trust middleware). Any such request to `PATCH /worklist/customers/{party_id}/unclaim` or `PATCH /customers/{party_id}/unclaim` with `reason=<any valid reason>` and no authenticated session unclaims **any** customer's claim — precisely reproducing the original vulnerability this phase exists to close. Contrast with this same file's own established convention for exactly this situation — `handle_assign_me` at `screen_worklist.py` (~line 442, cited directly by this same phase file at step 5) does `if not uid: return 401` before proceeding. Phase 2 does not apply that pattern here.
- **Evidence:** Phase 2 file, Implementation Steps step 3, literal quoted text above. `AuthorizationService.is_owner()` itself (Phase 1, `authorization_service.py:46-48`) is correctly fail-closed (`if not actor_id or not resource_assignee_id: return False`) — the bug is entirely in how Phase 2 *calls* it, not in Phase 1's service. Also: Phase 2's own Success Criteria only specifies a test for "2 different actor_ids" (mismatched-but-both-present) — there is no planned test case for `actor_id=""`/`None`, so this regression would ship without being caught by the phase's own test plan.
- **Suggested fix:** Change the guard to unconditionally require a valid actor and ownership match: `if not actor_id or not self._authz.is_owner(existing.assignee_user_id, actor_id): return "forbidden"`. Add a test case: `actor_id=""` → `"forbidden"`, no state change.

---

## Finding 2: Phase 3's IDOR fix leaves a sibling code path — `complete_task_ids` — completely unguarded, in the same file, same function, 10 lines away

- **Severity:** Critical
- **Location:** Phase 3, "Overview"/"Requirements" (scoped only to `resolve_action_ids`/`resolve_task_ids` via `resolve_actions_and_tasks()`)
- **Flaw:** `execute_side_effects()` in `crm/src/application/activity_side_effects.py` has TWO independent code paths that call `task_svc.transition_status(tid, "done")` on client-supplied ids with no ownership/party check:
  - **Step 6** ("Complete linked task(s)", lines 230-236): iterates `complete_task_ids` directly — `for tid in complete_task_ids: task_svc.transition_status(tid, "done")`. No party check, no `AuthorizationService` involvement anywhere in the plan.
  - **Step 7** (lines 238-249): calls `resolve_actions_and_tasks()` — the ONLY path Phase 3 patches.

  Both paths call the identical `task_svc.transition_status(tid, "done")` with zero ownership validation (`TaskService.transition_status`, `task_service.py:175-199`, has no owner/party check of its own — verified). Phase 3's plan text literally describes the vulnerability as belonging to `resolve_actions_and_tasks()` "extracted from `execute_side_effects` step 7" — but ignores step 6 sitting right above it in the same function.
- **Failure scenario:** `complete_task_ids` is client-controlled via `POST /api/activities/{activity_id}/finalize`'s `complete_task_ids: str = Form(default="")` param (`screen_customer_360_activity.py:706`, parsed via `_parse_id_list` at line 748) and via `POST /customers/{party_id}/log-activity`'s `task_id`/`complete_task` Form params (lines 261-262, built into `complete_task_ids = [task_id.strip()]` at line 372). An attacker who can finalize/log ANY activity (their own, on a party they legitimately have access to) can supply an arbitrary `complete_task_ids` value pointing at another customer's or another staff member's task and force it to `"done"` — with no cross-party check anywhere in the call chain (`finalize_activity()` in `activity_service.py:332` only validates `activity_id`/`contact_outcome` state, never touches `complete_task_ids`). This is the exact same IDOR class Phase 3 claims to close, left open in a path the plan's own "Grep for any OTHER caller of `resolve_actions_and_tasks`/`bulk_resolve`" step (Phase 3, Implementation Step 6) would NOT catch, because `complete_task_ids` never calls `resolve_actions_and_tasks` — it's an entirely separate branch inside `execute_side_effects()`.
- **Evidence:** `crm/src/application/activity_side_effects.py:230-236` (step 6, unguarded); `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py:706,748` and `:261-262,372` (client-supplied entry points); `crm/src/application/task_service.py:175-199` (`transition_status` has no ownership check).
- **Suggested fix:** Apply the same `authz.is_same_party(task_svc.get_task(tid).party_id, party_id)` guard to step 6's loop that Phase 3 adds to step 7, inside the same `execute_side_effects()` edit.

---

## Finding 3: A structurally identical, unaddressed IDOR exists in `screen_customer_360_tasks.py` — `party_id` is in the URL but never checked against the task

- **Severity:** Critical
- **Location:** Not covered by any phase — scope gap in Phase 3 (and the underlying research report never surfaced it)
- **Flaw:** `PATCH /customers/{party_id}/tasks/{task_id}/done`, `PATCH /customers/{party_id}/tasks/{task_id}/cancel`, and `PATCH /customers/{party_id}/tasks/{task_id}/postpone` all take `party_id` as a URL path segment but call `task_svc.transition_status(task_id, ...)` / `task_svc.get_task(task_id)` / `task_svc.update_task(task_id, ...)` using ONLY `task_id` — `party_id` is read into the handler but never cross-checked against the task's actual `party_id` before mutating it.
- **Failure scenario:** Any staff viewing customer A's C360 page (`party_id=A`) can submit `PATCH /customers/A/tasks/{B's task_id}/done` (or `/cancel`, or `/postpone`) using a `task_id` belonging to a completely different customer B — the mutation succeeds because the handler never resolves or compares `task_id`'s real owner/party. `task_id` values are visible in rendered HTML across the app (worklist rows, task board, other C360 panels), so guessing/harvesting a foreign `task_id` requires no more effort than viewing another page.
- **Evidence:** `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_tasks.py:59-67` (`handle_task_done_c360`), `:71-79` (`handle_task_cancel_c360`), `:83-108` (`handle_task_postpone_c360`) — all three read `party_id` as a parameter and never use it in the mutation call.
- **Suggested fix:** This is the exact shape of check `AuthorizationService.is_same_party()` (Phase 1) is designed for — this file should be added to Phase 3's scope (or a new Phase) before this plan can claim to have closed "the" resolve-actions IDOR class, since this is a second, live instance of it.

---

## Finding 4: Phase 2's "required, no default" `authz` param breaks 7+ existing `TaskService(...)` call sites the plan never lists

- **Severity:** High
- **Location:** Phase 2, "Implementation Steps" step 2 ("`authz: AuthorizationService` — **required, no default**") and "Related Code Files" (lists only `composition.py`)
- **Flaw:** `TaskService.__init__` currently has 4 params, only 2 required (`task_repo`, `cache_repo`; `db`/`party_repo` optional) — verified at `task_service.py:64-74`. The plan adds `authz: AuthorizationService` as a 5th, **required**, parameter. Grepping `TaskService(` across the repo finds 8 total instantiation sites; only 1 (`composition.py:328`) is listed as a file the plan will modify:
  - `crm/src/tests/test_task_service_title_fallback.py:33` — `TaskService(task_repo, cache_repo, db=None, party_repo=party_repo)`
  - `crm/src/tests/test_task_kind.py:155,231` — `TaskService(task_repo, cache_repo, db=None)`
  - `crm/src/tests/test_task_claim_action_types_snapshot.py:49,67,80,113` — same pattern
  - `crm/src/tests/test_claim_context_snooze_r14.py:71` — same pattern
  - `crm/src/tests/test_activity_disposition_api_routes.py:134` — `TaskService(task_repo, MagicMock(), db=db)`

  None of these pass `authz` (or `notes_repo`). If `authz` truly has no default, all 7 files fail at test-collection/instantiation time with `TypeError: missing 1 required positional argument: 'authz'`.
- **Failure scenario:** Two possible outcomes, both bad: (a) Phase 2 ships and the "Full CRM test suite green" success criterion is immediately false because these 7 files are never updated (they aren't in the plan's file list, so a literal implementation misses them) — a real risk given the plan is executed phase-by-phase; or (b) an implementer notices the breakage and "fixes" it by making `authz: Optional[AuthorizationService] = None` to unblock the tests quickly, silently defeating the "no silent-skip failure mode" design goal Phase 1/2 explicitly call out as the reason `authz` must be required. This is precisely the failure mode the review brief asked to check for.
- **Evidence:** grep results above; `crm/src/application/task_service.py:64-74` (current constructor, no `authz`/`notes_repo` params exist yet).
- **Suggested fix:** Add all 7 test files to Phase 2's "Related Code Files" list with an explicit instruction to pass a real or mock `AuthorizationService()` at each call site, and add a CI-visible check (or at minimum an explicit implementation step) that greps for `TaskService(` before considering Phase 2 done.

---

## Finding 5: `notes_repo` wiring calls the wrong layer — the audit-note write (the compensating control Phase 2's whole policy rests on) will silently no-op

- **Severity:** High
- **Location:** Phase 2, "Related Code Files" (`composition.py`) + "Implementation Steps" step 4 vs. step 3
- **Flaw:** Step 4 wires `TaskService`'s new `notes_repo` param to `sqlite_repos["note"]`, i.e. the raw adapter `SQLiteNoteRepository` (`composition.py:248`). That adapter satisfies `NoteRepository` (`domain/ports/tag_repository.py:98-107`), whose `add_note` signature is:
  ```python
  def add_note(self, note: Note) -> None: ...   # takes ONE Note object
  ```
  But step 3 instructs calling it as `self._notes_repo.add_note(...)` with `NoteService`-shaped kwargs (`party_id`, `body`, `author_user_id`, `note_type`, `visibility` — the signature of `NoteService.add_note`, `note_service.py:30-39`, which itself builds the `Note` object with a fresh `note_id`/`created_at` before delegating to the raw repo, `note_service.py:42-53`). Calling the raw repo's `add_note` with those kwargs raises `TypeError` every time.
- **Failure scenario:** Per step 3's own instruction, this call is "Wrap[ped] in try/except-log (never let the audit-note write block the actual unclaim...)". That means the `TypeError` from the signature mismatch is caught and logged, and the unclaim proceeds successfully with **no audit note ever written** — every single time, in production, silently. This defeats the entire policy rationale stated in the plan's Overview: "do NOT block the unclaim action outright... require an ownership check PLUS a mandatory reason + audit note ... matches industry practice for claim/drop queues: visibility over hard gating." If the audit note never writes, there is no visibility — the compensating control for the deliberately-not-hard-gated policy is dead on arrival, and nothing in the stated Success Criteria would catch it (criterion "`crm_note` row written with correct `party_id`/`author_user_id`/`note_type`" is listed, but only as a manual/functional check — if implementers wire a `MagicMock()`/stub in tests rather than the real `SQLiteNoteRepository`, this mismatch will not surface in CI either).
- **Evidence:** `crm/src/domain/ports/tag_repository.py:98-107`; `crm/src/application/note_service.py:30-56`; `crm/src/composition.py:248` (`"note": SQLiteNoteRepository(db)`). The plan itself flags this exact ambiguity in its own Risk Assessment ("wasn't 100% pinned during research... check for double-validation or layering concerns at implementation time") but Implementation Step 4 already commits to the wrong wiring (`sqlite_repos["note"]`, the raw repo) while step 3 already commits to the `NoteService`-shaped call — the two steps are internally inconsistent as written.
- **Suggested fix:** Wire `TaskService`'s new dependency to a `NoteService` instance (`services["note"]`, already constructed at `composition.py:323`), not the raw `sqlite_repos["note"]` repo, and call `self._notes_svc.add_note(party_id, body, author_user_id=actor_id, note_type="unclaim_reason", visibility="team")` matching `NoteService.add_note`'s real signature. Add an integration test (not a MagicMock-only unit test) that asserts a `crm_note` row is actually persisted after a successful unclaim.

---

## Finding 6: Stale `TaskClaimWriter` Protocol left with the old `bool` return type

- **Severity:** Medium
- **Location:** Phase 2, "Architecture" (return-type change `bool` → `str`) — "Related Code Files" omits this symbol
- **Flaw:** `screen_worklist.py:77` defines `class TaskClaimWriter(Protocol): def unclaim_customer_actions(self, party_id: str) -> bool: ...` — the structural type that `task_claim: Optional[TaskClaimWriter]` (the param `make_worklist_router` accepts) is checked against. Phase 2 changes `TaskService.unclaim_customer_actions`'s real return type to a 3-state string (`"ok"|"not_found"|"forbidden"`) and changes its signature to accept `actor_id`/`reason`, but this Protocol definition is not listed anywhere in Phase 2's "Related Code Files" and none of the 9 implementation steps mention it.
- **Failure scenario:** Not a runtime crash (`Protocol` classes are structural/duck-typed, not enforced at call time in plain Python), but it is a stale, misleading type contract: any type-checker run against this file (mypy/pyright, if this repo runs one in CI) would flag the mismatch, and any future maintainer reading `TaskClaimWriter` to understand what `task_claim.unclaim_customer_actions()` returns would be misled into writing `if result:` (truthy) checks — which the plan's own Phase 2 Risk Assessment explicitly warns against ("a non-empty string is always truthy, so `not_found`/`forbidden`/`ok` would all pass a bare truthiness check").
- **Evidence:** `crm/src/adapters/inbound/web/screen_worklist.py:77`.
- **Suggested fix:** Add `screen_worklist.py:77`'s `TaskClaimWriter` Protocol to Phase 2's file list; update its return type and signature to match.

---

## Finding 7: Phase 1's "wired once in composition.py" DI promise cannot be honored for `resolve_actions_and_tasks()` as the file list is currently scoped

- **Severity:** Medium
- **Location:** Phase 1 "Requirements" ("Wired once in `composition.py`... param injection for plain functions like `resolve_actions_and_tasks`") vs. Phase 3 "Related Code Files"
- **Flaw:** `resolve_actions_and_tasks()` is called from two places, neither of which has direct composition.py access:
  1. Inside `execute_side_effects()` (`activity_side_effects.py:246-249`) — a pure application-layer function with no `authz` in its own parameter list (Phase 3 doesn't list `execute_side_effects()`'s own signature as something to modify, only `resolve_actions_and_tasks()`'s).
  2. Inside `outcome_resolve_helpers.bulk_resolve()` (`outcome_resolve_helpers.py:21-67`), invoked via a bare-import alias `_bulk_resolve` inside `register_activity_routes()` (`screen_customer_360_activity.py:22-24,478`) — whose factory signature (`profile, identities, notes, activity_log, task_svc, app_users, action_state, party_insights`) has no `authz` slot and is not listed as a Phase 3 modify target.

  Phase 3's own Implementation Step 4 acknowledges this and offers an escape hatch ("instantiated inline... prefer threading from composition if straightforward, fall back to inline construction only if it isn't") — but given neither `execute_side_effects()` nor `register_activity_routes()` is in the file list, the realistic implementation outcome is 2 separate `AuthorizationService()` inline constructions, not the single composition-wired instance Phase 1's Requirements promise.
- **Failure scenario:** Not a security defect on its own (the class is stateless, so two instances behave identically) — but it is a plan-accuracy defect: Phase 1's stated architecture goal ("single source of truth"/"wired once") will not be what actually ships, and no phase file's Success Criteria would catch the discrepancy since neither lists a check for "only one `AuthorizationService()` construction exists in the codebase."
- **Evidence:** `crm/src/application/activity_side_effects.py:44-51,93-112,246-249`; `crm/src/adapters/inbound/web/screens/customer360/outcome_resolve_helpers.py:21-29`; `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py:22-24,60-70,478-485`.
- **Suggested fix:** Either add `execute_side_effects()`'s and `register_activity_routes()`'s signatures to Phase 3's file list with an explicit `authz` param, or update Phase 1's Requirements to say plainly "inline construction is the expected outcome for the `resolve_actions_and_tasks` consumers, not composition-wired DI" so the plan doesn't over-promise.

---

## Fact Checker Verification Results

| # | Claim | Result |
|---|---|---|
| 1 | `screen_worklist.py:527` `handle_unclaim_customer`, `PATCH /worklist/customers/{party_id}/unclaim` | VERIFIED (screen_worklist.py:526-527) |
| 2 | `screen_customer_360_panels.py:131` `handle_c360_unclaim_customer`, `PATCH /customers/{party_id}/unclaim` | VERIFIED (screen_customer_360_panels.py:130-131) |
| 3 | `TaskService.unclaim_customer_actions(self, party_id: str) -> bool` — current signature, no ownership check | VERIFIED (task_service.py:297-307) |
| 4 | `app_user.py:13-39` role constants + "auth deferred" comment at 28-29 | VERIFIED (app_user.py:13,17,28) |
| 5 | `activity_side_effects.py:44-51` `resolve_actions_and_tasks` signature | VERIFIED (lines 44-51 match exactly) |
| 6 | `action_state_repository.py:81-118` `_resolve_party_and_action_type` (private, cache-join) | VERIFIED (line 81 confirmed; also called internally at line 63) |
| 7 | `action_state_port.py:7-20` — `dismiss`/`snooze`/`reopen` only, no `resolve_party_id` | VERIFIED (7,10,14,18) |
| 8 | `composition.py:328` `TaskService(sqlite_repos["task"], sqlite_repos["cache"], db, sqlite_repos["party"])` | VERIFIED (exact match, line 328) |
| 9 | `composition.py:248` `"note": SQLiteNoteRepository(db)` | VERIFIED (line 248) |
| 10 | `note_service.py:30-56` `add_note` signature (`party_id, body, author_user_id=..., note_type=..., ...`) | VERIFIED (lines 30-56) |
| 11 | `domain/ports/tag_repository.py` `NoteRepository` Protocol — plan cites it as "oddly named" | VERIFIED — `class NoteRepository(Protocol)` at tag_repository.py:98, `add_note(self, note: Note) -> None` at line 101 — confirms the signature mismatch in Finding 5 |
| 12 | `task_service.py:122` `task_data.get("priority", 0)` | VERIFIED (line 122 exact) |
| 13 | `screen_tasks_board.py:131-163` `handle_create_task` — 5 Form params, hardcoded `HX-Redirect: /tasks`, no `return_to` handling | VERIFIED (lines 131-163, matches research report verbatim) |
| 14 | `screen_modal_task.py:190-192` `return_to` pattern in `post_task` | VERIFIED but with a nuance — actual code sends `HX-Trigger: '{"worklistRefresh": true}'` only (no `closeModal`); Phase 4 explicitly deviates by combining `closeModal`+`worklistRefresh` for `/tasks`, self-flagged as a deliberate choice, not a factual error |
| 15 | `worklist.html:26` button `hx-get="/modals/m05?return_to=stay"`, no `party_id` | VERIFIED (lines 24-29) |
| 16 | `task_kind.py:49-51` "Rule 1: no customer party → generic, confident=True" | UNVERIFIED — function signature confirmed at task_kind.py:28-33 but rule text at lines 49-51 not read in this pass; low risk, not security-relevant |
| 17 | `test_quick_outcome_cockpit_post.py:28-49,121-140` handler-recovery + invocation pattern | VERIFIED (`_get_log_activity_handler` at line 28; `HX-Redirect not in response.headers` assertions at 134-135,158,325,367,403) |
| 18 | `crm/src/tests/test_modal_task_return_to.py` does not yet exist (Phase 5 creates it) | VERIFIED — no matches found |
| 19 | `domain/entities/task.py:76` `party_id: Optional[str] = None` | VERIFIED (line 76 exact) |
| 20 | `activity.py:60-78` `VALID_OUTCOME_REASONS`, `:80` `REASON_REQUIRED_OUTCOMES = {"refused"}` | VERIFIED (lines 60, 80) |

No sampled claim FAILED outright. All file:line citations across both research reports and all 5 phase files that I sampled resolve to real code at (or very near) the cited locations — the plan's factual grounding in the codebase is solid. The defects found are in the *proposed logic* (Findings 1-5) and *scope completeness* (Findings 2, 3, 4, 6, 7), not in misremembered file paths or symbols.

---

## Summary

The plan's factual research is accurate (all 20 sampled citations verified), but three of the findings are Critical: Phase 2's own prescribed ownership-check pseudocode is fail-open on missing `actor_id` (Finding 1), and Phase 3's IDOR fix is scoped too narrowly — it patches `resolve_actions_and_tasks()` but leaves an identical unguarded `task_svc.transition_status()` call 10 lines above it in the same function (Finding 2), plus a second live IDOR instance in an entirely different file the plan never touches (Finding 3). Two High findings show the plan's own "Related Code Files" lists are incomplete in ways that would either break the existing test suite or silently defeat the audit-trail control that is the stated justification for not hard-blocking unclaim (Findings 4, 5). None of these are caught by the plan's own stated Success Criteria as written.
