# Profile Cohort Khách Mua-Lặp — Deadstock Thanh Lý FJV

**Generated:** 2026-06-21 | **Mart:** mart_deadstock_target_queue (parquet 20260621T141616)

---

## TL;DR — 5 Đặc Tính Cốt Lõi

1. **414 khách distinct / 499 rows** (4 SKU). Hầu hết (**97.3%**) đã mua ≥2 lần lịch sử; 16.7% mua >1 trong 4 SKU ế — cross-sell khả thi.
2. **Phần lớn đã lạnh** — 61.8% im >1 năm (tier LAPSED_VALUABLE 46.6% + MASKED_REPEAT 36.7%). Chỉ 18.4% warm (≤90d). Cần hook mạnh để kéo dậy.
3. **Tập trung nặng ở promo** — 98.3% voucher-eligible, 84.1% PROMO_DEPENDENT. Rủi ro ăn margin nếu không phân tầng offer. Chỉ 7 khách (1.7%) full-price thật sự.
4. **63.3% tiếp cận được qua HUG (số điện thoại thật)**; 36.7% masked Shopee — leg-2 cần native Shopee outreach riêng.
5. **91.5% affinity PRODUCT_FINE_JAPAN** — đây là fan thương hiệu, không phải SKU chéo. Natto Kinase (VCST21003L001) chiếm 61.8% audience nhưng median lần mua cuối 989 ngày (~2.7 năm) — khó nhất về recency.

---

## 1. Quy Mô & Cấu Trúc

| Chỉ số | Giá trị |
|--------|---------|
| Tổng rows (khách × SKU) | 499 |
| Khách distinct | **414** |
| SKU | 4 |
| Holdout (~25%) | 113 (27.3%) |
| Active cohort (non-holdout) | **334** |

**Multi-SKU overlap:**

| SKU count / khách | Khách | % |
|-------------------|-------|---|
| 1 SKU | 345 | 83.3% |
| 2 SKU | 53 | 12.8% |
| 3 SKU | 16 | 3.9% |

→ 16.7% (69 khách) mua ≥2 SKU ế — cross-sell bundle tiềm năng.

---

## 2. Tier Mix (Strategic)

| Tier | Khách | % | Ý nghĩa |
|------|-------|---|---------|
| LAPSED_VALUABLE | 193 | **46.6%** | Từng có giá trị, đã dừng mua |
| MASKED_REPEAT | 152 | **36.7%** | Shopee-masked, mua lặp nhưng không contact thật |
| DORMANT_VALUABLE | 42 | 10.1% | Ngủ đông, từng valuable |
| LIVE_CORE | 24 | 5.8% | Đang active — nhóm chủ lực nhưng nhỏ |
| SECOND_ORDER | 3 | 0.7% | Vừa mua lần 2 |

---

## 3. Giá Trị (Value Group & LTV)

| Value Group | Khách | % | Median LTV (VND) | Tổng LTV (tỷ) |
|-------------|-------|---|-----------------|----------------|
| VALUE_VIP | 59 | 14.3% | 97.2M | **75.2 tỷ** |
| VALUE_GOLD | 33 | 8.0% | 26.9M | 1.2 tỷ |
| VALUE_SILVER | 109 | 26.3% | 8.5M | 1.1 tỷ |
| VALUE_BRONZE | 213 | 51.4% | 1.2M | 0.4 tỷ |

**LTV Distribution (414 khách distinct):**

| Percentile | LTV (VND) |
|-----------|-----------|
| Min | 0 |
| P25 | 665K |
| Median | 4.4M |
| P75 | 12.1M |
| Max | 12.0 tỷ |
| **Tổng** | **~34 tỷ** |

**VIP tập trung ở đâu:**

| Tier | VIP count | Median LTV VIP |
|------|-----------|----------------|
| LIVE_CORE | 11 | **349.8M** |
| MASKED_REPEAT | 19 | 73.0M |
| DORMANT_VALUABLE | 6 | 90.7M |
| LAPSED_VALUABLE | 23 | 57.3M |

→ 11 LIVE_CORE VIP = 20.6 tỷ LTV — nhỏ nhưng impact thanh lý lớn nhất.

---

## 4. Recency — Độ Nguội

| Bucket | Khách | % |
|--------|-------|---|
| ≤90 ngày (warm) | 76 | **18.4%** |
| 91–365 ngày (cool) | 82 | **19.8%** |
| >365 ngày (cold) | 256 | **61.8%** |

→ 61.8% cold. Campaign reactivation cần incentive đủ mạnh; warm 18.4% là low-hanging fruit.

---

## 5. Repeat Depth

**Order count (toàn bộ lịch sử mua):**

| Bucket | Khách | % |
|--------|-------|---|
| 1 đơn | 11 | 2.7% |
| 2–3 đơn | 222 | 53.6% |
| 4–10 đơn | 116 | 28.0% |
| 10+ đơn | 65 | 15.7% |

→ 97.3% đã mua ≥2 lần; 43.7% mua ≥4 lần — khách quen thương hiệu.

**buyer_sku_qty (số đơn vị SKU ế đó đã mua):**
Median 2 units; avg 18.2 (bị kéo bởi outlier max 4,278 — có thể đại lý).

**Lần mua cuối SKU ế (days ago, median):**

| SKU | Product | Median (ngày trước) | Min (ngày trước) |
|-----|---------|---------------------|-----------------|
| VCSC23054B001 | Coix Beauty | **242** | 6 |
| VTST23023L001 | Shark Cartilage | 846 | 20 |
| VTSL21005C001 | Shijimi Drink | 919 | 906 |
| VCST21003L001 | Natto Kinase | **989** | 6 |

→ Coix Beauty recency tốt nhất (median 242d, có người mua 6 ngày trước). Natto Kinase và Shijimi rất nguội (989d / 919d median).

---

## 6. Tín Hiệu Tái Mua (Replenishment)

| Signal | Khách | % |
|--------|-------|---|
| OVERDUE | 290 | **70.0%** |
| ON_TRACK | 66 | 15.9% |
| DUE_SOON | 32 | 7.7% |
| NULL | 26 | 6.3% |

→ **77.7% đang OVERDUE hoặc DUE_SOON** = đến nhịp tái mua hoặc đã trễ. Timing tốt để push.

---

## 7. Discount Sensitivity & Voucher

| Sensitivity | Khách | % | Voucher eligible |
|------------|-------|---|-----------------|
| PROMO_DEPENDENT | 348 | **84.1%** | 100% |
| PROMO_MIXED | 59 | 14.3% | 100% |
| FULL_PRICE | 7 | **1.7%** | 0% |

- **98.3% voucher_eligible** — nếu không phân tầng offer, sẽ ăn margin toàn tập.
- 7 khách FULL_PRICE = segment nhỏ nhưng không cần giảm giá → ưu tiên khác.

---

## 8. Kênh Tiếp Cận (Route Channel & Contact Quality)

| Channel | Contact Quality | Khách | % |
|---------|----------------|-------|---|
| HUG | real | 262 | **63.3%** |
| SHOPEE_NATIVE | masked | 152 | **36.7%** |

→ **Leg-1 (HUG):** 262 khách — push qua Zalo/SMS trực tiếp với voucher cá nhân hóa.
→ **Leg-2 (Shopee):** 152 khách masked — dùng Shopee Follow Prize / Shopee Live / retargeting; không có số điện thoại thật.

---

## 9. SKU Concentration

| SKU | Product | Khách | % Audience | Stock Value (MAC) | Health | Dead? |
|-----|---------|-------|-----------|-------------------|--------|-------|
| VCST21003L001 | Natto Kinase | 256 | **61.8%** | 35.2M | DOG | No |
| VCSC23054B001 | Coix Beauty | 148 | 35.7% | 2.2M | DOG | No |
| VTST23023L001 | Shark Cartilage | 92 | 22.2% | 41.5M | QUESTION | No |
| VTSL21005C001 | Shijimi Drink | 3 | 0.7% | 2.1M | BALANCED | **Yes** |

**Ghi chú:**
- `dead_stock_value_at_risk = 0` cho 3 SKU đầu — có thể chưa tagged is_dead_stock=True dù health=DOG. Chỉ Shijimi có deadstock_risk ghi nhận (2.06M).
- Shark Cartilage có stock_value_mac cao nhất (41.5M) nhưng health=QUESTION; audience 92 khách, recency median 846d.
- Natto Kinase audience lớn nhất (256) nhưng recency nguội nhất (989d median).

---

## 10. Holdout

| | Khách | % |
|--|-------|---|
| Active (non-holdout) | 334 | **80.7%** |
| Holdout | 113 | **27.3%** |

→ Holdout ~27.3% (cao hơn mục tiêu ~20% một chút — cần kiểm tra logic gate).

---

## 11. Affinity, Acquisition & Geo (via dim_customers JOIN)

**Channel Preference:**

| Channel | Khách | % |
|---------|-------|---|
| CHANNEL_MARKETPLACE | 179 | 43.2% |
| CHANNEL_DIRECT | 90 | 21.7% |
| CHANNEL_OTHER | 85 | 20.5% |
| CHANNEL_SOCIAL | 44 | 10.6% |
| CHANNEL_OFFLINE | 16 | 3.9% |

**Product Affinity:**

| Affinity | Khách | % |
|---------|-------|---|
| PRODUCT_FINE_JAPAN | 379 | **91.5%** |
| PRODUCT_MULTI | 35 | 8.5% |

→ Đây là fan FJ thuần. Messaging nên nhấn vào brand trust, không phải deal.

**Acquisition Source (top 10):**

| Source | Khách | % |
|--------|-------|---|
| US (US store) | 83 | 20.0% |
| Shopee - Fine Japan Vietnam | 71 | 17.1% |
| Đại Lý | 60 | 14.5% |
| Shopee - JPC OFFICIAL | 28 | 6.8% |
| Shopee - FWG Vietnam | 25 | 6.0% |
| Zalo | 19 | 4.6% |
| Shopee - JPC SHOP | 18 | 4.3% |
| Other | 18 | 4.3% |
| Lazada - FINE WORLD GROUP | 15 | 3.6% |
| Facebook | 14 | 3.4% |

→ 20% từ US store (flagship); 14.5% đại lý — cần xác nhận đại lý có trong phễu thanh lý không.

**Geo Region:**

| Region | Khách | % |
|--------|-------|---|
| GEO_HCMC | 232 | **56.0%** |
| GEO_OTHER | 93 | 22.5% |
| GEO_MEKONG | 41 | 9.9% |
| GEO_CENTRAL | 38 | 9.2% |
| GEO_HANOI | 10 | 2.4% |

→ HCMC chiếm 56% — nếu có offline event / flash sale tại điểm, HCMC là địa bàn ưu tiên.

---

## Hàm Ý Campaign (Offer Sizing, Messaging, Ưu Tiên)

### Phân tầng offer (tránh ăn margin)

| Segment | Size | Offer gợi ý |
|---------|------|-------------|
| FULL_PRICE (7 khách) | 1.7% | Không cần giảm — ưu tiên trải nghiệm, quà tặng |
| LIVE_CORE VIP (11 khách, LTV median 350M) | 2.7% | Flash exclusive, không cần % lớn; loyalty framing |
| LAPSED/DORMANT VIP (29 khách) | 7.0% | Reactivation offer mạnh (15–20%?); bundle cross-SKU |
| PROMO_DEPENDENT bulk (348 khách) | 84.1% | Voucher có floor (mua đủ X → giảm Y); tránh blanket % |

### Ưu tiên SKU / kênh

1. **Coix Beauty (148 khách, median recency 242d)** — recency tốt nhất, warm nhất → test trước, expect CR cao nhất.
2. **Shark Cartilage (92 khách, stock 41.5M)** — stock value lớn nhất, nhưng recency 846d → cần hook mạnh hơn; QUESTION health = vẫn bán được nếu đúng moment.
3. **Natto Kinase (256 khách, stock 35.2M)** — audience lớn nhất nhưng nguội nhất (989d); cần warm-up trước; 6 người mua gần (min 6d) = hạt nhân micro-advocate.
4. **Shijimi Drink (3 khách)** — audience quá nhỏ, không tạo campaign riêng; bundle vào offer.

### Leg phân kênh

- **HUG leg (262 khách):** Zalo OA / SMS cá nhân hóa với mã voucher riêng. Có thể A/B ngưỡng giảm giá.
- **Shopee leg (152 khách):** Shopee Follow Prize, voucher Shopee collection, hoặc retargeting quảng cáo Shopee; không push qua Zalo.
- OVERDUE+DUE_SOON = 310/414 (75%) → timing push ngay trong 2 tuần tới.

### Holdout & Measurement

- Holdout 27.3% (113 khách) đủ để đo incremental; nếu muốn chính xác ~20% nên re-check gate logic.

---

## Unresolved Questions

1. **dead_stock_value_at_risk = 0 cho Natto / Coix / Shark** — 3 SKU health=DOG/QUESTION nhưng không có deadstock_risk ghi nhận; `is_dead_stock=False` cho cả 3. Đây là mart logic issue hay thực sự chưa tagged? Nếu chưa tagged, tổng at-risk thực tế lớn hơn nhiều (stock_value_at_mac = 35.2M + 2.2M + 41.5M = ~78.9M).
2. **buyer_sku_qty outlier 4,278 units** — có thể là khách đại lý (acquisition_source = Đại Lý chiếm 14.5%). Đại lý có nên trong phễu thanh lý cá nhân không? Hay tách sang kênh bulk B2B?
3. **Holdout 27.3% vs target ~20%** — gate logic có đúng không? Cần xác nhận.
4. **CHANNEL_OTHER 20.5%** — chưa rõ là kênh nào. Nếu là offline POS, outreach digital sẽ miss họ.
5. **next_purchase_signal NULL 6.3% (26 khách)** — thiếu predicted_next_purchase_date hay logic chưa cover?
6. **Đại lý trong cohort** — 60 khách có acquisition_source = "Đại Lý" (~14.5%); họ đại diện end-consumer hay reseller? Nếu là reseller, LTV và order_count sẽ skew.
