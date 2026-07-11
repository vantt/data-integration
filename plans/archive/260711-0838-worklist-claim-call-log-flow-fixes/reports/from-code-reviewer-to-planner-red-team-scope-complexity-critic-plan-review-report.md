# Red Team Review — Scope & Complexity Critic

Plan: `plans/260711-0838-worklist-claim-call-log-flow-fixes/plan.md` + 7 phase files.
Reviewer role: YAGNI enforcer (over-engineering, scope creep, missing MVP cuts) + Contract Verifier (interface change → all callers enumerated).

All findings verified against current repo state (`D:\Vantt\app\data-integration`), not against plan text alone.

---

## Finding 1: Phase 6a adds a second parallel auto-claim trigger instead of replacing the existing one — violates the plan's own "một đường ghi duy nhất" principle

- **Severity:** Critical
- **Location:** Phase 6, section "6a. Claim-at-call-start (#9)"
- **Flaw:** The plan adds `task_svc.auto_claim_from_contact(...)` as a new side effect inside `handle_create_call_session` (call-session-start, T1) but does **not** remove or gate the pre-existing auto-claim call that already fires at finalize time (`execute_side_effects` step 2, gated on `auto_claim=bool(activity.contact_outcome and not activity.task_id)`, `activity_side_effects.py:104-108`). Since `create_draft`/`handle_create_call_session` never sets `activity.task_id` as a side effect of claiming, the finalize-time gate `not activity.task_id` stays `True` for the common no-task_id flow — meaning **every single call now invokes `auto_claim_from_contact` twice**: once at call-start (new) and once again at finalize (pre-existing, untouched).
- **Failure scenario:** Staff presses "Gọi" → claim fires (6a). Staff talks, hits an outcome, finalizes → `execute_side_effects` step 2 fires `auto_claim_from_contact` again for the same party/actor. Functionally masked by `get_customer_claim`'s idempotent early-return (confirmed at `task_service.py:309-334` per the plan's own citation), but it is genuine architectural duplication: two independent call sites now perform the same write-triggering role for the same event, directly contradicting the codebase's own stated invariant that `activity_side_effects.py`'s docstring calls "một đường ghi duy nhất" (`activity_side_effects.py:6-11`) — the very principle Phase 2 and Phase 6b lean on to justify *not* adding new write paths elsewhere in this same plan.
- **Evidence:** `activity_side_effects.py:102-108` (finalize-time auto-claim, untouched by Phase 6a) vs. phase-06 Implementation Step 1 ("in `handle_create_call_session`, ... call `task_svc.auto_claim_from_contact(...)`"). Phase 6 file list does not include `activity_side_effects.py` at all — the finalize-time trigger is never revisited.
- **Suggested fix:** Either (a) gate step 2's finalize-time auto-claim to skip when a claim already happened this session (requires threading a flag/timestamp through), or (b) explicitly document in the plan that finalize-time auto-claim becomes a harmless no-op post-6a and is being *intentionally* left as a redundant safety net (not silently omitted) — currently the plan does neither, it simply doesn't mention the interaction.

## Finding 2: Phase 1 uses two different query-param names (`caller` vs `source`) for the identical "who opened this modal" concept

- **Severity:** Medium
- **Location:** Phase 1, "Requirements" + Implementation Steps 1-11
- **Flaw:** M05 gets a new `caller` param (`caller=s01`/`caller=s14`) while M08 gets a new/extended `source` param (`source=worklist`/`source=call_cockpit`) — both encode the exact same semantic ("which screen opened this modal, so I know whether to redirect"). This is unnecessary API surface duplication: a future maintainer touching either modal now has to remember which of the two names applies to which route, and any future M0x modal will need to guess which convention to follow.
- **Failure scenario:** A later change adds a third opener context to M05 (e.g. from a new S16 screen) — the implementer, pattern-matching on M08's `source` convention (documented and already precedent-setting since `source=call_cockpit` predates this plan), adds `source=` to M05 instead of `caller=`, silently no-opping the fix for that path because M05's POST handler only checks `caller`.
- **Evidence:** Phase 1 Implementation Step 3: `if caller.strip() in ("s01", "s14"): return HTMLResponse(content="")`. Step 8: `elif source.strip() == "worklist": return HTMLResponse(content="")`. Two param names for one concept, both introduced/extended in the same phase, with no requirement or note explaining the naming split.
- **Suggested fix:** Standardize on one param name (`source`, since M08 already precedent-sets it via the existing `source == "call_cockpit"` dead code) for both M05 and M08 in this same phase — it's a pure rename in the M05 branch, zero added cost since both are new/mostly-new call sites being edited anyway.

## Finding 3: Phase 1's worklist-header M05 "no party_id" edge case is explicitly untraced and deferred to implementation, despite being on the success-criteria path

- **Severity:** High
- **Location:** Phase 1, Implementation Step 12
- **Flaw:** Step 12 reads verbatim: *"At implementation time, verify the worklist header 'no party' M05 flow (`hx-post="/customers//tasks"` when `party_id` is empty) — confirm the modal has a customer-picker step that fills in a real `party_id` before POST, or that this edge case is already handled elsewhere. Not fully traced during planning; do not assume."* This is a core path explicitly named in the plan's own Success Criteria ("Worklist header '+ Tạo task' → task created, stays on worklist, no navigation to `/customers/`") — yet the plan ships without verifying the route even works with an empty `party_id` path segment. `POST /customers//tasks` with a literal empty path segment is very likely to 404 at the routing layer (FastAPI path params don't match empty segments) *before* any of Phase 1's `caller`-gating logic is reached at all.
- **Failure scenario:** Implementer follows the plan, wires `caller=s01` end-to-end, and only discovers at manual-verify time that the worklist header "+ Tạo task" flow was already broken (or worked via a different mechanism entirely, e.g. a customer-picker JS step this plan never traced) — potentially invalidating the phase's file list/line citations for that call site (`worklist.html:26-28`).
- **Evidence:** Plan's own words: "Not fully traced during planning; do not assume." Contradicts the plan's stated Success Criteria bullet for the same flow.
- **Suggested fix:** This should have been resolved during planning (one grep/read of `modal_m05_create_task.html` for a customer-picker step) rather than shipped as a known gap in a P0 phase. Trace it now before implementation starts.

## Finding 4: Phase 1 leaves a now-inaccurate regression-test invariant uncorrected

- **Severity:** Medium
- **Location:** Phase 1 (no corresponding requirement/step); contract evidence in `crm/src/tests/test_quick_outcome_cockpit_post.py:152-166`
- **Flaw:** The existing test `test_unknown_source_keeps_hx_redirect` asserts, with the docstring *"Only the exact 'call_cockpit' marker skips the redirect"*, that any `source` value other than `"call_cockpit"` must keep the `HX-Redirect` header. Phase 1 Step 8 adds a second value (`source == "worklist"`) that also skips the redirect. The specific test case uses `source="timeline"` so it will not literally fail, but the codified invariant in its docstring becomes false the moment Phase 1 ships, and nothing in the plan requires updating this test/docstring.
- **Failure scenario:** A future engineer reads this test to understand the redirect contract, trusts the docstring ("only call_cockpit skips redirect"), and builds new logic on a false premise — or worse, "fixes" the test to reflect the doc without realizing `worklist` is an intentional second exemption, causing a false regression signal.
- **Evidence:** `test_quick_outcome_cockpit_post.py:152-154` — `def test_unknown_source_keeps_hx_redirect(): """Only the exact 'call_cockpit' marker skips the redirect."""`. Phase 1 Success Criteria only says "Existing tests covering M05/M08 redirect behavior still pass" — passing ≠ contract-accurate.
- **Suggested fix:** Add a requirement/step to Phase 1 to update this test's docstring and add an explicit `source="worklist"` case alongside it, rather than relying on "still passes" as the bar.

## Finding 5: Phase 5c threads a new parameter through a 3-call-site shared render function and adds inline JS, when the underlying bug is a one-line attribute fix

- **Severity:** Medium
- **Location:** Phase 5, section "5c. Claim feedback biến mất (#7)"
- **Flaw:** The actual bug is: `worklist_fragment.html`'s "Đã Claim" `<details>` lacks the `open` attribute that "Chưa Claim" already has (`:92` vs `:119`). The plan's fix threads a new `highlight_task_id: Optional[str] = None` parameter through `_render_worklist_fragment(request)` — a function with **zero existing parameters beyond `request`**, called from 3 separate route handlers (`screen_worklist.py:498, 524, 538`, confirmed by grep) — plus adds a hardcoded highlight CSS class and an inline `<script>...scrollIntoView...</script>` appended to the fragment response. This is materially more surface area than the finding requires: the report's own fix note only asks for "auto-open Đã Claim + highlight row vừa claim," and auto-opening alone (unconditional `open` on both `<details>`, matching the existing "Chưa Claim" pattern) already satisfies the primary complaint ("claim feedback biến mất") without any new parameter, without touching all 3 call sites, and without inline JS.
- **Failure scenario:** The two non-claim callers of `_render_worklist_fragment` (line 498's stale-action fallback, line 538 elsewhere) must now be reviewed and confirmed to correctly omit/default the new param — extra verification surface for a fix whose core requirement ("newly claimed task visible without manually expanding Đã Claim") doesn't need per-row targeting at all.
- **Evidence:** `screen_worklist.py:336-350` (`_render_worklist_fragment(request: Request)` — no params today), call sites at `:498`, `:524`, `:538`; phase-05 Implementation Step 3 ("extend `_render_worklist_fragment(request, ...)` ... the claim handler passes the newly claimed task's id").
- **Suggested fix:** Ship the minimal fix first (unconditional `open` on "Đã Claim", matching "Chưa Claim"'s existing pattern) to satisfy the stated requirement; treat highlight-row/scroll-into-view as a separate, explicitly-optional enhancement rather than bundling it into the same phase/requirement.

## Finding 6: Phase 6b's proposed removal of `handle_dismiss_session` has zero test coverage and an un-updated doc reference not listed in the phase's file list

- **Severity:** Medium
- **Location:** Phase 6, section "6b. Dismiss-session bắt buộc log (#10)", Implementation Step 3
- **Flaw:** Contract Verifier check: `handle_dismiss_session` (`screen_customer_360_panels.py:296-306`) has exactly **one** caller in the entire repo — the form at `c360_insight_panel.html:55` (`hx-post="/customers/{party_id}/actions/dismiss-session"`). Grep across `crm/src/tests` for `dismiss-session`/`handle_dismiss_session` returns **zero matches** — there is no regression test protecting this route's current behavior, so "confirm nothing else calls it" (the plan's stated bar for removal) is not actually a safety net; a route with no test coverage removed on a grep-only confirmation has no automated proof the removal is safe. Separately, `docs/ui-spec/panels/P01-insight-panel.md:80` documents this exact endpoint ("Submit POSTs to `/customers/{party_id}/actions/dismiss-session`") — this doc file is not in Phase 6's "Related Code Files" list, so if the route is removed, the doc goes stale and nothing in the plan catches that.
- **Failure scenario:** Implementer removes `handle_dismiss_session` per option (b), ships it, nothing breaks in CI (no test existed either way), but `docs/ui-spec/panels/P01-insight-panel.md` still describes a dead endpoint — the next engineer reading the spec designs against a route that no longer exists.
- **Evidence:** `Grep dismiss-session|handle_dismiss_session` across `crm/src/tests` → no matches. `Grep dismiss-session` across `crm/src` + `crm/docs` → only `screen_customer_360_panels.py` (route def) and `c360_insight_panel.html:55` (sole caller) and `docs/ui-spec/panels/P01-insight-panel.md:80` (doc).
- **Suggested fix:** Add `docs/ui-spec/panels/P01-insight-panel.md` to Phase 6's file list with an explicit doc-update step if removal is chosen; add a regression test for whichever end-state (removed-route-404 or repointed-to-M08) is picked, since none currently exists to catch a mistake either way.

## Finding 7: Phase 7 #12 bundles an indecisive "wire it up unless it conflicts, in which case remove it instead" branch into a P3 "minor cleanup" phase

- **Severity:** Medium
- **Location:** Phase 7, section "#12 — Dead `claimSuccess` trigger"
- **Flaw:** For a phase explicitly scoped as "5 cosmetic/dead-code findings... safe to batch and do last," #12 asks the implementer to make a live runtime judgment call at implementation time ("check for double-refresh conflicts with Phase 5c's `highlight_task_id` mechanism before wiring this; if they'd fight each other, do (b) instead") rather than deciding the approach during planning. Given Finding 5 above (Phase 5c already directly re-renders the fragment on claim, no separate event-driven refetch needed for the claim path itself), wiring a *second* trigger (`claimSuccess`) that fires an *additional* fragment refetch on top of the claim handler's own direct-render response is very likely to double-render by construction, not just "possibly" — the plan's own escape hatch (option b, just delete the dead trigger) is almost certainly the correct call here, but the plan doesn't commit to it, adding avoidable decision overhead to what's billed as a trivial cleanup phase.
- **Failure scenario:** Implementer, following "Recommend (a)," wires `claimSuccess` emission on the claim button; claim now both re-renders `#worklist-container` directly (existing behavior, Phase 5c's target) AND fires `claimSuccess from:body` which re-fetches `/worklist/fragment` again — a visible double-render/flicker exactly as the plan's own Risk section predicts, on a "minor" phase that was supposed to be zero-risk.
- **Evidence:** Phase 7 Overview: "Recommend (a) — cheap, ... check for double-refresh conflicts with Phase 5c's `highlight_task_id` mechanism before wiring this; if they'd fight each other, do (b) instead." Risk Assessment repeats the same warning almost verbatim, confirming the plan itself doesn't believe (a) is safe by default.
- **Suggested fix:** Given the claim handler already fully re-renders its own container (per Phase 5c), default to option (b) (remove the dead `claimSuccess` trigger) rather than leading with "recommend (a)" — simpler, avoids the flagged double-render risk entirely, and is more consistent with YAGNI (don't wire a second refresh path that has no independent reason to exist once 5c ships).

## Finding 8: Phase 3's `source="callback"`/`"followup"` provenance split changes an externally-observable field with only a self-described "likely regression" check, not a verified one

- **Severity:** Medium
- **Location:** Phase 3, Implementation Step 5 + Risk Assessment
- **Flaw:** Phase 3 changes the `source` field written on callback/follow-up tasks from `"manual"` to two new distinct values, and explicitly says: *"Check `badge_catalog.py`/worklist templates for any `source`-keyed label/icon lookup... out of scope for the report's finding but a likely regression if such a lookup exists."* — i.e., the plan flags a plausible regression vector but does not verify it, again deferring a knowable check to implementation. (Verification during this review: `badge_catalog.py` has no `source`-keyed lookup today, and `VALID_TASK_SOURCES` is not enforced on write anywhere in `task_service.py` — so this particular risk turns out to be a non-issue, but the plan itself did not do this check despite having the tooling to do so during planning.)
- **Failure scenario:** Had a source-keyed lookup existed (it happens not to), tasks would render with a raw/unknown source string in S07/S15 badges post-ship, discovered only in manual verification or by an end user.
- **Evidence:** `Grep "TASK_SOURCE_MANUAL|\"manual\""` across `crm/src` — no source-keyed label/icon dispatch found in `badge_catalog.py`/`fmt_badge.py` (both files only import task-kind/status constants, not source-branching logic). `Grep VALID_TASK_SOURCES` in `task_service.py` — zero matches (not enforced).
- **Suggested fix:** Not a blocker given the verification above resolves it cleanly, but flag as a process gap: plans should not defer greppable safety checks to "implementation time" when the grep takes seconds and materially changes phase risk (this is the second instance of this pattern in the same plan — see Finding 3).

---

## Contract Verifier Verification Results

### 1. `redirect_to_customer()` / M05 & M08 POST route HX-Redirect removal (Phase 1)

- `redirect_to_customer` defined at `screen_modal_shared.py:36`.
- All callers (grep, repo-wide):
  1. `screen_modal_task.py:184` — M05 POST `/customers/{party_id}/tasks` (**target of Phase 1's change**)
  2. `screen_modal_tags.py:126` — M06-ish tags modal POST (**not touched by plan — confirmed correctly out of scope, different modal**)
  3. `screen_modal_custom_fields.py:54` — custom fields modal POST (**not touched — out of scope, different modal**)
  4. `screen_modal_contact.py:126, 139, 151, 233, 273` — contact/identity modal POST, 5 call sites (**not touched — out of scope, different modal**)
- M08's redirect is NOT via `redirect_to_customer` — it's inlined at `screen_customer_360_activity.py:386` (`return HTMLResponse(content="", headers={"HX-Redirect": ...})`), separate from the M05/tags/contact modals' shared helper. Plan correctly targets this line directly (Step 8) rather than the shared helper — consistent with actual code structure.
- **Test caller enumeration:** `test_quick_outcome_cockpit_post.py` has 4 tests asserting HX-Redirect behavior on the M08 POST path: `test_call_cockpit_source_returns_fragment_no_redirect` (no redirect expected, unaffected), `test_call_cockpit_source_busy_label` (no redirect expected, unaffected), `test_no_source_keeps_hx_redirect` (redirect expected, unaffected — Phase 1 only adds a `worklist` branch, doesn't touch the empty-source default), `test_unknown_source_keeps_hx_redirect` (redirect expected for non-`call_cockpit`/non-`worklist` sources — **docstring becomes inaccurate post-Phase-1, see Finding 4**, though the specific assertion with `source="timeline"` still passes literally).
- No existing test asserts M05 POST's `HX-Redirect` behavior at all (grep for `/customers/.*tasks` in `crm/src/tests` found only bulk-resolve/disposition test files, not a dedicated M05-POST-redirect test) — Phase 1's claim "Existing tests covering M05/M08 redirect behavior still pass" is accurate for M08 but there is no existing M05 test to regress in the first place.
- **Type/count compatibility:** Safe — additive branch, no existing branch removed, no signature change to `redirect_to_customer` itself.

### 2. `execute_side_effects()` signature / call-site count (Phase 2)

- Defined: `activity_side_effects.py:34`.
- Direct callers (grep, repo-wide, excluding test files and docs): **exactly 1** — `screen_customer_360_activity.py:77`, inside the local closure `_run_side_effects(activity, actor_id, **effects)`.
- `_run_side_effects` (the closure wrapping `execute_side_effects`) is itself called from **exactly 2** sites in the same file: `screen_customer_360_activity.py:354` (legacy `POST /customers/{party_id}/log-activity`) and `:634` (new `POST /api/activities/{activity_id}/finalize`).
- **Plan's claim verified accurate**: "execute_side_effects() already receives the full activity object... and is the sole executor for both the legacy M08 POST and the new finalize API" — confirmed exactly 2 logical call sites (via the single wrapper), matching the plan's "single-point fix, not duplicated per caller" framing.
- **Type/count compatibility:** Phase 2's gating change (step 7 branch on `contact_outcome`) is internal to the function body, no signature change — safe for both call sites, no consumer update needed.

### 3. Phase 6b's proposal to remove `handle_dismiss_session` (`/actions/dismiss-session`)

- Route defined: `screen_customer_360_panels.py:296-306` (`@router.post("/customers/{party_id}/actions/dismiss-session")`).
- **All callers (grep, repo-wide):**
  1. `c360_insight_panel.html:55` — `<form hx-post="/customers/{{ party_id }}/actions/dismiss-session" ...>` — the sole production caller (P01 "Hoàn tất ✓" button).
  2. `docs/ui-spec/panels/P01-insight-panel.md:80` — documentation reference, not a code caller, but a stale-doc risk if removed (see Finding 6).
  3. **Test files: zero matches** for `dismiss-session` or `handle_dismiss_session` anywhere under `crm/src/tests` — no regression test exists for this route today.
- **Total caller count: 1 production caller, 0 test callers, 1 doc reference.** Plan's "grep for dismiss-session before removing" check, if performed, would correctly find only the single template caller — removal is technically safe from a caller-count perspective, but Finding 6 flags that "safe by caller count" ≠ "verified by tests," and the doc reference is not in Phase 6's file list.
- **Type/count compatibility:** N/A (route removal, not a signature change) — but note Phase 6's own success criteria says "removed... or left as a documented fallback — decide explicitly" without committing, meaning the actual end-state (and therefore whether the doc needs updating) is undetermined at plan time.

---

## Unresolved Questions

1. Should Phase 1 standardize on a single param name (`source`) for both M05 and M08, or is `caller`/`source` split intentional for some reason not stated in the plan? (Finding 2)
2. Has the worklist-header "no party_id" M05 flow (Phase 1 Step 12) been traced since this review — does `POST /customers//tasks` even route successfully today? (Finding 3)
3. Does Phase 6a intend for the finalize-time auto-claim (`activity_side_effects.py` step 2) to remain as an intentional redundant no-op after 6a ships, or was its continued existence simply not considered? (Finding 1)
4. For Phase 6b, which of options (a)/(b)/(c) is actually being committed to before implementation starts — the plan says "decide at implementation time," but Finding 6/Contract Verifier results show there's no test safety net either way, so the decision should arguably be locked now, not during coding.
