# Phase 04 — Tests

**Context:** `plan.md`. **Priority:** P1. **Status:** pending. **Depends:** Phase 01,02,03.

## Overview
Unit-test the pure ranking module (highest value, deterministic) + smoke-test the rendered fragment. Follow existing pytest patterns in `src/tests/`.

## Key insights
- Ranking is pure → exhaustive unit tests cheap & high-confidence.
- Template rendering testable via existing `test_web_templating.py` pattern.
- Priority-scale + banding are the regression-prone areas — cover explicitly.

## Requirements
**`test_worklist_ranking.py` (new)**
- `urgency_score`: action CALL_NOW(rank1)→9 > WIN_BACK(rank4)→6; task urgent(2)→9, normal(0)→7. Cross-source: CALL_NOW ≥ normal task.
- `assign_band`:
  - task `due_at` yesterday (ICT) → Band 0
  - task due today → Band 1; action CALL_NOW → Band 1; snoozed woke-up (snoozed_until past) → Band 1
  - action pending_since ≥7d, non-urgent → Band 3
  - else → Band 2
  - **ICT boundary:** item dated "today 00:30 ICT" not misfiled as overdue (regression on naive UTC).
- `rank_worklist`: ordering within bands (0: most-overdue first; 1/2: urgency→value); counts + value totals correct; empty input → empty bands.
- Regression: "urgent" priority filter includes CALL_NOW (old `:84` bug).

**Smoke (`test_web_templating.py` extend or new)**
- Fragment renders with mixed actions+tasks → contains band headers, counts, no template error.
- Empty + all-done states render.
- action_type from mart set (REORDER_PREEMPT etc.) renders a styled badge (no raw fallback crash).

## Related code files
- **Create:** `src/tests/test_worklist_ranking.py`
- **Modify:** `src/tests/test_web_templating.py` (fragment smoke)
- **Read:** `src/tests/` conftest/fixtures for entity builders.

## Implementation steps
1. Locate existing Task/ActionQueueItem fixtures in tests; reuse/extend.
2. Write ranking unit tests (table-driven where possible).
3. Add fragment smoke tests.
4. Run: `pytest crm/src/tests/test_worklist_ranking.py crm/src/tests/test_web_templating.py -q` (venv/container).
5. Fix failures per recommendations; do not weaken assertions to pass.

## Todo
- [ ] ranking unit tests (urgency, band, sort, ICT boundary, counts)
- [ ] priority-filter regression test
- [ ] fragment smoke tests (bands, states, badges)
- [ ] all green

## Success criteria
- All new tests pass; existing worklist tests still pass.
- ICT-boundary test guards 0h–7h misfiling.
- Coverage of the two priority scales explicit.

## Risks
- Container vs host test env (DuckDB/SQLite paths) — ranking tests are pure (no DB), so run anywhere; template smoke may need Jinja env only.
