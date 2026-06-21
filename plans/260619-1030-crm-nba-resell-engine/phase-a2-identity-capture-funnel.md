# Phase A2 — Identity Capture Funnel (ROI cao nhất)

> Stage A · Status: 🔵 ưu tiên cao nhất · Phụ thuộc: A1 (tier) + **Hug platform** · Context: [`discussion.md`](./discussion.md) §16–17 · research report
> Cơ chế delivery: **[Hug](./phase-hug-dynamic-touchpoint-platform.md)** (A2 là campaign chạy trên Hug).

## Mục tiêu

Chuyển khách **masked → contactable**, nhắm **364 masked-repeat Shopee** trước (intent cao nhất — mua lặp dù ta không liên lạc). Vì Shopee identity **resolves**, capture được SĐT là kế thừa ngay full RFM/value → nhảy thẳng vào engine core. KHÔNG phải CS-action trên màn 360, mà là **funnel vận hành/marketing chạy qua Hug**.

## Business case (số thực)

> **364 khách masked-repeat = 1.54 TỶ VND lifetime value, 683 TRIỆU VND contribution margin** đang khóa sau việc thiếu định danh. Mỗi khách de-anonymize = **~1.88M VND CM** treo. Avg 3.1 đơn/khách.

## Hạ tầng đã có

✅ Zalo OA cơ bản · ✅ Tự đóng gói (in QR động được) → chi phí capture gần 0.

## Funnel (chạy trên Hug)

```
Kiện hàng → thẻ QR Hug (token/đơn) → quét
→ Hug route campaign "opt-in capture" → Zalo OA follow + lộ ưu đãi
→ khách follow/để SĐT → Hug bridge nối customer_id + ghi consent
→ tier nâng masked_repeat → contactable → vào core
→ (sau) re-engage qua Zalo/ZNS
```

## Kinh tế ưu đãi opt-in (từ order-economics report)

- Trần ưu đãi an toàn (median CM/đơn): Shopee 381K → **≤30–50K**; overall 592K → ≤50–100K.
- ⚠️ **12.2% đơn âm margin** → voucher BẮT BUỘC **min-order + loại SKU lỗ** (Hug voucher engine lo).
- **Đề xuất:** **50K off đơn kế, min order 300K, valid 60d, chỉ redeem khi mua lại → self-funding.** Với segment đáng 1.88M CM, 50K acquisition là không đáng kể → ROI cực dương. A/B **50K voucher vs quà** (Hug experimentation).

## Phạm vi

- Định nghĩa campaign "opt-in capture" trong Hug (audience = tier MASKED_REPEAT, ưu tiên Shopee).
- Thiết kế thẻ QR + nội dung ưu đãi (in lúc đóng gói).
- Tracking: capture rate, masked→contactable conversion, theo nguồn — qua Hug smart-tracking.

## Open

- Ưu đãi: 50K voucher vs quà tặng — A/B trên Hug.
- Map SĐT↔customer_id edge cases → xem Hug §Open #4.
- Mục tiêu định lượng: % của 364 chuyển contactable trong N ngày = thành công?
- ZNS bật ngay hay sau khi có tập follower?
