---
title: "Decision Log — Nhật ký quyết định"
stage: 3
status: living
source: new
---

# Decision Log — Nhật ký quyết định

> Ghi lại mọi quyết định chiến lược đã chốt. Quyết định mở → xem [open-decisions.md](./open-decisions.md).

| Ngày | Quyết định | Lý do | Dựa trên finding | Ảnh hưởng (stage/plan) |
|---|---|---|---|---|
| 2026-06-09 | Hạ ưu tiên "B2B-first", nghiêng B2C-first + cashflow | Điều tra B2B RESOLVED: cầu B2B 2026 = 2–3× 2025; "sụp" là artifact completed-only + COD lag + 491tr OPEN | [b2b-collapse-root-cause](../02-understand/b2b-collapse-root-cause.md) | sequencing, spawn cashflow-collection-ar |
| 2026-06-09 | "Ế" nhiều khả năng = cash/công nợ, KHÔNG phải mất cầu — nhưng chặn bởi data gap | Điều tra cashflow: 2.7 tỷ AR B2B (84% >90 ngày, 77% vào 2 VIP) nhưng fact_payments rỗng | [cashflow-collection-ar](../02-understand/cashflow-collection-ar.md) | cần hỏi chủ + fix data trước khi action |
| 2026-06-09 | Chốt FOCUS = bán lẻ/B2C (quyết định cá nhân của chủ) | B2B không phải đám cháy (resolved); chủ chọn retail | [b2b-collapse](../02-understand/b2b-collapse-root-cause.md) + cá nhân | toàn path ưu tiên retail; đòn bẩy #1 = VOC phỏng vấn khách |
| 2026-06-10 | Ads GÁC LẠI; mọi thông điệp marketing đi qua "Message Core" → adapter mỗi kênh; ưu tiên listing + telesales > ads | Ads đi ngược chẩn đoán (leak-first §7.1) + chưa đo được (ROAS disabled, fact_payments rỗng); telesales/ads/listing là cùng 1 thông điệp | [messaging-core](../04-opportunities/messaging-core.md) | gom messaging về 1 lõi; ads chờ offer+đo được; build sau product-truth+VOC |
| 2026-06-10 | KHÔNG build pipeline product lớn — data đã đủ; chỉ fix Tier 1 (bug margin 🔴, product_group, return_reason, inventory coverage); Tier 2 hoãn | 4-agent assessment: mart_sku_economics + fact_sales + inventory_health trả lời được hầu hết; retention theo sản phẩm tính được ngay | [product-performance-assessment](../02-understand/product-performance-assessment.md) | mũi nhọn retail = xây quanh Cordyceps + gateway Gaba/Chondroitin; reframe portfolio sức khỏe người lớn tuổi |
| 2026-06-10 | Fix bug margin: COGS ×10 overcount (5 SKU H010, MISA ghi theo Hộp) — seed `misa_qty_multiplier=1` + thêm cột `realized_margin_pct` | H010 KHÔNG bán dưới giá vốn; "lỗ 440M" là artifact hoàn toàn; biên thực +59–83% | [product-performance-assessment](../02-understand/product-performance-assessment.md) | cần materialize qua pipeline (KHÔNG rebuild serving thủ công lúc Metabase đang chạy) — ✅ pipeline đã chạy 2026-06-10 03:xx |
