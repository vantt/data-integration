# Order P&L — design docs cluster

Design/reference docs for the per-order Profit & Loss program (COGS → contribution → fully-loaded net profit). Execution roadmap lives in the plan: `plans/260604-1030-unified-order-pl-cogs-overhead/`.

## The P&L waterfall (single source of truth)
```
net_revenue (Sapo VAT-inclusive: net = total − total_tax)
 − COGS                  (Sapo-MAC primary, sold-lines only, MISA-632 reconciled)  → gross_profit            [tier 1]
 − promo_goods_cost      (gift/giveaway, revenue=0; incl gift-no-invoice = sapo_only)
 − platform/ship/payment (TK641 trace) − shop discount                              → channel_net_profit      [tier 2] ★ decision
 − allocated_overhead    (TK642 net-of-promo + 635 + 641-common, closure-based)     → fully_loaded_net_profit [tier 3] ★ report
```

## Documents in this folder
| Doc | Tier | Scope |
|-----|------|-------|
| `order-pl-schema-design.md` | all | Existing per-order P&L schema (`fact_order_economics`, `fact_order_costs`); the base everything extends. |
| `cogs-reconciliation-design.md` | 1 | COGS: Sapo-MAC primary vs MISA-632 reconciliation; MISA 632/642 mix; promo/gift split; gift-no-invoice; `std_misa_sales_lines`. Flags BUG-1 (642 lumped in COGS). |
| `discount-classification.md` | 2 | Discount taxonomy (10 types) feeding the contribution tier. |
| `overhead-cost-allocation-design.md` | 3 | Closure-based overhead allocation (TK6422 + 6421-keep) → `fully_loaded_net_profit`; MISA monthly + GSheet config. §Quyết định Q1–Q5 (TT133). |
| `overhead-account-ledger-ingestion-design.md` | 3 | Ingest MISA "Sổ chi tiết các tài khoản" (6421/6422) — folder/sensor/section-parser/grain(account×month)/upsert/classification gsheet/count-once. Feeds the overhead pool. |
| `overhead-allocation-and-classification-guide.md` | 3 | **Tra cứu**: cách điền gsheet `overhead_account_classification` (cột/treatment/base) + **công thức phân bổ** (pool→pro-rata→closure) + ví dụ + ước tính trong tháng (Q4-B). |

## Cross-cutting (kept in parent `docs/architecture/`, NOT moved)
- `std-layer-conventions.md` — std-gate rules (apply to all sources).
- `naming-conventions.md` — column/model naming lexicon.

## Key cross-tier rule
**COUNT-ONCE:** promo-goods TK642 (~1.08B, in MISA sales ledger) belongs to `promo_goods_cost` (tier 2); the monthly overhead pool (tier 3) must EXCLUDE it → counted exactly once. See `cogs-reconciliation-design.md` §9 + the plan's phase-03/04.
