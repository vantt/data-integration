# Playbook: Finance Services Revenue

> **Tài liệu này mô tả mục đích và cách sử dụng dashboard/report từ góc nhìn người dùng nghiệp vụ.**
> Nó giải thích dashboard dành cho ai, dùng để trả lời câu hỏi nào, cần đọc theo luồng nào, dùng những metric nào từ domain documents, và khi thấy tín hiệu bất thường thì ai cần làm gì.
> Playbook không định nghĩa công thức tính metric; mọi logic nghiệp vụ phải được tham chiếu từ `domains/`.

## Overview

- **Audience:** CFO (primary), Finance Manager, CEO (secondary)
- **Goal:** Theo dõi 2.4B VND/năm doanh thu dịch vụ (DV* + CPBH) riêng biệt khỏi doanh thu hàng hóa — đảm bảo CFO nắm cơ cấu doanh thu đầy đủ trong buổi MBR hàng tháng.
- **Metabase Collection:** `Finance`
- **Blueprint:** [blueprints/finance_services_revenue.md](../blueprints/metabase/finance_services_revenue.md)
- **Cadence:** Monthly review (đọc trong 5-7 phút đầu buổi MBR)

## Data Lineage

- **Source:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) WHERE `is_service_line = true`
- **Flag dependency:** `is_service_line = (product_code LIKE 'DV%' OR product_code LIKE 'CPBH%')` — implemented in P0
- **Grain:** Per invoice line (posting_date, product_code, revenue_net_of_discount)
- **No join needed:** Services không có COGS trong MISA → cogs_amount = 0 cho tất cả DV* lines

## Filters

- **Date Range:** MTD (tháng này) + tháng trước + YTD — hardcoded trong SQL, không có dashboard filter
- **No channel filter:** Service lines không có channel attribution rõ ràng trong MISA (thường = CS hoặc KHAC)

## Reading Flow (5-7 phút monthly)

1. **Tab 1 — Tổng Quan (2 phút):** Mở dashboard, đọc hero metric "Doanh thu DV tháng này". MoM% và YoY% có màu không? Nếu đỏ → chuyển Tab 2 ngay.
2. **Tab 1 — Trend (1 phút):** Line chart 12 tháng. Đường đi ngang? tăng? hay sụt 1-2 tháng gần đây?
3. **Tab 1 — Pie (30 giây):** Pie phân bổ theo service code. DVCCNS + DVCCNS1 có chiếm > 90%? Nếu tỷ lệ thay đổi → xem Tab 3.
4. **Tab 2 — US HR Deep Dive (2 phút):** DVCCNS + DVCCNS1 MoM/YoY. Trend 24 tháng — có đều không? "Hóa đơn cuối" còn trong tháng hiện tại không? Nếu DVCCNS1 = 0 tháng này → contract issue.
5. **Tab 3 — Kiểm Tra (1 phút):** Bảng dịch vụ active/inactive — có mã DISCONTINUED nào tái xuất hiện không? CPBH tháng này có > -100M không?

## Visualizations

### Tab 1: Tổng Quan

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Doanh Thu DV MTD** | Table (1 row) | [S1. Services Revenue](../domains/finance.md#s1-services-revenue) | Current / Prior Month / Prior Year + MoM% / YoY% |
| **Dịch Vụ Active** | Scalar | [S3. Service Type Breakdown](../domains/finance.md#s3-service-type-breakdown) | COUNT(DISTINCT product_code) tháng này |
| **Dịch Vụ YTD** | Scalar | [S1. Services Revenue](../domains/finance.md#s1-services-revenue) | Lũy kế từ đầu năm |
| **DV % Tổng DT** | Gauge | [S2. Services as % of Total Revenue](../domains/finance.md#s2-services-as--of-total-revenue) | Tháng trước (closed month). Ngưỡng: <5% vàng, 5-15% xanh |
| **Xu Hướng 12M** | Line Chart | [S1. Services Revenue](../domains/finance.md#s1-services-revenue) | Monthly trend, 12 tháng gần nhất |
| **Phân Bổ Theo Loại** | Pie/Donut | [S3. Service Type Breakdown](../domains/finance.md#s3-service-type-breakdown) | By product_code, tháng trước |
| **Top 5 MTD** | Table | [S1. Services Revenue](../domains/finance.md#s1-services-revenue) | Top 5 codes MTD + MoM delta |

### Tab 2: US HR Services Deep Dive

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **US HR Revenue MTD** | Table (1 row) | [S1. Services Revenue](../domains/finance.md#s1-services-revenue) | DVCCNS + DVCCNS1 combined, MoM/YoY |
| **Xu Hướng 24M** | Multi-Line | [S1. Services Revenue](../domains/finance.md#s1-services-revenue) | DVCCNS vs DVCCNS1 riêng biệt |
| **DVCCNS Breakdown** | Table | [S3. Service Type Breakdown](../domains/finance.md#s3-service-type-breakdown) | Lines, revenue, last invoice date per code |

### Tab 3: Kiểm Tra Dịch Vụ Khác

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Danh Sách Dịch Vụ** | Table | [S3. Service Type Breakdown](../domains/finance.md#s3-service-type-breakdown) | All codes, last date, 12M revenue, ACTIVE/Low/DISCONTINUED status |
| **CPBH Điều Chỉnh** | Table | [S4. CPBH Adjustments](../domains/finance.md#s4-cpbh-adjustments) | Monthly CPBH by month (24 tháng) |

## Action Triggers

| Metric | Threshold | Owner | Action |
| :--- | :--- | :--- | :--- |
| Services Revenue MoM% | < -20% | CFO | Kiểm tra DVCCNS/DVCCNS1 — contract vẫn active? "Hóa đơn cuối" có trong tháng này không? Liên hệ Finance Manager |
| Services Revenue YoY% | < -15% | CFO | So sánh DVCCNS vs DVCCNS1 riêng — 1 trong 2 có bị drop không? Xác nhận US HR contract renewal |
| CPBH tháng | > -100M VND (tuyệt đối) | Finance Manager | Tìm nguyên nhân điều chỉnh lớn, reconcile với chứng từ gốc, báo CFO |
| DV* DISCONTINUED tái xuất hiện | Bất kỳ mã nào (DVRENTAL / DVDIEN / etc.) | Accounting | Xác nhận với kế toán — nhập nhầm mã hay có hợp đồng mới thực sự? |
| DVVC (vận chuyển) tháng | > 10M VND | Finance Manager | Verify có hợp đồng vận chuyển mới không (bình thường < 1M/tháng) |
| DV % Tổng DT | > 20% | CFO | Kiểm tra tổng DT hàng hóa có sụt giảm không (% tăng có thể do denominator giảm) |

## Reading Scenarios

### Scenario 1: DVCCNS sụt giảm tháng này

**Tín hiệu:** Tab 1 hero metric đỏ (MoM < -20%) + Tab 2 trend chart DVCCNS dipped.

**Đọc theo thứ tự:**
1. Tab 2 → "Hóa đơn cuối DVCCNS" — có trong tháng hiện tại không?
2. Nếu `last_invoice_date` = tháng trước → contract chưa xuất HĐ tháng này (có thể delay) → chờ thêm 1 tuần
3. Nếu `last_invoice_date` > 2 tháng → escalate: Finance Manager kiểm tra trạng thái hợp đồng US HR
4. DVCCNS1 có bù đắp không? Nếu DVCCNS1 tăng cùng kỳ → chỉ là code migration, không phải revenue loss

### Scenario 2: CPBH âm lớn bất thường

**Tín hiệu:** Tab 3 → cột "Điều chỉnh CPBH" highlight đỏ (< -100M).

**Đọc theo thứ tự:**
1. Xem tháng nào có spike — tháng này hay hồi truy?
2. COUNT số dòng — 1 dòng lớn (đơn lẻ) hay nhiều dòng nhỏ?
3. Finance Manager: pull chi tiết từ MISA AMIS, đối chiếu với phiếu điều chỉnh gốc
4. Nếu là reversals hợp lệ → ghi chú vào monthly finance report
5. Nếu không có chứng từ → flag cho kiểm toán nội bộ

### Scenario 3: DV discontinued tái xuất hiện

**Tín hiệu:** Tab 3 bảng dịch vụ → mã DVRENTAL / DVDIEN / DVQL có "Hóa đơn cuối" = tháng gần đây.

**Đọc theo thứ tự:**
1. Xem revenue amount — nhỏ (< 5M) hay lớn?
2. Accounting: tìm invoice trong MISA, xác nhận customer + ngày
3. Nếu là nhập nhầm mã → yêu cầu kế toán điều chỉnh + đổi sang mã đúng
4. Nếu là hợp đồng mới thực sự (vd thuê văn phòng mới) → update domain với mã mới

## Data Lineage & Caveats

### Lineage

```
MISA AMIS → [ingestion: filedrop] → raw_misa_sales_lines
  → [dbt] → int_misa_sales_lines (+ is_service_line flag từ P0)
  → [Metabase Native Query] → Finance Services Revenue Dashboard
```

### Caveats Quan Trọng

1. **Không có COGS:** Services (DV*) không có giá vốn trong MISA → gross_profit = revenue. Không được dùng gross margin % để so sánh với hàng hóa (hàng hóa COGS ratio ~54%).
2. **Không có channel attribution:** Service lines thường map vào channel_code = CS hoặc KHAC. Không phân tích theo kênh bán hàng.
3. **CPBH là điều chỉnh âm:** CPBH (Chi phí bán hàng khác) là adjustment entries, giá trị thường âm. Tổng services revenue = DV* + CPBH — nếu CPBH âm lớn, tổng services revenue bị giảm.
4. **is_service_line flag:** Dashboard phụ thuộc vào P0 flag. Trước khi P0 deploy + Metabase restart, tất cả queries sẽ return 0 rows (flag chưa tồn tại).
5. **Posting date vs created date:** Dùng `posting_date` (ngày ghi sổ MISA), không phải `created_at`. Một số tháng có posting_date delay 1-3 ngày so với transaction date thực tế.

## Implementation Notes

- **Blueprint:** Đầy đủ SQL + viz config tại [blueprints/finance_services_revenue.md](../blueprints/metabase/finance_services_revenue.md)
- **Deploy:** `node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/finance_services_revenue.md`
- **Prerequisite:** P0 agent phải implement + deploy `is_service_line` flag trước khi deploy blueprint
- **Tool:** metabase
- **Collection:** Nằm trong `Finance` collection (cùng với Finance P&L Dashboard)
