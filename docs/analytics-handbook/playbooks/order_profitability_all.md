# Playbook: Order Profitability [All]

## Overview

- **Audience:** CFO, Finance, Sales Ops
- **Goal:** Phân tích P&L từng đơn hàng — gross margin, lãi ròng kênh, phân bổ chi phí. Bao gồm tất cả kênh (kể cả non-sales). Phát hiện đơn lỗ, đơn bất thường.
- **Tool:** metabase
- **Collection:** `Finance`
- **Cadence:** Custom (date filter driven)
- **Archetype:** Profitability Explorer
- **Blueprint:** [blueprints/order_profitability_all.md](../blueprints/metabase/order_profitability_all.md)

## Key Questions

- Gross margin % tổng kỳ này là bao nhiêu? Có đạt ngưỡng 50%?
- Kênh nào có channel net margin cao nhất/thấp nhất?
- Cơ cấu chi phí theo kênh: lãi gộp vs giá vốn vs phí sàn ra sao?
- Đơn hàng nào lỗ (gross margin < 0)? Nguyên nhân?
- Xu hướng lãi gộp theo ngày trong kỳ có biến động bất thường không?

## Reading Flow

1. **Gross Margin % gauge** — Kỳ này biên lợi nhuận gộp trung bình có đạt target?
2. **KPI bar** — Tổng lãi gộp, lãi ròng kênh, số đơn có COGS (coverage).
3. **Channel Net Margin %** — Ranking kênh theo margin. Kênh nào đang ăn mòn lợi nhuận?
4. **Cost Structure by Channel** — Tỷ trọng giá vốn và phí sàn theo từng kênh.
5. **Margin Distribution** — Phân bổ đơn theo vùng margin (lỗ / thấp / cao).
6. **Profit by Date** — Xu hướng lãi gộp theo ngày.
7. **Order P&L Table** — Drill-down từng đơn, sort theo lãi/lỗ, click mã đơn xem chi tiết.

## Data Lineage

- **Primary:** `fact_order_economics` — P&L per order với gross_profit, cogs_amount, channel_net_profit, gross_margin_pct
- **Joins:** `dim_channels` (channel_name), `dim_date` (date_actual)
- **Scope:** `status = 'COMPLETED' AND has_cogs` (~65% coverage); revenue queries drop `has_cogs` filter
- **Caveat:** COGS coverage ~65% — orders without MISA match excluded from margin metrics
