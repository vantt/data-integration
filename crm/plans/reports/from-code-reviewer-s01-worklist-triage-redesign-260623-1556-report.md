# Code Review — S01 Worklist Triage Redesign

**Date:** 2026-06-23 · **Reviewer:** code-reviewer · **Scope:** uncommitted working-tree changes (branch main)
**Verdict:** Solid core (ranking pure/tested, 117 new tests green). Two real wiring bugs in band-0 task controls + a project-rule violation (plan refs in code). Ship after fixing Critical/High.

## Scope
- Files reviewed: `worklist_ranking.py` (NEW), `screen_worklist.py`, `badge_catalog.py`, `_wl_bands.html` `_wl_filter_bar.html` `_wl_row.html` `task_done_row.html` `worklist_fragment.html`, `test_worklist_ranking.py` (NEW), `test_web_templating.py`
- Verified: ran `pytest test_worklist_ranking.py test_web_templating.py` → **117 passed**. `_parse_date` exercised against 10 formats. Live cache `wh_action_queue` priority distribution queried.

## Overall Assessment
Ranking module is clean, pure, well-documented, fully unit-tested. The two-scale normalization is correct and the OLD bug (`a.priority >= 2` for actions) is gone — replaced by `urgency_score()` comparison, verified at `screen_worklist.py:127-138`. KPI strip regression (4th KPI counted tasks-only) is fixed via `urgent_count`. Main problems are in the band-0 task action buttons (template wiring) and plan-reference comments.

---

## CRITICAL

### C1 — Band-0 "Dọn" (cancel) button hits a non-existent route → silent failure
`_wl_row.html:174-177`
```
hx-patch="/tasks/{{ t.task_id }}/cancel"
hx-target="#task-{{ t.task_id }}" hx-swap="delete"
```
No `/tasks/{task_id}/cancel` route exists. The worklist router only registers done/dismiss/snooze (verified `screen_worklist.py:233,261,275`). The only cancel route is `/customers/{party_id}/tasks/{task_id}/cancel` (`screen_customer_360.py:606`). Result: PATCH → **404**; HTMX does not swap on 4xx, so the row stays and the user thinks nothing happened (silent data-integrity confusion — task not cancelled).
**Fix (two parts):**
1. Point at the real route, guarding null pid:
   `{% if pid %}hx-patch="/customers/{{ pid }}/tasks/{{ t.task_id }}/cancel"{% endif %}`
2. The c360 cancel handler returns the **full tasks panel** HTML, not an empty body — incompatible with `hx-swap="delete"`. Either add a dedicated worklist cancel route (mirroring `handle_mark_task_done`, returning a confirmation row or empty body) OR change swap to match. Recommended: add `@router.patch("/tasks/{task_id}/cancel")` to `screen_worklist.py` returning `HTMLResponse("", 200)` so `hx-swap="delete"` works, same shape as dismiss. Tasks with `party_id=None` otherwise can never be cancelled from the worklist.

---

## HIGH

### H1 — Plan/phase references in code comments (project-rule violation)
Rule `review-audit-self-decision.md §5`: code comments/filenames must not reference plan artifacts (phase numbers, plan paths, finding codes). Found 6:
- `worklist_fragment.html:3` — `see plans/260623-1519-.../phase-01-output-contract.md` (direct plan path)
- `worklist_fragment.html:20` — `(Phase 01)`
- `worklist_fragment.html:64` — `Filter bar (Phase 02 will fill this stub)` — **also stale**: stub is already filled (include is live)
- `worklist_fragment.html:67` — `Banded rows (Phase 03 will replace this stub)` — **also stale**
- `_wl_bands.html:2` — `(always 4 entries from Phase 01 ranking output)`
- `_wl_row.html:146` — `days overdue from Phase 01 neglect_days`
**Fix:** rewrite to describe the WHY/contract, not the plan. E.g. `worklist_fragment.html:3` → "Context vars produced by rank_worklist() in worklist_ranking.py". Drop "Phase 0X will…" stubs entirely (work is done). Keep the symbol reference `rank_worklist` / `neglect_days` (same-codebase symbols are allowed).

---

## MEDIUM

### M1 — `assignee`/`q`/`description` filter & search hit fields, but `assignee` filter is parsed and silently ignored
`_parse_filters` extracts `assignee` (default "me") and `_active_filter_count` counts it, but `_load_worklist_data` never filters by it (no auth context — documented honestly in `_wl_filter_bar.html:22-26`). Consequence: if a URL ever carries `?assignee=all`, `_active_filter_count` returns 1 (badge shows "1 filter active") while nothing is actually filtered — misleading badge. Low user impact today (toggle not rendered), but the dead branch in `_active_filter_count` (`assignee != "me"`) can only mislead. **Fix:** drop the `assignee` clause from `_active_filter_count` until the toggle is wired, OR stop parsing it. Keep the honest NOTE comment.

### M2 — `_sort_key_b2` comment is wrong; missing-pending rows sort to the FRONT
`worklist_ranking.py:151-155`: comment says "oldest pending sorts last (asc)" but ascending sort by ordinal puts the **oldest (smallest ordinal) first**, and `ps_ord = … if ps else 0` makes a missing pending_since sort **first** (ordinal 0 < any real date). In practice SQL always supplies pending_since via `COALESCE(pending_since, generated_date)` (`cache_repository.py:131`), so missing-date never occurs — correctness is fine, but the comment misleads future maintainers and the `else 0` fallback is backwards vs `_sort_key_b0`/`_sort_key_b1` which use `99999` (missing = last). **Fix:** correct the comment; use `99999` for consistency if you want missing → last.

---

## LOW

### L1 — Action `priority=0` would be treated as MAX urgency (defensive gap, not reachable)
Entity maps NULL priority → `0` (`cache_repository.py:167`), and `urgency_score("action", 0) = 10` → lands in Band 1 (urgent). Ranking's own default is `or 9` (least urgent) — the two defaults disagree. Live data: priority ∈ {1..6}, **0 NULLs** (queried `wh_action_queue`), so unreachable today. **Fix (cheap):** clamp in `urgency_score`: `return max(1, min(9, 10 - int(priority_or_rank)))` so rank≤0 caps at 9 instead of 10, aligning with the documented `[1,9]` range in the docstring (line 39 claims [1,9] but 0 yields 10 — docstring is currently inaccurate).

### L2 — Both Python files exceed the 200-LoC project guideline
`worklist_ranking.py` 267, `screen_worklist.py` 303. Guideline (not hard rule). `screen_worklist.py` could split `_parse_filters`/`_active_filter_count`/filter-application into a `worklist_filters.py` helper. Ranking is cohesive; splitting would hurt readability — recommend leaving it. Flag only.

### L3 — Duplicate nested `#worklist-container` id on initial page load
`worklist.html:34` wraps the include in `<div id="worklist-container">` and `worklist_fragment.html:17` re-declares the same id. Two same-id elements on first render (invalid HTML); self-heals after the first outerHTML swap. **Pre-existing** (old templates had identical structure) — not a regression. Cleanest fix: remove the wrapper from `worklist.html` and let the fragment own the id.

---

## NITS

- `_wl_filter_bar.html:65,95,117` use `{{ fq | e }}` — redundant under Starlette `Jinja2Templates` (autoescape on for .html); harmless.
- `_wl_filter_bar.html:38-50` — three stale "Form approach / Simpler:" design-musing comment blocks left in; trim to the one accurate description.
- `_wl_row.html` defines `contact_btn` macro **inside** `wl_row` macro — valid Jinja but re-defined on every row call; negligible cost, slightly unusual. Fine to leave.
- Orphaned `wl-at--*` CSS rules in `ds-extra.css` (known, low sev) — confirm removed or leave for cleanup pass.

---

## What's CORRECT (verified, do not regress)

- Two-scale normalization correct; old `a.priority >= 2` action bug **gone** (`screen_worklist.py:127-138`). `high`=urgency≥8 (ranks 1-2), `urgent`=urgency≥9 (CALL_NOW only) — matches live priority distribution {1:25, 2:303, …}.
- Filters applied BEFORE ranking; `available_types` derived from UNFILTERED data (chip list stable) — `screen_worklist.py:122-124`.
- ICT used for "today" (`today_ict`, UTC+7) — no naive-UTC drift.
- Snooze-wake boundary consistent: SQL returns snoozed rows only when `snoozed_until < today_ICT` (`cache_repository.py:149-150`); band logic `snoozed_until <= today` catches them. No double-handling — `list_all_action_queue` already filters dismissed/snoozed-future/has-open-task; ranking does not re-filter.
- `_parse_date` robust across YYYY-MM-DD, ISO+Z, +offset, space-sep, empty, None, garbage (tested live).
- KPI regression fixed: `value_total` sums actions; `urgent_count` = bands 0+1 (actions+tasks) replaces the old tasks-only "Ưu tiên cao".
- Autoescape on → `rationale_vi`, `customer_name`, `title`, reflected `q` all escaped. No XSS.
- `min_value` parse bounded (ValueError→0); snooze `days` clamped 1-30 (`screen_worklist.py:281`).
- New badge keys (`reorder_preempt`, `second_order`, `high_cancel_risk`) map real warehouse action_types (confirmed in transformation/exposures.yml); `bdg_lookup` lowercases keys so UPPERCASE entity values resolve.
- HTMX filter forms carry all other active filters as hidden inputs → state preserved on any single change (no manual URL merge). Dismiss(action ✕) vs done(task ☑) controls visually + structurally distinct. Empty/all-done state intact (`_wl_bands.html:19-28`).

---

## Recommended Actions (priority order)
1. **C1** — fix `Dọn`/cancel route + swap semantics (add worklist cancel route or repoint to c360 route with null-pid guard).
2. **H1** — strip 6 plan/phase refs from template comments; delete stale "Phase 02/03 stub" lines.
3. **M1** — drop `assignee` from `_active_filter_count` (or stop parsing) until auth wired.
4. **M2** — fix `_sort_key_b2` comment + align missing-date fallback to 99999.
5. **L1** — clamp `urgency_score` to [1,9] to match docstring.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Core ranking solid + tested (117 green); two band-0 task-control wiring bugs (cancel 404 = Critical) and 6 plan-reference comments violating §5 rule must be fixed before ship.
**Evidence:** pytest 117 passed; route grep (only done/dismiss/snooze in worklist router, cancel only under /customers/...); live cache priority {1..6, 0 nulls}; _parse_date tested 10 formats; autoescape via Starlette Jinja2Templates.
**Concerns:** C1 cancel button silently 404s for the user; if band-0 overdue tasks are common this is user-visible breakage.

## Unresolved Questions
1. Should worklist task-cancel return empty body (delete swap) or a confirmation row like task-done? Needs a product/UX call — affects whether to add a new route vs reuse c360's panel-returning handler.
2. `VALID_ACTION_TYPES` in `cache_insight.py:51` omits the 3 new action types — out of scope here, but should it be updated for consistency with the badge catalog and warehouse?
3. Is the band-0 "Dời hạn" (m05 with task_id) confirmed working for worklist tasks with `party_id=None`? m05 resolves party from task (`screen_modals_party.py:174`), so likely yes — not re-tested live.
