# Economic Concept Audit — Shopee Pipeline

**Date:** 2026-04-21 | **Scope:** sources → staging → intermediate → marts

---

## 1. Field Lineage Map

| Concept | Source Column | Transform | Business Definition | Risk |
|---------|--------------|-----------|--------------------|----|
| **gross_revenue** | `total_paid_amount + refund_amount` | `stg_shopee_order_revenue` L47–49 | Khi refund=0 thì bằng total_paid_amount | 🔴 CRITICAL |
| **net_settlement** | `total_paid_amount` (alias) | `int_shopee_order_fees` L69 | Shopee payout thực nhận, fees đã embedded | ✓ |
| **service_fee / payment_fee / fixed_fee** | Doanh thu sheet | Cast BIGINT, giữ sign âm | Đã deducted khỏi total_paid_amount | ✓ |
| **infrastructure_fee / voucher_xtra_fee** | Service Fee Details sheet (riêng) | LEFT JOIN vào int | Đã embedded, nhưng 4/90 orders thiếu | ⚠️ |
| **total_platform_fees** | tổng fee từ stg | stg L66–72 | Không include infra + voucher_xtra | 🔴 INCOMPLETE |
| **total_paid_amount** | `Tổng tiền đã thanh toán` | Cast BIGINT | Net payout sau tất cả fee/tax/discount | ✓ Source of truth |

---

## 2. Vấn đề phát hiện

### Issue 1 🔴 — Settlement Margin % luôn ~100% (vô nghĩa)

**Bằng chứng:** `stg_shopee_order_revenue.sql` L47–49:
```sql
gross_revenue = total_paid_amount + refund_amount
net_settlement = total_paid_amount  (int L69)
```
→ Khi refund_amount = 0 (hầu hết đơn): `gross_revenue = net_settlement` → ratio = 100% luôn.

**Root cause:** `total_paid_amount` trong export Shopee là **net payout sau phí**, không phải gross trước phí. Shopee không export "customer invoice total" — con số đó không có trong data.

**Impact:** Metric Settlement Margin % trên dashboard không có ý nghĩa kinh tế.

---

### Issue 2 🔴 — total_platform_fees thiếu 2 loại phí quan trọng

**Bằng chứng:**
- `stg`: `total_platform_fees = service_fee + payment_fee + fixed_fee + affiliate + piship + auto_topup`
- Blueprint dashboard dùng: `service_fee + payment_fee + fixed_fee + infrastructure_fee + voucher_xtra_fee`
- → 2 aggregation khác nhau, không có alias/constant nào để tránh nhầm

**Impact:** Nếu analyst dùng `total_platform_fees`, bỏ qua ~6% chi phí.

---

### Issue 3 🔴 — gross_revenue Shopee vs gross_revenue Sapo là 2 khái niệm khác nhau

**Bằng chứng:**
- Sapo `fact_orders`: `gross_revenue = total_amount + discount_amount` (trước thuế, sau discount của khách)
- Shopee `stg`: `gross_revenue = total_paid_amount + refund_amount` (Shopee net payout)
- Cả hai có thể appear cùng trong `fact_order_economics` nhưng đo khác nhau

**Impact:** Analyst dùng sai concept khi so sánh cross-channel.

---

### Issue 4 ⚠️ — Adjustments chưa rõ có embedded trong total_paid_amount không

**Bằng chứng:** `int_shopee_order_fees` L72–73:
```sql
net_settlement_adjusted = total_paid_amount + total_adjustment_amount
```
Chưa có test để verify adjustments không bị double-count với fee đã embedded.

---

### Issue 5 ⚠️ — 4 orders thiếu trong Service Fee Details sheet

**Bằng chứng:** LEFT JOIN với COALESCE(0) → 4 orders luôn hiển thị infrastructure_fee = 0, dù có thể có phí thực tế.

---

## 3. Điều đúng (không cần thay đổi)

- `net_settlement = total_paid_amount` — đúng per Shopee accounting, có test enforce
- Fees giữ dấu âm — consistent, dễ sum downstream  
- `int_shopee_order_fees` comment rõ: "Fees ALREADY embedded; do NOT recompute" — đúng và documented

---

## 4. Recommendations

**Ngắn hạn (dashboard fix):**
- Đổi tên metric "Settlement Margin %" → "Payout Ratio" hoặc xóa nếu không có gross_before_fees
- Hoặc reconstruct gross trước phí: `net_settlement + ABS(service_fee) + ABS(payment_fee) + ...`

**Trung hạn (model fix):**
- Rename Shopee `gross_revenue` → `shopee_order_payout` để tránh xung đột với Sapo gross_revenue
- Thống nhất fee aggregation: tạo `total_shopee_fees` gồm tất cả 7 loại phí trong `int_shopee_order_fees`
- Clarify `refund_amount` semantics trong stg comment

---

## 5. Câu hỏi mở (cần domain expert xác nhận)

1. `refund_amount` (`Số tiền hoàn lại`) trong Shopee export là gì? Post-payout refund hay embedded? Thường = 0 không?
2. Shopee có export "customer invoice total" (số khách trả trước khi Shopee khấu trừ) không?
3. Adjustments có bao giờ duplicate với fee đã deducted trong total_paid_amount không?
4. 4 orders thiếu trong Service Fee Details là random hay có pattern (e.g. order type cụ thể)?
