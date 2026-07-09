# Phase 01 — Ranking split helper

**Status:** ✅ done — `split_worklist_view()` added to `worklist_ranking.py`; 9 tests in
`TestSplitWorklistView` (test_worklist_ranking.py), all passing. Shape ended up as symmetric
band-dicts (`queue_action_bands` + `my_task_bands`) rather than the flat urgent/rest dict
originally sketched here — revised after discovering the existing `/worklist/band/{id}/more`
overflow route already re-ranks actions-only by band id, so reusing that exact shape lets both
sections render through `_wl_bands.html` unmodified. See plan.md Outcome for the overflow-route
follow-up this discovery required in phase 02.

## Context

`rank_worklist()` (`crm/src/application/worklist_ranking.py:190-322`) returns `bands` = list of
5 dicts (`id, label, icon, rows, count, total_value, vip_count`), ordered `4,0,1,2,3`. Rows in
bands 1 and 2 currently mix `kind=='action'` and `kind=='task'`. Band 0 is task-only, band 3 is
action-only, band 4 is mixed by design (recently-contacted, either kind) — do not touch that
invariant.

Do NOT change `assign_band`, `urgency_score`, sort keys, or `rank_worklist`'s own return shape.
Existing 79+ tests in `test_worklist_ranking.py` pin that behavior — this phase only adds a new
pure function consuming `rank_worklist()`'s output.

## Requirement

Add `split_worklist_view(ranked: dict) -> dict` to `worklist_ranking.py` that regroups
`ranked["bands"]` into a presentation-ready structure without re-deriving urgency/band/sort:

```python
{
    "queue_actions": {
        "urgent": [...],    # rows from band 1 where kind=='action' (urgency>=9 / CALL_NOW-tier)
        "rest": [...],      # rows from band 2 + band 3 where kind=='action', concatenated in
                             # that order (band 2's existing sort, then band 3's existing sort —
                             # do not re-sort across the concatenation)
        "count": int,       # urgent + rest
    },
    "my_task_bands": [...], # same 5 band dicts, each with `rows` filtered to kind=='task';
                             # band 3 will always end up count=0 (fine — template's existing
                             # `{% if band.count > 0 %}` guard hides it)
}
```

Notes:
- `my_task_bands` band 4 keeps its rows **unfiltered** (mixed kind) — copy band 4 through
  as-is, do not filter by kind. This preserves the existing "Đã liên hệ" behavior exactly
  (first, collapsed, both kinds).
- `queue_actions.urgent`/`rest` must never include a row already routed to band 4 by
  `rank_worklist` (that routing already happened via `contacted_party_ids` before this
  function runs — band 1/2/3 by construction exclude contacted parties). No extra filtering
  needed here; just don't reach into band 4 when building `queue_actions`.
- Keep it a pure function: input is the `dict` `rank_worklist()` already returns, output is a
  plain dict of the same nested primitives (dataclass instances, ints) — no new I/O, no new
  dataclass needed unless it clearly reduces complexity (prefer plain dict per existing module
  style).

## Files to modify

- `crm/src/application/worklist_ranking.py` — add `split_worklist_view()` near the bottom,
  after `rank_worklist()`. Add a one-line module-level docstring note explaining the 3-way
  split (queue / my-tasks / contacted), mirroring the existing docstring style.

## Tests

Add to `crm/src/tests/test_worklist_ranking.py` (follow existing test style/fixtures in that
file — check existing `_action`/`_task`-equivalent fixtures there first, do not duplicate):
- Mixed input (2 actions + 2 tasks spanning bands 0/1/2/3) → assert `queue_actions` contains
  only the action rows, `my_task_bands` contains only task rows in bands 0/1/2, band 3 of
  `my_task_bands` has count 0.
- Band 4 (contacted) row of either kind → appears in `my_task_bands`'s band-4 entry, NOT
  duplicated into `queue_actions`.
- Empty input → both `queue_actions.count == 0` and all `my_task_bands` counts 0 (no crash).

## Risks / rollback

- Low risk: pure function, additive only, `rank_worklist()` untouched. Revert = delete the new
  function + its tests if wiring in phase 02 needs a different shape.
