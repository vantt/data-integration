# Standalone XK Promo (64214) — P&L Under-count Investigation

**Date:** 2026-06-05 | **Scope:** 2026-01..06 (account_ledger ingested period)
**Analyst:** Read-only investigation against raw parquet + dbt SQL

---

## Summary

The "standalone XK promo" (40.4M in 2026) is **inventory goods dispatched via MISA Phiếu xuất kho (XK) without any corresponding Sapo sales order**. All 139 account_ledger rows for account 64214 are XK-type with offset_account=156 (inventory), confirming pure warehouse outflows. The items are exclusively branded health supplements dispatched in small-to-medium batches (1 product per voucher line), consistent with **influencer/KOL gifting and trade/marketing sampling** — no customer or invoice reference is available in the ledger format. At 40.4M it represents **5.3% of the 2026 overhead pool (767M keep_* accounts), 39% of total 64214 ledger (103M), and ~4.8% of 2026 channel_net_profit (~836M rolling)**. The standalone portion is **lumpy, not steady** — driven by a few bulk campaign batches (XK00155 alone = 15.3M in Feb). Recommended treatment: **(b) route into marketing overhead pool** for the standalone-identified portion. The mechanism is technically feasible — standalone XK rows are already identifiable in the raw ledger (voucher_no appears in account_ledger but NOT in sales_lines) — with moderate pipeline effort.

---

## 1. Standalone XK 64214 Postings (2026)

### What "standalone" means precisely

Two MISA document types both book account 64214:
- **XK (Phiếu xuất kho)** → appears in `std_misa_account_ledger` only. Warehouse dispatch voucher. No invoice, no customer reference.
- **SON/BH (Phiếu bán hàng)** → appears in `std_misa_sales_lines` only. Sales invoice tied to a Sapo order.

When A (account_ledger XK total) = B (sales_lines SON total) for a month, the SAME gifting event was booked under both doc types — the SON/BH version has a Sapo order anchor, so cost flows through COGS. **The "standalone" gap = A − B = XK dispatches with no SON counterpart = no Sapo order.**

### Month-by-month breakdown

| Month | A (XK ledger) | B (SON sales_lines) | Standalone gap | Notes |
|-------|-------------:|--------------------:|---------------:|-------|
| 2026-01 | 15,852,649 | 15,852,649 | 0 | Fully order-linked |
| 2026-02 | 31,667,789 | 16,337,869 | **15,329,920** | XK00155 bulk campaign |
| 2026-03 | 18,428,059 | 18,428,059 | 0 | Fully order-linked |
| 2026-04 | 15,146,596 | 6,111,005 | **9,035,591** | |
| 2026-05 | 9,997,434 | 5,977,784 | **4,019,650** | |
| 2026-06 | 12,020,648 | 0 | **12,020,648** | B=0: Jun SON not yet ingested; true standalone TBD |
| **TOTAL** | **103,113,175** | **62,707,366** | **40,405,809** | |

**Key:** Jan and Mar show A=B → zero standalone that month. The 40.4M (2026) is the gap across 4 months; Jun figure may partially resolve when Jun sales_lines are ingested.

### Confirmed standalone voucher set (Feb + Apr + May = 28.4M confirmed; Jun TBD)

Key large standalone postings:
| Voucher | Date | Product | Amount (VND) | Notes |
|---------|------|---------|-------------:|-------|
| XK00155 | 2026-02-11 | Hyaluron & Collagen Plus | 9,252,209 | Bulk campaign batch |
| XK00155 | 2026-02-11 | Cordyceps Plus | 6,077,711 | Same bulk batch |
| XK00546 | 2026-06-04 | Fucoidan | 3,611,111 | Jun (B not yet ingested) |
| XK00547 | 2026-06-05 | Hyaluron & Collagen Plus | 2,698,561 | Jun |
| XK00387 | 2026-04-22 | Natto Kinase | 2,161,884 | Apr standalone |
| XK00535 | 2026-06-01 | Natto Kinase | 2,161,884 | Jun |
| XK00269 | 2026-03-20 | Hyaluron & Collagen Plus | 2,313,052 | Part of Mar (A=B month — this IS order-linked) |

All vouchers share: account=64214, offset_account=156 (inventory), no invoice_no, no counterparty field in format.

---

## 2. Characterization (Buckets by Purpose)

### What the data shows

All 139 rows, 134 distinct vouchers, covering **7 distinct product SKUs** (branded health supplements). No customer name or invoice reference field exists in the account_ledger format (by design — it's an internal warehouse dispatch report, not a sales report). Description column = product name only.

| Product | Count | Total (VND) | % of 103M total |
|---------|------:|------------:|----------------:|
| Hyaluron & Collagen Plus | 57 | 35,235,490 | 34.2% |
| Coix Beauty tablets (Vit C) | 35 | 26,784,175 | 26.0% |
| Natto Kinase | 16 | 15,007,483 | 14.6% |
| Cordyceps Plus | 8 | 10,129,519 | 9.8% |
| Fucoidan | 9 | 9,027,779 | 8.8% |
| Shark Cartilage Extract | 12 | 5,817,615 | 5.6% |
| Hyaluron & Collagen with Swallow's Nest | 2 | 1,111,114 | 1.1% |
| **TOTAL** | **139** | **103,113,175** | **100%** |

### Purpose inference

The data does NOT contain a customer/recipient field, so precise bucketing requires business context. Based on dispatch pattern and design doc:

| Bucket | Evidence | Est. % of 40.4M standalone |
|--------|----------|--------------------------|
| **Influencer/KOL gifting** | Large single-voucher batches (XK00155 = 15.3M), products matching hero SKUs for beauty/wellness influencers | ~50–60% |
| **Trade/channel sampling** | Regular small batches (154K–770K each), recurring patterns across months | ~30–40% |
| **Internal/employee use** | Possible for small-value single-unit dispatches, cannot confirm without business context | ~5–10% |

**Cannot distinguish buckets from ledger alone** — the description field has only product name. To confirm, business must match XK voucher numbers to internal gifting records / influencer campaign logs.

---

## 3. Materiality

### Reference pool figures (from recon report)
- Total overhead pool 2026 (keep_* accounts, rolling): **813.9M** (all-time); 2026 keep_* portion implied ~767M from pool verification
- Total 64214 ledger 2026: **103.1M**
- Confirmed standalone gap 2026: **40.4M** (incl Jun unverified) / **28.4M** (Feb+Apr+May confirmed)
- 2026 channel_net_profit (rolling, Jan–Jun): **~135M per month** × 6 ≈ **~835M** (rough, using Sapo promo data as proxy; exact figure requires fact_order_economics query)

### Materiality table

| Denominator | Amount | Standalone 40.4M as % |
|-------------|-------:|----------------------:|
| Overhead pool 2026 (all keep_* ~767M) | 767,000,000 | **5.3%** |
| Total 64214 ledger 2026 (103M) | 103,113,175 | **39.2%** |
| Estimated 2026 channel_net_profit | ~835,000,000 | **~4.8%** |
| 2026 total revenue (est. ~2.5B based on overhead pool ratio) | ~2,500,000,000 | **~1.6%** |

### Monthly pattern: LUMPY, NOT STEADY

| Month | Standalone |
|-------|----------:|
| 2026-01 | 0 |
| 2026-02 | 15,329,920 (Feb spike — XK00155 bulk) |
| 2026-03 | 0 |
| 2026-04 | 9,035,591 |
| 2026-05 | 4,019,650 |
| 2026-06 | 12,020,648 (includes unverified SON-less Jun) |

The lumpiness means **per-order impact varies wildly by month** — Feb would receive ~2× the overhead allocation it would otherwise, zero impact in Jan/Mar. This argues against treating it as a smoothly-allocated overhead, and instead favors a separate line item OR a monthly-smoothed approach.

---

## 4. Options Analysis

### Option (a): Accept as known limitation — document only

**Treatment:** No pipeline change. Add a doc note acknowledging the gap.

| | |
|---|---|
| **Feasibility** | Trivially feasible — zero code |
| **P&L impact** | 40.4M/year invisible to per-order P&L and company P&L waterfall. channel_net_profit overstated by same amount. |
| **Pros** | Zero effort; no risk of introducing errors. Appropriate if standalone promo is strategically decided at brand level, not order level. |
| **Cons** | P&L is structurally incomplete. Fully_loaded_net_profit overstated by ~40M/year (4.8% of CNP). Management cannot see true cost of marketing gifting campaigns. |
| **Data feasibility** | N/A |

### Option (b): Route into overhead pool (un-drop the standalone portion)

**Treatment:** Change classification for standalone XK 64214 to `keep_marketing` (or `keep_selling`). The pipeline must distinguish standalone XK from order-linked XK within account_ledger.

**The identification mechanism:**
- Standalone XK = voucher_no appears in `src_misa_account_ledger` (XK docs) but NOT in `src_misa_sales_lines` (SON/BH docs)
- This anti-join is feasible at the ledger line level BEFORE the `std_misa_account_ledger` monthly rollup
- Monthly total standalone = SUM(debit) WHERE voucher_no NOT IN (sales_lines voucher_no set)
- OR simpler: use the A−B monthly difference at `(account, period_month)` grain directly

**Two sub-approaches:**
- **(b1) Anti-join at line level:** new intermediate model `int_standalone_xk_promo_monthly` that anti-joins account_ledger XK rows vs sales_lines. Output: monthly standalone amount for 64214. Feed this amount into the overhead pool as `keep_marketing`.
- **(b2) Monthly delta:** compute `MAX(0, account_ledger_64214_monthly − sales_lines_64214_monthly)`. Simpler, but month-boundary effects if the SON lags XK by days at month-end.

| | |
|---|---|
| **Feasibility** | Moderate effort. The anti-join identifier is available (voucher_no in both sources). Need: (1) new intermediate model; (2) adjust classification or add a new account entry for the standalone portion; (3) fix closure test to account for partial 64214. |
| **Complications** | (i) `std_misa_account_ledger` currently rolls up to (account, month) — loses line-level voucher_no. Need to either push the anti-join upstream or create a separate model. (ii) Jun's B=0 (not ingested) would incorrectly classify ALL Jun XK as standalone until SON arrives — a timing issue requiring provisional handling. (iii) The classification gsheet currently has a single row for account 64214 = `drop_promo_count_once`. Splitting it into "order-linked" (drop) vs "standalone" (keep_marketing) cannot be done at the account level — needs a sub-account or a separate model feeding the pool directly. |
| **Pool assignment** | `keep_marketing / net_revenue` is the most logical fit (these are marketing/campaign goods). Could also be `keep_selling` if considered general sales support. |
| **P&L impact** | 40.4M enters overhead pool → allocated pro-rata to all orders. Impact per order: +40M/~835M = ~4.8% overhead rate increase on 2026 net revenue base. Average order: ~50K VND extra overhead allocated (rough). |
| **Pros** | P&L is complete; marketing gifting cost is visible and allocated across the revenue-generating activity it supports. Consistent with TT133 treatment of marketing expenses. |
| **Cons** | Allocation dilutes accuracy (standalone promo benefits channel/brand broadly, not per-order); creates a timing/lag issue when SON parquet lags XK; adds pipeline complexity; requires changing the 64214 classification logic beyond a simple gsheet row. |

### Option (c): Separate marketing expense line (company-level P&L only)

**Treatment:** Create a separate reporting line "standalone_marketing_promo" at the company P&L summary level. Does NOT enter the per-order overhead allocation. Visible in the company waterfall but not in fully_loaded_net_profit per order.

| | |
|---|---|
| **Feasibility** | Moderate. Requires: (1) new model that computes monthly standalone XK 64214 (same anti-join as b1); (2) a reporting-layer view or Metabase card that adds this line below fully_loaded_net_profit in the company summary. No change to per-order P&L. |
| **P&L impact** | Per-order fully_loaded_net_profit unchanged. Company-level P&L gains a new "marketing gifting" line. EBITDA/operating profit correctly reduced at company level without distorting per-order economics. |
| **Pros** | Cleanest conceptually: standalone gifting is a brand/marketing decision, not directly tied to individual order economics. Company P&L is accurate. Per-order P&L not distorted by lumpy campaign spending. |
| **Cons** | Per-order P&L still does not reflect this cost. Requires dual reporting layers (per-order + company-level). |

---

## 5. Recommendation

**Recommended: Option (c) — company-level marketing expense line, with Option (a) (document) as minimum if (c) is deferred.**

**Rationale:**

1. **Lumpiness makes per-order allocation noisy.** XK00155 (15.3M in one batch in Feb) would spike Feb overhead allocation by ~2× then zero in Jan/Mar. Allocated pro-rata it creates distorted per-order economics that mask operational performance.

2. **Purpose is brand/campaign, not order.** Influencer gifting and trade samples are decisions made at brand strategy level, not tied to fulfilling any specific order. Allocating them per-order is economically inappropriate.

3. **Data feasibility is medium.** The anti-join (voucher_no anti-join between account_ledger and sales_lines) is technically doable but requires a new intermediate model and careful handling of the Jun timing issue (B=0 until SON ingested). For option (c) the anti-join is still needed — but its output feeds a reporting line, not the overhead pool, which is lower-stakes.

4. **Numbers support materiality for visibility.** 40.4M = 4.8% of CNP — not negligible. It should appear somewhere in the P&L waterfall. Option (a) (silent omission) is not acceptable long-term.

**Implementation path for (c):**
1. Build `int_standalone_xk_promo_monthly`: `SUM(account_ledger_64214_debit) - SUM(sales_lines_64214_debit)` grouped by month. Flag months where Jun B=0 as provisional.
2. Add a `standalone_marketing_promo` column or fact row in the company-level P&L reporting model.
3. Add doc note + dbt test confirming this amount is NOT in the overhead pool.
4. Business decision on which Metabase card surface this.

**Effort:** 1–2 dbt models + 1 dbt test + doc update. Medium complexity, low risk.

**If (c) is too much now:** Option (a) — document the gap with the exact numbers, commit to revisiting after sales_lines for Jun is ingested.

---

## 6. Risks / Unresolved Questions

1. **Jun 2026 standalone amount TBD:** B=0 for Jun because sales_lines parquet not yet ingested. The 12.0M Jun figure may partially resolve when SON is ingested. True standalone for Jun could be anywhere from 0 to 12M. Pipeline should NOT lock in 12M as standalone until Jun SON is ingested.

2. **Purpose confirmation needed from business:** Ledger description = product name only. Cannot distinguish influencer gifting vs trade sampling vs internal use from data alone. Business should confirm whether all XK00xxx standalone docs are authorized marketing campaigns or if any are internal/unauthorized.

3. **Pre-2026 magnitude unknown:** Account_ledger only ingested from 2026. If standalone XK promo runs ~40M/year, cumulative 2021–2025 gap = ~160–200M invisible in historical P&L. Management should confirm if historical standalone promo exists and whether retroactive accounting is needed.

4. **Timing lag risk for option (b):** If implemented, the anti-join depends on SON parquet being ingested before the month's account_ledger is finalized. A ~1 month lag between XK dispatch and SON invoice booking is plausible in MISA. Option (c) avoids this issue by not feeding the overhead pool.

5. **Is A=B (Jan, Mar) truly "order-linked"?** The recon shows Jan and Mar have A=B exactly — consistent with all XK dispatches having matching SON entries. But this needs business confirmation: were there truly zero standalone gifting events in Jan and Mar, or were some just not separately booked?

6. **Account 156 offset confirms goods-out but not recipient:** All rows show TK đối ứng = 156 (inventory). This confirms inventory left the warehouse but provides no information on recipient (influencer, trade partner, employee). The MISA system may have this in the voucher notes/attachment, but it is not captured in the parsed ledger columns.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Standalone XK 64214 = 40.4M (2026) of inventory dispatched via warehouse docs with no Sapo order anchor, lumpy (driven by bulk campaign batches), concentrated in 5 SKUs across all 7 product lines. Recommended treatment is (c) a separate company-level marketing expense line rather than per-order allocation. The gap is real, material (~5% of overhead pool, ~5% of CNP), and should not remain silently omitted.
**Concerns:** (1) Jun 2026 standalone amount (12M) is provisional until Jun sales_lines SON parquet is ingested — pipeline must not lock it in. (2) Business confirmation needed: purpose of standalone XK docs (influencer/trade/internal) — data alone cannot distinguish. (3) Pre-2026 magnitude entirely unknown — historical under-count may be substantial (est. ~160M over 2021–2025).
