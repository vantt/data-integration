# Playbook: Product Profitability [All]

## Overview

- **Audience:** Finance, Merchandising, CEO
- **Goal:** Ranking sản phẩm theo lãi gộp và margin — xác định top performers và sản phẩm kéo margin xuống. Phân tích cross-channel để quyết định product mix.
- **Collection:** `Finance`
- **Cadence:** Rolling 30 days (default), custom filter
- **Archetype:** Product Margin Ranker
- **Blueprint:** [blueprints/product_profitability.md](../blueprints/product_profitability.md)

## Key Questions

- Sản phẩm nào đóng góp lãi gộp tuyệt đối lớn nhất?
- Sản phẩm nào có margin % cao nhất / thấp nhất (min 3 giao dịch)?
- Margin trung bình toàn danh mục kỳ này là bao nhiêu?
- Sản phẩm nào margin < 25% đang chiếm tỷ trọng doanh thu lớn?
- Cùng một sản phẩm, margin theo kênh có chênh lệch đáng kể không?

## Reading Flow

1. **KPI bar** — Số sản phẩm có COGS data, avg margin %, sản phẩm margin cao/thấp nhất.
2. **Top 20 by Profit** — Sản phẩm nào đang tạo ra lãi gộp lớn nhất về giá trị tuyệt đối?
3. **Bottom 20 by Margin %** — Sản phẩm nào margin thấp nhất? Có đáng lo không (volume lớn)?
4. **Product Detail Table** — Drill-down theo sản phẩm × kênh: doanh thu, giá vốn, lãi gộp, margin %. Highlight đỏ < 25%, xanh ≥ 50%.

## Data Lineage

- **Primary:** `int_misa_sales_lines` — per-invoice-line với gross_profit, cogs_amount, revenue_net_of_discount theo product_name × channel_name
- **Scope:** `NOT is_promo_line AND revenue_net_of_discount > 0`; margin queries thêm `has_cogs = true`
- **Caveat:** SKU-level COGS only (MISA data) — sản phẩm chưa có trong MISA không xuất hiện trong ranking
