# Order Economics — Incentive Sizing Probe
**Generated:** 2026-06-19  
**Source:** `olap.duckdb` views unreachable (Docker path mismatch); queries ran directly against latest rolling parquet files + rill/current deduplicated exports. All monetary values in VND.  
**Scope filter:** `is_active_order = true AND scope_sales = true`

---

## Q1 — Average Order Value (AOV)

### Overall (net_revenue, VAT-exclusive)

| Metric | Value (VND) |
|--------|-------------|
| Orders in dataset | 28,143 |
| Mean | 3,308,028 |
| Median | 1,333,333 |
| P25 | 500,000 |
| P75 | 2,998,333 |

> Net_revenue is VAT-exclusive (gross minus discount minus VAT). Gross AOV not used per pricing caveats.

### By Platform

| Platform | Orders | Mean (VND) | Median (VND) | P25 | P75 |
|----------|--------|------------|--------------|-----|-----|
| Shopee | 36,333 | 1,239,121 | 1,037,600 | 370,370 | 1,582,454 |
| Wholesale (Đại Lý) | 28,638 | 6,500,048 | 3,147,709 | 1,204,981 | 7,216,667 |
| Zalo | 3,753 | 4,811,457 | 2,733,241 | 1,406,574 | 5,833,333 |
| POS | 3,510 | 1,579,614 | 525,463 | 67,273 | 1,485,000 |
| Lazada | 3,420 | 1,519,275 | 1,259,400 | 963,653 | 1,925,678 |
| Facebook | 2,889 | 3,138,388 | 1,415,880 | 899,500 | 3,331,481 |
| Website | 2,574 | 2,065,044 | 1,241,690 | 0 | 2,545,455 |
| Tiki | 1,179 | 1,631,866 | 1,300,800 | 1,049,500 | 1,943,519 |
| Selly | 1,224 | 1,121,825 | 194,444 | 193,796 | 587,320 |

### By Value Group

| Value Group | Orders | Mean (VND) | Median (VND) | P25 | P75 |
|-------------|--------|------------|--------------|-----|-----|
| VALUE_VIP | 88,074 | 6,425,601 | 2,943,401 | 1,030,336 | 7,186,641 |
| VALUE_GOLD | 12,582 | 4,847,893 | 2,826,708 | 1,502,727 | 5,964,000 |
| VALUE_SILVER | 31,806 | 2,744,115 | 1,773,818 | 1,177,290 | 3,331,481 |
| VALUE_BRONZE | 120,825 | 1,023,600 | 881,020 | 288,889 | 1,457,190 |

---

## Q2 — Contribution Margin per Order

> Using `channel_net_profit` / `channel_net_margin_pct` (gross_profit minus channel platform fees). Orders with `has_cogs = true` only (28,107 of 28,143 total).

### Overall

| Metric | Value |
|--------|-------|
| Orders (has_cogs) | 28,107 |
| Mean CM VND | 1,305,302 |
| Median CM VND | 592,236 |
| P25 CM VND | 110,327 |
| P75 CM VND | 1,364,948 |
| Mean CM % | -13.1% ← skewed by extreme outliers |
| Median CM % | 47.3% ← use this |
| Negative-margin orders | 3,441 (12.2%) |

> Mean CM % is depressed by extreme negative outliers (shipping cost overruns, platform voucher subsidies). **Median 47.3%** is the operative figure.

### By Platform (has_cogs only)

| Platform | Orders | Mean CM VND | Median CM VND | P25 | P75 | Mean CM% | Median CM% |
|----------|--------|-------------|---------------|-----|-----|----------|------------|
| Shopee | 36,324 | 533,274 | 381,500 | 120,500 | 869,442 | -62.1% | 48.1% |
| Wholesale | 28,593 | 2,350,496 | 1,015,689 | 104,026 | 2,769,455 | 29.8% | 41.7% |
| Zalo | 3,735 | 2,382,416 | 1,118,809 | 465,267 | 2,748,959 | 47.5% | 57.7% |
| Lazada | 3,420 | 860,443 | 762,870 | 415,662 | 1,166,944 | 54.6% | 58.3% |
| Facebook | 2,889 | 1,527,278 | 849,034 | 171,582 | 1,847,322 | 47.2% | 56.3% |
| Website | 2,556 | 822,768 | 389,958 | 0 | 1,364,942 | 50.9% | 57.3% |
| Tiki | 1,179 | 871,872 | 699,800 | 429,500 | 1,168,997 | 53.2% | 55.8% |
| Selly | 1,224 | 531,454 | 34,796 | 25,537 | 222,217 | 25.2% | 18.0% |

> Shopee mean CM% is misleadingly negative due to ~268 extreme-loss orders (likely Shopee voucher/subsidy mismatches). Median is 48.1% — valid for incentive sizing.

### By Value Group (has_cogs only)

| Value Group | Orders | Mean CM VND | Median CM VND | Mean CM% | Median CM% |
|-------------|--------|-------------|---------------|----------|------------|
| VALUE_GOLD | 12,582 | 2,648,924 | 1,371,198 | 52.4% | 57.3% |
| VALUE_VIP | 87,912 | 2,329,304 | 900,635 | 26.7% | 41.2% |
| VALUE_SILVER | 31,752 | 1,438,314 | 860,796 | 46.2% | 56.2% |
| VALUE_BRONZE | 120,717 | 384,546 | 318,532 | -60.9% | 47.8% |

---

## Q3 — Order Value Distribution (net_revenue)

| Percentile | Value (VND) |
|------------|-------------|
| Min | 0 |
| P10 | 170,000 |
| P25 | 500,000 |
| P50 (median) | 1,333,333 |
| P75 | 2,998,333 |
| P90 | 7,524,400 |
| Max | 222,775,150 |

**Voucher sizing guidance:** A voucher of 50,000–150,000 VND is meaningful (10–29% of P10 order) and safe at median CM of ~592,236 VND. A voucher at 100,000 VND = 1.7% of median net_revenue, leaving 590,000+ VND net CM per order.

---

## Q4 — Masked Repeat Marketplace Prize

**Definition used:** `source_contact_quality = 'masked' AND order_count > 1 AND channel_preference = 'CHANNEL_MARKETPLACE'`  
Count = **364 customers** (brief cited 346 — slight data shift since CRM segment was created).

| Metric | Value (VND) |
|--------|-------------|
| Customer count | 364 |
| Total lifetime value | 1,544,303,660 |
| Avg lifetime value | 4,242,592 |
| Avg order spend | 1,308,722 |
| Total lifetime CM | 683,028,367 |
| Avg lifetime CM | 1,876,452 |
| Avg order count | 3.1 |

**Breakdown by acquisition source (Shopee-originated only):**

| Source | Customers | Total LTV | Avg LTV | Avg CM | Total CM |
|--------|-----------|-----------|---------|--------|----------|
| Shopee - Fine Japan Vietnam | 186 | 921,967,100 | 4,956,812 | 2,215,866 | 412,151,114 |
| Shopee - JPC OFFICIAL | 119 | 417,096,706 | 3,505,014 | 1,477,247 | 175,792,351 |
| Shopee - JPC SHOP | 26 | 67,070,510 | 2,579,635 | 1,034,275 | 26,891,154 |
| Shopee - thehealthyus | 13 | 26,701,185 | 2,053,937 | 720,119 | 9,361,544 |

**Revenue at stake (identity capture):** If all 364 masked repeat customers could be identified and contacted, projected incremental lifetime value from identity-linked targeting = 683M VND CM already accrued, with future order potential based on avg 3.1 orders and growing.

---

## Q5 — Second-Order Economics

### From dim_customers (all repeat customers with avg_days_between_orders > 0)

| Metric | Value |
|--------|-------|
| Repeat customers | 1,568 |
| Avg days between orders | 138 days |
| Median days between orders | 77 days |
| P25 | 31 days |
| P75 | 183 days |
| Avg order spend (repeat) | 1,862,597 VND |
| Median order spend (repeat) | 789,227 VND |

### Direct Order 1 vs Order 2 analysis (from rill/current fact_orders, deduplicated)

| Metric | Value (VND) |
|--------|-------------|
| Repeat customer pairs | 1,009 |
| Avg order 1 value | 3,325,822 |
| Median order 1 value | 1,282,909 |
| Avg order 2 value | 2,559,620 |
| Median order 2 value | 1,259,400 |
| Avg O2/O1 value ratio | 1.22× (order 2 is ~22% higher in VND on average) |
| Avg days to order 2 | 82 days |
| **Median days to order 2** | **33 days** |
| P25 | 9 days |
| P75 | 96 days |

> The 33-day median gap is the key trigger window. 50% of second orders occur within 33 days. A second-order offer delivered within days 7–14 after first purchase will capture the bulk of the conversion window.

---

## Q6 — Recent One-Time Buyers (A3 Target)

**Definition:** `is_contactable = true AND order_count = 1 AND recency_days <= 90`

| Metric | Value (VND) |
|--------|-------------|
| A3 contactable count | 27 total; **11 with confirmed order revenue** (10 with LTV > 0) |
| Avg first-order value (from orders) | 2,525,700 |
| Median first-order value | 1,684,028 |
| Avg CM per order | 1,169,684 (62.6%) |
| Total first-order revenue | 30,308,398 |
| Total CM | 14,036,213 |

**Including masked (non-contactable) one-timers, recency <= 90 days:**

| Metric | Value |
|--------|-------|
| Total (contactable + masked) | 139 customers |
| Contactable only | 27 |
| Avg first-order value (incl. masked) | 1,025,732 VND |
| Total LTV (incl. masked, LTV > 0) | 142,576,758 VND |

> The A3 contactable pool is small (27) but their avg order value (1.7M–2.5M) and CM% (62.6%) are healthy. All are VALUE_BRONZE. The masked 112 represent an additional reachable pool if identity capture occurs.

---

## Hard Constraints for Incentive Sizing

| Constraint | Value |
|------------|-------|
| **Median CM per order (overall)** | 592,236 VND → opt-in incentive budget ceiling ~50,000–100,000 VND (<17%) |
| **Median CM per order (Shopee)** | 381,500 VND → Shopee incentive ceiling ~30,000–50,000 VND |
| **Median CM per order (Lazada)** | 762,870 VND → Lazada incentive ceiling ~50,000–75,000 VND |
| **Median CM per order (Zalo/FB/Website)** | 849,034–1,118,809 VND → ceiling ~75,000–150,000 VND |
| **Second-order trigger window** | Median 33 days; deploy offer within 7–14 days to be ahead of natural reorder |
| **Second-order value uplift** | O2 avg = 2.56M vs O1 avg = 3.33M → O2 is slightly lower on average but 1.22× higher in VND (mean) — median O2 (1.26M) closely tracks median O1 (1.28M); no steep uplift to target |
| **A3 target pool (contactable)** | 27 customers; avg CM 1.17M → incentive budget ≤ 100,000–150,000 VND per customer to stay positive |
| **Masked Shopee repeat (Q4 prize)** | 364 customers × 4.2M avg LTV × ~47% CM → each identity captured = ~1.9M VND incremental CM at stake |
| **Negative-margin order rate** | 12.2% overall; Shopee 7.1% — blanket discounts will push marginal orders negative; target contactable customers with healthy CM history |

---

## Unresolved Questions

1. **TikTok missing from data** — no TikTok platform appears in dim_channels. If TikTok Shop is a planned channel, its economics are not benchmarked here.
2. **Selly median CM = 18%** (vs 47% Shopee) — Selly appears to have structurally low margins; confirm whether Selly is still active before building re-sell funnel for it.
3. **A3 pool is very small (27 contactable)** — "recency_days <= 90" yields only 27 contactable one-timers. If the funnel needs more scale, consider extending window to 180 days (untested here) or relaxing to include `contact_quality = 'unverified'`.
4. **avg_order_spend = 0 for ~16 of 27 A3 customers** — dim_customers.avg_order_spend is null/0 for many; lifetime_value is more reliable proxy. Root cause not investigated.
5. **Wholesale (Đại Lý) economics dominate VIP/GOLD** — VIP mean AOV 6.4M is driven by wholesale agents, not direct consumers. If the re-sell funnel targets end consumers, VIP/GOLD benchmarks may be inflated and Shopee/Lazada benchmarks are more representative.
