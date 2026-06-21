---
title: "FIND-008 - Dead-stock → Customer Targeting + Match Granularity"
stage: 2
status: resolved
role: finding
source: "../../reports/data-probe-deadstock-customer-targeting-granularity-260620-1242-report.md (DuckDB read-only probe, marts rolling snapshot) — 2026-06-20"
created: 2026-06-20
updated: 2026-06-20
---

# FIND-008 - Dead-stock → Customer Targeting + Match Granularity

**Registry:** [FIND-008](../REGISTRY.md#find-008)

> Probe trả lời "thoát bán ế": nên ghép SKU ế ↔ khách ở granularity nào (SKU / category / brand) và quy mô cơ hội thực.
> Số liệu chi tiết: [report nguồn](../../reports/data-probe-deadstock-customer-targeting-granularity-260620-1242-report.md).

---

## TL;DR

**Chỉ SKU-level past-purchase (tái mua) có precision.** Category = blast/spam, brand = hỏng, affinity-column = quá thưa. Quy mô vốn-ế-bán-được hiện nhỏ (5.5M dead thật → ~40–77M nếu gộp slow-mover), nhưng cây cầu product→customer đang THIẾU hẳn.

---

## 1. Khung 3 trục — thiếu cây cầu product→customer

"Thoát bán ế" là bài toán phía **CUNG** (trạng thái tồn kho), nhưng plan resell/activation hiện thuần phía **CẦU** (trạng thái khách). Thiếu mắt xích nối SKU ế → khách.

- **Tier** (`mart_customer_tier`) = STATE biến đổi → "đáng chạm không".
- **Cohort** (entry DNA, `mart_cohort_retention`) = MEMBERSHIP bất biến → analytical, không actionable per-khách.
- **Demand-match** (product × customer) = quan hệ khách×SP = **LÕI thoát bán ế → chưa có**.

`mart_product_action_queue.CLEAR_DEADSTOCK` đã tính sẵn trigger phía cung NHƯNG (a) ~70% noise, (b) chưa bao giờ join sang khách.

## 2. Tập "ế" thật — nhỏ + nhiễu

| Nhóm | SKU | Vốn kẹt |
|---|---:|---:|
| `CLEAR_DEADSTOCK` thô | 17 | 42.1M |
| − noise Vận Hành/Uncategorized (UMBRELLA, demo VFJDEMOH001, mã VB23/VB24) | −12 | −36.6M |
| **= Dead-stock bán-được thật** | **5** | **5.5M** |

Mở rộng slow-mover (`mart_product_health` DOG/QUESTION): sellable slow = **6 SKU / ~79M**, nhưng thực sự kẹt vốn đáng campaign ≈ **2 SKU (~40–77M)** — số còn lại vẫn đang bán chạy.

## 3. Affinity coverage — brand-match vô dụng

| Cột | Coverage | Phán |
|---|---|---|
| `top_affinity_sku` | 68% | actionable nhưng thưa |
| `product_affinity` (brand) | 79% | **chỉ 2 giá trị** (FINE_JAPAN / MULTI) → brand-match VÔ DỤNG |

## 4. Test granularity — pool reachable 1,782

Pool = LIVE_CORE 56 + SECOND_ORDER 27 + DORMANT_VALUABLE 122 + LAPSED_VALUABLE 1,144 + MASKED_REPEAT 433 = **1,782**.

| Mức ghép | Audience | Phán |
|---|---:|---|
| **SKU — past-buyer** (`fact_sales`) | **8** (per-SKU 3/3/2/0/0) | Chính xác, gần rỗng |
| packsize-root past-buyer | 0 | Không data |
| brand (`product_affinity`) | 0 | Hỏng (taxonomy 2-giá-trị) |
| SKU-affinity (`top_affinity_sku`) | 4 | Gần rỗng |
| category (Medicine+DS) | 1,233–1,677 (~70–94%) | = cả base = blast, không phân biệt |

2/5 SKU dead có **0 người từng mua** → failed-launch → quyết định **merchandising** (bundle/markdown/delist), KHÔNG phải nhắm khách.

## 5. Phán quyết granularity (data-backed)

- Chỉ **SKU-level past-purchase** có precision. Category = spam (dead-cat ≈ toàn catalog FineJapan); brand = hỏng; affinity-col = quá thưa.
- **Tier × demand-match = segmentation** — KHÔNG cần đẻ cohort khách mới (state-cohort trên base nhỏ = YAGNI).
- Match key đề xuất = SKU past-purchase (`fact_sales.product_key`) + replenishment-due (`next_purchase_signal`, `predicted_next_purchase_date`) + discount-sensitivity gate. KHÔNG dùng category/brand/affinity-col làm match chính.

## Hệ Quả Cho Path

| Stage | Ảnh hưởng |
|---|---|
| 04-opportunities | spawn [OPP-005](../04-opportunities/OPP-005-deadstock-customer-targeting-engine.md) — engine ghép SKU ế → khách |
| 06-execute | cần dọn noise `mart_product_action_queue.CLEAR_DEADSTOCK` (loại Vận Hành/Uncategorized) trước khi engine "đáng tin" |

## Unresolved Questions

1. `mart_product_health` chỉ track ~104 SKU — toàn bộ catalog active hay đang lọc mất phần ế khác? Cần xác minh phủ.
2. Shopee seller messaging API / campaign-list export có sẵn để chạm 433 masked-repeat in-channel không?
3. Ngưỡng kích hoạt cụ thể (vốn-kẹt-bán-được ≥ ? / SKU có ≥ ? past-buyer) để engine "đáng chạy" — chờ user chốt con số.
4. `product_affinity` 2-giá-trị: có kế hoạch làm brand taxonomy thật không (ảnh hưởng brand-match tương lai)?
