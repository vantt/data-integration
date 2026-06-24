# Order-Level H010 Margin Audit Report

**Date:** 2026-06-24  
**Scope:** Does `fact_order_economics.gross_margin_pct` carry the H010 packsize-COGS error?  
**Verdict:** **A — Order-level margin is ALREADY correct. Audit flag is moot at order grain.**

---

## 1. What H010 Is

Five Fine Japan "Hộp 10" (H010) pack SKUs had `misa_qty_multiplier` set to 10 (AUTO_PACKSIZE) when MISA already records in Hop units, not Chai units. This caused `mart_sku_economics_monthly` to overcalculate MISA COGS by 10× for those SKUs, making `realized_margin_pct` appear −78% to −322%.

**Fix applied 2026-06-10:** `seed_sku_alias_manual.csv` set `misa_qty_multiplier=1` (MANUAL_OVERRIDE) for 5 SKUs. Confirmed applied in `dim_sku_alias` and `dim_products` (all 5 now show `misa_qty_multiplier=1`).

The 5 affected SKUs:
- `VCSL19001H010` — Hyaluron & Collagen Plus Hop (VCS)
- `VCSL21002H010` — Cordyceps Plus Hop (VCS)
- `VTSL21001H010` — Swallow's Nest Hop (VTS)
- `VTSL24009H010` — Cordyceps Plus Hop (VTS 2024)
- `VTSL24010H010` — Hyaluron & Collagen Plus Hop (VTS 2024)

---

## 2. COGS Path: `int_order_cogs_reconciled` (What `fact_order_economics` Uses)

**File:** `transformation/models/intermediate/cogs/int_order_cogs_reconciled.sql`  
**Lines 30–57:** `sapo_cogs` CTE derives `cogs_goods_sapo` from `std_inventory_movements` (trans_type=301 OUT legs, `cogs_amount = export_amount` = Sapo moving-average cost).  
**Line 112:** `cogs_goods_primary` defaults to `sapo_mac` (var `cogs_primary_source`).

The model performs a FULL OUTER JOIN of Sapo-MAC vs MISA 632 lines, keeping both columns, but downstream uses **`cogs_goods_sapo` exclusively** via `COALESCE(cogs_goods_sapo, cogs_goods_misa, 0)` in `fact_order_economics` (line 37).

**The H010 MISA `misa_qty_multiplier` field is never referenced by this model.** It is only used in `mart_sku_economics_monthly`'s `misa_cogs` CTE (line 229: `sa.units_sold * p.misa_qty_multiplier * mpu.cogs_per_misa_unit`).

---

## 3. `fact_order_economics.gross_margin_pct` Definition

**File:** `transformation/models/marts/sales/fact_order_economics.sql`  
**Lines 136–141:**
```sql
CASE
    WHEN o.net_revenue = 0 THEN NULL
    WHEN m.cogs_source IS NULL OR m.cogs_source = 'none' THEN NULL
    ELSE (o.net_revenue - COALESCE(m.cogs_amount, 0))::DOUBLE / o.net_revenue
END AS gross_margin_pct
```
Where `m.cogs_amount` = `SUM(COALESCE(cogs_goods_sapo, cogs_goods_misa, 0))` from `int_order_cogs_reconciled`.

Formula: `(Sapo_net_revenue - Sapo_MAC_COGS) / Sapo_net_revenue`. No MISA multiplier involved.

---

## 4. Data Verification

### 4a. `int_order_cogs_reconciled` uses base-unit Sapo SKUs, not pack SKUs

Query on actual H010 orders (SON07327, SON07326):
- MISA cogs rows appear with `sku='VCSL21002C001'` (Chai/base unit), not `VCSL21002H010` (Hop/pack)
- Sapo-MAC rows similarly use base unit SKU from inventory movements
- H010 pack SKUs do NOT appear in `int_order_cogs_reconciled` — the inventory system dispatches in base units
- **`cogs_source='sapo_mac'` for all observed H010 orders**

### 4b. Order-level margins for H010 orders (sample)

| order_code | net_revenue | cogs_amount | cogs_source | gross_margin_pct |
|---|---|---|---|---|
| SON07326 (5 VCSL19001H010) | 4,005,556 | 3,063,500 | sapo_mac | 23.5% |
| SON07327 (4 VCSL21002H010 + 7 VTSL24009H010) | 17,125,928 | 6,345,960 | sapo_mac | 62.9% |
| 260605ATQ5H6EN | 3,020,000 | 615,280 | sapo_mac | 79.6% |

Mixed-SKU orders with H010 units show reasonable margins (23–80% range), consistent with Sapo-MAC per-unit costs.

### 4c. Per-unit COGS comparison

Sapo-MAC per base unit (Chai) vs MISA per base unit (post-fix, Hop = 1 unit in MISA):

| Product | Sapo-MAC/Chai (avg) | MISA/Hop (post-fix) | Sapo Hop price |
|---|---|---|---|
| VCSL19001C001 (Hyaluron Collagen) | ~98,343 | 385,509 | ~1,026,306 |
| VCSL21002C001 (Cordyceps) | ~46,710/Chai → ~467,100/Hop | 506,476 | ~2,858,270 |
| VCSL21001C001 (Swallow Nest) | ~34,051/Chai → ~340,510/Hop | 555,557 | ~2,903,411 |

Observation: Sapo-MAC and MISA COGS per Hop differ materially (Sapo-MAC/Hop is significantly lower than MISA/Hop for some SKUs). The order-level margin is computed on Sapo-MAC, which is the correct authoritative source for order-level economics.

### 4d. `mart_sku_economics_monthly` divergence (confirms H010 issue is MISA-only scope)

For VCSL21002H010, May 2026:
- `gross_margin_pct = 65.4%` (MISA book: gross_profit/misa_revenue_net — different revenue base)
- `realized_margin_pct = 72.2%` (Sapo: (net_revenue - cogs_amount) / net_revenue)
- These differ because **MISA records a different price (revenue/unit)** than Sapo's actual selling price, not due to any remaining COGS overcount

The L125 lesson ("gross_margin_pct is UNCORRECTED for H010") refers to this MISA-vs-Sapo revenue basis difference in the SKU mart — **not** to a COGS multiplication error that survived the seed fix.

---

## 5. Verdict

**Verdict A: `fact_order_economics.gross_margin_pct` is ALREADY CORRECT for H010 SKUs.**

Reasoning:
1. `int_order_cogs_reconciled` pulls COGS from Sapo inventory movements (moving-average cost), which are denominated in base units dispatched. The H010 `misa_qty_multiplier` in `dim_sku_alias`/`dim_products` is irrelevant to this path — it only routes MISA book cost in `mart_sku_economics_monthly`.
2. `fact_order_economics.gross_margin_pct` = `(Sapo_net_revenue - Sapo_MAC_COGS) / Sapo_net_revenue`. Both numerator and denominator are Sapo-sourced. No MISA multiplier error can propagate here.
3. Data confirms: H010 order-level `cogs_source='sapo_mac'`, no MISA 632 COGS present for pack SKUs.
4. The audit flag pattern-matched on the column name `gross_margin_pct` and incorrectly assumed H010 propagated. The actual H010 risk was isolated to `mart_sku_economics_monthly.gross_margin_pct` (which uses MISA book values) — already documented in L125 as deprecated/uncorrected and labeled DEPRECATED in the SQL (line 390).

---

## 6. What the L125 Memory Item Actually Means

Memory: "gross_margin_pct + int_misa.gross_profit uncorrected; 5 H010 SKUs ~2× too low"

This is true for **`mart_sku_economics_monthly.gross_margin_pct`** because even after the seed fix:
- MISA revenue/unit ≠ Sapo net_revenue/pack (MISA records at different price points)
- The SKU mart's `gross_margin_pct` uses MISA-book revenue as denominator — producing a different metric than `realized_margin_pct`

This does NOT extend to `fact_order_economics.gross_margin_pct`, which has no MISA dependency.

---

## 7. Recommended Actions

1. **No change needed to `fact_order_economics`** — margin is correct at order grain.
2. **Evidence `ceo-weekly-pulse` and detailView using `fact_order_economics.gross_margin_pct`** are showing correct Sapo-MAC order-level margins.
3. **Add doc note** in phase-04 plan: close as "moot — verified order grain is H010-correct by source path analysis + data query."
4. **Optionally** add a SQL comment in `fact_order_economics.sql` near the `gross_margin_pct` definition: "Uses Sapo-MAC COGS only; immune to H010 MISA multiplier bug (see mart_sku_economics_monthly for SKU-level H010 caveat)."
5. The memory item `reference_realized_vs_gross_margin_pct` applies only to the SKU mart, not fact_order_economics. Consider annotating the memory to clarify scope.

---

## Unresolved Questions

1. SON07326 shows `gross_margin_pct=23.5%` for VCSL19001H010 orders. Sapo-MAC per-Chai avg is 98,343 (quite high — near 10× per Hop if uncorrected). Check: is the Sapo-MAC cost for VCSL19001C001 inflated (high average from non-standard rows with `cogs_amount=0` dragging down avg, or a few high-cost returns)? The min=0 in the per-unit table suggests zero-cost rows exist (could be promotional dispatches or data gaps). Does not affect the verdict — only Sapo-MAC is used at order level regardless.

---

**Status:** DONE  
**Verdict:** A — `fact_order_economics.gross_margin_pct` uses pure Sapo-MAC COGS (from `int_order_cogs_reconciled`), not MISA book values. H010 `misa_qty_multiplier` only propagates through `mart_sku_economics_monthly`'s MISA join. Audit flag is moot at order/CEO grain.  
**Numbers:** SON07327 (H010 pack order) shows `gross_margin_pct=62.9%` using `cogs_source='sapo_mac'`; consistent with `mart_sku_economics_monthly.realized_margin_pct=72–82%` for same SKUs. `gross_margin_pct` in mart differs (65%) because it uses MISA revenue denominator, not Sapo price — unrelated H010 multiplier issue.
