---
title: "Action Flows — Luồng hành động, lịch vận hành"
stage: 5
status: committed
source: "../archive/2026-06-04-original-sales-slowdown-playbook.md — §5"
---

# Action Flows — Luồng hành động, lịch vận hành

> Trích nguyên văn §5 từ [`../archive/2026-06-04-original-sales-slowdown-playbook.md`](../archive/2026-06-04-original-sales-slowdown-playbook.md).
> Perspectives bổ sung: xem [`../01-perspectives/`](../01-perspectives/).

---

## 5. Kế hoạch hành động: làm khách liên hệ được mua lại

> Tệp đích: **1.082 khách lẻ có SĐT đã từng mua** (lưu ý 76% là người nhận quà US — xem [`us-gift-recipients.md`](./us-gift-recipients.md)
> để tách luồng). Số liệu thật 2026-06-04.

### 5.1 Năm nguyên tắc bất biến

1. **Timing theo chu kỳ cá nhân, không blast đồng loạt.** Dùng `predicted_next_purchase_date` /
   `avg_days_between_orders` → nhắc khi họ sắp hết hàng.
2. **Mức chạm theo giá trị.** VIP/Gold → gọi điện người thật. Silver → Zalo cá nhân. Bronze/nguội → blast.
3. **Offer theo độ nhạy giảm giá** (`discount_sensitivity`). FULL_PRICE/ON_TRACK → đừng tặng voucher
   (họ mua đủ giá), tặng quà/sample/ưu tiên. Chỉ dùng voucher cho win-back/nhạy KM.
4. **Luôn hỏi "vì sao ngừng".** Mỗi cuộc win-back ghi lý do → xây bản đồ nguyên nhân bỏ để chữa gốc.
5. **Mở bằng product experience, không phải voucher.** Câu hỏi đầu tiên luôn là "lần trước dùng
   có thấy gì không?" — nếu không thấy hiệu quả, voucher không cứu được; nếu thấy, không cần voucher
   mạnh. Biết trả lời này trước → chọn offer đúng hơn và ghi nhận dữ liệu chất lượng sản phẩm.

### 5.2 Năm luồng hành động

**Luồng 1 — CALL_NOW: VIP/Gold đang At-Risk** · *6 khách · ~56tr* · **Owner: Sales lead**
- Trigger: `value_group∈(VIP,GOLD)` & `customer_status='At Risk'`. Gọi điện trong 48h.
- Script: hỏi thăm cá nhân → "bên em vừa về lô [brand] mới / có ưu đãi cho khách thân thiết" →
  chốt đơn hoặc hẹn lại. KHÔNG mở đầu bằng giảm giá.
- KPI: 100% được gọi trong tuần; ≥40% đặt lại/hẹn.

**Luồng 2 — WIN_BACK: khách giá trị đã churned** · *35 khách · ~911tr* · **Owner: CSKH + Sales lead**
- Trigger: `value_group∈(VIP,GOLD,SILVER)` & churned. Gọi/Zalo cá nhân, kèm micro-survey "vì sao ngừng".
- **Script Zalo (product-experience first):**
  *"Chào anh/chị [tên], lần trước dùng [Fine Japan / FG Care] anh/chị có thấy gì không ạ?
  Bên em hỏi vì nhiều khách thấy rõ nhất từ tuần 4–6, muốn xem mình có dùng đúng cách chưa."*
  → Nếu **thấy hiệu quả**: *"Vậy thì tiếc quá — em gửi ưu đãi quay lại [X%] cho [SKU] tới hết [ngày] nhé."*
  → Nếu **không thấy gì**: tư vấn cách dùng đúng (liều, thời điểm) → offer thử lại với cam kết rõ hơn.
  → Nếu **lý do khác** (giá, tìm chỗ khác, hết nhu cầu): ghi lại, không ép.
- Offer: voucher comeback có thời hạn (7–10 ngày) + freeship; ưu tiên SKU theo `product_affinity`.
- KPI: ≥50% tiếp cận có phản hồi; ≥15% mua lại trong 30 ngày; thu ≥20 lý-do-bỏ + **ghi "có thấy hiệu quả"**.

**Luồng 3 — REORDER_NUDGE: OVERDUE** · *31 khách action-queue (166 toàn tệp) · ~344tr* · **Owner: CSKH**
- Trigger: `next_purchase_signal='OVERDUE'`. Nhắc theo chu kỳ cá nhân.
- Script: *"Anh/chị [tên] ơi, [sản phẩm] mình hay dùng chắc sắp hết rồi. Em giữ hàng + giao nhanh
  giúp mình nhé?"* (nhắc tiện lợi, không cần giảm giá).
- KPI: M1 reorder ≥25%.

**Luồng 4 — SECOND_ORDER: one-timer mới** · *16 nóng (15–45 ngày) + 25 (46–90) · ~2tr* · **Owner: CSKH**
- Trigger: `total_orders_count=1` & recency 15–45 ngày. Cú hích chuyển 1-lần → 2-lần.
- **Lưu ý product journey:** Đây là nhóm đang ở tuần 2–6 — đúng giai đoạn Danger Zone (chưa thấy gì)
  hoặc bắt đầu thấy. Touchpoint này quan trọng hơn về giáo dục sản phẩm, không chỉ về discount.
- Script: *"Anh/chị dùng [sản phẩm] được [X tuần] rồi, cơ thể đang hấp thụ và thay đổi từ bên trong.
  Nhiều khách thấy rõ nhất từ tuần 4–6 nếu dùng đều. Em hỏi thăm anh/chị có dùng đúng cách chưa?"*
  → Kèm hướng dẫn dùng đúng + ưu đãi đơn #2 nhỏ.
- KPI: tỷ lệ one-timer→repeat tăng; ghi nhận "dùng đúng cách" Y/N. Pool nhỏ vì acquisition chủ yếu
  Shopee không liên hệ được → ưu tiên song song nước đi "bắt liên hệ Shopee" để nuôi pool này.

> **Luồng này sẽ được thay phần lớn bởi 3-touchpoint sequence (mục 5.7) khi đã triển khai —**
> sequence chạy tự động cho khách mới, Luồng 4 chỉ là backup cho khách lọt qua.

**Luồng 5 — BULK win-back nguội** · *~700+ one-timer/churned cũ* · **Owner: Marketing**
- Kênh: Zalo OA broadcast/SMS, theo đợt. Low-touch, chi phí thấp.
- Nội dung: chiến dịch theo mùa/brand (Fine Japan) + voucher comeback, phân nhóm theo `product_affinity`.
- KPI: response ≥3–5%; đo doanh thu/đợt.

### 5.3 Lịch vận hành tuần

| Thứ | Việc | Ai |
|---|---|---|
| T2 | Mở worklist tuần trên [dashboard 103 — Daily · Customer Action Queue](https://bi.lan.fwg.vn/dashboard/103), lọc Luồng 1–4 + có SĐT (không export — đọc trực tiếp) | CSKH |
| T2–T4 | Gọi Luồng 1 (CALL_NOW) + Luồng 2 (WIN_BACK cao giá trị) | Sales lead |
| T3–T6 | Zalo Luồng 2 (còn lại) + Luồng 3 (REORDER) + Luồng 4 (SECOND_ORDER) | CSKH |
| T5 | 1 đợt Bulk (Luồng 5) theo brand/mùa | Marketing |
| T7 | Cập nhật kết quả (đặt lại / lý do bỏ) vào Sheet → review | CSKH lead |

### 5.4 Offer matrix

| | ON_TRACK / Active | At-Risk | Churned/nguội |
|---|---|---|---|
| **VIP/Gold** | Quà tặng, ưu tiên hàng mới | Gọi tay + quà | Gọi + voucher comeback mạnh |
| **Silver** | Sample kèm đơn | Zalo + ưu đãi nhẹ | Voucher comeback |
| **Bronze/one-timer** | Nhắc tiện lợi | Ưu đãi đơn #2 | Bulk voucher (Luồng 5) |

### 5.5 Đo lường (bắt buộc có nhóm chứng)

- **Holdout 10–20%** mỗi luồng (không tác động) để đo incremental — tránh nhận công cho đơn tự đến.
- KPI tổng: M1 reorder tệp owned **3–17% → ≥25%** (2 quý); reactivation rate win-back ≥15%/30 ngày;
  doanh thu reactivation/tháng; số lý-do-bỏ thu được.

### 5.6 Tuần 1 — checklist khởi động (0-build)

- [ ] Export ~120 khách high-touch (Luồng 1–4, có SĐT) ra Sheet (cảnh báo: chứa PII — không commit vào git).
- [ ] Soạn 4 script Zalo mẫu + 3 mức voucher (offer matrix).
- [ ] Sales lead gọi 6 CALL_NOW + 10 WIN_BACK giá trị nhất (T2–T4).
- [ ] CSKH Zalo 31 REORDER + 16 SECOND_ORDER nóng.
- [ ] Ghi outcome + lý-do-bỏ vào Sheet; review T7.

### 5.7 3-Touchpoint Onboarding Sequence (khách mới — ưu tiên cao nhất)

> **Đây là action có đòn bẩy cao nhất** — fix tỷ lệ M1 repeat trên khách mới mà không cần data engineering.
> Cần thiết kế xong và chạy tay trong tuần này; automation vào P4.

| Điểm chạm | Thời điểm | Nội dung | Kênh | Mục tiêu |
|---|---|---|---|---|
| **Touch 1** | Day 3 sau mua | Xác nhận nhận hàng + cách dùng đúng (liều, thời điểm, uống với gì) | Zalo/SMS | Đảm bảo dùng đúng từ đầu |
| **Touch 2** | Day 21 | "3 tuần rồi — đây là giai đoạn cơ thể đang thay đổi từ bên trong. Anh/chị thấy gì chưa?" + tip tiếp tục | Zalo | Giữ họ qua Danger Zone; thu feedback |
| **Touch 3** | Day 45 | "Sắp hết rồi — 6 tuần liên tục là lúc kết quả rõ nhất, đừng để đứt quãng" + link reorder dễ | Zalo | Convert sang đơn #2 đúng lúc hết hàng |

**Nội dung Touch 1 mẫu:**
> *"Chào anh/chị [tên], [Fine Japan / tên sản phẩm] đã đến chưa ạ? Để thấy kết quả tốt nhất:
> uống [X viên/gói] mỗi sáng sau bữa ăn, dùng đều ít nhất 4–6 tuần. Tuần đầu chưa thấy gì là bình thường —
> cơ thể đang hấp thụ từ bên trong. Có gì cần hỗ trợ anh/chị nhắn em nha!"*

**Nội dung Touch 3 mẫu:**
> *"Anh/chị [tên] ơi, [Fine Japan] dùng đã gần 6 tuần rồi — đây là lúc nhiều khách thấy rõ nhất.
> Để không bị đứt quãng, em giữ hàng cho anh/chị nhé? [Link đặt lại — freeship đơn này]"*

**Tracking:** ghi vào Sheet: delivery confirmed (Day 3), feedback at Day 21 (thấy gì?), ordered again Y/N at Day 45.

**Owner:** CSKH. Automation vào P4 (Dagster job + Zalo OA API).

---

> **KPI & đo lường** → [06-execute/kpi](../06-execute/kpi.md).
