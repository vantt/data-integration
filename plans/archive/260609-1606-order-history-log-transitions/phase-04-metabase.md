# Phase 4 — Metabase Order Lifecycle Cards

**Priority:** P2 · **Status:** done (2026-07-06) · **Effort:** 2h · **Blocked by:** P2, P3

**Output:** `docs/analytics-handbook/blueprints/metabase/order_lifecycle_transitions.md` —
deployed to collection `Operations > Order Lifecycle`, Dashboard ID 146 "Order Lifecycle
Transitions [Cross]", 4 cards (IDs 2440-2443). Deployed via
`node --env-file=.env.local .skills/metabase-automation/scripts/deploy_from_markdown.js <blueprint>`.

**Blocker resolved:** `fact_order_transitions` was invisible to `bootstrap_serving_views.py`
because of a materialization config bug fixed in phase-02 (was `materialized='table'`, should
inherit project-default `external`/parquet). Fixed, serving views rebuilt (Metabase stop → run →
restart), then blueprint deployed.

**Verified card output (via Metabase API `/api/card/:id/query`), all non-null and plausible:**
| Card | Result |
|---|---|
| Coverage & Caveat | "99.0% of orders (Jan 2026+)..." |
| Avg Time to Complete (trend) | 4 months, 0.02–1.29 days |
| Avg Time to Cancel | 180.6 hours |
| Cancel Timing Distribution | 28 rows, 0.3–224.4 hours |

## Context links
- Skill: `.skills/metabase-automation/SKILL.md`, `STRATEGY.md`, blueprint template
- Deploy: `/deploy-metabase-blueprint` (ALWAYS via skill — never patch manually, see memory)
- Blueprints dir: `docs/analytics-handbook/blueprints/`
- Mart input: `fact_order_transitions` (built in P2 as `fact_order_transitions.sql`, not `fact_order_status_transitions`)

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
- [x] Draft blueprint cards (4)
- [x] Add coverage-disclaimer text card — implemented as a live scalar (recomputes each load, not static text)
- [x] Deploy via skill
- [x] Visual sanity check vs P0/P2 counts — queried all 4 cards via API, values non-null and plausible

## Success criteria
- [x] 4 cards deployed and rendering with non-null values.
- [x] Time metrics in plausible range (hours/days, not negative) — 0.02-1.29 days to complete, 180.6h avg / 0.3-224.4h range to cancel.
- [x] Coverage disclaimer visible on dashboard — top card, full width, "99.0%... APPROXIMATE" wording.

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

**Note on baseline mismatch:** step 5 above expected "cancel≈198, completed≈372" — those were
rough guesses from phase-02's original spec, not from actual data. Real mart counts (verified
2026-07-06): cancelled=28, completed=160, shipped=62, payment_received=17, updated=181 (total
1485 transition rows over 1037 orders). The lower cancel/complete counts reflect the
`transition_type` classification logic actually implemented (first-touch-only per type, not
every occurrence) — not a data quality issue.
