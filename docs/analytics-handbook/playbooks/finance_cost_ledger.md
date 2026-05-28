# Playbook: Cost Ledger Analyzer [All]

## Overview

- **Audience:** CFO, Accounting Manager
- **Goal:** Trả lời "Tiền của tôi đi đâu?" — phân tích cơ cấu chi phí (COGS, phí sàn, thuế, vận chuyển, chiết khấu) theo kênh bán hàng và theo thời gian.
- **Metabase Collection:** `Finance`
- **Blueprint:** [finance_cost_ledger.md](../blueprints/finance_cost_ledger.md)
- **Scope:** All sales channels (`is_sales_channel = true`, loại trừ `status IN ('CANCELLED','Voided')`)

## Filters

- **Date Range:** Default = Tháng này (thismonth). Có thể đổi sang tháng trước hoặc custom range.
- **Dimensions:** Không có filter kênh (dashboard hiển thị tất cả kênh để so sánh)

## Visualizations

### Section 1: KPI Row — Tổng quan chi phí tháng này

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Total Costs MTD** | Scalar | [Total Costs](../domains/finance.md#1-total-costs-tổng-chi-phí) | VND, compact. Hiển thị tổng tất cả loại chi phí |
| **COGS %** | Scalar | [COGS Ratio — Cost Ledger](../domains/finance.md#2-cogs-ratio--cost-ledger-tỷ-lệ-giá-vốn--tổng-chi-phí) | % COGS / tổng chi phí. Chỉ đơn có dữ liệu MISA |
| **Platform Fees %** | Scalar | [Platform Fees Ratio](../domains/finance.md#3-platform-fees-ratio-tỷ-lệ-phí-sàn--tổng-chi-phí) | % phí sàn Shopee / tổng chi phí. Alert >12% |
| **Voucher Subsidy %** | Scalar | [Voucher / Discount Ratio](../domains/finance.md#4-voucher--discount-ratio-tỷ-lệ-chiết-khấu--tổng-chi-phí) | % chiết khấu / tổng chi phí |

### Section 2: Cost Composition — Cơ cấu và xu hướng

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Cost Composition by Month** | Stacked Bar (12M) | [Cost Composition by Month](../domains/finance.md#5-cost-composition-by-month-cơ-cấu-chi-phí-theo-tháng) | 5 màu cho 5 cost_category; x=tháng, y=VND |
| **Platform Fees Ratio Trend (6M)** | Line Chart | [Platform Fees Ratio](../domains/finance.md#3-platform-fees-ratio-tỷ-lệ-phí-sàn--tổng-chi-phí) | Goal line tại 12%. Alert nếu trending up |

### Section 3: Channel Analysis — Breakdown theo kênh

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Top 20 Channels by Total Cost** | Table | [Top Channels by Total Cost](../domains/finance.md#6-top-channels-by-total-cost-kênh-tốn-nhiều-chi-phí-nhất) | Sort DESC by total cost; conditional red nếu Phi san % >12% |

### Section 4: Distribution — Phân phối chi phí

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Cost Breakdown Donut MTD** | Pie/Donut | [Total Costs](../domains/finance.md#1-total-costs-tổng-chi-phí) | 5 slices = 5 cost_category. CFO nhìn ngay tỷ trọng |
| **Cost by Channel Category** | Horizontal Stacked Bar | [Top Channels by Total Cost](../domains/finance.md#6-top-channels-by-total-cost-kênh-tốn-nhiều-chi-phí-nhất) | Top 10 kênh. Dễ thấy kênh nào "nặng phí sàn" vs "nặng COGS" |

## Business Logic Notes

- **COGS coverage:** Chỉ đơn hàng matched trong MISA (`source_system = 'misa'`). Một số đơn không có COGS row nếu chưa xuất hóa đơn MISA.
- **Platform fees coverage:** Chỉ đơn Shopee (`source_system = 'shopee'`). Các kênh non-Shopee không có `PLATFORM_FEE` rows.
- **Discount coverage:** Tất cả kênh Sapo có `discount_items`. Đơn không có discount sẽ không có `DISCOUNT` rows.
- **date_key format:** Integer YYYYMMDD — cần CAST khi so sánh với date_trunc output.
- **is_sales_channel filter:** Áp dụng trên `fact_orders`, không trực tiếp trên `fact_order_costs`.

## Alert Thresholds (Reference)

| Metric | Healthy | Watch | Alert |
| :--- | :--- | :--- | :--- |
| Platform Fees % | < 8% | 8–12% | > 12% |
| COGS % | 50–70% (normal range) | < 40% hoặc > 80% | Cần điều tra |
| Discount % | < 10% | 10–20% | > 20% (khuyến mãi quá nhiều) |
