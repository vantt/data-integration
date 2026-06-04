# Unified Order P&L — COGS Reconciliation + Overhead Allocation

> Merge of two adjacent P&L tiers into ONE program, managed end-to-end. Source designs:
> `docs/architecture/order-pl/cogs-reconciliation-design.md` (COGS tier) +
> `docs/architecture/order-pl/overhead-cost-allocation-design.md` (overhead tier) +
> `docs/architecture/order-pl/order-pl-schema-design.md` (existing schema).

## Goal waterfall (single source of truth)
```
net_revenue (Sapo VAT-inclusive: net = total − total_tax)
 − COGS                  (Sapo-MAC primary, sold-lines only, MISA-632 reconciled)  → gross_profit          [tier 1]
 − promo_goods_cost      (gift/giveaway, revenue=0; incl gift-no-invoice = sapo_only)
 − platform/ship/payment (TK641 trace) − shop discount                              → channel_net_profit    [tier 2] ★DECISION
 − allocated_overhead    (TK642 net-of-promo + 635 + 641-common, closure-based)     → fully_loaded_net_profit[tier 3] ★REPORT
```

## Locked decisions (CONTRACT — every phase file must obey)
1. **COGS = Cost of Goods SOLD (Option A):** Sapo-MAC primary; MISA TK632 = reconciliation only (variance, never summed). Sold lines only (`revenue>0`).
2. **Promo/gift split:** `revenue=0` lines → `promo_goods_cost` (NOT COGS). Gift-no-invoice (Sapo has MAC, MISA none) → kept from Sapo-MAC, flag `cogs_source='sapo_only'`.
3. **Keep tiers separate** — never overwrite `channel_net_profit`; only ADD `fully_loaded_net_profit`. Reports show both.
4. **COUNT-ONCE (cross-tier crux):** promo-642 (~1.08B, sitting in MISA sales ledger) belongs to `promo_goods_cost` (tier 2). The monthly overhead pool (tier 3) **MUST exclude** that sales-ledger-642 portion → counted exactly once.
5. **std-gate:** add `std_misa_sales_lines` (faithful, keep `cogs_account`/accounts + `cost_account_group`). MISA is multi-report → report-specific std names.
6. **Closure:** `SUM(allocated_overhead per period) == pool_period` (dbt test).
7. **Verify every phase via a real Dagster run** (manual launch → SUCCESS).

## Phases
| # | File | Scope | Status |
|---|------|-------|--------|
| 01 | `phase-01-data-foundations-std-gate.md` | `std_misa_sales_lines`; ingest MISA monthly overhead (`overhead_costs_monthly`) + gsheet `overhead_allocation_config` | std-gate ✅ DONE (std_misa_sales_lines + int repoint, verified Dagster); overhead ingestion = schema chốt, implement deferred to phase-04 (blocked on Q1 MISA API vs export) |
| 02 | `phase-02-cogs-reconciliation.md` | `int_order_cogs_reconciled` (Sapo-MAC primary + MISA-632 recon + variance) **incl. BUG-1** (filter 632 in `fact_order_economics`/`fact_order_costs`) | ✅ DONE — BUG-1 interim (f4f5783) + `int_order_cogs_reconciled` built (rolling parquet, var-driven primary, 5 tests pass, serving bootstrapped, verified Dagster). cogs_goods_primary=48.45B (Sapo-MAC full coverage); both=4,696 recon, misa-only=4,375, none=975 pure-return. Fact repoint = phase-05 |
| 03 | `phase-03-cost-taxonomy-promo-642-dedup.md` | `promo_goods_cost` (revenue=0 split, gift-no-invoice); cross-tier **642 count-once** rule | TODO |
| 04 | `phase-04-overhead-allocation.md` | `int_order_overhead_allocation` (closure-based pools/base) + `fully_loaded_net_profit` | TODO |
| 05 | `phase-05-pl-marts-serving.md` | unified `fact_order_economics`/`fact_order_costs` columns + serving views + Metabase P&L | TODO |
| 06 | `phase-06-detailview-pl.md` | detailView per-line COGS/margin + reconciliation panel + full P&L (coordinate w/ concurrent detailView work) | TODO |
| 07 | `phase-07-shopee-fee-fixes.md` | **Shopee platform-fee fixes** (tier-2): BUG-2 service-fee double-count (use F detail, drop D aggregate) + BUG-3 payment-fee column rename. Corrects `channel_net_profit`. | ✅ DONE (commit f4f5783) — parser+stg+int+marts, drift guard, guard test, clean re-ingest (also fixed months 2-4 dup parquet), verified Dagster run SUCCESS |

## Dependencies
`01 → 02 → 03 → 04 → 05 → 06`. **Tier-correctness fixes BUG-1 (in 02) + phase-07 (Shopee fees) must precede phase-04** — they fix the COGS (tier-1) and platform-fee (tier-2) inputs that overhead allocation uses as its `channel_net_profit` base. Both can ship early/independently. 04 needs 01 (overhead data) + 03 (count-once) + clean tier-1/tier-2. 06 last (after concurrent detailView stream merges).

## Coordination / concurrency (CRITICAL)
- A concurrent work-stream (same git identity) is editing `detailView` (customer pages), and ran P1/P2 renames + the overhead design. **`fact_order_economics.sql` / `fact_order_costs.sql` are shared** — confirm not being edited before phases 02/05; avoid interleaved commits.
- **Phase 06 (detailView) only after** the concurrent detailView work lands.
- Overhead decisions ✅ RESOLVED (overhead doc §Quyết định Q1–Q5): Q1=export thủ công (+estimate tạm); Q2=pool 642-only net-promo (635 out, 641-common defer v2); Q3=2-pool ABC-lite (handling→order_count, admin→net_revenue); Q4=closure + provisional nhẹ (trailing rate, est→actual swap); Q5=base=fulfilled orders (cancel-pre-fulfill excluded, returns keep, RTO in). Phase-04 design-ready; còn cần 1 export Sổ cái TK642 thật để seed + xác nhận count-once.

## Reports
Plan reports → this dir; analysis basis: `plans/reports/analysis-260604-0001-inventory-v2-data-nature.md`.
