# Phân Tích & Kế Hoạch Triển Khai Sales Metrics trên Metabase

Tài liệu này phân tích tính khả thi và hướng dẫn kỹ thuật để triển khai phần **2. SALES METRICS & CHARTS** từ tài liệu yêu cầu lên Metabase, dựa trên hệ thống dbt models hiện tại.

## 1. Tổng Quan & Đánh Giá Khả Thi

| Nhóm Chỉ Số              | Trạng Thái        | Ghi Chú                                                                                     |
| :----------------------- | :---------------- | :------------------------------------------------------------------------------------------ |
| **A. Sales Overview**    | ✅ Khả thi (90%)  | Thiếu dữ liệu "Mục tiêu" (Target) để so sánh.                                               |
| **B. Sales by Time**     | ✅ Khả thi (100%) | Đủ dữ liệu (Order TS, Revenue).                                                             |
| **C. Sales by Channel**  | ⚠️ Một phần       | Có doanh thu theo kênh. Thiếu dữ liệu "Traffic/Visitors" để tính Conversion Rate chính xác. |
| **D. Sales by Location** | ✅ Khả thi (95%)  | Đủ dữ liệu Tỉnh/Thành/Cửa hàng.                                                             |

---

## 2. Chi Tiết Kỹ Thuật (Data Mapping)

Các reports sẽ được xây dựng chính trên 2 bảng Fact table: `fact_orders` và `fact_sales`.

### A. Sales Overview Dashboard

#### 1. Daily Sales Trend (Line Chart)

- **Mục tiêu:** Theo dõi doanh thu, số đơn và AOV theo ngày.
- **Source Table:** `fact_orders`
- **Mapping:**
  - `Date`: `order_timestamp` (Group by Day)
  - `Orders`: `Count`
  - `Revenue`: `Sum(gmv)` (Gross Merchandise Value)
  - `AOV`: `Average(gmv)`
- **Metabase Guide:**
  - Question: Simple Query vs `fact_orders`.
  - Summarize: Sum of GMV, Count of Rows, Average of GMV.
  - Group by: `Order Timestamp: Day`.

#### 2. Revenue vs Target (Combo Chart)

- **Mục tiêu:** So sánh thực tế vs kế hoạch.
- **Thách thức:** Hệ thống chưa có bảng lưu trữ Target/Goal.
- **Giải pháp tạm thời:**
  - Sử dụng tính năng "Goal Line" (Đường mục tiêu tĩnh) trên chart Metabase nếu target cố định.
  - Hoặc tạo câu SQL Native tự điền cứng target (VD: case when month = 1 then 100M...).
  - **Khuyến nghị:** Tạo thêm bảng seed/Google Sheet chứa target tháng và import vào warehouse.

### B. Sales by Time Period

#### 1. Hourly Sales Pattern (Heatmap)

- **Mục tiêu:** Heatmap đơn hàng theo Giờ trong ngày vs Thứ trong tuần.
- **Source Table:** `fact_orders`
- **Mapping:**
  - `Hour`: Extract Hour từ `order_timestamp`.
  - `Day of Week`: Extract SOL từ `order_timestamp`.
  - `Metric`: `Count` hoặc `Sum(gmv)`.
- **Metabase Guide:**
  - Dùng Pivot Table hoặc Grid visualize.
  - Rows: `Order Timestamp: Hour of Day`.
  - Columns: `Order Timestamp: Day of Week`.

#### 2. Monthly Sales & YoY

- **Source Table:** `fact_orders`
- **Mapping:** Tương tự Daily Trend nhưng Group by Month và Year.
- Dùng tính năng "Compare to previous period" của Metabase (trong SQL là `lag()`/`lead()`).

### C. Sales by Channel

#### 1. Revenue by Channel (Pie Chart)

- **Source Table:** `fact_orders` JOIN `dim_channels` (đã có `channel_key`).
- **Mapping:**
  - `Dimension`: `dim_channels.channel_name` (Hoặc dùng `channel_key` nếu bảng dim chưa sync đủ tên đẹp).
  - `Metric`: `Sum(gmv)`.

#### 2. Channel Performance Table

- **Vấn đề:** Chỉ số **Conversion Rate** yêu cầu số liệu `Sessions` (lượt truy cập) mà hiện tại Warehouse ERP/POS (Sapo) thường không có (dữ liệu này nằm ở Google Analytics/Tracking).
- **Giải pháp:**
  - Hiện tại: Hiển thị Revenue, Order Count, AOV.
  - Tương lai: Import dữ liệu GA4 vào warehouse để join tính Conversion Rate.

### D. Sales by Location

#### 1. Revenue by Location (Map)

- **Source Table:** `fact_orders` JOIN `dim_geography` (qua `shipping_geography_key`).
- **Mapping:**
  - `Location`: `dim_geography.province` (Tên tỉnh thành).
  - `Metabase Map`: Cài đặt Region Map là "Vietnam" (cần khớp tên tỉnh hoặc dùng mã ISO).
  - `Metric`: `Sum(gmv)`.

#### 2. Top Performing Stores (Table)

- **Source Table:** `fact_orders` JOIN `dim_branch_location` (qua `branch_location_key`).
- **Mapping:**
  - `Store Name`: `dim_branch_location.branch_location_name`.
  - `Revenue`: `Sum(gmv)`.
  - `Orders`: `Count`.

---

## 3. Kế Hoạch Thực Hiện

1.  **DBT Layer (Data Prep):**
    - Đảm bảo `fact_orders` và `fact_sales` đã được build và update mới nhất.
    - Kiểm tra bảng `dim_geography` đã chuẩn hóa tên tỉnh thành để map visualization chưa.

2.  **Metabase Implementation (Reporting):**
    - Tạo **Collection** mới: "Executive Validation" hoặc "Sales Dashboard".
    - Thực hiện tạo từng Question theo danh sách trên.
    - Gom lại vào 1 Dashboard chung.

3.  **Xử lý Gap:**
    - Thống nhất phương án nhập liệu Target (Google Sheet hay Hardcode).

Bạn có muốn tôi tiến hành tạo các câu hỏi (Cards) này trên Metabase ngay bây giờ không? (Tôi sẽ cần quyền truy cập hoặc confirm context server Metabase đã sẵn sàng và kết nối với DWH).
