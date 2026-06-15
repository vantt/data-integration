---
title: "FIND-006 - Margin And Activation Signals"
stage: 2
status: resolved
date: 2026-06-11
source_queries:
  - ../../../reports/realized-margin-by-customer-segment-query-260611-2230-report.md
  - ../../../reports/delivery-experience-retention-query-260611-2230-report.md
  - ../../../reports/action-queue-p3-signals-refresh-query-260611-2230-report.md
---

# FIND-006 - Margin And Activation Signals

**Registry:** [FIND-006](../REGISTRY.md#find-006)

> 3 mart mới commit SAU lần cập nhật plan (2026-06-09/10): `fact_order_economics` (realized margin),
> `fact_fulfillments` (shipment tracking), action_queue/P3 đã refresh. Query trên
> `sapo_export_latest.duckdb` (fresh 2026-06-11 10:12 ICT, retail scope).

---

## ĐẢO KHUNG: "bán ế" KHÔNG chỉ là thiếu cầu — 1/3 đơn lẻ ĐANG LỖ

Realized margin (mới có) cho thấy vấn đề thứ 2, cấp bách hơn retention:

- **30.7% đơn lẻ (199/649) lỗ fully-loaded — TẤT CẢ nằm trên Shopee.**
- Kênh nhà đều LÃI: Web **+24.9%** FL margin · Facebook **+23.2%** · Zalo **+6.9%**.
- Shopee đều LỖ: Fine Japan VN **−18.8%** · JPC SHOP **−32.7%** · thehealthyus **−44.7%**. Riêng phí sàn Fine Japan VN nuốt **−48.7tr**.
- → **Activation trên channel/discount mix hiện tại = scale LỖ.** Plan đã trực giác "Shopee thuê không sở hữu" + "rò discount" — data giờ ĐỊNH LƯỢNG, nâng từ giả thuyết thành **ràng buộc cứng**: retail activation phải có **margin gate**.

**Rò discount đã định lượng:**
- PROMO_DEPENDENT (639 đơn, 98.5% cohort): discount nuốt **55.4%** gross revenue, FL margin **−20.1%**.
- 1,235 khách lặp lại **100% phụ thuộc discount**. Không sửa được bằng "bảo vệ full-price" — **FULL_PRICE chỉ 11 khách, toàn BRONZE & 9/11 đã churn**. Không tồn tại cohort premium để bảo vệ.
- → Phải **thiết kế lại offer** (loyalty/bundle/reframe giá trị), KHÔNG phải tăng/giữ discount.

**VALUE_BRONZE (71% đơn) net-NEGATIVE** — đừng đổ công CSKH win-back khách bronze lỗ. Sweet spot lãi nhất = **VALUE_SILVER (+10.8% FL, +25.4tr)**.

> ⚠️ Reconcile cần làm: VIP/GOLD gross margin cao (54–56%) nhưng FL margin về âm sau overhead — **nghi do phương pháp phân bổ overhead** (đè đơn lớn). Xác minh allocation key TRƯỚC khi tuyên VIP lỗ. (Caveat agent margin #2.)

---

## Delivery KHÔNG phải đòn bẩy (negative finding — chuyển hướng công sức)

`fact_fulfillments` phủ 99.9% đơn lẻ (1,870/1,871), 2021–2026:
- **Tốc độ giao KHÔNG dự báo mua lại.** Cohort 2026 cùng cửa sổ quan sát: fast≤3d **21.6%** vs slow>7d **25.0%** repeat — phẳng. (Số raw "slow lặp lại nhiều hơn" là tenure bias.)
- Giao THẤT BẠI có tín hiệu yếu (repeat 11.1% vs 21–25%) nhưng chỉ chạm **5.5%** khách 2026 → không giải thích được 71.8% one-timer.
- `shipment_status` toàn NULL → không bóc được lý do (mất/từ chối/hoàn).
- → **Đừng đầu tư fix tốc độ giao để cứu retention.** WHY của one-timer nằm ở product-fit / acquisition quality / offer — KHÔNG ở logistics.

---

## Tín hiệu activation — refresh (số plan cũ 06-09 đã stale, nhiều cái GIẢM)

**🎯 Việc #1 NGAY TUẦN NÀY — 142 khách contactable đang "trên đồng hồ" = 653.8tr LTV**
(131 OVERDUE + 11 DUE_SOON, có phone). Đây là call-list Zalo/CSKH ưu tiên tuyệt đối.

**Action queue (110 dòng, fresh 10:16 hôm nay) — co lại 34%:**

| action_type | count | value_at_stake | contactable |
|---|---|---|---|
| WIN_BACK | 30 | 911.4tr | 27 |
| REORDER_NUDGE | 21 | 112.1tr | 8 |
| CALL_NOW | 3 | 82.8tr | 1 |
| SECOND_ORDER | 54 | 50.1tr | 10 |
| HIGH_CANCEL_RISK | 2 | — | 2 |
| **TỔNG** | **110** | **1,156tr** | **48 (44%)** |

**Mỏ reactivation chất lượng (SILVER/GOLD/VIP):** 71 khách, 1,185.7tr LTV — **61 đang At-Risk/Churned = 992tr**. Giải lớn nhất: **4 VIP đã churn = 253tr**; SILVER 35 churned = 347tr. Đây là nhóm high-touch ĐÁNG gọi tay (khác bronze).

**Ràng buộc xuyên suốt = CONTACTABILITY (chỉ 44% queue có phone).** SECOND_ORDER tệ nhất (18%). Toàn bộ cỗ máy CSKH bị bóp còn <½. → **Thu phone/Zalo OA tại điểm bán là hạ tầng mở khóa lớn nhất** (plan đã có `is_contactable` trong backlog — data xác nhận nó là bottleneck #1, không phải nice-to-have).

**Corrections cho plan (data cũ sai):**
- OVERDUE LTV "3,549tr" → **đúng 579.9tr** (lỗi data plan cũ).
- FULL_PRICE "2 khách" → **11** (nhưng toàn bronze/churn, kết luận "không có cohort premium" vẫn đúng).
- REORDER_NUDGE 62→21 (−66%), CALL_NOW 9→3, HIGH_CANCEL_RISK 11→2 — kiểm tra lại logic generate queue (drop bất thường).

---

## Hệ quả cho customer domain / playbooks / blueprints

1. **Customer domain doc — thêm trục PROFITABILITY:**
   - `value_group` hiện thuần LTV (revenue). Cần khái niệm **value điều chỉnh-margin**: BRONZE net-âm, VIP/GOLD FL collapse sau overhead. Thêm metric customer-level contribution margin.
   - CLV (metric #2) = `SUM(order_total)` = gross. **Ghi rõ CLV ≠ profit** — khách LTV cao vẫn có thể contribution âm (Shopee/promo).
   - discount_sensitivity guidance ("dồn budget PROMO_MIXED — ROI cao nhất") **moot**: PROMO_MIXED chỉ 1 khách. Cập nhật.

2. **mart_customer_action_queue (playbook+blueprint):** thêm cột **contribution/margin flag** (đừng win-back bronze lỗ) + **alt-channel** (email/Zalo OA cho khách no-phone). Surface `is_contactable`.

3. **NEW dashboard chưa có — giá trị cao nhất: Channel-Profitability × Retention.** Ghép `fact_order_economics` channel margin với retention theo kênh: Shopee vừa giữ chân kém (1.47 đơn/đời) VỪA lỗ → 2 lý do để migrate sang owned. Không playbook nào hiện nối 2 mặt này.

4. Retention waterfall bug (survivorship, thổi ACTIVE ~9×) **vẫn chưa fix** — giữ nguyên ưu tiên trong backlog §3.3.

---

## Unresolved questions
1. Overhead allocation key? — quyết định VIP/GOLD có thực sự lỗ hay artifact. Chặn kết luận margin theo tier.
2. REORDER_NUDGE drop 66% — đổi logic queue hay recency shift thật?
3. Có kênh email/Zalo OA bù cho 56% khách no-phone không? (SECOND_ORDER chỉ 18% contactable.)
4. `is_delivered=false` nghĩa gì (mất/từ chối/hoàn)? — chặn bởi shipment_status toàn NULL.
