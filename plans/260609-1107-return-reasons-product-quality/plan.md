# Plan: Return Reasons and Product Quality

> Created: 2026-06-09
> Status: Backlog (decided 2026-07-08 — remaining items not worth pursuing until reason-capture is fixed upstream)
> Origin: `analytics_improvement_opportunities.md` § Return Reasons and Product Quality
> (re-verified 2026-07-08: reason ranking cards + SKU-line approximation now live via `int_return_sku_lines`; product quality queue/supplier link/CS notes still not built — see Todo)

## Objective

Identify whether returns are caused by product quality, wrong description, shipping damage, or customer preference. Surface return reason ranking and product quality issue queue.

## Status

**✅ Data layer + reason ranking done, product quality queue not built** — re-verified 2026-07-08:
- `fact_order_returns`: **13 rows** (Jan 12 – Jun 22 2026, up from 10 at 2026-06-09) — growth still far below the ~50/month target
- `return_reason` field: **12/13 rows blank**, only 1 populated (`"KHÁCH TRẢ HÀNG"`) — the underlying data quality gap, not just volume, is what blocks meaningful reason segmentation
- `int_return_sku_lines` (NEW, `transformation/models/intermediate/sapo/int_return_sku_lines.sql`) — return × `product_key` grain (35 rows / 13 returns / 11 products), proportional refund allocation by line revenue. Explicitly documented as an **approximation** (all SKUs in a returned order appear, not just the confirmed-returned SKU) — covers "partial return by line item" and gives product_key linkage, feeds `mart_sku_economics_monthly` return-adjusted margin
- Dashboard: **Return Impact Analysis [All]** — blueprint now has a dedicated **"Tab: Return Reasons"** with "Top 10 Return Reasons by Revenue Impact" + "Return Reason by Volume" cards (blueprint moved to `docs/analytics-handbook/blueprints/metabase/finance_return_impact.md`)
- Blueprint: `docs/analytics-handbook/blueprints/metabase/finance_return_impact.md` (path changed, added `metabase/` subfolder)
- Playbook: `docs/analytics-handbook/playbooks/finance_return_impact.md`
- **No supplier link and no dedicated "product quality queue" surface** — `product_key` join exists but nothing joins to supplier or surfaces a triage queue

## Todo

- [x] `fact_order_returns` with return_reason, return_status, refund_status
- [x] Return Impact Analysis dashboard (refund liability, return rate by channel)
- [x] Return reason ranking card ("Tab: Return Reasons" in blueprint) — built, but data still too sparse/blank to be meaningful
- [ ] Product quality issue queue (link return_reason → product_key → supplier) — product_key link exists (`int_return_sku_lines`), supplier join + queue surface still missing
- [ ] CS notes / free-text reason (source not available yet) — `return_reason` itself still 92% blank
- [x] Partial return by line item — `int_return_sku_lines` (return × product_key, documented approximation, not exact per-line)

## Note

13 rows (was 10) is still too sparse, and 12/13 have blank `return_reason` — the ranking cards exist but have near-nothing to rank. Real blocker is upstream reason capture (Sapo return flow doesn't force a reason), not just volume.

**Decision (2026-07-08):** leave as backlog. Don't invest in product quality queue / supplier link / CS notes / forcing reason capture upstream until user revisits — not a technical blocker, a deliberate priority call.
