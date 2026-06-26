---
title: "WS-B S14 Dynamic Branching Script"
description: "Turn S14 call cockpit from a static one-shot script into a dynamic surface driven by a static branching script + a backend interpreter."
status: pending
priority: P2
effort: 6h
branch: main
tags: [crm, s14, approach-script, branching, interpreter]
created: 2026-06-26
---

# WS-B — S14 Dynamic Branching Script

## Decided Model (locked — do not relitigate)

From `plans/260625-1808-s14-approach-script-backend-feed/roadmap-rich-dynamic-script.md` WS-B:

- **Generation**: offline/batch, 1 static branching script per customer. No live LLM during a call.
- **"Dynamic"**: backend interprets static branching tree + staff's recorded interaction → surfaces the next node. Not live regeneration.
- **Tree depth**: shallow (1–2 levels). Most call value is level-1 (opening + first reaction).
- **State model**: light — client holds `current_node_id`; backend is a near-pure function of `(script, node_id, outcome)` → next node. Durable per-call session is out of v1.
- **Capture reuse**: the existing outcome bar (Gọi được/Không nghe/Hẹn lại/Đã mua) already writes to `crm_activity.contact_outcome`. Each navigation step maps to an outcome the staff already records.
- **Entity unchanged**: `ApproachScript.data: dict` absorbs the full branch tree; zero entity change required.

## Phases

| # | Name | Status | Est. | Blockers |
|---|------|--------|------|----------|
| 01 | Branch-tree schema + PoC script | pending | 1h | none |
| 02 | Backend interpreter endpoint | pending | 1.5h | Phase 01 |
| 03 | S14 template rework — progressive node rendering | pending | 2h | Phase 02 |
| 04 | Activity logging per nav step (audit + flywheel) | pending | 0.5h | Phase 03 |
| 05 | PoC end-to-end on customer 603264280 | pending | 1h | Phase 04 |

## Dependencies

- Prerequisite: existing `crm_activity.contact_outcome` enum (`reached|no_answer|callback|refused`) — migration 0013, already live.
- Prerequisite: `FileApproachScriptRepository` — already wired on `app.state.approach_repo`.
- No DB migration needed for v1 (file-based, state-light).

## Acceptance Criteria

1. Staff opens S14 for a customer with a branching script → sees only the **current node's** opening + a small set of outcome buttons (not the full script document).
2. Tapping an outcome button sends `POST /api/parties/{id}/script-nav` with `{current_node_id, outcome}` → backend returns the next node fragment via HTMX swap.
3. Each navigation step writes one row to `crm_activity` (audit trail, keyed with `node_id` in the body or a future `script_node_id` column).
4. If customer has a **legacy v2 flat script** (`approach.talking_points` present, no `nodes` key), S14 renders the old flat view unchanged (backward compatibility).
5. `recommended=false` (R14 STOP gate) still fires before any node is shown — STOP state unchanged.
6. Refreshed_at trust footer always visible (R2 unchanged).

## File Ownership (by phase — no cross-phase file conflicts)

| Phase | Files owned |
|-------|-------------|
| 01 | `branch-tree-schema.md` (this plan dir only — no code) |
| 02 | `crm/src/adapters/inbound/http/script_nav_handler.py` (new), `crm/src/composition.py` |
| 03 | `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` |
| 04 | `crm/src/adapters/inbound/web/screen_customer_360.py` (minor: pass `node_id` through form POST) |
| 05 | `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/603264280.json` (convert) |

## Explicitly OUT of v1

- Durable session engine (server-side call session table)
- Auto-gen of branching trees (WS-C)
- Product × customer-type script library
- Escape-hatch live LLM ("soạn giúp") — roadmap thang-2
- Zalo/SMS fallback per-node (uniform for now)
- Analytics flywheel queries (which branches close most) — data accumulates in `crm_activity`, queries later

## Links

- Schema: [branch-tree-schema.md](branch-tree-schema.md)
- Phase 01: [phase-01-schema-and-poc-script.md](phase-01-schema-and-poc-script.md)
- Phase 02: [phase-02-interpreter-endpoint.md](phase-02-interpreter-endpoint.md)
- Phase 03: [phase-03-s14-template-rework.md](phase-03-s14-template-rework.md)
- Phase 04: [phase-04-activity-logging-per-nav-step.md](phase-04-activity-logging-per-nav-step.md)
- Phase 05: [phase-05-poc-end-to-end.md](phase-05-poc-end-to-end.md)
- Source spec: `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`
- Roadmap: `plans/260625-1808-s14-approach-script-backend-feed/roadmap-rich-dynamic-script.md`
