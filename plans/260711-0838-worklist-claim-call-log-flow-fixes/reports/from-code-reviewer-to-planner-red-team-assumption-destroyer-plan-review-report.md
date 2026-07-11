# Red-Team / Assumption-Destroyer Review — Worklist-Claim-Call-Log Flow Fixes Plan

Reviewer role: Scope Auditor (state-lifetime verification) + general assumption destroyer.
Scope: `plan.md` + all 7 `phase-*.md` files in `plans/260711-0838-worklist-claim-call-log-flow-fixes/`.
Method: every finding below is grep/read-verified against the live codebase at `D:\Vantt\app\data-integration\crm\src`, not inferred from the plan text.

---

## Finding 1: Phase 1 reactivates a retired, dead UI code path — wiring will ship a broken confirmation fragment

- **Severity:** Critical
- **Location:** Phase 1, section "Overview" + Implementation Step 8 ("M08 POST handler")
- **Flaw:** The plan treats `screen_customer_360_activity.py:375`'s `if source.strip() == "call_cockpit":` branch as safe, structurally-sound dead code that merely needs a template to start setting `source`. In reality this branch is a leftover from a UI generation ("static outcome_bar + `s14OpenOutcome`") that a **later, already-shipped plan (phase-03 disposition strip v2, commit `89d10c67`)** explicitly tore out and added a regression test forbidding its reappearance.
- **Failure scenario:** Phase 1 wires `source=call_cockpit` into the M08 GET (`_m08_ctx`) → hidden form field → POST, for the cockpit's M08 fallback call sites (idbar Zalo button, `s14StripStartCall`'s catch-fallback, `s14StripOpenManual`). Once reachable, `handle_log_activity` returns:
  ```
  '<div class="s14-outcome__done">...<button ... onclick="s14OpenOutcome(\'...\')">Hoàn tác</button></div>'
  ```
  `s14OpenOutcome` does not exist anywhere in the current template — `crm/src/tests/test_disposition_strip_v2.py::TestOldOutcomeBarFullyRemoved::test_old_identifiers_gone_from_template` (lines 294-306) asserts `"s14OpenOutcome("` is **absent** from `c360_call_cockpit_panel.html`, and grep confirms zero matches for `s14OpenOutcome` in any template file. Clicking "Hoàn tác" throws a `ReferenceError` in the browser console — silent failure, undo button dead. Additionally, `modal_log_activity.html:110`'s form uses `hx-target="#modal-root" hx-swap="innerHTML"` unconditionally — this tiny confirmation fragment would replace the entire modal shell (scrim, close button, everything) with a bare orphaned div, not integrate into the disposition-strip's own DOM the way the code comment ("outcome bar stays in place") implies. There is no `#modal-root`-scoped element in the strip's actual DOM designed to receive this fragment.
- **Evidence:**
  - `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py:375-385` — the branch, including the `s14OpenOutcome(...)` onclick.
  - `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html:801-808` — code comment: *"DISPOSITION STRIP v2 ... replaces the old static outcome_bar + s14OpenOutcome (M08-per-click) ENTIRELY, no dual code path kept."*
  - `crm/src/tests/test_disposition_strip_v2.py:14-17, 294-306` — regression test asserting `s14OpenOutcome(` is gone from the template; docstring: *"Old outcome_bar markup/JS ... is fully gone from the template."*
  - `crm/src/tests/test_quick_outcome_cockpit_post.py:1-4, 92-111` — a **stale, orphaned test** from the earlier "phase-01 (activity-log disposition API, P0)" plan that still asserts the handler returns `s14-outcome__done`/`Hoàn tác` — it tests the handler function directly (mock-closure pattern), never renders the fragment inside a real DOM, so it will keep passing green even though the feature it validates is unreachable/broken by design today and would ship broken if Phase 1 makes it reachable.
  - `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html:110` — `hx-target="#modal-root" hx-swap="innerHTML"` (unconditional, no branch for a "small fragment stays in place" mode).
- **Suggested fix:** Do not resurrect the `call_cockpit` branch. Either (a) delete it and the stale `test_quick_outcome_cockpit_post.py` as part of this plan (they're dead-code remnants of the pre-disposition-strip-v2 design), or (b) if a "no redirect" response is still wanted for the cockpit's M08 fallback paths, return a genuinely empty body (matching what Phase 1 already does for `source=worklist`) instead of the `s14-outcome__done`/`s14OpenOutcome` fragment.

---

## Finding 2: One of Phase 1's "4 M08 fallback call sites" doesn't route through the branch being fixed at all

- **Severity:** High
- **Location:** Phase 1, "Related Code Files" (`c360_call_cockpit_panel.html` M08 fallback call sites) and Implementation Step 9
- **Flaw:** The plan lists `c360_call_cockpit_panel.html:256,1075,1081,1088` as 4 uniform call sites needing `&source=call_cockpit` appended. Line 1088 is `s14StripOpenDetail()`, which opens M08 in `mode=edit_activity`.
- **Failure scenario:** `modal_log_activity.html:30` sets, for `edit_activity` mode: `save_url = '/api/activities/' ~ activity_id`, `http_verb = 'patch'` — i.e. the form PATCHes `/api/activities/{activity_id}` (`screen_customer_360_activity.py:533`, `handle_patch_activity`), a completely different route from `POST /customers/{party_id}/log-activity` where the `source` gate lives. Appending `&source=call_cockpit` to the GET call at line 1088 threads a hidden `source` field into a form that never posts to the endpoint that reads it — the change is inert for this call site, and the plan's "4 call sites, uniform fix" framing overstates completeness.
- **Evidence:** `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html:1085-1091` (`s14StripOpenDetail`); `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html:28-31` (mode→verb/url branching).
- **Suggested fix:** Drop line 1088 from the "add `&source=call_cockpit`" list, or explicitly scope Phase 1's requirement to `mode=log` M08 opens only.

---

## Finding 3: Phase 3's stated goal ("S15 provenance đúng") is not achieved — the S15 template still shows "thủ công" for the new sources

- **Severity:** High
- **Location:** Phase 3, "Overview" (fix note quoted from report: *"source callback/followup thay vì manual để S15 provenance đúng"*) and "Related Code Files"
- **Flaw:** Phase 3 changes the persisted `source` value on auto-created callback/follow-up tasks from `"manual"` to `"callback"`/`"followup"`, explicitly to fix S15's provenance display. But the S15 "Xuất xứ" (provenance) label in `task_detail.html` only special-cases two values and defaults everything else — including the new ones — to the Vietnamese label for "manual":
  ```jinja
  {% if task.source == 'action_queue_claim' %}action_queue (gộp claim)
  {% elif task.source == 'action_queue' %}action_queue
  {% else %}thủ công{% endif %}
  ```
  `task_detail.html` is **not** in Phase 3's "Related Code Files" list.
- **Failure scenario:** After Phase 3 ships, a callback/follow-up task's DB row correctly has `source='callback'`/`'followup'`, but S15 still renders "Nguồn: thủ công" — visually indistinguishable from a genuinely staff-typed manual task. The very UI symptom the finding cites as motivation ("S15 provenance đúng") is unchanged. Success criteria in Phase 3 only check the DB field, not the S15 render, so this gap would pass all listed success criteria while leaving the report's stated problem unsolved.
- **Evidence:** `crm/src/adapters/inbound/web/templates/fragments/task_detail.html:257-263`.
- **Suggested fix:** Add `task_detail.html` to Phase 3's Related Code Files and extend the provenance branch with `callback`/`followup` cases (e.g. "gọi lại (tự động)" / "theo dõi (tự động)").

---

## Finding 4: New `TASK_SOURCE_CALLBACK`/`TASK_SOURCE_FOLLOWUP` constants are dead on arrival — nothing imports or validates against them

- **Severity:** Medium
- **Location:** Phase 3, Requirements bullet 3 and Implementation Steps 1-2
- **Flaw:** Plan adds two new constants to `domain/entities/task.py` and extends `VALID_TASK_SOURCES`, framed as necessary plumbing. Verified via grep across `crm/src`: `VALID_TASK_SOURCES` has exactly one producer (its own definition in `task.py:39`) and one re-export (`domain/entities/__init__.py:69`) — **zero consumers** anywhere that validate a source string against it. Separately, `activity_side_effects.py` (the file Phase 3 actually edits) currently writes `"source": "manual"` as a **raw string literal**, not via `TASK_SOURCE_MANUAL` — and Phase 3's own implementation steps say to change it to the raw string `"source": "callback"` / `"source": "followup"`, never mentioning importing the new constants at the call site.
- **Failure scenario:** Not a runtime bug, but the plan claims "New `TASK_SOURCE_CALLBACK`/`TASK_SOURCE_FOLLOWUP` constants must be added ... and included in `VALID_TASK_SOURCES`" as a requirement without ever using them — inert code addition that looks load-bearing but isn't, and drifts further from the file's own established raw-string convention.
- **Evidence:** grep for `VALID_TASK_SOURCES` (2 hits total, both definition/re-export, `crm/src/domain/entities/task.py:39`, `crm/src/domain/entities/__init__.py:69,174`); grep for `"source": "manual"` in `activity_side_effects.py:136,150` (raw string, no import of `TASK_SOURCE_MANUAL`).
- **Suggested fix:** Either drop the constant addition (match the file's existing raw-string convention, since nothing enforces `VALID_TASK_SOURCES`) or actually import and use them at the call site for internal consistency — don't add unused exports.

---

## Finding 5: Phase 1 and Phase 5 both rewrite the same 4 lines of `_wl_row.html`'s `contact_btn` macro — conflict not listed in plan.md's Dependencies audit

- **Severity:** Medium
- **Location:** plan.md, "Dependencies" section; Phase 1 Related Code Files; Phase 5 (5a) Related Code Files
- **Flaw:** `plan.md`'s Dependencies section explicitly calls out two cross-phase file collisions ("phases 2 and 4 both touch `c360_call_cockpit_panel.html`"; "phases 2 and 3 both touch `activity_side_effects.py`") as the reason phases must run sequentially. It misses a third: Phase 1 step 10 changes `_wl_row.html`'s `contact_btn` macro at lines `~30/35/40/45` to append `&source=worklist`, and Phase 5a (`_wl_row.html` `contact_btn` macro `~30-46`) changes the SAME 4 call sites' `channel=` param to `hinh_thuc=`. Both phases edit the exact same 4 lines in the exact same macro.
- **Failure scenario:** Sequential execution (as the plan mandates) avoids a literal git conflict, but the plan's own "which phases touch which files" risk audit is demonstrably incomplete — an implementer skimming only the Dependencies section (not full cross-referencing all 7 phase files) would not know Phase 5 must re-touch lines Phase 1 already edited, risking one phase's edit being silently reverted/overwritten if done out of documented order or by different sub-agents in a parallel/team session.
- **Evidence:** `plan.md:53-57` (Dependencies, lists only 2 pairs); Phase 1 file `phase-01-redirect-context-loss-fix.md:38` (`_wl_row.html` contact_btn 4 call sites, `&source=worklist`); Phase 5 file `phase-05-medium-findings-batch.md:48` (`_wl_row.html` contact_btn ~30-46, `channel=`→`hinh_thuc=`).
- **Suggested fix:** Add `_wl_row.html`'s `contact_btn` macro as a third documented cross-phase collision in plan.md's Dependencies section (Phase 1 before Phase 5, matching the existing phase order — but state it explicitly rather than relying on phase numbering alone).

---

## Finding 6: Worklist header "+ Tạo task" no-party_id edge case may 404 the POST outright — Phase 1 defers verification of its own success criterion

- **Severity:** Medium
- **Location:** Phase 1, Implementation Step 12 and Success Criteria bullet 3
- **Flaw:** `worklist.html:25-30`'s "+ Tạo task" button does `hx-get="/modals/m05"` with **no `party_id` param at all**. `modal_m05_create_task.html:60-70` confirms there is no customer-picker — the "Khách hàng" `<select>` is rendered `disabled` showing "— (không gắn)" when `party_id` is empty. The create form then does `hx-post="/customers/{{ party_id }}/tasks"` (`modal_m05_create_task.html:41`), which with an empty `party_id` renders as `hx-post="/customers//tasks"`. FastAPI/Starlette's default path-parameter matching does not match empty path segments — this is a plausible 404, not merely an untested branch. Phase 1 already flags this as "not fully traced" and defers to implementation time, but treats it as a footnote risk rather than a blocker to one of its own listed Success Criteria ("Worklist header '+ Tạo task' → task created, stays on worklist, no navigation to `/customers/`").
- **Failure scenario:** If the POST already 404s today (pre-existing, unrelated to this plan), Phase 1's success criterion for this flow is unachievable as written regardless of the `caller=s01` redirect fix — the task creation itself fails before the redirect-vs-no-redirect question is even reached. This would only surface at implementation/QA time, potentially forcing rework of Phase 1's scope for this one entry point.
- **Evidence:** `crm/src/adapters/inbound/web/templates/worklist.html:25-30` (no `party_id` in the GET); `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html:41-70`; Phase 1 file `phase-01-redirect-context-loss-fix.md:54` (own "not fully traced" caveat) and `:60` (the success criterion this affects).
- **Suggested fix:** Verify the empty-`party_id` POST path first (before touching the redirect logic) — either confirm the route already handles it (e.g. a party-less task genuinely gets created today) or treat "party-less task creation from worklist header" as its own small pre-requisite fix.

---

## Scope Auditor Verification Results

### 1. Phase 1: `caller`/`source` hidden fields + `taskSaved`/`activitySaved` body events

- **Lifetime classification:** Request-scoped form fields (new `caller: Form`/`source: Query`/`Form` params, one per HTTP request) + DOM CustomEvent dispatched once per htmx swap (no persistence, no listener registered outside the single `#worklist-container` element which only exists on S01).
- **Instantiation/usage sites checked:** grepped `taskSaved` and `activitySaved` across `crm/src` — **0 matches** anywhere in the current codebase (templates, Python, tests). No naming collision with an existing event of a different purpose.
- **Verdict: PASS.** No conflicting prior use; additive and safely scoped (the `#worklist-container` id only exists on the worklist page per the plan's own claim, verified true — it does not appear in `customer_360.html` or the cockpit template).

### 2. Phase 3: `TASK_SOURCE_CALLBACK`/`TASK_SOURCE_FOLLOWUP` + `VALID_TASK_SOURCES`

- **Lifetime classification:** Module-level constants (process-global, immutable strings) — no shared mutable state risk by construction.
- **Instantiation/usage sites checked:** grepped `TASK_SOURCE_*` and `VALID_TASK_SOURCES` across `crm/src` (32 hits). `VALID_TASK_SOURCES` itself: defined once (`task.py:39`), re-exported once (`__init__.py:69,174`), **consumed nowhere** (no `in VALID_TASK_SOURCES` check found). `derive_task_kind()` (`task_kind.py`) branches on raw string `"manual"` and falls through identically for any unrecognized source (including the new ones) — confirmed by reading the full function body: both the `"manual"` branch and the final fallback return `(TASK_KIND_CONTACT, False)`, so no behavior change/regression there.
- **Verdict: PASS for state-leak purposes** (no shared/global mutation risk), **but see Finding 4** — the constants are functionally inert (nothing validates against them), and **see Finding 3** — the actual UI purpose the source rename was meant to serve (S15 provenance label) is not wired up by anything in Phase 3's file list.

### 3. Phase 5c: `highlight_task_id` param through `_render_worklist_fragment`

- **Lifetime classification:** Request-scoped local variable, passed as an optional kwarg into a per-request template-render call. `_render_worklist_fragment` itself is a closure defined once at router-registration time (process lifetime) but every invocation is parameterized purely by the `request` object passed in at call time — no cross-request mutable state.
- **Instantiation/usage sites checked:** grepped `_render_worklist_fragment` in `screen_worklist.py` — exactly 3 call sites: line 498 (stale-action-id early return in `handle_claim_action`), line 524 (successful claim, end of `handle_claim_action` — this is the ONE site that would pass `highlight_task_id`), line 538 (`handle_unclaim_customer`). Function signature today: `async def _render_worklist_fragment(request: Request) -> Response` (single param). Adding `highlight_task_id: Optional[str] = None` as a new trailing optional kwarg is backward compatible with all 3 existing call sites (2 of which would implicitly omit it, defaulting to `None` — verified their surrounding code does not manufacture a `highlight_task_id`-shaped value that would need to be threaded, so no accidental leak of a stale value from a prior request is possible since each is a fresh call within its own request handler).
- **Verdict: PASS.** Additive, safely scoped, matches the plan's own risk-assessment claim. No existing "highlight" or "just-changed" mechanism found elsewhere in `worklist_fragment.html`/`_wl_row.html` that this would duplicate (grepped for `highlight`, `just-changed` — no pre-existing equivalent).

---

## Unresolved Questions

1. Finding 1 is the most severe: does the team want the `call_cockpit`/`s14OpenOutcome` branch deleted outright (it appears to be dead-code fallout from the disposition-strip-v2 migration that was never cleaned up), or was there an intended-but-unbuilt UI target for this fragment that should be built instead? This changes whether Phase 1 needs a scope cut or a scope addition.
2. Finding 6 (empty-`party_id` POST route matching) needs an actual runtime check (not just static reading) to confirm whether `POST /customers//tasks` 404s under the app's actual FastAPI routing config — this determines whether Phase 1's worklist-header success criterion is achievable as scoped.
