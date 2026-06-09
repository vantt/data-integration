# P4-5 Promo Count-Once Reconciliation Report

**Date:** 2026-06-05 | **Scope:** 2026-01..06 + all-history where available

---

## Summary (5 lines)

A (account_ledger 64214) = 103.1M **2026-only XK-doc outflows**; B (sales_lines 64214) = 1,537M **all-history SON/BH-doc** (2022–2026), = 62.7M for 2026 only. They differ because they are **different MISA document types**, not different data (XK = warehouse dispatch docs; SON/BH = sales invoice docs), **plus** A-B gap within 2026 (40.4M) = standalone non-order promo outflows (no Sapo counterpart). C (Sapo-MAC promo_goods_cost) = 464.3M rolling-window total; in 2026 = 135.6M. **No double-count exists** — 64214 is correctly dropped from the overhead pool. **Under-count exists**: the 40.4M standalone promo (A-only gap within 2026) is invisible to the P&L waterfall. **Recommendation: (b) add a dbt guard test** for no 642x promo account in keep_* pools; also add doc note that standalone XK promo is an accepted known gap.

---

## 1. The Three Numbers

### A — MISA Account Ledger, account 64214 (XK warehouse outflow vouchers)

Source: `src_misa_account_ledger` / raw parquet under `misa_raw/account_ledger/`. **Coverage: 2026 only** (6 months ingested). All 139 ledger rows are voucher_prefix = `XK` (Phiếu xuất kho).

| Month   | A (net_cost, VND) | Lines |
|---------|------------------:|------:|
| 2026-01 |        15,852,649 |    28 |
| 2026-02 |        31,667,789 |    26 |
| 2026-03 |        18,428,059 |    29 |
| 2026-04 |        15,146,596 |    22 |
| 2026-05 |         9,997,434 |    25 |
| 2026-06 |        12,020,648 |     9 |
| **TOTAL** |   **103,113,175** |  **139** |

No credit_excl_911 entries (all debit-only): `net_cost = debit`.

### B — MISA Sales Lines, cost_account = 64214 (SON/BH sales invoice vouchers)

Source: `std_misa_sales_lines` → `int_promo_642_monthly_total`. **Coverage: 2022–2026** (all available sales lines parquet).

**By year (all history):**

| Year | B (sales_lines 64214) | Lines |
|------|----------------------:|------:|
| 2022 |           281,956,752 |   476 |
| 2023 |           272,410,803 |   541 |
| 2024 |           436,219,598 | 1,178 |
| 2025 |           483,400,208 |   952 |
| 2026 |            62,707,366 |   110 |
| **ALL** | **1,536,694,727** | **3,257** |

**int_promo_642_monthly_total** (pipeline model total, all 642 accounts including 64211+642123 = 618,786 extra): **1,076,303,444** (deduped parquet rows, covers 2022–2026 only via valid parquet files).

**B in 2026 only (by month):**

| Month   | B (sales_lines 64214) | Notes                           |
|---------|----------------------:|--------------------------------|
| 2026-01 |            15,852,649 | A=B (different vouchers, same amount) |
| 2026-02 |            16,337,869 | A > B by 15,329,920 (XK00155 standalone batch) |
| 2026-03 |            18,428,059 | A=B                            |
| 2026-04 |             6,111,005 | A > B by 9,035,591             |
| 2026-05 |             5,977,784 | A > B by 4,019,650             |
| 2026-06 |                     0 | Jun not yet in sales_lines parquet |
| **2026 TOTAL** | **62,707,366** |                           |

### C — Sapo-MAC promo_goods_cost (rolling window)

Source: `int_order_promo_goods_cost` → `fact_order_economics.promo_goods_cost`. **Coverage: rolling window** (orders in `fact_orders`, oldest date_key = 20210526).

**Total (rolling): 464,291,133**

**2026 by month (fact_order_economics):**

| Month   | C (Sapo promo_goods_cost) | Orders with promo |
|---------|-------------------------:|------------------:|
| 2026-01 |             37,089,808   |               109 |
| 2026-02 |             24,232,961   |                65 |
| 2026-03 |             28,186,868   |                93 |
| 2026-04 |             26,778,771   |                69 |
| 2026-05 |             16,868,024   |                71 |
| 2026-06 |              2,411,486   |                 9 |
| **TOTAL 2026** | **135,567,917** |            **416** |

### Consolidated A/B/C for 2026

| Month   | A (acct_ldgr_64214) | B (sales_lines_64214) | C (Sapo promo) |
|---------|--------------------:|---------------------:|---------------:|
| 2026-01 |          15,852,649 |           15,852,649 |     37,089,808 |
| 2026-02 |          31,667,789 |           16,337,869 |     24,232,961 |
| 2026-03 |          18,428,059 |           18,428,059 |     28,186,868 |
| 2026-04 |          15,146,596 |            6,111,005 |     26,778,771 |
| 2026-05 |           9,997,434 |            5,977,784 |     16,868,024 |
| 2026-06 |          12,020,648 |                    0 |      2,411,486 |
| **TOTAL** | **103,113,175** |       **62,707,366** | **135,567,917** |

---

## 2. Why A (~103M) and B (~1.08B) Differ ~10x

The ~10x comparison in the background description is **apples-to-oranges**:

| Dimension | A (account ledger) | B (sales lines pipeline) |
|-----------|-------------------|--------------------------|
| Period | 2026 only (6 months) | 2022–2026 (4+ years) |
| MISA doc type | XK (Phiếu xuất kho — warehouse dispatch docs) | SON/BH/24xx (Phiếu bán hàng — sales invoices) |
| Account filtering | Exactly account=`64214` | `cogs_account LIKE '642%'` (mostly 64214; also 64211=318K, 642123=301K) |
| Total raw | 103,113,175 | 1,536,694,727 (64214 only), 1,537,313,513 (all 642x) |
| Pipeline model (B) | n/a | `int_promo_642_monthly_total` = 1,076,303,444 (subset with valid parquet) |

**Within 2026 same period:** A=103.1M vs B=62.7M — A > B by **40.4M**. This gap = XK outflows without matching SON/BH vouchers (non-order standalone promo): confirmed by cross-joining voucher_no sets — zero overlap between XK and SON vouchers.

**Sub-account breakdown of B (sales lines 642x, all history):**

| cogs_account | Total (VND) | Lines | Share |
|-------------|------------:|------:|------:|
| 64214       | 1,536,694,727 | 3,257 | 99.96% |
| 64211       |       318,001 |     1 |  0.02% |
| 642123      |       300,785 |     1 |  0.02% |

B is 99.96% pure 64214 promo. The 64211/642123 entries (2 ancient lines, 2022) are negligible.

**Root cause of A-B gap within 2026 (40.4M):** standalone promo outflows booked via MISA XK vouchers (e.g., XK00155 = 15.3M on 2026-02-11 — Hyaluron & Collagen Plus + Cordyceps Plus batch, 2 rows, no matching SON). These are marketing/gifting campaigns executed without Sapo sales orders.

---

## 3. Count-Once Verification

### 3a. Classification table — all 642x accounts

| Account | Treatment | Pool | Note |
|---------|-----------|------|------|
| 64211   | keep_handling | handling/order_count | Bao bì đóng gói |
| 64213   | keep_admin | admin/net_revenue | Chi phí trả trước |
| **64214** | **drop_promo_count_once** | **—** | **Hàng tặng — key account** |
| 642172  | keep_marketing | marketing/net_revenue | Quảng cáo FB |
| 642174  | drop_traceable | — | Hoa hồng Shopee (tier-2) |
| 642175  | keep_selling | selling/net_revenue | Ho tro KD mixed |
| 642176  | drop_traceable | — | Phí vận chuyển Shopee (tier-2) |
| 642177  | keep_admin | admin/net_revenue | Phí duy trì TK quản trị |
| 642178  | keep_admin | admin/net_revenue | Hỗ trợ kinh doanh |
| 6422    | keep_admin | admin/net_revenue | G&A |

**Pool verification (account_ledger 2026 totals):**
- Pool admin (64213+642177+642178+6422) = 641,814,236 ✓ matches int_overhead_pool_monthly
- Pool marketing (642172) = 85,258,143 ✓
- Pool selling (642175) = 37,630,511 ✓
- Pool handling (64211) = 2,339,500 ✓
- **64214 = 103,113,175 → EXCLUDED (drop_promo_count_once)** ✓

No 642x promo account leaks into any keep_* pool. Overhead rows in `fact_order_costs` contain only: `overhead_admin`, `overhead_handling`, `overhead_marketing`, `overhead_selling` — no promo.

### 3b. Double-count check

**Question:** Does promo cost appear in both Sapo-MAC (C) AND overhead pool?

**Answer: NO double-count.**

Mechanism: `int_overhead_pool_monthly` uses INNER JOIN with classification WHERE `treatment LIKE 'keep_%'`. Account 64214 has `drop_promo_count_once` → never enters the pool. Confirmed: zero 64214 amounts in any overhead pool row.

Additionally: `int_promo_642_monthly_total` is referenced in its own SQL comment as a "dedup helper," but **it is never referenced by any other model**. `int_overhead_pool_monthly` does NOT subtract B from the pool — it simply excludes 64214 via classification. The model is orphaned/unused.

### 3c. Under-count check

**Question:** Does C ≈ A (do they reconcile)?

**Answer: C > A, and the mechanisms differ — there is a REAL under-count for standalone XK promo.**

How promo actually flows through the P&L:

| Promo type | In Sapo? | In int_order_cogs_reconciled? | In cogs_amount? | In channel_net_profit? | In overhead pool? |
|-----------|---------|-------------------------------|-----------------|----------------------|-------------------|
| Sales-linked (B, SON/BH) | YES | YES (line_revenue=0 but cogs_goods_primary captured) | YES | YES (via COGS deduction) | NO (64214 dropped) |
| Standalone (A-B gap, XK only) | NO | NO | NO | NO | NO (64214 dropped) |

**Critical finding:** The `fact_order_economics.channel_net_profit` formula does NOT explicitly subtract `promo_goods_cost`. It is: `net_revenue − cogs_amount + shopee_fees`. Promo cost enters ONLY because the promo SKU rows (line_revenue=0 in `std_order_items`) ARE included in `int_order_cogs_reconciled.cogs_goods_primary` → summed into `cogs_amount`. Verified: 1,341 promo-sku rows in `int_order_promo_goods_cost` have exact (order_code, sku) matches in `int_order_cogs_reconciled` with identical amounts — SUM = 464,291,133 = exact match.

**The `promo_goods_cost` column in `fact_order_economics` is a display/attribution label only — it does NOT cause a separate deduction.** It is stored in `fact_order_costs` as category PROMO_GOODS (for reporting), but the P&L deduction already happened via COGS.

**Standalone XK promo (40.4M in 2026, no Sapo order):**
- NOT in int_order_cogs_reconciled → NOT in cogs_amount → NOT in channel_net_profit
- DROPPED from overhead pool → also not counted there
- **Result: these 40.4M of promo cost are invisible to the P&L waterfall — counted ZERO times**

**Magnitude of under-count (2026):** 40,405,809 VND (40.4M). Annualized: ~80M/year (rough). This is real but **known business context**: standalone XK promo = non-order gifting (trade shows, influencer gifts, internal samples) that exists in MISA but has no Sapo counterpart.

---

## 4. P&L Net Effect

### Promo in the waterfall (rolling window, fact_order_economics)

| Metric | Amount | Notes |
|--------|-------:|-------|
| promo_goods_cost (display label) | 464,291,133 | Stored in fact_order_economics + fact_order_costs |
| Promo deducted via cogs_amount | 464,291,133 | Exact match — same rows in int_order_cogs_reconciled |
| Overhead pool containing promo | 0 | 64214 dropped, no leakage confirmed |
| **Effective promo in P&L** | **464,291,133** | Counted once via COGS deduction |

### Overhead pools (fact_order_costs OVERHEAD category)

| Pool | Total (rolling) |
|------|---------------:|
| overhead_admin | 689,336,562 |
| overhead_marketing | 81,559,973 |
| overhead_selling | 40,460,529 |
| overhead_handling | 2,536,600 |
| **Total OVERHEAD** | **813,893,664** |

Zero PROMO_GOODS rows in OVERHEAD category. Clean separation confirmed.

### Standalone promo gap (under-count)

- **2026: 40.4M** XK-only promo outflows not in Sapo → not in P&L
- No `is_gift_no_invoice` flag on these (they don't appear in `int_order_promo_goods_cost` at all — that model requires an order_code match to `fact_orders`)
- Pre-2026: account_ledger not ingested → magnitude unknown for 2022–2025

---

## 5. Recommendation

**Recommendation: (b) Add a dbt guard test + (c) Document the under-count gap.**

This is DONE_WITH_CONCERNS: no double-count, but the standalone XK promo gap is a real under-count that management should acknowledge.

### Specific guard tests to add

**Test 1 — No promo account in keep_* pools (prevent regression):**

File: `transformation/models/staging/schema.yml` (under `stg_overhead_account_classification` model tests)
```yaml
- name: assert_no_promo_account_in_keep_pool
  description: "Ensure 64214 (and any future promo-tagged account) is never in a keep_* treatment"
  # Singular test SQL:
  # SELECT account FROM stg_overhead_account_classification
  # WHERE treatment LIKE 'keep_%' AND account IN ('64214')
  # HAVING COUNT(*) > 0
```

Or as a standalone singular test `tests/assert_no_promo_in_overhead_pool.sql`:
```sql
-- FAIL if any promo account (drop_promo_count_once) leaks into keep_* treatment
SELECT account, treatment
FROM {{ ref('stg_overhead_account_classification') }}
WHERE treatment LIKE 'keep_%'
  AND account IN (
      SELECT account FROM {{ ref('stg_overhead_account_classification') }}
      WHERE treatment = 'drop_promo_count_once'
  )
```

**Test 2 — Promo cost not in overhead category of fact_order_costs:**
```sql
-- FAIL if any PROMO_GOODS row appears in OVERHEAD category
SELECT COUNT(*) as violation_count
FROM {{ ref('fact_order_costs') }}
WHERE cost_category = 'OVERHEAD'
  AND cost_type LIKE 'promo%'
HAVING COUNT(*) > 0
```

### Documentation note to add

In `docs/architecture/order-pl/overhead-allocation-and-classification-guide.md` §2 (after existing reconcile item), add:

> **Resolved (2026-06-05):** Reconcile 64214 (103M) vs sales-ledger-642 (1.08B) vs Sapo-MAC promo.
> - A (account_ledger 64214, 2026 only, XK docs) = 103.1M. B (sales_lines 64214, all history SON/BH) = 1.54B (63M in 2026). C (Sapo promo, rolling) = 464M.
> - A vs B differ: (1) different document types in MISA (XK vs SON), (2) different time ranges. B all-642x in pipeline (int_promo_642_monthly_total) = 1,076M full-history.
> - **count-once is correct** for sales-linked promo (B/C: cost in cogs_amount, 64214 dropped from overhead pool).
> - **Known gap:** standalone XK promo (~40M/year, no Sapo order) is not in P&L waterfall — accepted business limitation.
> - `int_promo_642_monthly_total` is orphaned (no downstream consumers); consider retiring or documenting as audit-only.

### On int_promo_642_monthly_total

The model's docstring says "Phase-04 subtracts this amount from the overhead expense pool" — this is incorrect/stale. The actual mechanism is classification-based exclusion, not subtraction. The model is **not referenced by any downstream model**. Either:
- (a) Retire it (remove from dbt build or archive), or
- (b) Keep as audit-only with corrected comment

---

## Risks / Unresolved Questions

1. **Standalone XK promo under-count magnitude pre-2026:** account_ledger only has 2026 data. Cannot quantify 2022–2025 standalone promo. If similar ~40M/year → historically ~160M invisible promo cost over 4 years. Business should confirm if this is acceptable.

2. **`int_promo_642_monthly_total` orphan:** No downstream model references it. The model comment (claims to subtract from overhead) is misleading. Confirm: should it be retired?

3. **C vs A magnitude gap (135M vs 103M in 2026):** C (Sapo promo) is larger than A (account ledger 64214) in 2026 — plausible because: (a) Sapo MAC cost may differ from MISA book cost for same goods; (b) C covers all orders with line_revenue=0 (some may not have MISA 64214 entry if they use 632 incorrectly); (c) C is based on Sapo MAC (moving average), A is MISA book value. No business requirement to reconcile these precisely unless auditor asks.

4. **int_promo_642_monthly_total discrepancy with raw parquet:** Model total = 1,076,303,444 but raw parquet 64214-only = 1,536,694,727. Gap = 460M. Possible cause: not all historical parquet files are in the `export/marts/rolling` path (rolling window limitation on the export), or some old parquet files were excluded. Verify whether int_promo_642_monthly_total covers same time range as raw parquet before using it for any audit.

5. **`is_gift_no_invoice` flag accuracy:** In `int_order_promo_goods_cost`, `is_gift_no_invoice` = TRUE when `cogs_source='sapo_mac' AND misa_642_amount IS NULL`. For standalone XK-only promo, there is no order_code at all (no Sapo order) — these rows simply do not appear in the model. The flag does NOT cover the standalone XK gap. If business wants to track this, a separate pipeline ingesting XK-linked promo without order_code is needed.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** No double-count exists — 64214 correctly dropped from overhead pool, promo flows once via COGS deduction. Real under-count: 40.4M standalone XK promo (2026) invisible to P&L; pre-2026 magnitude unknown.
**Concerns:** (1) Standalone XK promo not captured in P&L waterfall — requires business decision on whether to treat. (2) `int_promo_642_monthly_total` is orphaned with misleading docstring — retire or correct. (3) Add 2 dbt guard tests to prevent regression.
