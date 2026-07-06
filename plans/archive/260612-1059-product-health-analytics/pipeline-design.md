# Product Health — Pipeline / Data-Layer Design (ultrathink)

> Câu hỏi: "cân nhắc kỹ pipeline để calculate more insight?" — đây là phân tích data layer TRƯỚC khi build board.
> Nguyên tắc: **DRY tối đa** — rất nhiều health primitive đã tính sẵn; chỉ build lớp SYNTHESIS/CLASSIFICATION còn thiếu.

## 1. DRY audit — cái gì ĐÃ có (KHÔNG build lại)

| Tín hiệu | Đã có ở | Cột |
|---|---|---|
| Inventory health | `mart_inventory_health` | is_oos, is_low_stock, is_overstock, **days_of_supply**, is_slow_mover, is_dead_stock, slow/dead_stock_value_at_risk, on_hand, mac, stock_value_at_mac |
| Velocity/margin/returns | `mart_sku_economics_monthly` | daily_velocity, units_sold, realized_margin_pct, cogs_variance_pct, return_rate, return_adjusted_margin_pct, **days_since_last_sale, is_slow_mover, revenue_share_pct, margin_outlier**, top_channel |
| Cost/COGS variance | sku_economics | cogs_per_unit, cogs_per_unit_3m_avg, cogs_variance_pct |

→ Inventory & cost & velocity & returns = **xong**. Đừng tính lại.

## 2. Gap — cái CHƯA có (lớp insight cần build)

| # | Insight mới | Vì sao | Nguồn |
|---|---|---|---|
| G1 | **Product Health Classification** (⭐STAR/🐎WORKHORSE/❓QUESTION/🐕DOG) | mảnh ghép có (velocity, margin) nhưng KHÔNG có phân loại tổng hợp — đây là centerpiece "product health" | NTILE(velocity) × NTILE(margin) trên SKU có data |
| G2 | **ABC / Pareto class** (A/B/C theo % doanh thu lũy kế) | revenue_share_pct có nhưng chưa bucket A/B/C | cumulative sum revenue_share |
| G3 | **Velocity momentum** (ACCELERATING/STABLE/DECELERATING) | health = xu hướng, không chỉ mức hiện tại; có 24 tháng history chưa dùng | slope/MoM trên sku_economics 24m |
| G4 | **Lifecycle stage** (NEW/GROWING/MATURE/DECLINING/DORMANT) | analog customer lifecycle | momentum (G3) + days_since_last_sale + first_sale |
| G5 | **Discount dependency / SKU** (share doanh thu/đơn có discount) | analog customer discount_sensitivity; nối margin erosion | fact_sales.discount_amount per product |
| G6 | **OOS-risk có ưu tiên** (STAR/A-class sắp hết hàng) | is_oos thô có, nhưng chưa gắn với value tier để ưu tiên restock | join inventory flag × health class |
| G7 | **Current-state mart 1-row/product** | sku_economics = monthly grain; inventory = daily; CHƯA có 1 view "sức khỏe SP hiện tại" (analog dim_customers) | join latest |
| G8 | **Product action queue** (RESTOCK/CLEAR/REVIEW_MARGIN/PROMOTE/DELIST) | analog mart_customer_action_queue — lớp operational | health class × inventory × margin |

## 3. Đề xuất pipeline (mirror customer: int → mart current → action queue)

```
fact_sales ─┐
sku_economics(24m) ─┼─► int_product_velocity_trend   (G3 momentum, G4 lifecycle dates)
            └─► int_product_discount_dependency (G5)

mart_sku_economics_monthly(latest) ─┐
mart_inventory_health(latest)       ─┼─► mart_product_health  (1 row/product, current state)
int_product_velocity_trend          ─┤      G1 health_class · G2 abc_class · G3 momentum
int_product_discount_dependency     ─┤      G4 lifecycle · G6 oos_risk · days_of_supply(reuse)
dim_products                        ─┘      is_dead_stock(reuse) · discount_dependency · has_margin_data

mart_product_health ─► mart_product_action_queue (G8: RESTOCK/CLEAR/REVIEW_MARGIN/PROMOTE/DELIST)
```

### mart_product_health (centerpiece, analog dim_customers)
Grain: 1 row / product_key (current). Cột:
- Identity: product_key, sku, product_name, category, brand
- **abc_class** (A/B/C), **health_class** (STAR/WORKHORSE/QUESTION/DOG), **lifecycle_stage**, **velocity_momentum**
- Perf: daily_velocity, units_sold_30d/last_month, revenue_share_pct, days_since_last_sale
- Margin (where has_margin_data): realized_margin_pct, cogs_variance_pct, margin_outlier
- Inventory (reuse): on_hand, days_of_supply, is_oos, is_low_stock, is_dead_stock, stock_value_at_mac, dead_stock_value_at_risk
- **oos_risk** (high velocity + low stock), **discount_dependency**
- **has_margin_data** BOOL (coverage caveat — chỉ ~42 SKU có COGS)

### Classification logic (grounded, NTILE relative — như customer RFM phase 2)
- velocity_score = NTILE(5) trên daily_velocity · margin_score = NTILE(5) trên realized_margin_pct (chỉ SKU has_margin_data)
- STAR: vel≥4 & margin≥4 · WORKHORSE: vel≥4 & margin≤2 · QUESTION: vel≤2 & margin≥4 · DOG: vel≤2 & margin≤2 · else BALANCED
- Overlay (ưu tiên): 🚨 OOS_RISK nếu (is_oos|is_low_stock)&velocity cao · 🐌 DEAD nếu is_dead_stock · 📉 nếu momentum=DECELERATING

## 4. Coverage caveats (phải ghi rõ trên board)
- **Margin health chỉ ~42/685 SKU** (COGS từ MISA chỉ map hero SKU). Inventory health phủ 685. → board tách "có margin data" vs không; đừng kết luận margin cho SKU thiếu COGS.
- `fact_order_returns` chỉ 10 dòng → return signal yếu, dùng return_rate từ sku_economics (đã allocate) thay vì fact_order_returns.

## 5. Cái HOÃN (YAGNI / build lớn riêng)
- Market-basket / frequently-bought-together (đòn bẩy cross-sell, nhưng build lớn — domain riêng).
- Sell-through rate (cần receiving/PO data — incoming có nhưng cần kỳ receiving).
- Mở rộng COGS coverage >42 SKU (data-source/MISA mapping — ngoài scope analytics).

## Open questions
1. mart_product_health current-state: lấy "latest month" của sku_economics (2026-05) hay rolling-30d từ fact_sales? (rolling-30d tươi hơn nhưng tính lại velocity)
2. Action queue: build luôn (G8) hay phase sau? (centerpiece là health mart; action queue là operational layer thêm)
3. Health_class dùng NTILE tuyệt đối (toàn tệp) hay theo category (so sánh trong nhóm SP)? — theo category công bằng hơn cho SP ngách.
