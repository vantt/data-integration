# Plan: Return Reasons and Product Quality

> Created: 2026-06-09
> Status: ✅ Partially done
> Origin: `analytics_improvement_opportunities.md` § Return Reasons and Product Quality

## Objective

Identify whether returns are caused by product quality, wrong description, shipping damage, or customer preference. Surface return reason ranking and product quality issue queue.

## Status

**✅ Data layer done** — verified 2026-06-09:
- `fact_order_returns`: 10 rows (Jan–May 2026), columns: `return_id`, `order_id`, `order_code`, `returned_at`, `return_date`, `refund_amount`, `return_quantity`, `return_status`, `refund_status`, `return_reason`, `channel_key`, `date_key`
- Dashboard: **Return Impact Analysis [All]** (Metabase id=75) — ACTIVE
- Blueprint: `docs/analytics-handbook/blueprints/finance_return_impact.md`
- Playbook: `docs/analytics-handbook/playbooks/finance_return_impact.md`

## Todo

- [x] `fact_order_returns` with return_reason, return_status, refund_status
- [x] Return Impact Analysis dashboard (refund liability, return rate by channel)
- [ ] Return reason ranking card (return_reason breakdown — needs more data volume)
- [ ] Product quality issue queue (link return_reason → product_key → supplier)
- [ ] CS notes / free-text reason (source not available yet)
- [ ] Partial return by line item (current grain is per-return, not per-line)

## Note

10 rows is too sparse for reliable ranking. Dashboard exists but reason distribution will be meaningful only when volume grows (target: ~50+ returns/month for segmentation to be useful).
