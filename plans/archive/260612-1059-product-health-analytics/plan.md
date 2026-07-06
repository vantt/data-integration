---
title: "Product Health Analytics — domain enrich + health classification + board set"
created: 2026-06-12
status: done
# (updated 2026-06-24: confirmed done — all P0-P5 completed; boards #107-#110 live in Merchandising & Product; old boards #30/#36/#76/#94 retired; Metabase field filter Binder Errors on boards 107-110 fixed by audit commit a925c74)
approach: pipeline-first → boards → consolidate, with user validation gate before retire
refs:
  - ./pipeline-design.md
  - ../reports/customer-dashboard-portfolio-ia-evaluation-260612-0818-report.md  # IA precedent
---

# Product Health Analytics

> **Mục tiêu:** hiểu "product health" như customer health — phân loại SP khỏe/yếu + việc cần làm.
> **Trạng thái nền:** domain product ĐÃ có (3 context, 12 metric); 4 board product LIVE rải rác 3 collection (Analytics/Finance×2/Logistics) + overlap (#36 vs #76).
> **Cách làm:** pipeline (data layer) trước → boards → validate → mới retire/dọn. Mirror customer.

## Quyết định đã chốt (user 2026-06-12)
1. ✅ Build **product health classification** (STAR/WORKHORSE/QUESTION/DOG + lifecycle).
2. ✅ Làm **cả bộ** board (Overview + Performance + Profitability + Inventory).
3. ⚠️ Sub-collection **Product** — user đề xuất "dưới Marketing?" → **tôi phản biện** (xem §Collection).
4. ✅ Gộp/dọn overlap **#36 Product Profitability vs #76 Cost-to-Margin** (cả 2 Finance).
- Phải có plan (file này) trước khi build.

## Pipeline (chi tiết → [pipeline-design.md](./pipeline-design.md))
DRY: inventory health + velocity/margin/returns ĐÃ tính sẵn. Build lớp synthesis còn thiếu:
- `int_product_velocity_trend` (momentum, lifecycle) + `int_product_discount_dependency`
- **`mart_product_health`** (1 row/product, current — analog dim_customers): abc_class, health_class, lifecycle, oos_risk, has_margin_data
- `mart_product_action_queue` (RESTOCK/CLEAR/REVIEW_MARGIN/PROMOTE/DELIST — analog customer queue)
- ⚠️ margin health chỉ ~42/685 SKU (COGS coverage) — flag has_margin_data.

## Board set (target — Merchandising/Product owned)
| Board | Job | Nguồn |
|---|---|---|
| **Product Health Overview** (MỚI) | SP nào khỏe/yếu/cần xử lý — health class × velocity × margin × stock × action | mart_product_health + action_queue |
| **Product Performance** | velocity/revenue/trend | #30 (rework) |
| **Product Profitability** | margin ranking, cogs variance | #36 + #76 gộp |
| **Product Inventory Health** | OOS/dead-stock/days-of-supply | #94 (rework) |

## Collection (đề xuất — cần user chốt)
**KHÔNG nên dưới Marketing** (audience Merchandising/Inventory/Finance ≠ Marketing → vi phạm audience-org). Đề xuất:
- **(a) [KHUYẾN NGHỊ] New top-level `Product`** (hoặc `Merchandising & Product`) — như Finance được tách top-level khi domain explode. Product giờ có audience riêng + 4-5 board.
- (b) Dưới Analytics (nơi #30 đang ở) — nhưng Analytics = research cross-segment, không operational.
- (c) Dưới Marketing — yếu nhất (sai audience).

## Phases
| Phase | Việc | Trạng thái |
|---|---|---|
| **P0** | Plan + pipeline-design + cleanup-inventory | 🔵 plan+pipeline done; cleanup ⬜ |
| **P1** | Domain doc: context "Product Health Classification" (metric 13-18 + action queue) | ✅ done |
| **P2** | Pipeline: int×2 + mart_product_health + action_queue → Dagster RUN_SUCCESS, tests PASS | ✅ done; **spine broadened** (latest_econ ∪ inventory per-product-latest on_hand>0) → 119 SP, 86 dead-stock, CLEAR_DEADSTOCK fire (more-insight win) |
| **P3** | Collection `Merchandising & Product` (top-level, id 100) + 4 board MỚI | ✅ #107 Overview · #109 Performance&Velocity · #108 Profitability&Cost (gộp #36+#76) · #110 Inventory&Stock; index set |
| **P4** | Validate (user kiểm tra 4 board) | ✅ done (user approved 2026-06-23) |
| **P5** | Retire board cũ (#30/#36/#76/#94) + registry/files | ✅ done (archived 2026-06-23; registry.yml đã có comment) |

## Decisions chốt (2026-06-12)
1. **Collection: top-level `Merchandising & Product`** (không dưới Marketing — sai audience).
2. **Scoring: NTILE toàn tệp** cho health_class (by-category degenerate ở 42 SKU); category = filter; ABC class cho "top trong nhóm". Revisit by-category khi COGS phủ rộng.
3. **Window: classification = rolling 90d** (30d nhiễu cho supplement); **momentum = 30d vs 90d-avg**; freshness/days_of_supply = point-in-time.
4. **Action queue: build ngay P2** (`mart_product_action_queue`).
5. **#36+#76: gộp → 1 "Product Profitability" trong Merchandising & Product** ngay. **Deferred:** Finance có thể có board cost-accounting riêng sau (overlap nhẹ OK — khác audience).
