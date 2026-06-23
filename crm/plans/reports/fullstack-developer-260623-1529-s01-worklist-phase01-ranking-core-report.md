# Phase 01 Implementation Report — S01 Worklist Ranking Core

**Date:** 2026-06-23 · **Phase:** 01 — Ranking core (normalize + banding)
**Plan:** `plans/260623-1519-s01-worklist-triage-redesign/`

---

## Files Modified / Created

| File | Action | LoC |
|---|---|---|
| `crm/src/application/worklist_ranking.py` | CREATED | 168 |
| `crm/src/adapters/inbound/web/screen_worklist.py` | REWRITTEN | 198 |
| `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` | REWRITTEN | 62 |
| `crm/src/adapters/inbound/web/templates/fragments/_wl_filter_bar.html` | CREATED | 38 |
| `crm/src/adapters/inbound/web/templates/fragments/_wl_bands.html` | CREATED | 149 |
| `plans/260623-1519-s01-worklist-triage-redesign/phase-01-output-contract.md` | CREATED | 168 |

---

## Tasks Completed

- [x] `worklist_ranking.py` pure module (no DB/HTTP imports)
- [x] `urgency_score(kind, priority_or_rank)` — action: 10-rank; task: 7+priority
- [x] `assign_band(...)` — 4-band logic, first-match-wins, all 6 cases covered
- [x] Within-band sort keys (B0 due asc/value desc; B1 urgency desc/value desc/due asc; B2 urgency desc/value desc/pending asc; B3 value desc)
- [x] `rank_worklist(actions, tasks, today)` — returns bands list + value_total + counts + urgent_count + task_open
- [x] `today_ict()` helper (UTC+7 boundary)
- [x] Defensive date parsing (multi-format try/except, mirrors `_is_cache_stale`)
- [x] `WorklistRow` dataclass
- [x] `_load_worklist_data` refactored: accepts `filters` dict, applies all 5 filter types before ranking
- [x] Priority filter bug fixed: uses normalized urgency (high>=8, urgent>=9) for both actions and tasks — CALL_NOW (rank=1→urgency=9) now correctly appears in "urgent"
- [x] `available_types` derived from unfiltered data (for Phase 02 type chips)
- [x] `active_filter_count` computed
- [x] `handle_worklist` + `handle_worklist_fragment` parse full filter dict from query params
- [x] `worklist_fragment.html` rewritten as skeleton (KPI strip, progress bar, two includes, freshness footer)
- [x] `_wl_filter_bar.html` stub — preserves existing assignee/priority toggles
- [x] `_wl_bands.html` stub — renders all bands end-to-end with full action/task row fidelity (dismiss, snooze, quick-contact, task done HTMX preserved)
- [x] `phase-01-output-contract.md` — complete variable table, band struct, WorklistRow fields, ActionQueueItem fields, Task fields, filter state, query-param names, file ownership, HTMX behaviour table, deviations

---

## Compile / Test Status

- **AST parse** (`python -c "ast.parse(...)"` on both .py files): PASS
- **Logic assertions** (import + 6 band rules + 6 urgency cases): PASS
  - CALL_NOW (rank=1) → urgency=9 ✓
  - WIN_BACK (rank=4) → urgency=6 ✓
  - ELSE (rank=9) → urgency=1 ✓
  - normal/high/urgent task → 7/8/9 ✓
  - overdue task → band 0 ✓
  - task due today → band 1 ✓
  - urgency=9 action → band 1 ✓
  - woke-up snoozed action → band 1 ✓
  - neglected action (>=7d) → band 3 ✓
  - recent non-urgent action → band 2 ✓
- **No DB/HTTP imports in ranking module**: confirmed (pure)
- `today_ict()` returns correct ICT date

---

## Deviations from Spec

See `phase-01-output-contract.md §9`. Summary:
1. `urgency_score` is two-arg (kind + scalar) not one-arg (entity) — avoids entity import into pure module.
2. `assign_band` takes explicit scalars not a `row_like` object — same reason; simpler to unit-test.
3. `WorklistRow.urgency` (not `urgency_score`) — avoids redundant suffix.
4. `rank_worklist` returns `dict` with bands+metadata — a flat list would require template re-grouping.

---

## Issues / Concerns

None blocking. One observational:
- `_wl_bands.html` at 149 LoC is a stub — Phase 03 replaces it entirely, so the line count is temporary and acceptable.
- `screen_worklist.py` sits at 198 LoC (2 under limit). If Phase 02 adds helpers here, extract to a `worklist_filter_helpers.py` module.

---

## Next Steps Unblocked

- **Phase 02** (filter bar): can start immediately. Reads `available_types`, `active_filter_count`, `filters` dict. Owns `_wl_filter_bar.html`. Query-param contract in §3/§6 of output contract.
- **Phase 03** (banded UI): can start immediately. Reads `bands` list structure (§2), `WorklistRow` fields (§3), payload field tables (§4, §5). Owns `_wl_bands.html`. Must preserve HTMX behaviours in §8.
- Both phases can run in parallel — no shared file ownership.
