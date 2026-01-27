# Phân Tích & Kế Hoạch Triển Khai Sales Metrics trên Metabase (Updated)

Tài liệu này phân tích tính khả thi và hướng dẫn kỹ thuật để triển khai phần **2. SALES METRICS & CHARTS** từ tài liệu yêu cầu lên Metabase, dựa trên hệ thống dbt models hiện tại.

## 1. Tổng Quan & Đánh Giá Khả Thi

| Nhóm Chỉ Số              | Trạng Thái        | Ghi Chú                                                                                     |
| :----------------------- | :---------------- | :------------------------------------------------------------------------------------------ |
| **A. Sales Overview**    | ✅ Khả thi (100%) | Đã có dữ liệu `fact_targets` để so sánh KPI.                                                |
| **B. Sales by Time**     | ✅ Khả thi (100%) | Đủ dữ liệu (Order TS, Revenue).                                                             |
| **C. Sales by Channel**  | ⚠️ Một phần       | Có doanh thu theo kênh. Thiếu dữ liệu "Traffic/Visitors" để tính Conversion Rate chính xác. |
| **D. Sales by Location** | ✅ Khả thi (95%)  | Đủ dữ liệu Tỉnh/Thành/Cửa hàng.                                                             |

---

## 2. Chi Tiết Kỹ Thuật (Data Mapping)

Các reports sẽ được xây dựng chính trên: `fact_orders`, `fact_sales` và **`fact_targets`**.

### A. Sales Overview Dashboard

#### 1. Daily Sales Trend (Line Chart)

- **Metric:** Revenue, Orders, AOV.
- **Source:** `fact_orders`.
- **Guide:** Simple Query, Group by `order_timestamp: Day`.

#### 2. Revenue vs Target (Combo Chart)

- **Mục tiêu:** So sánh Thực tế vs Kế hoạch theo Tháng.
- **Source:** `fact_orders` + `fact_targets`.
- **Query Strategy (Native SQL):**
  ```sql
  WITH actuals AS (
      SELECT date_trunc('month', created_at) as month, sum(gmv) as actual FROM fact_orders GROUP BY 1
  ), targets AS (
      SELECT period_date as month, sum(target_val) as target
      FROM fact_targets
      WHERE metric_code = 'gmv' AND is_current = true
      GROUP BY 1
  )
  SELECT
      coalesce(a.month, t.month) as month,
      coalesce(a.actual, 0) as actual,
      coalesce(t.target, 0) as target
  FROM actuals a FULL OUTER JOIN targets t ON a.month = t.month
  ORDER BY month
  ```

### B. Sales by Time Period

#### 1. Hourly Sales Pattern (Heatmap)

- **Source:** `fact_orders`.
- **Guide:** Pivot Table (Hour x DayOfWeek).

### C. Sales by Channel

#### 1. Revenue by Channel (Pie Chart)

- **Source:** `fact_orders` join `dim_channels`.

#### 2. Channel Performance

- **Gap:** Conversion Rate.
- **Action:** Hiển thị Revenue/Orders trước. Đánh dấu "Coming Soon" cho Conversion Rate.

### D. Sales by Location

#### 1. Revenue by Location (Map)

- **Source:** `fact_orders` join `dim_geography`.

---

## 3. Lộ Trình Triển Khai (Revised)

### Phase 1: Data Verification (Done)

- [x] Build `fact_orders`, `fact_sales`.
- [x] Build `fact_targets` (Universal Target Model).

### Phase 2: Metabase Setup (Next)

- [ ] Tạo Collection: **"Sales Analytics"**.
- [ ] Thiết lập Data Model trong Admin Panel (Foreign Keys, Formatting tiền tệ).

### Phase 3: Dashboard Creation

1.  **Chart: Daily Revenue**: Line chart.
2.  **Chart: Monthly Actual vs Target**: Combo chart.
    - **SQL Logic**:
      ```sql
      WITH actuals AS (
          SELECT date_trunc('month', created_at) as month, sum(gmv) as actual
          FROM fact_orders
          GROUP BY 1
      ), targets AS (
          SELECT period_date as month, sum(target_val) as target
          FROM fact_targets
          WHERE metric_code = 'gmv' AND is_current = true
          GROUP BY 1
      )
      SELECT
          coalesce(a.month, t.month) as month,
          coalesce(a.actual, 0) as actual,
          coalesce(t.target, 0) as target
      FROM actuals a FULL OUTER JOIN targets t ON a.month = t.month
      ORDER BY month
      ```
3.  **Chart: Revenue by Channel**: Pie/Donut.
4.  **Chart: Top Stores**: Table with formatting.
5.  **Dashboard**: Gom tất cả vào "Sales Executive Dashboard".
