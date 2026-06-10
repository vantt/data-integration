# Phase 4 — Metabase Order Lifecycle Cards

**Priority:** P2 · **Status:** pending · **Effort:** 2h · **Blocked by:** P2, P3

## Context links
- Skill: `.skills/metabase-automation/SKILL.md`, `STRATEGY.md`, blueprint template
- Deploy: `/deploy-metabase-blueprint` (ALWAYS via skill — never patch manually, see memory)
- Blueprints dir: `docs/analytics-handbook/blueprints/`
- Mart input: `fact_order_status_transitions` (P2)

## Overview
Add lifecycle cards to a blueprint. Source = the new transition mart joined to fact_orders.
Metrics center on dwell/timing of terminal transitions.

## Cards (KISS — start with 4)
1. **Avg time to complete** — mean `dwell`/total elapsed from first observation → `completed`
   transition. Scalar + trend by month.
2. **Avg time to cancel** — same for `cancelled` terminal. Scalar.
3. **Cancel timing distribution** — histogram of hours-to-cancel (how fast do cancels happen?).
4. **Coverage banner** — text/scalar card: "% of orders with history coverage" (from P3),
   so viewers know the sample is partial. MANDATORY given approximation contract.

## Key insights / guardrails
- Metabase serving TZ = ICT; TIMESTAMPTZ auto-converts — NO manual ICT↔UTC offset (memory).
- Metabase v0.60 native SQL path = `dataset_query.stages[0].native` (pMBQL) (memory).
- Field filters need `field_id` in blueprint (memory) — verify via query_metadata if adding date filter.
- Cards must label data as "history_log derived (approximate, Jan 2026+)".

## Related files
- Create/modify: blueprint .md under `docs/analytics-handbook/blueprints/` (new or extend
  an order-lifecycle blueprint). No code edits — blueprint is source of truth.

## Implementation steps
1. Confirm serving view exists for `fact_order_status_transitions` (rebuilt in P2).
2. Author/extend blueprint .md with 4 cards (SQL against serving DuckDB).
3. Set `> **Database:**` header if overriding default (memory: deploy reads this).
4. Deploy via `/deploy-metabase-blueprint <blueprint.md>`.
5. Verify cards render; sanity-check numbers vs P2 baselines (cancel≈198, completed≈372).

## Todo
- [ ] Draft blueprint cards (4)
- [ ] Add coverage-disclaimer text card
- [ ] Deploy via skill
- [ ] Visual sanity check vs P0/P2 counts

## Success criteria
- [ ] 4 cards deployed and rendering with non-null values.
- [ ] Time metrics in plausible range (hours/days, not negative).
- [ ] Coverage disclaimer visible on dashboard.

## Risk assessment
| Risk | L×I | Mitigation |
|------|-----|------------|
| viewers treat approximate timing as exact | M×H | mandatory coverage + "approximate" labels |
| manual Metabase patching diverges from blueprint | M×M | deploy ONLY via skill (memory) |
| serving view stale after mart rebuild | M×M | rebuild views (Metabase stopped) before deploy |

## Backwards compatibility
New cards only; no edits to existing dashboards/cards. Rollback = delete the new cards.

## Next steps
After deploy → docs-manager updates analytics handbook if dashboard published.
