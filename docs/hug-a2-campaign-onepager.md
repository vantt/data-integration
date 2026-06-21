# Hug A2 — One-pager (Mở khóa khách mua-lặp ẩn danh)

> Bản **tập trung 1 trang** cho chiến dịch A2 — mũi nhọn của Hug. Chi tiết kỹ thuật/kế hoạch ở **§ Nguồn chi tiết** cuối trang.
> Cập nhật 2026-06-21. Số liệu từ dữ liệu sống (`mart_customer_tier`).

---

## 1. A2 là gì
Chiến dịch **bắt liên hệ ~418 khách "mua-lặp ẩn danh" (MASKED_REPEAT)** bằng **tem QR trong kiện + ưu đãi**, biến họ từ "vô hình" (chỉ mua qua sàn) → **khách liên hệ trực tiếp** để remarketing suốt đời.

## 2. Vì sao đáng làm
Nhóm này mua lặp, giá trị cao (avg **6,8 đơn**, AOV cao, ~**2,95 tỷ CM** lifetime) nhưng **không có SĐT/Zalo** → không bán lại được. Mỗi lần "bắt" = **tài sản liên hệ vĩnh viễn**, không chỉ 1 đơn.

## 3. Nhắm ai
Điều kiện: **`op_type = package_insert` × `tier = MASKED_REPEAT`**. Chia 3 vùng:

| Vùng | Recency | Số khách | A2 đánh thế nào |
|---|---|---|---|
| Active | ≤90d | **69** | ✅ **A2 (tem trong kiện)** — bắt ngay đơn kế tiếp |
| Dormant | 91–720d | **283** | Cần **Shopee broadcast** đánh thức trước |
| Lost | >720d | **81** | Bỏ (ngoài tầm công cụ) |

*Loại ~15 tài khoản B2B/export bị phân loại nhầm + khách AOV<1M (lợi nhuận mỏng).*

## 4. Cách chạy — luồng "Chị Lan" (B0→B4)
```
B0  Tạo mã HUG50 trong Sapo (giảm 50K · đơn ≥300K · 1 lần/khách)
B1  Kho đóng đơn masked → DÁN TEM QR → "gắn" tem vào đơn (1 lần quét)
B2  Khách nhận → QUÉT QR → "Follow Zalo + để SĐT → nhận 50K" → nhập số
       → HIỆN HUG50 → ✅ có liên hệ (THOÁT MASK)
B3  Khách đặt đơn mới nhập HUG50 → Sapo giảm 50K
B4  Đơn về → khớp (khách + mã) → đánh dấu đã dùng → ĐO ROI
```

## 5. Cấu hình (tạo bằng UI `/hug/campaigns`)
`targeting={op_type:[package_insert], tier:[MASKED_REPEAT]}` · `destination=Zalo OA` · `offer_ref=HUG50` · `priority=10` · `status=active`.

## 6. Kinh tế (đã hiệu chỉnh theo dữ liệu)
- **50K = token để khách chịu opt-in**, KHÔNG phải đòn bẩy (AOV cao → 50K quá nhỏ).
- Offer **bậc thang**: loại 15 B2B + khách AOV<1M; chỉ áp **AOV ≥1M**.
- **Bắt buộc holdout** đo incrementality (tránh tặng cho người dù sao cũng mua).

## 7. Đo lường
Phễu: **phủ tem → quét → opt-in (tỷ-lệ-thoát-mask) → mua lại → redeem** — đối chiếu **holdout**. Màn ROI: **`/hug/vouchers`**.

## 8. Trạng thái & Go-live
- **Code DONE + live:** mint/in tem · trạm gắn tem · trang opt-in · bắt định danh · sổ voucher · campaign UI · ROI screen · vòng issue→redeem trong `/admin/refresh`.
- **Chờ go-live (~30–45'):** tạo HUG50 · set Zalo OA · `wrangler deploy` · tạo campaign A2 · brief kho.
- **Khuyến nghị:** chạy **PILOT có holdout** (Vùng 1 trước) rồi scale theo số liệu.

## 9. Rủi ro chính
76% masked-repeat **ngủ đông** → A2-tem chỉ ăn ~69 active; phần lớn cần **Shopee Chat Broadcast** (đã validate; cần xác nhận portal VN). 50K có thể quá nhỏ. Mẫu nhỏ → holdout chỉ định hướng.

## 10. Quyết định còn chờ chốt
Offer (50K vs %/quà bậc) · xác nhận Shopee broadcast VN · kho phân biệt tem theo khách (cho control) · bật holdout · *(rộng hơn Hug)* sửa lỗi dữ liệu export/zero-revenue ~23,7 tỷ.

## 11. Pilot — đo trước khi scale (~2–4 tuần)
| Arm | Tệp | Treat/Control | Đo gì | Đọc |
|---|---|---|---|---|
| **A — Hug tem** | Vùng 1 active (AOV≥1M, loại B2B) | ~40 / ~22 | opt-in + mua-lại | 60–90 ngày |
| **B — Shopee broadcast** | Vùng 2 dormant ≤720d | ~130 / ~70 | reactivation **R** (định hướng) | 120–180 ngày |

- Mỗi arm **1 mã riêng**; loại tài khoản zero-net-revenue khỏi mọi phép tính.
- **Cổng quyết định:** opt-in / redeem / R đạt ngưỡng → scale; không đạt → chỉnh offer/landing hoặc dừng.
- Bản chất: chi tiền nhỏ để **học con số thật** (opt-in, redeem, R) thay vì đoán.

---

> 📎 *Tài liệu kỹ thuật/backing (TÙY CHỌN — one-pager này đã đủ để nắm + hành động, không cần mở):*
> chiến lược tổng `hug-campaign-overview-for-leadership.md` · go-live runbook & code `plans/260620-1408-crm-hug-voucher-a2-golive/` · campaign UI `plans/260620-1148-crm-hug-campaign-admin-ui/` · pilot đầy đủ `plans/260620-2357-hug-a2-pilot-holdout/` · nghiên cứu nền `plans/reports/`.
</content>
