---
title: "REG-000 — Workflow Registry"
status: living
role: registry
updated: 2026-06-15
---

# REG-000 — Workflow Registry

Registry là index cross-stage để thấy mỗi item xuất phát từ đâu và sẽ đi đâu. Registry không thay thế canonical file; source of truth vẫn nằm trong file của stage.

## Canonical Item Registry

| ID | Type | Stage | Item | Status | From | Moves To | Canonical Link |
|---|---|---|---|---|---|---|---|
| <a id="pers-001"></a>PERS-001 | perspective | 01 | First-principles lenses | living | archive | INV / OPP | [PERS-001](./01-perspectives/PERS-001-first-principles-lenses.md) |
| <a id="pers-002"></a>PERS-002 | perspective | 01 | Retail first-principles | living | session 2026-06-09 | INV / OPP | [PERS-002](./01-perspectives/PERS-002-retail-first-principles.md) |
| <a id="pers-003"></a>PERS-003 | perspective | 01 | Product × Customer Journey | living | archive | FIND / PLAN | [PERS-003](./01-perspectives/PERS-003-product-customer-journey.md) |
| <a id="pers-004"></a>PERS-004 | perspective | 01 | Engine vs treadmill synthesis | living | session 2026-06-13 | DEC / OPP | [PERS-004](./01-perspectives/PERS-004-engine-vs-treadmill-synthesis.md) |
| <a id="find-000"></a>FIND-000 | finding | 02 | Current diagnosis | living | all stage 02/03 evidence | DEC / OPP / PLAN | [FIND-000](./02-understand/FIND-000-current-diagnosis.md) |
| <a id="find-001"></a>FIND-001 | finding | 02 | Channel mix illusion | resolved | archive + data correction | FIND-004 / DEC-001 | [FIND-001](./02-understand/FIND-001-channel-mix-illusion.md) |
| <a id="find-002"></a>FIND-002 | finding | 02 | Retention leak | resolved | archive + waterfall diagnostic | OPP / PLAN / EXEC | [FIND-002](./02-understand/FIND-002-retention-leak.md) |
| <a id="find-003"></a>FIND-003 | finding | 02 | Customer segments | resolved | customer marts | PLAN / EXEC | [FIND-003](./02-understand/FIND-003-customer-segments.md) |
| <a id="find-004"></a>FIND-004 | finding | 02 | B2B collapse root cause | resolved | PERS-001 + data scan | DEC-001 / INV-001 | [FIND-004](./02-understand/FIND-004-b2b-collapse-root-cause.md) |
| <a id="find-005"></a>FIND-005 | finding | 02 | Product performance assessment | resolved | 4-agent assessment | OPP / PLAN | [FIND-005](./02-understand/FIND-005-product-performance-assessment.md) |
| <a id="find-006"></a>FIND-006 | finding | 02 | Margin and activation signals | resolved | refresh 2026-06-11 | OPP / PLAN | [FIND-006](./02-understand/FIND-006-margin-activation-signals.md) |
| <a id="find-007"></a>FIND-007 | finding | 02 | Fresh scan data + market | resolved | 6-agent scan 2026-06-13 | DEC / OPP / PLAN | [FIND-007](./02-understand/FIND-007-fresh-scan-data-market.md) |
| <a id="inv-001"></a>INV-001 | investigation | 02 | Cashflow collection AR | blocked | FIND-004 | DEC / OPP-004 | [INV-001](./02-understand/INV-001-cashflow-collection-ar.md) |
| <a id="inv-002"></a>INV-002 | investigation | 02 | Demand migration recon | mostly-resolved | PERS-001 | DEC / OPP | [INV-002](./02-understand/INV-002-demand-migration-recon.md) |
| <a id="inv-003"></a>INV-003 | investigation | 02 | VOC customer interviews | open | DEC-001 focus retail | FIND / OPP | [INV-003](./02-understand/INV-003-voc-customer-interviews.md) |
| <a id="inv-004"></a>INV-004 | investigation | 02 | Unboxing experience audit | open | retention leak | OPP / PLAN | [INV-004](./02-understand/INV-004-unboxing-experience-audit.md) |
| <a id="q-001"></a>Q-001 | question | 02 | Open questions | open | all investigations | INV / DEC | [Q-001](./02-understand/Q-001-open-questions.md) |
| <a id="comp-001"></a>COMP-001 | companion | 02 | VOC interview script | ready-to-use | INV-003 | INV-003 results | [COMP-001](./02-understand/COMP-001-voc-interview-script.md) |
| <a id="dec-001"></a>DEC-001 | decision | 03 | Decision register | living | stage 02 findings | OPP / PLAN / EXEC | [DEC-001](./03-evaluate/DEC-001-decision-register.md) |
| <a id="rubric-001"></a>RUBRIC-001 | rubric | 03 | Evaluation framework | living | stage 03 | OPP scoring / PLAN promotion | [RUBRIC-001](./03-evaluate/RUBRIC-001-evaluation-framework.md) |
| <a id="opp-001"></a>OPP-001 | opportunity | 04 | Retention mechanisms | idea | PERS-001 | PLAN | [OPP-001](./04-opportunities/OPP-001-retention-mechanisms.md) |
| <a id="opp-002"></a>OPP-002 | opportunity | 04 | Retail offline plays | idea | PERS-002 | PLAN | [OPP-002](./04-opportunities/OPP-002-retail-offline-plays.md) |
| <a id="opp-003"></a>OPP-003 | opportunity | 04 | Messaging core | idea | PERS-002 / DEC-001 | PLAN | [OPP-003](./04-opportunities/OPP-003-messaging-core.md) |
| <a id="opp-004"></a>OPP-004 | opportunity | 04 | Data backlog | idea | FIND / Q | INV / PLAN | [OPP-004](./04-opportunities/OPP-004-data-backlog.md) |
| <a id="plan-001"></a>PLAN-001 | action_plan | 05 | B2C reactivation phases | committed | DEC-001 / OPP | EXEC | [PLAN-001](./05-action-plans/PLAN-001-b2c-reactivation-phases.md) |
| <a id="plan-002"></a>PLAN-002 | action_plan | 05 | Action flows | committed | PLAN-001 | EXEC | [PLAN-002](./05-action-plans/PLAN-002-action-flows.md) |
| <a id="plan-003"></a>PLAN-003 | action_plan | 05 | US gift recipients | pending | OPP / archive §6 | EXEC / FIND | [PLAN-003](./05-action-plans/PLAN-003-us-gift-recipients.md) |
| <a id="exec-001"></a>EXEC-001 | execution | 06 | Execute board: KPI, log, dashboard | tracking | PLAN | FIND / DEC / PLAN update | [EXEC-001](./06-execute/README.md) |
| <a id="exec-board"></a>EXEC-BOARD | operating_board | 06 | Operating board | living | all stages | weekly execution management | [EXEC-BOARD](./06-execute/operating-board.md) |

## Update Rules

1. Add a row when a new canonical item is created.
2. Keep `Status`, `From`, and `Moves To` current.
3. Canonical files should include a registry backlink when edited materially.
4. Companion files can be listed but do not replace their parent item.
5. Archive and research files are provenance inputs, not workflow items.
