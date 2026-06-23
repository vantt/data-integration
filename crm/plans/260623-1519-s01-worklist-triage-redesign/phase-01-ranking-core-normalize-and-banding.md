# Phase 01 — Ranking Core (normalize + banding)

**Context:** `plan.md` · proposal report §3 · verification report (priority scales).
**Priority:** P0 (foundation; Phase 03 renders this output). **Status:** pending.

## Overview
Build a pure server-side ranking module that merges actions + tasks into one urgency-banded, sorted list. Wire into `_load_worklist_data`. Fix priority-scale bug. No template change here (Phase 03 consumes the output shape).

## Key insights
- Two opposite priority scales → MUST normalize (verification report). action `urgency=10−priority_rank`; task `urgency=7+priority`.
- `priority_rank` already encodes action-type tier — don't add a separate tier list.
- AI action present ⇒ valid (warehouse self-heals). `pending_since` = neglect signal, not deadline.
- Use **ICT** for "hôm nay" boundary (pipeline TZ = Asia/Ho_Chi_Minh; avoid 0h–7h drift).
- `list_all_action_queue` already excludes dismissed/snoozed-future/has-open-task; woke-up snoozed rows return with `status='snoozed'` + past `snoozed_until`.

## Requirements
**Functional**
- New module `src/application/worklist_ranking.py` (pure, no I/O), functions:
  - `urgency_score(item) -> int` — normalized (higher=urgent) for both sources.
  - `assign_band(item, today_ict) -> int` — 0/1/2/3 per rules below.
  - `rank_worklist(actions, tasks, today_ict) -> list[WorklistRow]` — unify, band, sort, return ordered rows + band metadata + counts.
- `WorklistRow` lightweight dataclass: `{kind: 'action'|'task', band, urgency_score, value, ref_id, payload}` (payload = original entity for template).
- Band assignment (first match wins):
  1. task & `due_at` date < today_ict → **Band 0 Quá hạn**
  2. (task `due_at` date == today) OR (urgency_score ≥ 9 i.e. task urgent / action CALL_NOW) OR (action `status=='snoozed'` & `snoozed_until` ≤ today) → **Band 1**
  3. action & neglect (`today − pending_since ≥ 7d`) & not Band 1 → **Band 3**
  4. else → **Band 2**
- Sort within band:
  - 0: `due_at` asc (most overdue first) → value desc
  - 1: urgency_score desc → value desc → due asc
  - 2: urgency_score desc → value desc → `pending_since` asc
  - 3: value desc
- Neglect age in days for Band 2 badge ("đã chờ N ngày") computed here (1–6d).

**Non-functional:** module < 200 LoC; pure & unit-testable; no DB/HTTP imports; snake_case (Python).

## Architecture
- Ranking lives in **application layer** (alongside `task_service.py`). Adapter (`screen_worklist.py`) stays thin: fetch → call `rank_worklist` → pass banded structure to template.
- ICT today: add small helper `today_ict()` (reuse existing ICT util if present in `screen_worklist.py`/filters; else local `date` via `datetime.now(timezone(timedelta(hours=7))).date()`).
- Date parsing: `due_at` is ISO datetime (TIMESTAMPTZ-origin); `pending_since`/`generated_date` are `YYYY-MM-DD`. Parse defensively (mirror `_is_cache_stale` multi-format try).

## Related code files
- **Create:** `src/application/worklist_ranking.py`
- **Modify:** `src/adapters/inbound/web/screen_worklist.py` (`_load_worklist_data` → return banded structure; fix priority filter to use `urgency_score`/normalized compare; drop broken `a.priority >= 2`)
- **Read:** `src/domain/entities/task.py`, `src/domain/entities/cache_insight.py`, `src/adapters/outbound/sqlite/cache_repository.py`

## Implementation steps
1. Add `urgency_score` mapping (action: `10 - priority_rank`; task: `7 + priority`).
2. Add `WorklistRow` dataclass + `assign_band` + within-band sort comparators.
3. Add `rank_worklist(actions, tasks, today_ict)` → returns `{bands: [{id,label,rows,count,total_value}], counts, value_total, done_progress?}`.
4. Refactor `_load_worklist_data` to call it; keep returning `party_extras`, `refreshed_at`, `is_stale`. Replace the buggy priority filter: filter on normalized urgency (high = urgency≥8, urgent = urgency≥9) for BOTH sources.
5. Keep `cache_repository` ORDER BY as-is (ranking now owns ordering) — or simplify later; do not regress.
6. Run compile check: `python -c "import crm.src.application.worklist_ranking"` (in container/venv).

## Todo
- [ ] `worklist_ranking.py` pure module
- [ ] `urgency_score` + `assign_band` + sorts
- [ ] `rank_worklist` aggregator (bands + counts + value totals)
- [ ] wire `_load_worklist_data`, fix priority filter bug
- [ ] compile check passes

## Success criteria
- CALL_NOW (rank1) ranks above WIN_BACK (rank4) and above a normal task. ✔ via urgency_score.
- A task `due_at` yesterday lands Band 0 regardless of priority.
- An action pending ≥7d (non-urgent) lands Band 3.
- "Urgent" priority filter now includes CALL_NOW (regression of `:84` bug fixed).
- Module has zero adapter imports (pure).

## Risks
- ICT boundary parsing mismatch → wrong band at 0h–7h. Mitigate: single `today_ict()` helper + unit tests at boundary.
- `priority_rank` ELSE=9 / unknown action_types → urgency=1 (lowest), acceptable default.
- Interleave task-vs-action in Band 1 is a value judgment (OQ#3 in plan) — default tie by urgency_score then value; tunable constant.
