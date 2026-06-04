# COGS Reconciliation Design — Sapo inventory MAC vs MISA giá vốn

**Status:** DESIGN (not implemented). **Precedence chốt: Sapo-MAC primary, MISA = reconciliation only** (store both + variance).
**Date:** 2026-06-04. **Related:** `std-layer-conventions.md`, `overhead-cost-allocation-design.md`, `naming-conventions.md`.
**Driver:** New `fact_inventory_movements` / `std_inventory_movements` (Sapo inventory v2) exposes per-line COGS, overlapping MISA's existing COGS → must reconcile without double-counting.

---

## 1. Problem

Two sources now report **cost of goods sold (giá vốn hàng)** for the same Sapo order lines:

| | Giá vốn hàng (COGS goods) | Chi phí khác (services / CPBH / …) |
| --- | --- | --- |
| **Sapo inventory v2** | ✅ per (order, sku, movement); MAC at fulfillment; ~100% fulfilled orders; real-time | ❌ none |
| **MISA** (`int_misa_sales_lines`) | ✅ per line (product_code); accounting TK632; ~65% orders | ✅ only MISA has (DV%/CPBH% lines) |

**The overlap (double-count risk) is ONLY the COGS-goods cell.** MISA non-goods cost lines have no Sapo counterpart → always additive, never reconciled.

Sapo = COGS-of-goods only. MISA = COGS-of-goods **plus** other costs. So the design splits cost by **role**, then reconciles only the shared part.

### 1a. CRITICAL data finding — MISA "Giá vốn" is mixed-account (verified 2026-06-04)

MISA's `cogs_amount` (cột "Giá vốn" of the sales ledger) is **NOT pure COGS** — it aggregates multiple accounts:

| `cogs_account` group | Nature | Lines | Amount | % |
| --- | --- | --- | --- | --- |
| **632** (632.1/632.3) | Giá vốn hàng bán = true COGS | 9,248 | 21.5B | **95.2%** |
| **642** (642.14) | Giá vốn hàng **KHUYẾN MÃI / biếu tặng** (promo-goods cost), NOT G&A overhead | 2,189 | 1.08B | **4.8%** |

The TK642 lines are **goods** SKUs (VCSC/VCSL/…) with **revenue = 0** and `is_promo_line = true` (1,709 of 2,189; rest near-zero-revenue): inventory issued as promo/giveaway, cost booked to 642 instead of 632. **It is still goods cost** — just not COGS-of-a-sale. NOT cash G&A (rent/salary/etc.).

**Consequence:** COGS reconciliation MUST filter MISA to `cogs_account LIKE '632%'`. The TK642 promo-goods portion → its own cost_type ('promo_goods_cost'), additive; never into COGS reconciliation (else it fabricates variance vs pure Sapo-MAC). Sapo likely captures these as inventory OUT movements with a non-sale `trans_type` (≠301) — see §6 / open Q2b.

### 1b. MISA is a multi-report source — only sales ledger ingested; cash overhead NOT present

Current pipeline ingests **one** MISA report: `So_chi_tiet_ban_hang_*.xlsx` → `sales_lines` (parser emits exactly one DataFrame). Verified: **0 rows without a product_code** → the sales ledger contains ONLY goods lines. Therefore **cash overhead/operating expenses (lương, thuê mặt bằng, điện, khấu hao, marketing tiền mặt = real TK642/641/635) are ABSENT** — they live in other MISA reports (Sổ chi tiết TK642/641, Bảng cân đối phát sinh) **not yet ingested**. The only "642" we have is the promo-goods cost above. Future overhead ingestion = the concurrent overhead session's responsibility → separate `std_misa_<report>` models.

---

## 1c. Rationale — why a separate COGS view (and a live lumping bug)

COGS is the cost that **varies per unit sold** and **matches revenue** (matching principle). Keeping it separate builds the profit ladder, each tier answering a distinct decision:

```
Revenue
 − COGS (variable/unit)            → Gross margin   → "Does each product earn before fixed costs?" (pricing, SKU mix, discount floor)
 − Variable selling (ship/fee/promo) → Contribution   → "Is this channel/order worth doing?"
 − Fixed overhead (rent/salary)     → Net profit     → "Is the whole business viable?"
```

Lumping all costs into one bucket destroys all three questions (only a blended profit/loss remains, with no *why*). Separation gives: per-unit pricing decisions, variable-vs-fixed scalability, root-cause diagnosis (COGS↑ vs promo↑ vs overhead↑), cross-period/SKU comparability, clean attribution (COGS attaches to a line; overhead must be allocated), and accounting/inventory-valuation compliance (TK632 vs TK641/642 are legally distinct).

**LIVE BUG (this repo):** `fact_order_economics.sql:32` does `SUM(cogs_amount)` from `int_misa_sales_lines` with **no TK632 filter** → it lumps the 1.08B of **TK642 promo** into COGS. Consequences happening now:
- `gross_profit = net_revenue − cogs_amount` (l.90) → **gross margin understated** on orders with gift lines.
- **1.08B promo spend invisible** — buried in COGS, not visible as marketing.
- `channel_net_profit` (l.116) inherits the same contamination → channel ranking skewed.

Classic failure modes the separation prevents: absorption-costing "death spiral" (fixed cost / fewer units → fake unit-cost rise → price hikes in a slump), wrong promo/pricing calls from blended margin, and the MISA+Sapo **double-count** (§5). → Another reason to build `int_order_cogs_reconciled` (filter 632, split promo).

## 2. Current state (baseline)

- `int_misa_sales_lines` — **line grain** (`voucher_no`, `line_no`), has `product_code`, `quantity`, `cogs_amount`, `gross_profit`, `is_service_line` (`product_code LIKE 'DV%' OR 'CPBH%'`).
- Consumed at **order grain**: `fact_order_economics` does `GROUP BY voucher_no → SUM(cogs_amount)`; `fact_order_costs` emits one order-level `cost_type='cogs'` row. → MISA line detail exists but is collapsed.
- **detailView** shows only order-level MISA COGS (`fact_order_economics.cogs_amount` + `has_cogs`; "Margin unverified — no MISA COGS" when missing). Line items have **no** COGS.
- `std_inventory_movements` (new) → `fact_inventory_movements.cogs_amount` (= Sapo `export_amount`), `document_code`, `sku`, `variant_id`, `quantity_delta`.
- **No double-count today** (detailView reads MISA only). Risk appears the moment inventory COGS is wired into the same total without rules.

---

## 3. Feasibility — line-level reconcile is viable

Measured (2026-06-04):
- MISA distinct `product_code` = 201 (190 goods + ~11 service); Sapo SKU (inventory) = 558.
- **MISA goods codes 182/190 = ~96% match Sapo `sku`.**
- MISA lines: 11,436 goods + 94 service.

→ Reconciliation grain = **(order_code, sku)**.
- MISA side: `(voucher_no AS order_code, product_code AS sku)`.
- Sapo side: `(document_code AS order_code, sku)`, COGS = net of inventory movements (see §6 returns/cancellations).

---

## 4. Decision (chốt): Sapo-MAC primary, MISA reconciliation

- **COGS definition = option A (Cost of Goods SOLD):** COGS counts only lines with revenue (`revenue > 0`). **Gift/promo lines (`revenue = 0`) are NOT COGS** → routed to `promo_goods_cost`. Matches accounting definition + MISA's own treatment (gifts → TK642, not TK632). Total profit unchanged (promo cost still subtracted, just labelled separately).
- **Primary goods-COGS = Sapo-MAC** (line-level, ~100% fulfilled orders, real-time, single consistent basis). `cogs_goods_primary = cogs_goods_sapo` (on revenue>0 lines).
- **MISA = reconciliation only** — still materialized per line (TK632 portion) + `cogs_variance`, surfaced for audit, **never summed** into the COGS total.
- Switching later (if ever) = one dbt var (`cogs_primary_source`), no schema change.

---

## 5. Proposed models (std-gated)

Per `std-layer-conventions.md` R1, anything feeding `int_`/`fact_` flows through `std_`.

```
std_inventory_movements (exists)  ─┐
                                   ├─► int_order_cogs_reconciled ─► fact_order_economics / fact_order_costs / detailView
std_misa_sales_lines (TO ADD*)  ──┘
```

\* **Std-gate fix (decided):** all Sapo entities already have `std_*` (12 models, incl. `std_inventory_movements`). MISA is the **only** source missing it — currently `src → stg → int_misa_sales_lines` (int reads stg directly), violating R1. It was historically treated as "enrichment, not a primary fact" so std was skipped; but feeding COGS reconciliation makes it a real input. → **Add `std_misa_sales_lines`** (faithful pass-through + `source_system='misa'`, `source_version`). Not optional.
  - **Keep account columns** (`cogs_account`, `debit_account`, `credit_account`) intact + add a derived `cost_account_group` (`'632'` = COGS / `'642'` = promo-goods cost / other) so downstream splits COGS vs promo-cost correctly (per §1a). Faithful std does NOT collapse the mix.
  - **Name is `std_misa_sales_lines` (report-specific), NOT `std_misa`** — MISA is a multi-report source (§1b); future expense ledgers get their own `std_misa_<report>` models. Do not assume one monolithic MISA std.

### `int_order_cogs_reconciled` (new, grain = order_code × sku)
| column | meaning |
| --- | --- |
| `order_code`, `sku`, `variant_id` | join keys |
| `qty_sapo` | net OUT qty from inventory (OUT − return IN) |
| `qty_misa` | MISA line quantity |
| `cogs_goods_sapo` | Σ Sapo MAC COGS for the line (net of returns) |
| `cogs_goods_misa` | Σ MISA `cogs_amount` **where `cogs_account LIKE '632%'`** (true COGS only; excludes TK642 expense + service lines) |
| `cogs_variance` | `cogs_goods_sapo − cogs_goods_misa` (NULL if one side missing) |
| `cogs_variance_pct` | variance / NULLIF(misa,0) |
| `has_sapo_cogs`, `has_misa_cogs` | coverage flags |
| `cogs_goods_primary` | interim chosen value (default = Sapo-MAC; var-driven) |
| `cogs_source` | 'sapo_mac' \| 'misa' \| 'both' \| 'none' |

MISA **non-COGS** lines bypass COGS reconciliation and flow to `fact_order_costs` as their own `cost_type`, additive:
- `cost_account_group='642'` (~4.8%, 1.08B) → **promo-goods cost** (hàng khuyến mãi/biếu tặng, revenue=0) — a marketing/promo cost_type, NOT COGS and NOT cash overhead.
- `is_service_line=true` (DV%/CPBH% product_code) → services / selling-expense.

---

## 6. Aggregation rules (no double-count)

1. **Never** `SUM(misa_cogs) + SUM(sapo_cogs)` for goods. Aggregates use exactly one column (`cogs_goods_primary`).
2. `fact_order_economics.cogs_amount` (goods) ← `Σ int_order_cogs_reconciled.cogs_goods_primary` per order. Add `cogs_source` for transparency.
3. MISA other-costs (services/CPBH) added separately (they are not COGS-goods).
4. **Returns / cancellations** (analysis caveats #2): Sapo `cogs_goods_sapo` = Σ COGS of OUT movements − Σ COGS of return/cancel IN legs (net), so returned units don't overstate COGS. Do not blind-sum `quantity_delta`.
5. **Marketplace orders** (~33%, no SON code): keyed by `document_code` (marketplace code). MISA may lack them → `cogs_source='sapo_mac'`. Out-of-scope channels flagged, not silently dropped.

---

## 7. Primary source + variance expectation

- **`cogs_goods_primary` = Sapo-MAC** (chốt), via dbt var `cogs_primary_source` default `'sapo_mac'`.
- MISA reconciliation side = **only `cogs_account LIKE '632%'`** (true COGS). TK642 lines excluded from COGS — they go to the expense/overhead bucket (§5, §9).
- **MAC ≠ accounting COGS by nature** — Sapo MAC = warehouse moving-average at fulfillment; MISA TK632 may include landed/adjustment costs and post on a different date. Variance is **expected, not an error**; surface for audit, don't "fix" it.

---

## 8. detailView spec (implement later — coordinate; see §9)

detailView is single-order drill-down → ideal place to show **both**, never to sum.

- **Line items (NEW):** per line show `cogs_goods` (primary) + `margin = revenue_line − cogs_goods`; tooltip/secondary shows MISA vs Sapo-MAC + variance when both exist. Source = `fact_inventory_movements` (Sapo) joined `(order_code, sku)`; MISA line via `int_misa_sales_lines`/reconciled.
- **Order level:** total goods-COGS (primary) + `cogs_source` badge; a small **reconciliation panel** (MISA vs Sapo-MAC + variance%). "Margin unverified" disappears for fulfilled orders (Sapo-MAC covers them).
- **Other costs:** MISA services/CPBH shown as separate cost rows (existing `order_costs.sql` cost ledger), unchanged.
- detailView reads `fact_*`/`mart_*` views only (never `int_`) → needs serving views for the reconciled mart.

---

## 9. Coordination (IMPORTANT)

- **Concurrent session** is editing `detailView` + `fact_orders`/`fact_order_costs` + `overhead-cost-allocation-design.md`. **Do NOT edit detailView UI concurrently** (file conflicts) — land the transformation layer first, wire detailView after their work merges.
- **Overhead allocation** builds `channel_net_profit = net_revenue − COGS − platform_fees − discounts`. It MUST read the **reconciled** goods-COGS (`cogs_goods_primary` = Sapo-MAC), not raw MISA `cogs_amount` — raw MISA mixes 4.8% TK642 expense into "Giá vốn" (§1a), which would understate overhead and overstate COGS.
- **Real cash overhead (lương/thuê/điện/khấu hao = TK642/641/635) is NOT in any ingested data** (§1b) — the overhead session must ingest separate MISA reports for it. The only "642" present is **promo-goods cost** (1.08B, inventory issued as giveaway), which is a marketing cost, not the G&A overhead pool — don't conflate the two. When standalone TK642 expense ledgers are ingested later, ensure the promo-goods 642 (already in sales ledger) isn't double-counted against them.

---

## 10. Implementation phases (when approved)

1. `std_misa_sales_lines` faithful pass-through (closes the std-gate gap — MISA is the only source without std_).
2. `int_order_cogs_reconciled` (grain order×sku; both COGS + variance + flags + interim primary var).
3. Repoint `fact_order_economics` / `fact_order_costs` goods-COGS → reconciled; keep MISA other-costs additive; add `cogs_source`.
4. Serving views + Metabase check (no double-count in P&L).
5. detailView per-line COGS/margin + reconciliation panel (AFTER concurrent detailView work lands).
6. Verify each step via a Dagster run.

---

## 11. Action items / tasks

| ID | Task | Priority | Status |
| --- | --- | --- | --- |
| **BUG-1** | **Fix TK642 lumping in `fact_order_economics.sql:32`** — `SUM(cogs_amount)` includes TK642 promo (1.08B) in COGS. Filter to true COGS: `... WHERE cogs_account LIKE '632%'` in the `misa_order` CTE (interim), OR repoint COGS sourcing to `int_order_cogs_reconciled` (proper, phase 3). Same for `fact_order_costs` cogs CTE. After fix: `cogs_amount`/`gross_profit`/`channel_net_profit` drop the promo contamination; route the 642 portion to a `promo_goods_cost` cost_type. | **High** | OPEN |

**Coordination:** `fact_order_economics.sql` / `fact_order_costs.sql` are currently being edited by the concurrent overhead session — **do NOT edit concurrently**. Either (a) hand BUG-1 to that session (it directly affects their `channel_net_profit` baseline), or (b) apply after their work merges. Verify the fix via a Dagster run (COGS total drops by ~1.08B; promo surfaces separately).

## Unresolved questions

1. ~~Precedence~~ → **RESOLVED: Sapo-MAC primary, MISA reconciliation** (§4).
2. **product_code ↔ sku mapping** — 96% match; handle the ~4% (8 codes) unmatched + the 8 Sapo SKUs MISA never sees. Mapping table or accept gaps?
2b. ~~TK642 promo goods ↔ Sapo trans_type~~ → **RESOLVED (verified):** Sapo has NO promo/giveaway trans_type. Sales COGS = `trans_type=301` (sale_order_fulfillment, 26,125 rows, 48.4B). The 1,709 MISA promo lines have no non-301 counterpart → promo goods are fulfilled as zero-price sale orders → they **ride inside trans_type 301**. So Sapo-MAC COGS(301) **includes promo cost**, whereas MISA splits it to TK642 → this is a known component of the MISA-632 vs Sapo-MAC variance (~1.08B). **DECISION (option A):** COGS = goods SOLD only. Sapo COGS computed on order lines with `revenue>0`; promo/gift lines (`revenue=0`) split to `promo_goods_cost`. **Requires joining order-line revenue** (`std_order_items`/`fact_sales`) — NOT optional, it is the design. This also captures the **gift-no-invoice case** (Sapo has MAC, MISA has nothing — goods bought without invoice): cost kept from Sapo-MAC, routed to `promo_goods_cost`, flagged `cogs_source='sapo_only'`. Net profit unchanged; COGS no longer inflated by gifts.
   - Other non-sale OUT to exclude from sales-COGS: `200/203 stock_transfer` (inter-warehouse, 16B), `400/401 stock_adjustment/balance`. Sales-COGS filter = `trans_type=301` only; returns (`350`) net against it.
3. **MISA quantity vs Sapo quantity per (order, sku)** — do they agree? If not, which drives unit-economics?
4. **Marketplace COGS** — Sapo-MAC only; confirm acceptable for those channels' P&L.
5. **Timing** — MISA posts later than fulfillment; for a freshly-shipped order, reconciled COGS will be Sapo-MAC then gain a MISA counterpart days later (variance appears retroactively). Acceptable?

(Resolved) ~~std_misa gate~~ → decided: add `std_misa_sales_lines` (§5). MISA was the only source skipping std_.
