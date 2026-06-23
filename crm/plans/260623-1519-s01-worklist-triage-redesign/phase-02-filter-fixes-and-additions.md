# Phase 02 — Filter Fixes + Additions

**Context:** `plan.md` · proposal §4 · verification report (action_type drift, dead assignee).
**Priority:** P1. **Status:** pending. **Depends:** Phase 01 (filters feed ranking input).

## Overview
Fix the dead "Người nhận" filter, add `action_type` multi-select chips (from real data), customer search, "chỉ giá trị cao" toggle, clear-all + active-count. All state in URL query (HTMX pattern).

## Key insights
- **Dead filter:** `filter_assignee` accepted by `_load_worklist_data` but never used; `list_tasks("","open")` ignores it; AQ has no owner. → Either wire real owner or hide until owner model exists (OQ#1).
- **action_type drift:** chips must come from distinct `action_type` present, not `VALID_ACTION_TYPES` constant (mart emits REORDER_PREEMPT/SECOND_ORDER/HIGH_CANCEL_RISK).
- Filtering happens **before** ranking (Phase 01 ranks the filtered set).

## Requirements
**Functional**
- `action_type` multi-select (chips): `?type=CALL_NOW,WIN_BACK`. Applies to actions; tasks unaffected (or excluded when any type selected — decide: default keep tasks visible under a "Task" pseudo-chip).
- Search `?q=` over customer_name / phone (case-insensitive substring; reuse existing FTS only if cheap, else in-memory filter on loaded set — KISS).
- Value toggle `?min_value=1` → only `value_at_stake_vnd >= THRESHOLD` (constant, e.g. 1_000_000) — actions only.
- Priority filter: keep but fix semantics via normalized urgency (Phase 01) so it works for actions.
- Assignee: if owner data exists → wire to task/action owner; else hide the control (feature-flag/comment), don't ship a dead toggle.
- Clear-all button + active-filter count badge (C05 spec already supports).

**Non-functional:** all filters composable; URL-driven; preserve on refresh/SSE; no N+1 (filter on already-loaded lists).

## Architecture
- Parse query params in `handle_worklist` / `handle_worklist_fragment`; pass filter dict into `_load_worklist_data`.
- Apply filters in `_load_worklist_data` BEFORE `rank_worklist`.
- Chips options computed from distinct action_types in the unfiltered fetch (so chip set is stable).

## Related code files
- **Modify:** `src/adapters/inbound/web/screen_worklist.py` (param parse + filter apply)
- **Modify:** `src/adapters/inbound/web/templates/fragments/worklist_fragment.html` (filter bar markup)
- **Read:** `src/adapters/outbound/sqlite/cache_repository.py`, `docs/ui-spec/components/C05-filter-bar.md`

## Implementation steps
1. Extend `_load_worklist_data` signature: `filters: dict` (assignee, priority, types[], q, min_value).
2. Apply type / search / min_value filters to `all_actions`; priority via normalized urgency.
3. Compute `available_types` (distinct) + `active_filter_count` for template.
4. Update filter bar template: type chips (multi), search input, value toggle, clear-all, count badge. Each control issues `hx-get /worklist/fragment?<merged query>`.
5. Decide assignee: wire or hide per OQ#1.
6. Compile + manual smoke (load `/worklist?type=CALL_NOW`).

## Todo
- [ ] query param parsing + filter dict
- [ ] action_type multi-select chips (from data)
- [ ] search q
- [ ] min_value toggle
- [ ] priority filter fixed via urgency
- [ ] clear-all + active count
- [ ] assignee wired-or-hidden (OQ#1)

## Success criteria
- `?type=CALL_NOW` shows only CALL_NOW actions; chips reflect real mart types.
- `?q=` narrows by name/phone; clear-all resets to defaults; count badge accurate.
- No dead toggle shipped.

## Risks
- Search over large loaded set — fine while no pagination; revisit if list capped server-side later.
- Tasks vs type-filter interaction ambiguous → default: selecting action types hides manual tasks; document in code comment.
