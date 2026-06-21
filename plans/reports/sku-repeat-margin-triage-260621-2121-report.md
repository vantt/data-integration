# SKU Repeat × Margin Triage — FineJapan
**Date:** 2026-06-21 | **Analyst:** analytics-analyst | **Scope:** Retail B2C (scope_retail=True, scope_sales=True, is_active_order=True, net_revenue>0)

---

## (1) KEY FINDINGS

### The Real Niche
**Cordyceps/Immune + Joint/Bone SKUs at 60–82% realized margin are the repeat engine.**

The top 6 SKUs by repeat buyers (77–115 repeat buyers each) are all functional health supplements (cordyceps, shark cartilage, natto kinase, collagen/hyaluron). These same SKUs sit in HIGH-REV HIGH-MARGIN quadrant. The repeat base (≥2 lifetime orders) = 1,126 customers generating 31.1B VND — 60.5% of retail B2C revenue from 22.9% of customers. One-timers (3,783 customers) = 20.3B VND.

**Top niche winners** (repeat buyers ≥ 44, margin ≥ 60%, revenue ≥ 500M VND):
- `VCSL21002H010` Cordyceps Plus — #1 by revenue (5,610M), 72.2% margin, 44 repeat buyers, 64% of revenue from repeaters
- `VTSC19002L001` Fucoidan — 34.9% repeat-buyer rate (highest among A-class), 70.5% margin, 79% of revenue from repeaters
- `VTSL21001H010` Hyaluron & Collagen with Swallow's Nest — 78% repeat revenue share, 80.9% blended margin (12m)

### Dead-Stock Summary
**58 SKUs flagged dead-stock; 42.1M VND stock value at risk.** These are almost entirely promotional/gift items (pens, bowls, bags, candles), discontinued supplements (Liver Care, Hepalyse drink), and old variant combos. No core supplement SKUs are dead-stock.

### 80/20 Concentration
**Top 5 SKUs = 25.1% of retail revenue. Top 10 = 34.4%. Top 20 = 37.6%.** (Out of 254 active retail SKUs. Long tail is combo/bundle variants.) Core flagship line accounts for 80%+ of meaningful GP.

### Critical Flag
`VTST23042L001` (Fine Japan Natto Kinase) shows **–32.7% realized margin** with 112M VND revenue — actively destroying margin. Investigate COGS vs price list.

---

## (2) THE FIVE TABLES

### Table 1 — SKU Winners by Repeat × Margin (Retail B2C, all-time)

> Exclusions applied: scope_b2b=True, customer_type ≠ RETAIL, net_revenue ≤ 0, is_active_order=False.
> Sorted by repeat_buyers DESC.

| SKU | Product | ABC | Health Class | Distinct Buyers | Repeat Buyers | Repeat% | Units | Net Rev (M VND) | Orders | Realized Margin% |
|-----|---------|-----|-------------|-----------------|---------------|---------|-------|-----------------|--------|-----------------|
| VCST21003L001 | Natto Kinase | A | DOG | 409 | 77 | 18.8% | 1,087 | 1,449 | 536 | 60.1% |
| VCSC20001L001 | Cordyceps | A | BALANCED | 340 | 70 | 20.6% | 1,248 | 2,004 | 479 | 61.5% |
| VCST21004L001 | Shark Cartilage Extract | A | WORKHORSE | 496 | 69 | 13.9% | 1,132 | 2,112 | 611 | 65.6% |
| VCSL19001H010 | Hyaluron & Collagen Plus | A | WORKHORSE | 216 | 56 | 25.9% | 1,343 | 1,726 | 391 | 59.8% |
| VCSL21002H010 | Cordyceps Plus | A | STAR | 184 | 44 | 23.9% | 1,603 | 5,611 | 261 | 72.2% |
| VTSC20001L001 | Cordyceps (*VT line) | A | STAR | 235 | 44 | 18.7% | 896 | 1,378 | 315 | 73.0% |
| VTSC19002L001 | Fucoidan | A | BALANCED | 86 | 30 | 34.9% | 544 | 1,117 | 141 | 70.5% |
| VCSC23054B001 | Coix Beauty Tablets | B | DOG | 175 | 28 | 16.0% | 253 | 63 | 216 | 30.8% |
| VCSL19001C001 | Hyaluron & Collagen Plus (C-pack) | C | BALANCED | 122 | 23 | 18.9% | 1,118 | 949 | 169 | — |
| VCSC23052H001 | Gaba Blood Fine Japan | B | BALANCED | 119 | 22 | 18.5% | 445 | 273 | 151 | — |
| VTSC21006L001 | Royal Reishi | B | BALANCED | 76 | 20 | 26.3% | 243 | 320 | 120 | — |
| VTST23023L001 | Shark Cartilage (*VT line) | A | QUESTION | 126 | 11 | 8.7% | 285 | 616 | 144 | 72.1% |
| VTSL24009H010 | Cordyceps Plus NEW | A | STAR | 17 | 3 | 17.6% | 131 | 509 | 22 | 82.2% |

### Table 2 — Repeat Base (≥2 orders) vs One-Timers

**Repeat base = 1,126 customers, 3,863 orders, 31.1B VND (60.5% of retail rev)**
**One-timers = 3,783 customers, 3,783 orders, 20.3B VND (39.5%)**

| SKU | Product | Repeat Buyers | Repeat Rev (M) | One-Time Buyers | One-Time Rev (M) | Repeat Rev% |
|-----|---------|---------------|----------------|-----------------|------------------|-------------|
| VCST21003L001 | Natto Kinase | 153 | 897 | 256 | 553 | 61.9% |
| VCSC20001L001 | Cordyceps | 146 | 1,119 | 194 | 885 | 55.8% |
| VCST21004L001 | Shark Cartilage Extract | 132 | 702 | 364 | 1,411 | 33.2% |
| VCSL19001H010 | Hyaluron & Collagen Plus | 115 | 1,333 | 101 | 393 | 77.2% |
| VTSC20001L001 | Cordyceps (*VT) | 115 | 833 | 120 | 545 | 60.4% |
| VCSL21002H010 | Cordyceps Plus | 79 | 3,598 | 105 | 2,013 | 64.1% |
| VCSC23054B001 | Coix Beauty Tablets | 60 | 32 | 115 | 31 | 50.4% |
| VCSL19001C001 | Collagen C-pack | 50 | 750 | 72 | 199 | 79.1% |
| VTSC19002L001 | Fucoidan | 48 | 887 | 38 | 230 | **79.4%** |
| VCSC23052H001 | Gaba Blood | 47 | 227 | 72 | 46 | 83.3% |
| VTST23023L001 | Shark Cartilage (*VT) | 43 | 308 | 83 | 308 | 50.0% |
| VTSL21001H010 | Collagen + Swallow's Nest | 19 | 537 | 9 | 149 | **78.3%** |
| VTSL24009H010 | Cordyceps Plus NEW | 11 | 402 | 6 | 107 | **79.0%** |

**Repeat niche vs acquisition mix:** Cordyceps, Shark Cartilage, and Natto Kinase dominate in absolute buyer count for one-timers too — but their revenue-from-repeaters ratios (55–79%) confirm these are genuine rebuyers. Coix Beauty Tablets (B2C skincare) has 175 distinct buyers but only 16% repeat rate — primarily acquisition product, not loyalty driver.

### Table 3 — Dead-Stock / Tail SKUs (Flagged for Action)

**Stock-on-hand data: AVAILABLE** (via `mart_product_health.on_hand` — MAC-costed)
**Total: 58 dead-stock SKUs, 42.1M VND at risk, 100 SKUs with any on-hand (969M VND total stock value)**

| SKU | Product | Dead? | Days Since Sale | Rev 180d (M) | On Hand (units) | Dead Value (M) | Notes |
|-----|---------|-------|-----------------|--------------|-----------------|----------------|-------|
| MJZXB01WC | Bút bi in logo FG Care | Yes | — | 0 | 530 | 9.3M | Promo pen — liquidate/gift |
| VB24016 | Bát tre khảm trai mỹ nghệ | Yes | — | 0 | 149 | 9.0M | Premium gift bowl — no sales |
| VB23002 | Túi giấy nhỏ Fine Japan | Yes | — | 0 | 270 | 4.9M | Branded bag — obsolete |
| VB24019 | Quà tặng nến thơm | Yes | — | 0 | 47 | 4.4M | Scented candle — stop reorder |
| VB24017 | Bộ đũa muỗng JPC | Yes | — | 0 | 64 | 3.7M | Gift chopstick set |
| VB24001 | Sổ tay Fine Japan & FG Care | Yes | — | 0 | 148 | 3.2M | Notebook — write off |
| VCMC21010H001 | Viên Xông EUCA OPC | Yes | — | 0 | 105 | 2.7M | Non-supplement, dead |
| VTSL21005C001 | Fine Liver Care Shijimi Drink | Yes | — | 0 | 20 | 2.1M | Discontinued supplement |
| VTST23042L001 | Natto Kinase (*VT line) | No | 12d | 65.4M | — | 0 | **–32.7% margin; active but destroying GP** |
| VCSC24007G001 | Rose Supplement Seedcoms | Yes | — | 0 | 1 | 0.1M | Dead, negligible |
| VCST24006G001 | Vitamin C Seedcoms | Yes | — | 0 | 1 | 0.1M | Dead, negligible |
| CB.3SHA / CB.12COR etc. | Old combo SKUs | Yes | — | 0 | various | 0 | Phantom/virtual stock in system |

**No core supplement flagship SKUs are dead-stock.** Dead items are exclusively: (a) branded promo gifts/merch, (b) one discontinued supplement line (Liver Care, Hepalyse drink), (c) obsolete combo/bundle SKUs from old system. Recommend: bundle promo items into future orders, write off notebooks/bags if >90d since last gifting event.

### Table 4 — Margin Distribution Quadrants (Retail B2C)

> Threshold: HIGH-REV = net_rev > 500M VND; HIGH-MARGIN = realized_margin_pct ≥ 60%

| Quadrant | SKUs | Key Products | Action |
|----------|------|--------------|--------|
| **HIGH-REV + HIGH-MARGIN** ← Real Niche | 8 | Cordyceps Plus (5,611M, 72%), Shark Cartilage (2,112M, 66%), Cordyceps (2,004M, 62%), Natto Kinase (1,449M, 60%), Fucoidan (1,117M, 71%), Shark Cart VT (616M, 72%), Cordyceps Plus NEW (509M, 82%) | **Protect & push. These are the business.** |
| HIGH-REV + LOW-MARGIN (margin <60% or null) | 3 | Hyaluron & Collagen Plus (1,726M, 59.8%), Collagen C-pack (949M, margin null), Collagen + Swallow's Nest (685M, margin null) | Margin data gap for 2 SKUs. Hyaluron at 59.8% — borderline; investigate COGS. |
| LOW-REV + HIGH-MARGIN (≥60%, <500M) | 5 | Collagen Plus NEW (69M, 66%), Natto Kinase L002 (64M, 66%), Fucoidan L002 (37M, 74%), Cordyceps variants | **Growth candidates — push volume with existing margin.** |
| LOW-REV + LOW-MARGIN (<60% or null, <500M) | 42 | Royal Reishi (320M, null), Gaba Blood (273M, null), Natto VT line (112M, –33%), combo bundles | Investigate nulls. Natto VT is actively negative. Combos are channel artefacts. |

**Note on discount dependency:** ALL high-revenue SKUs are flagged `PROMO_HEAVY`. This means realized margin is already post-promo but volume depends on promotions — a structural risk if promo spend is pulled.

### Table 5 — Concentration: Top SKUs as % Net Revenue + Estimated GP

> All-time retail B2C (scope_retail + scope_sales). Total retail revenue in fact_sales = 12.52B VND active.
> mart_sku_economics_monthly (last 12m, MISA-costed): used for GP estimates.

| Rank | SKU | Product | Rev (M) | Rev% | Cum Rev% | Realized Margin% | Est GP (M) |
|------|-----|---------|---------|------|----------|-----------------|------------|
| 1 | VCSL21002H010 | Cordyceps Plus | 5,611 | 10.9% | 10.9% | 72.2% | 4,051 |
| 2 | VCST21004L001 | Shark Cartilage | 2,112 | 4.1% | 15.0% | 65.6% | 1,386 |
| 3 | VCSC20001L001 | Cordyceps | 2,004 | 3.9% | 18.9% | 61.5% | 1,232 |
| 4 | VCSL19001H010 | Hyaluron & Collagen Plus | 1,726 | 3.4% | 22.3% | 59.8% | 1,032 |
| 5 | VCST21003L001 | Natto Kinase | 1,449 | 2.8% | 25.1% | 60.1% | 871 |
| 6 | VTSC20001L001 | Cordyceps (*VT) | 1,378 | 2.7% | 27.8% | 73.0% | 1,005 |
| 7 | VTSC19002L001 | Fucoidan | 1,117 | 2.2% | 30.0% | 70.5% | 788 |
| 8 | VCSL19001C001 | Collagen C-pack | 949 | 1.9% | 31.8% | — | — |
| 9 | VTSL21001H010 | Collagen + Swallow's Nest | 685 | 1.3% | 33.2% | — | — |
| 10 | VTST23023L001 | Shark Cartilage (*VT) | 616 | 1.2% | 34.4% | 72.1% | 444 |
| 11 | VTSL24009H010 | Cordyceps Plus NEW | 509 | 1.0% | 35.4% | 82.2% | 419 |
| 12–20 | Various | Royal Reishi, Gaba, Natto VT, combos | ≤320 each | ≤0.6% | 37.6% | mixed | mixed |

**Concentration summary (254 active retail SKUs):**
- Top 5 SKUs = 25.1% of revenue
- Top 10 SKUs = 34.4% of revenue  
- Top 20 SKUs = 37.6% of revenue
- ≥80% revenue requires all 254 SKUs (highly fragmented beyond top 20 — almost all combo/variant/tail)

**Estimated realized GP (top 9 with margin data):** ~10.8B VND across 7 flagship SKUs (rough: 9.3B from the 7 with margin data among top 11).

---

## (3) DATA CAVEATS + EXCLUSIONS

### Exclusions Applied
| What | How Many | Why |
|------|----------|-----|
| scope_b2b = True orders | 3,042 orders, 20.1B VND | B2B/wholesale "Đại Lý" channel |
| scope_retail=False + US channel | ~2,922 orders, 11.1B VND | US gift/export shipments (separate economics) |
| net_revenue ≤ 0 | Various | Gift/zero-price orders, returns |
| is_active_order = False | Various | Cancelled orders |
| customer_type ≠ RETAIL (WHOLESALE, CROSSBORDER, PARTNER) | ~483 WHOLESALE + 1,986 CB + 33 PARTNER | Wholesale buyers have different repeat patterns |

**The known 23.7B B2B/export distortion** maps to: WHOLESALE customers (customer_type=WHOLESALE) with ~184B VND all-time + US channel orders (11B). These are correctly excluded from the retail repeat/margin analysis above.

### Stock-on-Hand
**Available**: `mart_product_health.on_hand` column exists (MAC-costed). 300 SKUs have on_hand > 0, totalling ~654,463 units / 969M VND stock value. Dead-stock SKUs = 58, at-risk value = 42.1M VND.

### Margin Data Coverage
- **mart_product_health**: 104 distinct SKUs; `realized_margin_pct` populated for 24 SKUs (those with MISA COGS data). 80 SKUs show NULL — these are SKUs where MISA COGS has not been matched.
- **mart_sku_economics_monthly**: 67 MISA-sourced SKUs with valid realized margin; 38 sapo_mac SKUs have extreme outlier margins (–9,367% average — data quality issue, excluded).
- `gross_margin_pct` and int_misa.gross_profit NOT used (uncorrected per project rules).

### Parquet Triplication
Three rolling parquet files existed per table (3 pipeline runs same day). All analyses used `SELECT DISTINCT` on natural keys (order_line_id, order_id, product_key+snapshot_month, customer_key) to deduplicate.

### mart_sku_economics_monthly Revenue Scale
The mart covers 12.17B VND all-time (MISA SKUs only) — lower than fact_sales retail 12.52B because it appears to aggregate a specific channel subset. Used for margin benchmarks only, not revenue totals. Revenue totals taken from fact_sales.

---

## (4) UNRESOLVED QUESTIONS

1. **Hyaluron & Collagen (VCSL19001C001, VTSL21001H010) margin NULL** — these are rank-8 and rank-9 by revenue (1.6B VND combined). No MISA COGS match. Are these sourced from a different supplier not in MISA? What is their actual realized margin?

2. **Royal Reishi (VTSC21006L001, 320M) and Gaba Blood (VCSC23052H001, 273M) both NULL margin** — 20+ repeat buyers each, but we can't quantify GP. Are these profitable enough to actively push to repeat base?

3. **VTST23042L001 Natto Kinase (–32.7% margin, 112M revenue)** — Is this a COGS mismatch (e.g. premium Japanese variant mis-priced vs MISA cost entry)? Or a genuine pricing error? Needs immediate investigation.

4. **VCSC23054B001 Coix Beauty Tablets — 30.8% margin, 175 buyers, 28 repeat buyers** — worth keeping as skincare entry-point? Margin too low for its promo-heavy discount dependency. Is it a feeder to higher-margin products?

5. **All flagship SKUs flagged PROMO_HEAVY** — what % of orders are discounted vs full-price? Are there any full-price repeat buyers? This is critical for understanding true demand vs promotion-driven demand.

6. **US channel (11B VND)** — excluded from retail analysis but represents a significant revenue stream. Is this the 23.7B distortion partially, or does the 23.7B refer specifically to miscoded B2B accounts? Need clarification on which specific customer_keys are the "miscoded export accounts."

7. **fact_sales all-time retail = 51.35B VND vs fact_orders retail = 12.2B** — large gap. The 51.35B includes all historic line-items across all channels (including B2B scope). The 12.2B is scope_retail=True only. Which number should be used as the "true retail consumer base" for strategic sizing?
