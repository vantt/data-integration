# CRM Parallel Phases: Warehouse Exports + Bulk-Resolve + Cockpit Queue

**Date**: 2026-07-05 14:30  
**Severity**: Medium  
**Component**: CRM (crm/, data_platform/)  
**Status**: Completed (with known defer)

## What Happened

Delivered 6 phases across CRM in parallel: warehouse data-loop closure (P0), bulk-resolve UI wiring (P0), outcome reason enum (P1), cockpit context+queue+snooze (P1), R14 warn-with-ack UX (P1), and capture UI quick wins (P2). Total: 1 migration, 5 new export assets, 4 staging views, 3 endpoints, 27 tests, ~15 UI components touched.

## The Brutal Truth

The work felt scattered across 6 semi-independent tracks because it was—parallel agent execution without a single codified sequence meant lots of integration points deferred until now. The real pain was the **party_insights deferral**: we wired the UI ("★ Đúc kết" collapsible in M08), wrote the activity export, exposed it to the warehouse, and then discovered the factory wasn't registered in `register_activity_routes`, so creation is a logged no-op. That's a sloppy handoff: UX complete, backend half-baked. Should have verified the full chain before shipping the UI.

The snooze endpoint (D4) introduced a deliberate asymmetry: ICT-anchored resets are deterministic server-side, but the cockpit queue state lives in the URL (no session), which means a snoozed task disappears from the current queue until navigation/refresh. Acceptable for our use case but fragile if we ever add async queue updates.

## Technical Details

**Warehouse Closure (P0):** Added `crm_note`, `crm_tag`, `crm_party_tag`, `crm_party_insight`, `crm_customer_profile_custom` export assets + corresponding `stg_crm__*` staging views. The data loop now closes: NV creates a note in CRM → export fires → `stg_crm__note` materializes → available to dbt models + Metabase. Before: CRM was write-only from warehouse perspective.

**Bulk-Resolve (P0):** M08 GET handler now extracts `resolve_action_ids` and `resolve_task_ids` from query string, populates a templated summary ("Sẽ đóng N task · M hành động"), and POST writes a `custom_fields` snapshot **before** calling `_bulk_resolve`. This ordering matters: if the action queue update fails (which it did in test), we still have the snapshot for audit.

**Outcome Reason Enum (P1):** Migration 0035 added `outcome_reason TEXT` column. The enum is 2-tier: `contact_outcome` is channel-specific (call/messaging/visit have different outcome lists), then `outcome_reason` is an 8-value enum conditional on refused outcome. M08 UI is 2-step pill selection; 22 tests verify the 3-way conditional (channel → outcome → reason). The `mart_crm_activity_log` export includes `is_reached` boolean derived from outcome.

**Cockpit Queue + Snooze (P1):** Migration 0036 persists `value_at_stake_vnd` and `top_affinity_product` on `crm_task` at claim time (immutable snapshot for the queue lifetime). `PATCH /tasks/{id}/snooze?days=N` resets state to "open" and anchors `snoozed_until` to ICT midnight+N. Queue counter in cockpit topbar (`#n/N`) and "Khách kế →" nav; all state is URL-encoded (stateless).

**R14 Warn-with-Ack (P1):** Hard-stop `.s14-frame--stop` CSS replaced with `.s14-frame--warn` + `.s14-locked` (content dims but remains accessible). `POST /customers/{id}/r14-ack` endpoint creates audit activity with `custom_fields={r14_ack: True}`. Client-side unlock is per-session intentionally (if a staff member resets their shift, they see the R14 banner again).

**Capture + Quick Wins (P2):** Custom fields (`skin_type`, `preferred_contact`) wired into cockpit Collect block. "★ Đúc kết" collapsible in M08 is UI-wired but no-op (factory not registered). B1 auto-expand on VIP/GOLD, B2 wake badge on 24h post-snooze, B4 AUTO badge extended to action queue claim. Inline save toast self-removes.

## Root Cause: Party_Insights Deferral

The factory registration was split from the export logic. When export assets were drafted, the `register_activity_routes` scope was unclear, so we deferred the routing registration. Then the UI was wired in parallel, assuming the factory would follow. It didn't—the ticket was closed before circling back to verify the chain. The module exists (`crm.activity.party_insight_factory`) but is never invoked.

## Lessons Learned

1. **Full-chain verification before UI wiring:** If UX depends on a factory or async operation, verify the chain is complete before shipping the UI. A wired-but-noop UI creates false confidence.

2. **URL state is fragile:** The cockpit queue state in the URL works now, but it's not horizontally scalable to async mutations (e.g., if we add a snooze timer that fires server-side, the client-side URL won't refresh). Document this constraint explicitly.

3. **Snapshot at write time, not read time:** The `custom_fields` snapshot before `_bulk_resolve` saved us during testing. Immutable snapshots are cheap and audit-critical.

4. **ICT anchor points:** Snooze resets at midnight ICT (not UTC), which is correct, but we now have 3 different time-anchor patterns across the codebase. Document this in the schema.

## Next Steps

1. **[BLOCKER] Wire party_insight_factory into register_activity_routes** — otherwise M08 insight creation is logged no-op. Owner: [assign to CRM lead]. Estimate: 30min. Test: verify M08 "★ Đúc kết" creates a row in `crm_party_insight`.

2. Verify `mart_crm_activity_log` is queried in active dashboards (not just exported). If not, defer materialization until used.

3. Document cockpit queue URL state constraints: no server-side state, no async updates without client refresh.

4. Add `snoozed_until` index to `crm_task` if snooze queries become hot (not yet flagged as slow).
