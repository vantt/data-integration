# Plan — S01 Worklist Triage Redesign

**Created:** 2026-06-23 · **Branch:** main · **Surface:** S01 Worklist/Dashboard
**Goal:** Trị "ngợp" — sắp xếp (banding theo deadline), filter, trình bày. Quick wins không đổi schema.

**Context:**
- Proposal: `plans/reports/design-proposal-260623-1513-s01-worklist-triage-redesign-report.md`
- Verified findings: `plans/reports/from-verification-to-planner-priority-scale-and-action-state-260623-1519-report.md`

## Decisions (chốt)
- Nhóm theo **băng urgency deadline-driven**: 🔴 Quá hạn → ⏰ Hôm nay/Khẩn → 📋 Trong hạn → 💤 Treo lâu.
- Neglect threshold **7 ngày** (`pending_since`), 1 ngưỡng chung. Treo lâu → Băng 3 collapse, KHÔNG auto-mutate.
- Task overdue → Băng 0 luôn hiện, chỉ "Dời hạn/Dọn" thủ công.
- **Priority normalize** bắt buộc (2 thang ngược nhau): action `urgency=10−priority_rank`, task `urgency=7+priority`.
- AI action: KHÔNG xây per-type expiry CRM-side (warehouse tự dọn — signal-based delete verified).

## Phases

| # | Phase | Status | Depends |
|---|-------|--------|---------|
| 01 | [Ranking core (normalize + banding, server-side pure module)](phase-01-ranking-core-normalize-and-banding.md) | ✅ done | — |
| 02 | [Filter fixes + additions](phase-02-filter-fixes-and-additions.md) | ✅ done | 01 |
| 03 | [Presentation — banded collapsible UI](phase-03-presentation-banded-collapsible-ui.md) | ✅ done | 01 |
| 04 | [Tests](phase-04-tests.md) | ✅ done | 01,02,03 |

## Outcome (2026-06-23)
- Tests: **568 passed, 13 skipped, 0 failed** in container (79 ranking + 37 fragment smoke).
- Priority-scale bug fixed (CALL_NOW now correctly urgent); dead assignee filter removed; AQ self-heal confirmed (no CRM-side expiry).
- Resolved OQs: cap 10/băng (B3=5); Band 1 tie = urgency→value; **assignee toggle hidden** (no auth/user context in request lifecycle yet — `crm_task.assignee_user_id` exists, wire when auth lands).
- Deferred: progress bar X=0 (no session tracking); `pytest`/`httpx` not in container reqs (manual install per recreate); 2 orphaned `wl-at--*` CSS rules (dead, harmless).
- Code review done (report: `plans/reports/from-code-reviewer-s01-worklist-triage-redesign-260623-1556-report.md`). Fixed: C1 (added worklist task-cancel route — "Dọn" was 404ing), H1 (removed plan refs from template comments), M1 (assignee excluded from active-filter count), M2 (Band-2 sort comment+fallback), L1 (urgency clamp ≤9), + VALID_ACTION_TYPES aligned to mart. Re-verified: 568 passed/13 skipped.
- Follow-ups done: removed 2 dead `wl-at--*` CSS rules; extracted filter logic to pure `application/worklist_filters.py` (screen_worklist 318→244 LoC) + added `test_worklist_filters.py` (13 tests). `worklist_ranking.py` (267) left intact — single cohesive concept, splitting would hurt readability (KISS).
- Final: **581 passed / 13 skipped** in container. Not committed — awaiting commit decision.

## Scope
- **In:** ranking/banding, filter rework, template/CSS rework, KPI fix, dead-assignee bug, priority-scale bug, dismiss/done split.
- **Out (later):** owner per-customer ("Của tôi" đúng nghĩa), phân trang server thật, per-type expiry, SSE badge changes.

## Key files
- `src/adapters/inbound/web/screen_worklist.py` — `_load_worklist_data` (thin adapter)
- `src/adapters/outbound/sqlite/cache_repository.py` — `list_all_action_queue:121` (`ORDER BY a.priority ASC:152`)
- `src/adapters/inbound/web/templates/fragments/worklist_fragment.html` — render
- `src/application/worklist_ranking.py` — **NEW** pure ranking module
- `src/domain/entities/{task,cache_insight}.py` — priority constants / ActionQueueItem
- `src/tests/` — pytest

## Open questions
1. Owner data per-customer có chưa? Nếu chưa → Phase 02 ẩn filter "Của tôi" (không block).
2. Cap N/băng = 10? Băng 3 cap riêng 5?
3. Interleave task-vs-action trong Băng 1: urgent manual task nên trên hay dưới CALL_NOW? (default: tie theo urgency_score, value break — tunable)
