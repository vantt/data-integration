# Phase 02 — Screen adapter + template: 2 queue sections

**Status:** ✅ done, with a mid-flight correction. Initial implementation missed the explicit
"check `handle_worklist_band_more`" instruction below — code review caught it: band ids 1/2
exist in both `queue_action_bands` and `my_task_bands`, but the overflow route always
re-ranks actions-only, so it would have injected action rows into a task band's "Xem thêm".
Fixed by rendering `my_task_bands` eager/uncapped (`show_overflow=false`, new param on
`_wl_bands.html`) instead of routing it through the shared lazy-overflow mechanism. See
plan.md Outcome for full detail and the 2 regression tests added.

## Context

`_load_worklist_data()` (`crm/src/adapters/inbound/web/screen_worklist.py:95-...`) currently
calls `rank_worklist(all_actions, all_tasks, today, contacted_party_ids)` (~line 219) and
spreads `ranked` straight into the template context dict (check the `return {...}` around
line 219-270 for the exact keys — includes `bands`, `value_total`, `counts`, `unassigned_tasks`,
`current_user_id`, etc.).

`worklist_fragment.html` currently:
- Renders `unassigned_tasks` team-queue block (lines 74-106) with bare custom markup.
- Includes `_wl_bands.html` (line 109), which iterates `bands` (5-entry list from
  `rank_worklist`) and renders every row via `wl_row()` regardless of kind.

## Requirement

1. In `screen_worklist.py`, after computing `ranked = rank_worklist(...)`, call
   `split_worklist_view(ranked)` (phase 01) and merge its two keys (`queue_actions`,
   `my_task_bands`) into the context dict returned to the template. Keep `ranked["bands"]`
   available too only if something else still reads it directly — check
   `handle_worklist_band_more` (the `/worklist/band/{id}/more` HTMX overflow route, referenced
   in `_wl_bands.html:74`) since it re-renders a single band's overflow and must use the same
   task-filtered rows, not raw `rank_worklist` bands, for bands 0-3 (band 4 stays mixed).
2. In `worklist_fragment.html`:
   - Keep the existing "Hàng Đợi Chung" block (redesign of its rows is phase 03 — don't touch
     row markup here, only its position/heading if needed).
   - Add a new "🎯 Cơ Hội Hệ Thống" `<details>` block immediately after it, same visual
     pattern (`class="wl-band"`, `<summary>` with icon/label/count), BEFORE the
     `{% include "fragments/_wl_bands.html" %}` line.
     - Sub-structure inside: an "urgent" sub-list (open by default) rendering
       `queue_actions.urgent` rows via the existing `wl_row()` macro (import from
       `_wl_row.html` same as `_wl_bands.html` does), and a collapsed "Xem thêm cơ hội"
       `<details>` for `queue_actions.rest` (mirrors the per-band overflow pattern already
       used in `_wl_bands.html:68-79`, but simpler — no HTMX lazy-load needed unless the list
       is large; start with plain render, add lazy-load only if `queue_actions.rest` routinely
       exceeds ~30 rows in practice).
   - Change `_wl_bands.html`'s include to receive `my_task_bands` in place of `bands` (rename
     the variable it reads, or pass `bands=my_task_bands` explicitly at the include call site
     — check `_wl_bands.html:14` `{% set bands = bands | default([]) %}` for the exact context
     var name it expects).
3. Verify `counts.actions` / `counts.tasks` / KPI strip numbers (`worklist_fragment.html:30-49`)
   still reflect the right totals — these come from `ranked["counts"]` (computed from
   pre-band-split `all_actions`/`all_tasks`), so they should already be correct un-touched;
   confirm with a manual render rather than assuming.

## Files to modify

- `crm/src/adapters/inbound/web/screen_worklist.py`
- `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html`
- `crm/src/adapters/inbound/web/templates/fragments/_wl_bands.html` (only if the context var
  it reads needs renaming — prefer passing `bands=my_task_bands` at the include site over
  editing this file, to minimize diff)
- Check `handle_worklist_band_more` route in `screen_worklist.py` for the same
  `my_task_bands` vs `queue_actions` distinction (band 0-3 overflow must pull task rows only).

## Tests / verification

- Extend `test_web_templating.py` fragment smoke tests: render with a mix of unclaimed
  actions + claimed/manual tasks, assert action rows appear inside the "Cơ Hội Hệ Thống"
  block and NOT inside any `wl-band--b0/b1/b2/b3` band, and task rows are the reverse.
- Manual: `docker compose restart crm`, open `/worklist`, confirm 3 sections render, counts
  add up (`Hành động AQ` KPI == queue_actions.count + any in band 4).

## Risks / rollback

- Medium risk: touches the main worklist request path. Keep the diff to context-wiring +
  template restructure only — no change to claim/dismiss/snooze endpoints. If something
  breaks, the previous single `bands` (5-entry, mixed-kind) shape is still produced by
  `rank_worklist()` unchanged, so reverting `screen_worklist.py`'s context dict + the template
  include is a clean rollback (phase 01's helper is additive and can stay unused).
