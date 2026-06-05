# Promo goods — count-once reconciliation (P4-5)

How "hàng tặng" (gift/giveaway promo goods, revenue=0) cost enters the P&L exactly once, the tie-out across the three data sources, and the residual under-count. Settles whether MISA TK64214 promo is double-counted or under-counted.

> **Headline:** Count-once is **sound** — no double-count. Promo cost is counted once **via COGS** (not via a separate deduction). Residual genuine under-count for 2026 ≈ **29.1M VND** (~3.5% of channel_net_profit), almost all explainable (gifting / MISA-internal / not-yet-ingested).

## The mechanism — promo is inside COGS, not a separate deduction

Promo SKUs ship at `line_revenue = 0` but carry a real cost. That cost flows through **`int_order_cogs_reconciled.cogs_goods_primary`** (Sapo-MAC COGS of all shipped lines, incl. zero-revenue promo lines) → **`fact_order_economics.cogs_amount`**. So:

```
gross_profit       = net_revenue − cogs_amount          (cogs_amount ALREADY includes promo cost)
channel_net_profit = net_revenue − cogs_amount + fees   (does NOT deduct promo again)
```

`fact_order_economics.promo_goods_cost` is an **attribution label** ("of which promo"), **not** an independent deduction. Rendering it as a separate `−` waterfall step double-counts on screen (see lesson L109; fixed in detailView). On the MISA side, account **64214** is classified `drop_promo_count_once` → excluded from the overhead pool so it is never counted a second time as overhead.

## The three sources (2026)

| Source | What | Total |
|---|---|---|
| **A** — `std_misa_account_ledger` acct 64214 | MISA promo-goods account, all XK (Phiếu xuất kho) | **103.11M** |
| **B** — `std_misa_sales_lines` (cogs_account 64214) | promo lines tied to Sapo sales docs | 62.7M (2026) |
| **C** — `int_order_promo_goods_cost` | Sapo-MAC per-order promo SKU cost | 135.6M (label only) |

A vs B is **apples-to-oranges**, not a 10× error: A = XK warehouse-dispatch docs; B = SON/BH sales-invoice docs. The earlier "40.4M counted zero times" claim was a **monthly-sum anti-join artifact** — per-document it is wrong (see below).

## Per-document tie-out of A (64214, 103.11M, 139 XK rows)

Bridge MISA→Sapo: `account_ledger.invoice_no` → `sales_lines.invoice_no` → `sales_lines.order_code` (Sapo) → `int_order_cogs_reconciled`. **`invoice_no` resets monthly/quarterly** — join MUST use the 3-part key `(invoice_no, month, amount)`, never `invoice_no` alone (lesson L110).

| Bucket | VND | % of 103M | Counted once? |
|---|---:|---:|---|
| Matched to Sapo order, promo in COGS | **60.34M** | 58.5% | ✅ yes |
| XK00155 — no `invoice_no` (true gifting) | 15.33M | 14.9% | ❌ no |
| Apr+May standalone (no SON in sales_lines) | 12.64M | 12.3% | ❌ no |
| PT-vouchers (PT00002/03, MISA-internal) | 1.16M | 1.1% | ❌ no |
| June (sales_lines not yet ingested) + May tentative | 13.64M | 13.2% | ❓ resolves on ingest |

- **Confirmed counted once: 60.34M.** **Confirmed under-counted: 29.13M.** **Uncertain: 13.64M** (self-resolves when June MISA sales ledger is ingested → most should land in "counted").
- **No double-count** — verified 3 ways: 64214 excluded from overhead pool; 642x excluded from `cogs_goods_misa` (632-only filter); each counted row traces to exactly one `cogs_goods_sapo` source.

## Residual under-count — accepted known limitation

~29.1M (2026, ~3.5% of channel_net_profit) is genuinely counted zero times:
- **XK00155 (15.33M)** — one Feb gifting batch (Hyaluron + Cordyceps), no invoice, no Sapo order → not in COGS.
- **Apr+May standalone (12.64M)** — XK dispatches with no matching SON.
- **PT-vouchers (1.16M)** — MISA-internal documents, no Sapo inventory movement.

These are brand-level gifting / internal flows, not per-order economics. **Decision: accept + document** (do not dilute across orders). Pre-2026 magnitude is unknown (potentially ~similar/yr).

## Data-quality gotchas (guard knowledge)

1. **`invoice_no` is not unique** — MISA resets the counter monthly/quarterly; the same number recurs for unrelated docs. Always join with `(invoice_no, DATE_TRUNC('month', posting_date), amount)`. (Lesson L110.)
2. **VC/VT SKU alias** — MISA uses `VCSC*`, Sapo uses `VTSC*` for the same physical product. ~5.7M (10 rows) shows a **spurious** misa-only gap in `int_order_cogs_reconciled` although the cost IS counted once (Sapo dispatches under the VT-prefix SKU). Resolve via `dim_sku_alias`. (Lesson L111.)

## Guards in place
- `assert_promo_account_not_in_keep_pool` — no `drop_promo_count_once` account leaks into a `keep_*` overhead pool.
- `assert_no_promo_in_overhead_costs` — no promo `cost_type` in `fact_order_costs` OVERHEAD category.

## Source reports
`plans/reports/scout-260605-2230-p4-5-promo-count-once-recon.md` · `scout-260605-2245-xk-standalone-promo-investigation.md` (note: its "40.4M no-order" claim is superseded by the per-document tie-out above) · `scout-260605-2310-misa-invoice-to-sapo-order-match.md`.

## Unresolved
- June 2026 (13.64M uncertain) re-tally after MISA June sales ledger is ingested.
- VC/VT alias fix (5.7M spurious gap) — optional, cosmetic to reconciliation only.
- Pre-2026 standalone-gifting magnitude — not yet quantified.
