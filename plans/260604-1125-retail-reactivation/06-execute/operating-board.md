---
title: "EXEC-BOARD - Operating Board"
stage: 6
status: living
role: operating-board
source: ../NAVIGATION.md; ../REGISTRY.md; stage README files
updated: 2026-06-15
---

# EXEC-BOARD - Operating Board

**Registry:** [EXEC-BOARD](../REGISTRY.md#exec-board)

File này dùng để quản lý danh mục làm việc sau khi người đọc đã hiểu hệ thống qua [NAVIGATION.md](../NAVIGATION.md). Nó không còn là entrypoint của plan.

## TL;DR

`Priority -> Committed Plan -> Execution -> KPI/Learning -> Update Registry/Diagnosis`

- Navigation chính: [NAVIGATION.md](../NAVIGATION.md).
- Lineage/index chính: [REGISTRY.md](../REGISTRY.md).
- KPI/log/dashboard chính: [06 README](./README.md).
- Board này giữ trạng thái vận hành, blocker và next action.

## Current Operating Focus

| Lane | Current state | Next action | Source |
|---|---|---|---|
| Retail/B2C | Focus đã chốt | Chạy action queue + VOC + channel hygiene | [DEC-001](../03-evaluate/DEC-001-decision-register.md) |
| Revenue now | 116 khách / 1.17 tỷ là lane 0-build | Chốt owner/CSKH capacity | [STAGE-03](../03-evaluate/README.md#lane-tuần-này) |
| Cashflow | Blocked nhưng khẩn | Chủ/kế toán xác nhận AR thật; fix `fact_payments` | [INV-001](../02-understand/INV-001-cashflow-collection-ar.md) |
| Learning | VOC là đòn bẩy ngoài hệ thống | Bắt đầu 5-10 cuộc đầu | [INV-003](../02-understand/INV-003-voc-customer-interviews.md) |
| Infrastructure | Zalo OA mở nhiều play downstream | Chốt owner setup | [STAGE-03 priority](../03-evaluate/README.md#priority-board) |

## Work Board

| ID | Work item | Stage | Status | Owner needed | Next move |
|---|---|---|---|---|---|
| PLAN-002 | Action flows: CALL_NOW / WIN_BACK / REORDER | 05→06 | committed | CSKH lead | Start weekly execution log |
| INV-003 | VOC customer interviews | 02 | open | Owner/CSKH | Run first 5-10 calls, create finding |
| INV-001 | Cashflow collection AR | 02/03 | blocked | Owner/accounting/data | Confirm AR truth + data gap |
| OPP-004 | Payment/contactability/data backlog | 04 | idea | Data owner | Promote only blockers needed for active work |
| OPP-003 | Messaging core | 04 | idea | Marketing/CSKH | Adapt after VOC/product truth |
| PLAN-003 | US gift recipients | 05 | pending | Sales/CSKH | Test 51 hot recipients if capacity exists |

## Stage Health

| Stage | Health | What to watch |
|---|---|---|
| 01 Perspectives | stable | Add new lens only if it spawns a real item |
| 02 Understand | active | Keep FIND-000 current; do not let execution learning bypass 02 |
| 03 Evaluate | active | Keep priority board aligned with blockers |
| 04 Opportunities | broad backlog | Avoid treating ideas as committed |
| 05 Action Plans | runnable | Owner/timeline/KPI must be explicit |
| 06 Execute | tracking | Log weekly, preserve holdout, feed findings back |

## Cadence

| Cadence | Action |
|---|---|
| Before running work | Check [STAGE-03 priority board](../03-evaluate/README.md#priority-board), [STAGE-05 plans](../05-action-plans/README.md), and [REGISTRY.md](../REGISTRY.md) |
| Weekly review | Update [06 execution log](./README.md#execution-log), KPI deltas, blocker status |
| New learning | Create/update finding in [02-understand](../02-understand/README.md), then update decision/priority if needed |
| New commitment | Promote OPP -> PLAN, update registry, add to work board |
| Dropped item | Mark status in canonical file and registry; do not silently delete |

## Source-Of-Truth Routing

| Content | Put it here |
|---|---|
| Current diagnosis | [FIND-000](../02-understand/FIND-000-current-diagnosis.md) |
| Decision detail / audit trail | [DEC-001](../03-evaluate/DEC-001-decision-register.md) |
| Priority / blockers | [STAGE-03 README](../03-evaluate/README.md) |
| Candidate action | [04-opportunities](../04-opportunities/README.md) |
| Committed plan | [05-action-plans](../05-action-plans/README.md) |
| KPI/log/dashboard | [06 README](./README.md) |
| Cross-stage lineage | [REGISTRY.md](../REGISTRY.md) |

## Operating Rule

Nếu một item không có owner, KPI hoặc next move, nó chưa phải việc để chạy. Đẩy ngược về stage 03/04 thay vì để trong board vận hành.
