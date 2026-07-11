# Red-Team Review — Worklist-Claim-Call-Log Flow Fixes Plan (Failure Mode Analyst)

Reviewer role: Flow Tracer / Murphy's-Law failure-mode analysis.
Scope: `plans/260711-0838-worklist-claim-call-log-flow-fixes/plan.md` + all 7 phase files, cross-checked against live code in `crm/src`.

---

## Finding 1: Phase 2's snooze fix is undone by the existing "+Nhắn Zalo" follow-up button, which is shown specifically for the `no_answer` outcome it's supposed to protect

- **Severity:** Critical
- **Location:** Phase 2, "Resolve-Outcome Gating" — interacts with existing code at `c360_call_cockpit_panel.html:944-945,1237-1238,1248-1259` and `screen_customer_360_activity.py:390-448` (`handle_resolve_async`), `outcome_resolve_helpers.py:19-62` (`bulk_resolve`).
- **Flaw:** Phase 2 only patches `execute_side_effects()` step 7. It does not audit or touch the sibling write path `POST /customers/{party_id}/reason/resolve-async`, which calls `_bulk_resolve()` directly — unconditionally `action_state.dismiss(...)` and `task_svc.transition_status(tid, "done")`, with **no outcome parameter, no gating, no knowledge of Phase 2's new snooze branch**.
- **Failure scenario:** Staff finalizes a call with `outcome=no_answer`. Post-Phase-2, `execute_side_effects` step 7 correctly snoozes the action and pushes the task's due date (not dismiss/done). The cockpit then shows the `id="s14-strip-zalofollowup"` button (`display:none` by default, only unhidden when `S.chosenOutcome === 'no_answer'`, `c360_call_cockpit_panel.html:1237-1238`) — i.e. the exact "call a follow-up Zalo since they didn't pick up" nudge the flow is designed to encourage. Clicking it fires `s14StripZaloFollowup()` (line 1248-1259), which POSTs the SAME `action_id`/`task_id` (read from `#s14-resolve-action-ids`/`#s14-resolve-task-ids`, the same hidden fields `s14StripSave` used) to `/customers/{party_id}/reason/resolve-async`. That handler calls `_bulk_resolve()` (`outcome_resolve_helpers.py:19-62`), which dismisses the action (writing the 30-day `crm_action_dismissal` TTL row) and marks the task done — **unconditionally**, undoing the snooze Phase 2 just applied, for exactly the outcome Phase 2 exists to protect.
- **Evidence:**
  - `c360_call_cockpit_panel.html:944-945`: `<button ... id="s14-strip-zalofollowup" ... style="display:none" onclick="s14StripZaloFollowup()">＋Nhắn Zalo</button>`
  - `c360_call_cockpit_panel.html:1237-1238`: `var zaloBtn = $('s14-strip-zalofollowup'); if (zaloBtn) zaloBtn.style.display = (S.chosenOutcome === 'no_answer') ? '' : 'none';`
  - `c360_call_cockpit_panel.html:1252-1255`: posts `channel=zalo&action_id=...&task_id=...` to `/customers/{party}/reason/resolve-async`.
  - `screen_customer_360_activity.py:440-446`: `_bulk_resolve(action_ids=..., task_ids=..., action_state=action_state, task_svc=task_svc, actor_id=actor_id or "")` — no outcome/gating input at all.
  - `outcome_resolve_helpers.py:48-62`: unconditional `action_state.dismiss(aid, ...)` / `task_svc.transition_status(tid, "done")`.
- **Suggested fix:** Either (a) gate `handle_resolve_async`/`_bulk_resolve` the same way as Phase 2's step 7 (needs an outcome or explicit "snooze mode" signal), or (b) change `s14StripZaloFollowup` to not resolve the action/task at all when the underlying call outcome was `no_answer`/`busy` (it's a supplementary contact attempt, not a resolution). Phase 2's Success Criteria must be extended to cover this interaction — as written, "action reappears in the queue after `snoozed_until` passes" is falsified by clicking the button the UI itself surfaces immediately after.

---

## Finding 2: Phase 6b's "Hoàn tất ✓" repoint discards the existing per-checkbox selective-resolve UX — every click will resolve ALL unresolved actions, not just the checked ones

- **Severity:** Critical
- **Location:** Phase 6, section "6b. Dismiss-session bắt buộc log" — targets `c360_insight_panel.html` (actual button at line 97-99, not line 55 as cited) and `screen_customer_360_panels.py:296-306`.
- **Flaw:** The plan's recommended option (b) is: change the "Hoàn tất ✓" button from `hx-post="/customers/{party_id}/actions/dismiss-session"` (inside a `<form>` with per-item `<input type="checkbox" name="action_ids" value="...">`, default unchecked, count shown via `aqMarkDone`) to `hx-get` opening `/modals/m08?party_id={party_id}&resolve_action_ids={comma-joined ids}` — where "comma-joined ids" is described as a static template-rendered value, not a JS read of which checkboxes are actually checked.
- **Failure scenario:** Today, a rep can tick off a subset of the session's unresolved actions (e.g. resolve 2 of 5) and click "Hoàn tất (2) ✓" — only the 2 checked ids are submitted (`form.getlist("action_ids")` only returns checked inputs). If the button is repointed to a server-rendered `resolve_action_ids={all ids}` GET link as literally described, checking/unchecking boxes becomes cosmetic — clicking "Hoàn tất ✓" always resolves **every** unresolved action for the customer via a single M08 log entry with one outcome, silently expanding blast radius from "what I checked" to "everything on screen." Confirmed M08 has no per-item deselect UI once opened — `modal_log_activity.html:115-116,142-144` only renders `resolve_action_ids` as an opaque hidden field and a count (`_n_actions`), no checklist.
- **Evidence:**
  - `c360_insight_panel.html:60-63`: `<input type="checkbox" name="action_ids" value="{{ act.action_id }}" onchange="aqMarkDone(this)">` (unchecked by default, no `checked` attribute).
  - `c360_insight_panel.html:160-164`: `aqMarkDone` only updates button label based on `:checked` count; native form submit only sends checked values.
  - `modal_log_activity.html:115-116,142-144`: `resolve_action_ids` is a single hidden field / count display, no per-id toggle.
  - Phase 6, Implementation Step 3: "`hx-get` opening `/modals/m08?party_id={party_id}&resolve_action_ids={comma-joined ids}`" — no mention of reading `:checked` state via JS.
- **Suggested fix:** If option (b) is kept, the button must read `document.querySelectorAll('input[name=action_ids]:checked')` client-side (analogous to `s14StripSave`'s `document.getElementById(...).value` pattern) and build the URL/hx-vals dynamically — not bake in a server-rendered "all ids" string. Otherwise the checkbox UI becomes actively misleading (implies selection, ignores it).

---

## Finding 3: Phase 1's own required "no-party M05" flow likely 404s before reaching the fix — M05 has no customer picker and posts to a route that can't match an empty path segment

- **Severity:** Critical
- **Location:** Phase 1, Requirements bullet 3 / Success Criteria bullet 3 ("Worklist header '+ Tạo task' (no party_id) → task created, stays on worklist") and Implementation Step 12.
- **Flaw:** `worklist.html:24-30`'s "+ Tạo task" button does `hx-get="/modals/m05"` with no `party_id` at all. `modal_m05_create_task.html:41-46` unconditionally renders `<form hx-post="/customers/{{ party_id }}/tasks" ...>` — when `party_id` is empty, this becomes `hx-post="/customers//tasks"`. FastAPI/Starlette's default `{party_id}` path converter requires a non-empty segment (`[^/]+`), so this URL will not match the registered route `@router.post("/customers/{party_id}/tasks", ...)` — it will 404 before `post_task()` (and therefore before the plan's new `caller`-gating logic) ever executes. Compounding this: the "Khách hàng" field in M05 (`modal_m05_create_task.html:61-78`) is a **disabled, display-only `<select>`** (`disabled style="pointer-events:none"`) — there is no picker UI to fill in a real `party_id` before submit, confirming this isn't a data-entry gap the user can work around.
- **Failure scenario:** Staff clicks "+ Tạo task" on the worklist header (intentionally, for a task with no linked customer — e.g. an internal reminder), fills the modal, clicks "Lưu task" → request 404s (or, in edit mode, would need to hit the entirely different `POST /tasks` route already registered at `screen_tasks_board.py:131`, which M05's create-mode form never targets). This is a pre-existing bug, not introduced by this plan, but Phase 1 explicitly lists this exact flow as one of its Success Criteria to verify working, and its own Implementation Step 12 only says "verify... at implementation time... Not fully traced during planning; do not assume" — it does not identify that the target route is architecturally unable to accept the case, nor does it point at the existing `POST /tasks` route as the correct target.
- **Evidence:**
  - `worklist.html:24-30`: `hx-get="/modals/m05"` — no `party_id`.
  - `modal_m05_create_task.html:41`: `<form hx-post="/customers/{{ party_id }}/tasks" ...>`.
  - `modal_m05_create_task.html:61-70`: customer field is `disabled`, no picker.
  - `screen_tasks_board.py:131`: a separate `POST /tasks` (no path param) route exists — the correct target for party-less tasks — but is never wired to M05's create form.
- **Suggested fix:** Before landing Phase 1's worklist-header wiring, confirm/fix the no-party path: either M05's create-mode form should conditionally post to `/tasks` when `party_id` is empty, or the "+ Tạo task" worklist header button needs a customer step. This should be resolved as part of Phase 1, not deferred to "verify at implementation time," since Phase 1's success criteria assert this flow works.

---

## Finding 4: Phase 3's stated goal ("S15 provenance đúng") is not achieved — `task_detail.html` isn't in Phase 3's file list, and its label logic collapses new sources to "thủ công"

- **Severity:** High
- **Location:** Phase 3, Overview/Requirements ("source callback/followup thay vì manual để S15 provenance đúng") — missing file `task_detail.html`.
- **Flaw:** Phase 3's "Related Code Files" lists only `domain/entities/task.py` and `activity_side_effects.py`. But S15's provenance block (`task_detail.html:256-264`) renders the source label with `{% if task.source == 'action_queue_claim' %}... {% elif task.source == 'action_queue' %}... {% else %}thủ công{% endif %}`. Since `"callback"`/`"followup"` are neither `action_queue_claim` nor `action_queue`, they fall into the `else` branch and display as **"thủ công"** (manual) — the exact label the plan's fix is supposed to move away from.
- **Failure scenario:** After Phase 3 ships, a callback/follow-up task's DB `source` column correctly reads `"callback"`/`"followup"`, and it correctly gets an assignee — but staff opening S15 for that task still sees "Nguồn: thủ công," identical to a genuinely manually-typed task. The plan's stated success condition (distinguishing provenance in S15) silently fails while every other success criterion (assignee, DB `source` value) passes, making this easy to miss in review since the visible artifact (S15 label) looks unchanged.
- **Evidence:** `task_detail.html:258-263` (verbatim quoted above); Phase 3's `## Related Code Files` section omits `task_detail.html` entirely.
- **Suggested fix:** Add `task_detail.html`'s provenance block to Phase 3's file list; extend the `{% elif %}` chain (or switch to a label lookup dict) to cover `"callback"`/`"followup"`.

---

## Finding 5: Phase 6a's auto-claim-on-"Gọi" race is not actually closed — TOCTOU + unique index + the plan's own prescribed try/except means the losing staff member's claim silently vanishes with zero feedback

- **Severity:** Critical
- **Location:** Phase 6, section "6a. Claim-at-call-start (#9)" and Implementation Step 1.
- **Flaw:** The plan describes `auto_claim_from_contact` as "idempotent via `get_customer_claim(party_id)` early-return, safe to call on every 'Gọi' press." This conflates "won't create a duplicate row" with "race-safe." `auto_claim_from_contact` (`task_service.py:309-338`) does `existing = get_customer_claim(party_id); if existing is not None: return existing, False` then inserts a new task — this check-then-insert is **not** wrapped in a transaction/lock. There IS a DB-level guard: `uidx_task_source_ref` (migration `0037_task_source_ref_active_only_uniqueness.up.sql`), a partial UNIQUE index on `(source, source_ref) WHERE status NOT IN ('done','cancelled')` — so a true concurrent race between two staff pressing "Gọi" within the TOCTOU window results in one insert raising `sqlite3.IntegrityError`. Phase 6a's own Implementation Step 1 says to "Wrap in try/except-log... a claim failure must not block the call draft itself" — meaning the losing staff member's insert fails, is silently logged, and their call draft creation proceeds anyway with **no signal to them** that the customer was already claimed by someone else in that instant.
- **Failure scenario:** Staff A and Staff B both open the same unclaimed customer's cockpit and press "Gọi" within the same second (a realistic scenario for a hot lead surfaced to multiple reps). A's insert succeeds. B's insert hits the unique-index violation, gets swallowed by the try/except, and B's own call session proceeds uninterrupted — B has no way to know, in that moment, that A now owns this customer. B's UI shows no "👤 X đang xử lý" badge (that only renders on the NEXT full page load/re-render of P01/worklist, not mid-call in the cockpit strip that just fired the POST). The report itself offered a complementary fix ("hoặc idbar hiện '👤 X đang xử lý' như 360 đã có") which the plan explicitly declines to add ("Bỏ ngang → dùng Trả việc"), leaving no real-time signal.
- **Evidence:**
  - `task_service.py:317-319`: `existing = self._task_repo.get_customer_claim(party_id); if existing is not None: return existing, False` — no locking.
  - `migrations/0037_task_source_ref_active_only_uniqueness.up.sql:13-15`: `CREATE UNIQUE INDEX ... uidx_task_source_ref ON crm_task (source, source_ref) WHERE source_ref IS NOT NULL AND status NOT IN ('done','cancelled')`.
  - Phase 6 Implementation Step 1: "Wrap in try/except-log ... a claim failure must not block the call draft itself."
  - `c360_insight_panel.html:28-31`: the "👤 X đang xử lý" badge exists only in the P01 panel render path, not surfaced synchronously from `handle_create_call_session`'s response (`screen_customer_360_activity.py:526-531` returns only `activity_id/status/started_at/channel_value`, no claim-conflict info).
- **Suggested fix:** Have `handle_create_call_session` surface the claim outcome (or at least whether `auto_claim_from_contact` returned `is_new=False` with a DIFFERENT assignee than the current actor) back to the JS response, and show a visible "already claimed by X" warning in the cockpit at T1 — don't rely purely on silently-swallowed exceptions plus a stale-until-refresh badge.

---

## Finding 6: Phase 7 #12's "wire claimSuccess" option is a guaranteed double-fetch, not a maybe — the claim button's own `hx-target` IS the same container the new trigger would refetch

- **Severity:** Medium
- **Location:** Phase 7, "#12 — Dead `claimSuccess` trigger," option (a).
- **Flaw:** The plan hedges: "check for double-refresh conflicts with Phase 5c's `highlight_task_id` mechanism before wiring this; if they'd fight each other, do (b) instead." Tracing the actual markup shows this conflict is certain, not conditional. The claim button (`_wl_row.html:135-140`) already has `hx-patch="/worklist/actions/{action_id}/claim" hx-target="#worklist-container" hx-swap="outerHTML"`, and the handler (`screen_worklist.py:513-524`) directly returns a full `_render_worklist_fragment(request)` response that swaps `#worklist-container` in one round trip. If option (a) additionally fires `document.body.dispatchEvent(new Event('claimSuccess'))` via `hx-on::after-request` on that same button, and (post-Phase-1) `#worklist-container` carries `hx-trigger="claimSuccess from:body, taskSaved from:body, activitySaved from:body"`, then the freshly-swapped-in container (which also carries that same `hx-trigger` attribute, since it's part of the swapped fragment markup) will immediately issue a SECOND `GET /worklist/fragment` in response to the event its own claim response's after-request handler just fired — a guaranteed flicker/double-fetch on every single claim, not a hypothetical edge case.
- **Failure scenario:** Every "Nhận việc" click now does 2 full worklist refetches back-to-back — wasted round trip at minimum, and depending on server-side non-determinism (cache invalidation timing, `worklist_svc.invalidate_cache()` interaction with the 2nd fetch), a possible visible flash/reflow or a race where the 2nd fetch's data differs from the 1st.
- **Evidence:** `_wl_row.html:135-140` (button's own `hx-target="#worklist-container"`); `screen_worklist.py:513-524` (`_render_worklist_fragment` called directly by the claim handler); Phase 1 Implementation Step 11 (adds `claimSuccess`/`taskSaved`/`activitySaved` to the SAME container's `hx-trigger`); Phase 7 #12 Overview (frames the conflict as something to "check... before wiring," not a certainty).
- **Suggested fix:** Given the trace confirms the conflict is structural (not timing-dependent), decide now: drop `claimSuccess` from the trigger list (option b) rather than deferring to an "if it conflicts" implementation-time check that will always resolve to "yes, it conflicts."

---

## Finding 7: Phase 5a's premise that phone/other `contact_btn` variants "presumably already send `hinh_thuc=call` or equivalent" is factually wrong — all 4 variants currently send `channel=`, none send `hinh_thuc=`

- **Severity:** Medium
- **Location:** Phase 5, section "5a. Kênh không khớp modal," Implementation Step 1.
- **Flaw:** `_wl_row.html`'s `contact_btn` macro (lines 26-49) has 4 branches, and **all 4** — phone (`:28-32`), zalo (`:33-37`), facebook (`:38-42`), and the no-identity fallback (`:43-47`) — pass `channel=phone` / `channel=zalo` / `channel=facebook` / no channel param at all respectively. None send `hinh_thuc=`. The plan's step 1 says to change "worklist ... contact_btn's 4 variants from `channel=zalo`/`channel=facebook` to `hinh_thuc=zalo`/`hinh_thuc=fb` (phone/other variants presumably already send `hinh_thuc=call` or equivalent — verify all 4)" — the "presumably" is incorrect; the phone variant sends `channel=phone` (a param the GET handler doesn't read today, matching the report's own finding), and only "works" by accident because the current default channel selection happens to be "call" regardless of the ignored `channel` param.
- **Failure scenario:** If an implementer trusts the "presumably already fine" framing and only touches the zalo/facebook branches (as the parenthetical implies is sufficient), the phone/fallback branches keep passing a now-doubly-dead `channel=` param instead of being normalized to explicit `hinh_thuc=call`. This happens to still render correctly today only because "call" is the GET handler's default — but it's fragile: any future change to that default (or to `_HT_TO_ACT_TYPE`'s fallback) will silently break the phone path with no test coverage, since nothing currently asserts the phone contact button explicitly requests the call channel.
- **Evidence:** `_wl_row.html:26-49` (macro body, all 4 branches use `channel=`, never `hinh_thuc=`).
- **Suggested fix:** Normalize all 4 branches to `hinh_thuc=` explicitly (call/zalo/fb/call) in the same pass, not just the 2 the plan calls out — drop the "presumably" framing since it's disprovable by reading the macro.

---

## Flow Tracer Verification Results

**1. Phase 1's `caller`/`source`-param round-trip through GET→form→POST for M05 and M08.**
Traced path with file:line citations, with one confirmed break and one scope clarification:
- M05: `worklist.html:24-30` / `c360_call_cockpit_panel.html:262,312-313,619,666` (GET `/modals/m05`) → `screen_modal_task.py:39-111` (`get_modal_m05`, no `caller` param today) → `modal_m05_create_task.html:41-46` (form posts to `/customers/{party_id}/tasks`, hidden `source`/`source_ref` only rendered when `prefill_source` truthy) → `screen_modal_task.py:141-184` (`post_task`, unconditional `redirect_to_customer`, no `caller` Form field today). Matches the plan's "currently unconditional redirect" claim. **FAILED** for the worklist-header no-party case specifically — see Finding 3.
- M08: `screen_customer_360_activity.py:182-201` (`handle_modal_m08`, no `source` Query param today, confirming the plan's "GET doesn't accept source" claim) → `modal_log_activity.html` (no hidden `source` field rendered today) → `screen_customer_360_activity.py:221-386` (`handle_log_activity`; `source` Form field already exists at line 255; `call_cockpit` branch at 375-385 returns a fragment without `HX-Redirect`; default path at 386 redirects). Confirmed accurate for the cockpit's M08 **fallback** opens (`c360_call_cockpit_panel.html:256,1075,1081,1088`, "⋯ Chi tiết"/"Ghi thủ công"/Zalo-button). **Scope clarification** (not a plan error, but worth flagging): the cockpit's *primary* save path, `s14StripSave()` (`c360_call_cockpit_panel.html:1211-1244`), does NOT call this legacy route at all — it POSTs to `/api/activities/{id}/finalize` (`handle_finalize_activity`, `screen_customer_360_activity.py:590-659`), which never issues `HX-Redirect` and is source-agnostic already. Phase 1's Overview text ("Cockpit mid-call bấm Đặt lịch/Tạo task ... lưu xong bị đá sang 360") is accurate only for M05 (Đặt lịch/Tạo task) and M08's fallback opens — the main disposition-strip finalize flow never had this bug. The plan's actual file-level scope is correct; only the framing risks over-generalizing to readers.

**2. Phase 2's `execute_side_effects` step 7 outcome branch.**
Traced path with file:line citations: `activity_side_effects.py:164-183` (step 7), confirmed against `action_state_repository.py:40-52` (`dismiss`, writes both `crm_action_state` and the 30-day `crm_action_dismissal` TTL) and `:158-169` (`snooze`, touches only `crm_action_state`, confirming the plan's "does not trigger the 30-day TTL" claim). `CONTACT_OUTCOMES_CALL` constants confirmed at `activity.py:37-39`. The mechanical fix as scoped is correct. **FAILED** in the broader sense that a parallel resolve path (`/reason/resolve-async` → `_bulk_resolve`) reachable from a UI element the flow itself surfaces specifically for `no_answer` outcomes bypasses the new gate entirely — see Finding 1.

**3. Phase 3's `assignee_user_id`/`created_by` propagation into `create_task`.**
Traced path with file:line citations: `activity_side_effects.py:129-154` (steps 4/5, currently hardcode `"source": "manual"`, no `assignee_user_id`/`created_by` — confirmed) → `task_service.py:96-138` (`create_task`, confirmed reads `task_data.get("assignee_user_id")`/`get("created_by")` directly into `Task` fields at lines 130/132) → `task.py` (`Task` dataclass has both fields) → `task_kind.py:28-72` (`derive_task_kind`, confirmed the new `"callback"`/`"followup"` source values fall through to the same `TASK_KIND_CONTACT, False` result as today's `"manual"` case — no regression). Mechanically correct. **FAILED** on the plan's own stated success condition for S15 provenance — see Finding 4 (missing `task_detail.html` edit).

**4. Phase 6a's `auto_claim_from_contact` call from `handle_create_call_session`.**
Traced path with file:line citations: `screen_customer_360_activity.py:490-531` (`handle_create_call_session`, confirmed `task_svc`/`profile` already available per plan's claim) → proposed call into `task_service.py:309-338` (`auto_claim_from_contact`) → `task_repository.py:356-361` (`get_customer_claim`) and `insert` (`:251-274`) → `migrations/0037_task_source_ref_active_only_uniqueness.up.sql` (confirmed a genuine partial UNIQUE index enforces one active claim per party at the DB level). The plan's implementation is internally consistent (does what it says), but the claimed race-closure property does not hold under concurrent load as designed — see Finding 5.

---

## Unresolved Questions

- Does the team want Finding 1's fix (gate `/reason/resolve-async`) folded into Phase 2, or handled as a new follow-up phase — Phase 2's file list and success criteria as written do not cover it.
- For Finding 3 (no-party M05 flow), is party-less task creation from the worklist header actually an intended use case, or should "+ Tạo task" require picking/attaching a customer first? This changes whether the fix belongs in Phase 1 or is a pre-existing, separately-scoped bug.
