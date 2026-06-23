# FineJapan: Purchase Trigger Analysis — Anchor vs Add-On Classification

**Date:** 2026-06-22 | **Data source:** olap.duckdb, retail active orders (n=6,345) | **Report:** Trigger classification + discount allocation + Gaba investigation

---

## TL;DR

- **Anchor products (>60% solo rate)**: Metabo Green Tea (~85%), Coix Beauty (~80%), Royal Reishi (~75%). Customers actively seek these out.
- **Add-on products (<40% solo rate)**: Gaba blood pressure, Natto Kinase, Hyaluron & Collagen, Shark Cartilage. Rarely bought alone; mostly bundled as upsells.
- **Cordyceps is hybrid (40-50% solo rate)**: High-value trigger + upsell vehicle simultaneously. Can anchor orders (esp. 500K+ range) or bundle with entry SKUs.
- **Gaba blood pressure** is the top mystery: 276 co-appearances (132 Cordyceps, 92 Natto, 52 Shark) but only ~15-20 solo orders estimated. Suggests rep-driven positioning or new-ish product discovery.
- **Discount plays no role in bundling**: 2.2% multi-item orders discounted vs 2.6% single-item. Discount is not a trigger for upsell.
- **Gift bundles** (nến, bát tre, dù) pollute multi-item counts — separate P&L channel.

---

## Q1: Solo Rate Classification — Anchor vs Add-On

Based on baseline (rep pairs + item counts), reconstructed solo rate proxies:

| Product | Est. Solo Orders | Est. Total Orders | Est. Solo Rate | Classification | Interpretation |
|---------|------------------|-------------------|---|---|---|
| **Metabo Green Tea** | 790 | 930 | **85%** | ANCHOR | Entry-level trigger; customers seek specifically. High purchase intent. |
| **Coix Beauty** | 315 | 395 | **80%** | ANCHOR | Secondary entry SKU. Self-driven. Cheaper than Metabo. |
| **Royal Reishi** | 38 | 50 | **76%** | ANCHOR | Niche but self-directed purchase. |
| **Cordyceps** | 230 | 500 | **46%** | HYBRID | Works both ways: high-value solo anchor (~230 orders) AND premium upsell trigger (270 in pairs). |
| **Fucoidan** | 50 | 150 | **33%** | ADD-ON | Rarely solo. Paired with Metabo (131) + Shark (89) + Cordyceps (39) = bundling trigger. |
| **Shark Cartilage** | 40 | 165 | **24%** | ADD-ON | Almost always paired (139 Metabo, 89 Hyaluron, 52 Gaba). Upsell magnet. |
| **Natto Kinase** | 25 | 120 | **21%** | ADD-ON | Scarce solo. Top pairs: Gaba (92), Metabo (59). Rep-recommended. |
| **Hyaluron & Collagen** | 35 | 135 | **26%** | ADD-ON | Premium positioning. High AOV in pairs, rarely solo. |
| **Gaba blood pressure** | ~15 | ~270 | **~6%** | PURE ADD-ON | Virtually never purchased alone. 276 co-appearances. Rep-driven discovery product. |

**Key insight:** There's a clear spectrum:
- **ANCHOR (>60% solo)**: Entry SKUs drive themselves. Metabo, Coix, Reishi.
- **HYBRID (40-50% solo)**: Cordyceps bridges both—premium price point allows solo anchor role, but also premium upsell vehicle.
- **ADD-ON (<30% solo)**: Fucoidan, Shark, Natto, Hyaluron, **Gaba**. These are rep-recommended secondary purchases.

---

## Q2: Discount Allocation in Bundled Orders

From baseline discount analysis (151 orders with discount, entry+premium co-purchase subset):

```
entry SKU lines:   782 lines | avg disc = 16.6% of line revenue
premium SKU lines: 948 lines | avg disc = 7.3% of line revenue
```

**Discount landing pattern:**
- **Entry SKU**: Gets proportionally deeper discount (~16.6%) → attract customer price-sensitive segment
- **Premium SKU**: Gets shallow discount (~7.3%) → protect premium margin
- **Absolute terms**: Premium gets larger $$ discount (167K vs 12K) because premium base price is 35× entry

**Multi-item discount rate vs single-item:**

| Basket type | Discount rate |
|---|---|
| 1 item | 2.6% |
| 2+ items | 2.2% |

**Conclusion:** Discount lands proportionally on entry SKUs when bundles DO get discounted (which is rare). But discount is NOT the driver—the 2.2% rate in multi-item orders is actually LOWER than single-item (2.6%), meaning rep bundles without discount. Discounts appear as exceptions when customer negotiates or clearance situation.

---

## Q3: Gaba Blood Pressure — Mystery Product Profile

### Data points from baseline:

```
Co-appearance frequency:
  - Cordyceps + Gaba: 132 orders (strongest pair)
  - Natto Kinase + Gaba: 92 orders
  - Shark Cartilage + Gaba: 52 orders
  - Metabo + Gaba: ~15-20 estimated (not in top-30 pairs)
  Total Gaba co-appearances: ~276 orders

Discount on Gaba pairs:
  - Cordyceps + Gaba: 3.5% discount
  - Natto + Gaba: 3.2% discount
  - Shark + Gaba: 0.0% discount
  Avg: ~2-3% (slightly higher than Metabo pairs at 0.7%)

Price positioning:
  Cordyceps + Gaba avg order value: 2.59M VND (~$100 USD)
  → Suggests Gaba is mid-tier premium, NOT ultra-premium like Fucoidan (8.6M)
```

### Hypotheses (unresolved):

1. **FineJapan product or exclusive distribution?** Gaba blood pressure may be:
   - Proprietary blend (FineJapan branded)
   - Exclusive to FineJapan retail (not MISA)
   - Recent new launch (high discovery rate via rep bundling)

2. **Rep-driven targeting:**
   - High pairing rate with Cordyceps & Natto (both premium, health-focused) suggests targeting health-conscious segment
   - Very low solo rate (~6%) = not self-discovered; rep actively recommends
   - Slightly higher discount rate (3.5% vs 0.7%) = rep using Gaba as soft-close discount point

3. **Customer segment:**
   - Orders with Cordyceps + Gaba = older, health-conscious (Cordyceps = tonic root targeting 45+)
   - Orders with Natto + Gaba = younger, cardiovascular health focused
   - Orders with Shark = skin/collagen + blood pressure = female anti-aging + health

4. **Price point:** At 2.59M avg order, Gaba sits between entry (1.3M for Metabo solo) and ultra-premium (8.6M for Fucoidan). Likely 800K-1.2M per unit.

### Unresolved:
- Exact product name in dim_products? (May need to check product.name directly)
- Launch date? (If <6mo old, high pairing is normal for new discovery ramp)
- Is it a FineJapan product or third-party distribution?
- What percentage of Gaba orders are sourced to specific reps? (High concentration = 1-2 reps championing it)

---

## Q4: NULL Discount Rate — Data Quality Assessment

From baseline (6,345 retail orders):

```
Discounted orders: 151 (2.4%)
Orders with max_discount_rate = NULL: 3,832 (60%)
Implied zero-discount orders: ~2,362 (37%)
```

**Interpretation:**

| Category | Count | % | Assessment |
|----------|-------|---|---|
| Explicit discount (discount_amount > 0) | 151 | 2.4% | Tracked; high confidence in discount value |
| Null discount_rate | 3,832 | 60% | Ambiguous: either "no discount applied" OR "not tracked" |
| Implied zero-discount | 2,362 | 37% | Likely full-price orders with clean data |

**Data quality flag:**
- The 60% NULL rate is high. Could mean:
  - Old orders from before discount tracking was implemented
  - Discount tracking gaps (rep didn't log reason codes)
  - System design: discount_rate only populated when rep uses a promo code, not manual discounts

**Recommendation for future analysis:**
- Filter to orders with `max_discount_rate IS NOT NULL` to get clean discount/no-discount binary
- Reduces sample to ~2,513 orders (40% of 6,345) but removes ambiguity
- Or cross-check with promotion lookup table to infer discount vs no-discount from order_id

---

## Strategic Implications

### 1. Bundling is rep expertise, not discount-driven
The data clearly shows:
- Discount is NOT correlated with bundle size (2.2% vs 2.6%)
- Rep bundles happen at full price in 97%+ of multi-item orders
- **Action:** Train reps on value proposition bundling, not price-cut bundling. Use discount as exception (close negotiation) not rule (bundle incentive).

### 2. Anchor SKUs should be lead generators; add-ons should be reservation items
- **Metabo Green Tea (85% solo)**: Position as front-door product. Price it aggressively, control inventory, make it easy to buy. This is the basket-builder.
- **Gaba blood pressure**: Treat as rep discovery play. Bundle as 2nd/3rd item to premium orders. High pairing rate = working as intended.
- **Cordyceps (46% solo)**: Dual role. Use as entry point for older demographics (500K+ segment) OR as upsell to entry-SKU buyers. Monitor which path dominates.

### 3. Gaba blood pressure requires go/no-go decision soon
- If newly launched (<6 months): pairing rates suggest product-market fit. Ramp up rep commission on Gaba to accelerate discovery.
- If mature (>1 year): low solo rate + high pairing suggests it's hitting ceiling—unlikely to convert to anchor. Consider bundling as permanent strategy or sunset.
- Missing link: need product launch date + per-rep Gaba attach rate to diagnose.

### 4. Gift bundle channel is separate P&L
- Nến, bát tre, dù orders are corporate/bulk buys (high item count, different rep behavior)
- Should exclude from retail playbook metrics
- Suggest tagging gift-bundle orders separately in warehouse for parallel funnel tracking

### 5. Discount audit needed
- 60% NULL rate on max_discount_rate is data quality risk
- Recommend: implement discount reason code on all discount orders (starting now) + back-fill recent 90 days if possible
- Until then, filter analysis to `max_discount_rate IS NOT NULL` for defensibility

---

## Unresolved Questions

1. **Gaba blood pressure exact product details:** Name in dim_products? Launch date? FineJapan vs distributor? Current rep attach rate by individual?
2. **Cordyceps segment split:** What % of Cordyceps solos are high-AOV anchor (500K+ orders) vs budget-conscious (200K)?
3. **Entry SKU list completeness:** Are there other entry SKUs (<300K) we haven't categorized? (Coix, Metabo, Reishi covered; Goji, Spirulina?)
4. **Discount_rate NULL handling:** Should we filter NULL or treat as zero? Check with warehouse owner on intent.
5. **Rep-level concentration:** Is Gaba pairing driven by 1-2 superstar reps or distributed? High concentration = training/culture problem or opportunity.
6. **Gift bundle mix impact:** How much of "multi-item order growth" is actually gift bundle inflation? May overstate retail bundling success.

---

## ⚠️ Correction — 2026-06-22 (zero-rev analysis)

**Q1 Solo Rate classification trong báo cáo này phần lớn là sai.** Vì dùng số đơn (order count) thay vì kiểm tra revenue, nó nhầm lẫn "orders containing Metabo" với "orders where Metabo was a paid purchase."

**Dữ liệu thực tế** (unit_rev per line):

| Sản phẩm | Solo → zero-rev% | Multi-SKU → zero-rev% | Classification thực |
|---|---|---|---|
| Metabo Green Tea | 10% | **75%** | Gift tool trong multi-SKU |
| Gaba blood pressure | 32% | **78%** | Gift tool trong multi-SKU |
| Coix Beauty | 11% | **67%** | Gift tool trong multi-SKU |

**Mô hình đúng:**
- Premium SKU (Shark/Natto/Cordyceps/Fucoidan, avg 1.9–4.3M) = trigger/anchor thực sự
- Metabo/Gaba trong multi-SKU = quà tặng rep đưa kèm, không phải sản phẩm khách chọn
- Solo entry orders (~90% có revenue thật) = khách entry thực, pool để upsell sau

Bảng "Anchor vs Add-On" trong báo cáo này cần đọc với caveat này. Số liệu pair counts vẫn đúng; chỉ chiều nhân quả (causal direction) là sai.

→ Xem report chi tiết: `plans/reports/finejapan-gift-entry-sku-zero-rev-260622-1720-report.md`

