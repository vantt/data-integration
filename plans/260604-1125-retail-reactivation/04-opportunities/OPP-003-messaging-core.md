---
title: "OPP-003 - Messaging Core"
stage: 4
status: idea
blocker: "pending product-knowledge + VOC"
source: "session ultrathink 2026-06-10 (retail focus)"
lens: L1/L2/L4/L6
---

# OPP-003 - Messaging Core

**Registry:** [OPP-003](../REGISTRY.md#opp-003)

> Telesales, ads, listing sàn, bao bì, Zalo broadcast = **CÙNG một brand message thể hiện trên nhiều bề mặt**.
> Viết **lõi 1 lần** → mỗi kênh là **adapter mỏng**. KISS + DRY + nhất quán.
> **Copy chọn AI mua → messaging là thượng nguồn của retention**, không phải hạ nguồn của bán hàng.

---

## Lõi (Message Core) — viết 1 lần (CHƯA điền — chờ gate bên dưới)

| Thành phần | Nội dung |
|---|---|
| **Claims / công dụng được phép nói** | *(luật TPCN: KHÔNG claim "chữa bệnh")* |
| **Proof / bằng chứng kết quả** | *(before/after, cert, xuất xứ)* |
| **Set kỳ vọng THẬT** | *(timeline: tuần 1–2 chưa thấy gì là bình thường, rõ tuần 4–6)* ← **đòn bẩy GIỮ CHÂN** (hứa quá lời = churn) |
| **Objection answers** | *(giá · "không thấy hiệu quả" · "TikTok rẻ hơn" · sợ giả · quên/không tiện · đủ dùng)* |
| **Positioning** | result + trust + quan hệ, **KHÔNG đua giá** (L6) |
| **Tone / do-don't** | *(tư vấn, empathy, không over-claim)* |

---

## Adapters (mỗi cái = file riêng sau, thể hiện mỏng từ lõi)

| Adapter | Bề mặt | Priority | Trạng thái |
|---|---|---|---|
| `telesales-cskh-playbook` | gọi / Zalo 1:1 | **cao** | scaffold pending |
| `marketplace-listing` | mô tả sàn (Shopee / TikTok Shop) | **cao** — miễn phí, owner làm ngay, +kéo về Zalo OA (vá rent-not-own) | pending |
| `ad-angles` | góc quảng cáo | **THẤP — gác lại** (leak-first + chưa đo được; chỉ làm *angle*, không scale) | deferred |
| `package-insert` | card / hướng dẫn trong hộp | trung | pending |
| `zalo-broadcast` | tin hàng loạt | trung | pending |

> **Listing là dụng cụ GIỮ CHÂN** (set kỳ vọng + hướng dẫn dùng + QR→Zalo OA), không chỉ chuyển đổi.
> **Ads quay lại** chỉ khi: có offer (results-guarantee) + lõi xong + **đo được** (fix ROAS/`fact_payments`).

---

## Phụ thuộc (GATE — chưa build nội dung)

1. **Product-knowledge** (chưa có) — được phép hứa gì, timeline kết quả thật.
2. **VOC** — [voc-customer-interviews](../02-understand/INV-003-voc-customer-interviews.md) — phản đối thật, lời lẽ khách.

→ Build **lõi** sau 2 đầu vào → rồi **adapter** (listing + telesales trước; ads sau khi đo được).

**Vì sao quan trọng:** nhất quán across bề mặt = trust; mâu thuẫn thông điệp (ad hứa A, listing nói B, CSKH nói C) = phá niềm tin = churn.
