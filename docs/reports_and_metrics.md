# Các Chỉ Số, Chart và Table Trong Báo Cáo Bán Hàng E-commerce

## 📊 1. KEY PERFORMANCE INDICATORS (KPIs)

### Revenue KPIs

| Metric                            | Formula                                | Description                 | Data Source                           |
| --------------------------------- | -------------------------------------- | --------------------------- | ------------------------------------- |
| **GMV (Gross Merchandise Value)** | SUM(order_total)                       | Tổng giá trị đơn hàng       | Order.total                           |
| **Net Revenue**                   | GMV - Returns - Discounts              | Doanh thu thực tế           | Order.total - returns - discounts     |
| **Average Order Value (AOV)**     | Total Revenue / Number of Orders       | Giá trị trung bình đơn hàng | AVG(Order.total)                      |
| **Revenue per Customer**          | Total Revenue / Number of Customers    | Doanh thu/khách hàng        | Revenue / COUNT(DISTINCT customer_id) |
| **Revenue Growth Rate**           | (Current - Previous) / Previous × 100% | Tăng trưởng doanh thu       | Period comparison                     |

### Conversion & Traffic KPIs

| Metric                      | Formula                                   | Description        | Data Source                 |
| --------------------------- | ----------------------------------------- | ------------------ | --------------------------- |
| **Conversion Rate**         | Orders / Visitors × 100%                  | Tỷ lệ chuyển đổi   | Orders / Traffic (external) |
| **Cart Abandonment Rate**   | Abandoned Carts / Created Carts × 100%    | Tỷ lệ bỏ giỏ hàng  | Draft orders vs confirmed   |
| **Average Items per Order** | Total Items / Total Orders                | Số sản phẩm TB/đơn | AVG(OrderLineItem.quantity) |
| **Order Frequency**         | Orders / Customers                        | Tần suất mua hàng  | Orders per customer         |
| **Repeat Purchase Rate**    | Repeat Customers / Total Customers × 100% | Tỷ lệ mua lại      | Customers with >1 order     |

### Customer KPIs

| Metric                              | Formula                                      | Description         | Data Source                     |
| ----------------------------------- | -------------------------------------------- | ------------------- | ------------------------------- |
| **Customer Lifetime Value (CLV)**   | AOV × Purchase Frequency × Customer Lifespan | Giá trị trọn đời KH | Customer.sale_order.total_sales |
| **Customer Acquisition Cost (CAC)** | Marketing Spend / New Customers              | Chi phí thu hút KH  | External data                   |
| **Net Promoter Score (NPS)**        | % Promoters - % Detractors                   | Mức độ hài lòng     | Survey data                     |
| **Customer Retention Rate**         | ((CE-CN)/CS) × 100%                          | Tỷ lệ giữ chân KH   | Period comparison               |
| **Churn Rate**                      | Lost Customers / Total Customers × 100%      | Tỷ lệ rời bỏ        | Inactive customers              |

### Operational KPIs

| Metric                     | Formula                                | Description          | Data Source              |
| -------------------------- | -------------------------------------- | -------------------- | ------------------------ |
| **Order Fulfillment Rate** | Fulfilled Orders / Total Orders × 100% | Tỷ lệ hoàn thành đơn | Fulfillment.status       |
| **Average Delivery Time**  | AVG(Delivered Date - Order Date)       | Thời gian giao TB    | Shipment timestamps      |
| **Return Rate**            | Returns / Total Orders × 100%          | Tỷ lệ trả hàng       | OrderReturn count        |
| **Inventory Turnover**     | COGS / Average Inventory               | Vòng quay kho        | Product inventory        |
| **Out of Stock Rate**      | OOS Products / Total Products × 100%   | Tỷ lệ hết hàng       | Product.inventory_status |

---

## 📈 2. SALES METRICS & CHARTS

### A. Sales Overview Dashboard

**Metrics Table:**

```
┌─────────────────────┬──────────────┬──────────────┬──────────┐
│ Metric              │ Today        │ MTD          │ YTD      │
├─────────────────────┼──────────────┼──────────────┼──────────┤
│ Gross Revenue       │ $12,450      │ $345,890     │ $2.1M    │
│ Net Revenue         │ $11,200      │ $310,500     │ $1.9M    │
│ Orders              │ 156          │ 4,234        │ 28,901   │
│ AOV                 │ $79.81       │ $81.71       │ $72.65   │
│ Conversion Rate     │ 2.3%         │ 2.1%         │ 1.9%     │
└─────────────────────┴──────────────┴──────────────┴──────────┘
```

#### Chart: Daily Sales Trend (Line Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| order_date | DATE | Ngày đặt hàng |
| order_count | INTEGER | Số lượng đơn hàng trong ngày |
| revenue | DECIMAL(15,2) | Tổng doanh thu trong ngày |
| avg_order_value | DECIMAL(15,2) | Giá trị đơn hàng trung bình |

```sql
SELECT
    DATE(created_on) as order_date,
    COUNT(*) as order_count,
    SUM(total) as revenue,
    AVG(total) as avg_order_value
FROM orders
WHERE created_on >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_on)
ORDER BY order_date
```

**Chart: Revenue vs Target (Combo Chart)**

- Line: Actual Revenue
- Line: Target Revenue
- Bar: Difference (positive/negative)

---

### B. Sales by Time Period

#### Chart: Hourly Sales Pattern (Heatmap)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| hour | INTEGER | Giờ trong ngày (0-23) |
| day_of_week | INTEGER | Ngày trong tuần (0=Sunday, 6=Saturday) |
| order_count | INTEGER | Số lượng đơn hàng |
| revenue | DECIMAL(15,2) | Tổng doanh thu |

```sql
SELECT
    EXTRACT(HOUR FROM created_on) as hour,
    EXTRACT(DOW FROM created_on) as day_of_week,
    COUNT(*) as order_count,
    SUM(total) as revenue
FROM orders
GROUP BY hour, day_of_week
```

#### Chart: Monthly Sales Trend (Area Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| month | DATE | Tháng (đầu tháng) |
| revenue | DECIMAL(15,2) | Tổng doanh thu tháng |
| orders | INTEGER | Số lượng đơn hàng |
| customers | INTEGER | Số lượng khách hàng unique |

```sql
SELECT
    DATE_TRUNC('month', created_on) as month,
    SUM(total) as revenue,
    COUNT(*) as orders,
    COUNT(DISTINCT customer_id) as customers
FROM orders
GROUP BY month
ORDER BY month
```

#### Chart: Year-over-Year Comparison (Line Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| month | INTEGER | Tháng (1-12) |
| year | INTEGER | Năm |
| revenue | DECIMAL(15,2) | Tổng doanh thu |

```sql
SELECT
    EXTRACT(MONTH FROM created_on) as month,
    EXTRACT(YEAR FROM created_on) as year,
    SUM(total) as revenue
FROM orders
WHERE EXTRACT(YEAR FROM created_on) >= YEAR(CURRENT_DATE) - 2
GROUP BY month, year
ORDER BY year, month
```

---

### C. Sales by Channel

#### Chart: Revenue by Channel (Pie/Donut Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| channel | VARCHAR(100) | Tên kênh bán hàng |
| revenue | DECIMAL(15,2) | Tổng doanh thu |
| orders | INTEGER | Số lượng đơn hàng |
| pct | DECIMAL(5,2) | Phần trăm doanh thu |

```sql
SELECT
    channel,
    SUM(total) as revenue,
    COUNT(*) as orders,
    ROUND(SUM(total) * 100.0 / SUM(SUM(total)) OVER (), 2) as pct
FROM orders
GROUP BY channel
ORDER BY revenue DESC
```

**Table: Channel Performance**

```
┌──────────────┬───────────┬────────┬──────┬───────────┬─────────┐
│ Channel      │ Revenue   │ Orders │ AOV  │ Conv Rate │ Growth  │
├──────────────┼───────────┼────────┼──────┼───────────┼─────────┤
│ Online       │ $1.2M     │ 15,234 │ $79  │ 2.3%      │ +15%    │
│ Retail       │ $890K     │ 8,901  │ $100 │ 8.5%      │ +8%     │
│ Wholesale    │ $450K     │ 1,234  │ $365 │ 45%       │ +22%    │
│ Marketplace  │ $234K     │ 3,456  │ $68  │ 1.8%      │ +5%     │
└──────────────┴───────────┴────────┴──────┴───────────┴─────────┘
```

---

### D. Sales by Location

#### Chart: Revenue by Location (Map Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| location_name | VARCHAR(200) | Tên chi nhánh/kho |
| city | VARCHAR(100) | Thành phố |
| district | VARCHAR(100) | Quận/huyện |
| orders | INTEGER | Số lượng đơn hàng |
| revenue | DECIMAL(15,2) | Tổng doanh thu |

```sql
SELECT
    l.location_name,
    l.city,
    l.district,
    COUNT(o.order_id) as orders,
    SUM(o.total) as revenue
FROM orders o
JOIN locations l ON o.location_id = l.location_id
GROUP BY l.location_id, l.location_name, l.city, l.district
```

#### Table: Top Performing Stores

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| location_name | VARCHAR(200) | Tên chi nhánh |
| location_type | VARCHAR(50) | Loại chi nhánh (warehouse/store/virtual) |
| total_orders | INTEGER | Tổng số đơn hàng |
| total_revenue | DECIMAL(15,2) | Tổng doanh thu |
| avg_order_value | DECIMAL(15,2) | Giá trị đơn hàng TB |
| rank | INTEGER | Xếp hạng theo doanh thu |

```sql
SELECT
    l.location_name,
    l.location_type,
    COUNT(o.order_id) as total_orders,
    SUM(o.total) as total_revenue,
    AVG(o.total) as avg_order_value,
    RANK() OVER (ORDER BY SUM(o.total) DESC) as rank
FROM orders o
JOIN locations l ON o.location_id = l.location_id
GROUP BY l.location_id, l.location_name, l.location_type
ORDER BY total_revenue DESC
LIMIT 10
```

---

## 💰 3. FINANCIAL METRICS & CHARTS

### A. Revenue Breakdown

#### Chart: Revenue Waterfall

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| category | VARCHAR(50) | Loại doanh thu/chi phí |
| amount | DECIMAL(15,2) | Số tiền (âm nếu là chi phí) |

```sql
SELECT
    'Gross Revenue' as category, SUM(total) as amount
FROM orders
UNION ALL
SELECT 'Discounts', -SUM(total_discount) FROM orders
UNION ALL
SELECT 'Returns', -SUM(refund_amount) FROM order_returns
UNION ALL
SELECT 'Tax', SUM(total_tax) FROM orders
UNION ALL
SELECT 'Shipping', SUM(delivery_fee) FROM fulfillments
```

#### Table: Revenue Components

```
┌─────────────────┬────────────┬──────────┬─────────┐
│ Component       │ This Month │ Last Mo  │ Change  │
├─────────────────┼────────────┼──────────┼─────────┤
│ Product Sales   │ $345,890   │ $312,450 │ +10.7%  │
│ Shipping Fees   │ $12,340    │ $11,890  │ +3.8%   │
│ Tax Collected   │ $35,234    │ $31,678  │ +11.2%  │
│ Discounts       │ -$23,456   │ -$19,234 │ +21.9%  │
│ Returns         │ -$8,901    │ -$7,234  │ +23.0%  │
│ Net Revenue     │ $361,107   │ $329,550 │ +9.6%   │
└─────────────────┴────────────┴──────────┴─────────┘
```

---

### B. Payment Analysis

#### Chart: Payment Methods (Pie Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| payment_method_name | VARCHAR(200) | Tên phương thức thanh toán |
| transaction_count | INTEGER | Số lượng giao dịch |
| total_amount | DECIMAL(15,2) | Tổng số tiền |

```sql
SELECT
    pm.payment_method_name,
    COUNT(*) as transaction_count,
    SUM(p.amount) as total_amount
FROM payments p
JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
WHERE p.status = 'completed'
GROUP BY pm.payment_method_name
```

#### Table: Payment Status Tracking

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| payment_status | VARCHAR(50) | Trạng thái thanh toán |
| order_count | INTEGER | Số lượng đơn hàng |
| total_amount | DECIMAL(15,2) | Tổng số tiền |
| avg_order_value | DECIMAL(15,2) | Giá trị đơn TB |

```sql
SELECT
    payment_status,
    COUNT(*) as order_count,
    SUM(total) as total_amount,
    AVG(total) as avg_order_value
FROM orders
GROUP BY payment_status
```

---

### C. Discount Analysis

#### Chart: Discount Impact (Combo Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| date | DATE | Ngày |
| total_orders | INTEGER | Tổng số đơn hàng |
| discounted_orders | INTEGER | Số đơn có giảm giá |
| total_discounts | DECIMAL(15,2) | Tổng giảm giá |
| avg_discount_pct | DECIMAL(5,2) | % giảm giá TB |

```sql
SELECT
    DATE_TRUNC('day', created_on) as date,
    COUNT(*) as total_orders,
    SUM(CASE WHEN total_discount > 0 THEN 1 ELSE 0 END) as discounted_orders,
    SUM(total_discount) as total_discounts,
    AVG(total_discount * 100.0 / NULLIF(total, 0)) as avg_discount_pct
FROM orders
GROUP BY date
ORDER BY date
```

#### Table: Promotion Performance

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| promotion_name | VARCHAR(200) | Tên chương trình khuyến mãi |
| orders_used | INTEGER | Số đơn sử dụng |
| total_discount | DECIMAL(15,2) | Tổng giảm giá |
| revenue_with_promo | DECIMAL(15,2) | Doanh thu có khuyến mãi |
| avg_discount_per_order | DECIMAL(15,2) | Giảm giá TB/đơn |

```sql
SELECT
    pr.promotion_name,
    COUNT(DISTINCT o.order_id) as orders_used,
    SUM(pr.discount_amount) as total_discount,
    SUM(o.total) as revenue_with_promo,
    AVG(pr.discount_amount) as avg_discount_per_order
FROM orders o
JOIN promotion_redemptions pr ON o.order_id = pr.order_id
GROUP BY pr.promotion_id, pr.promotion_name
ORDER BY total_discount DESC
```

---

### D. Profit Analysis

#### Chart: Profit Margin by Category (Bar Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| category | VARCHAR(200) | Danh mục sản phẩm |
| revenue | DECIMAL(15,2) | Doanh thu |
| cogs | DECIMAL(15,2) | Giá vốn hàng bán |
| gross_profit | DECIMAL(15,2) | Lợi nhuận gộp |
| margin_pct | DECIMAL(5,2) | % lợi nhuận |

```sql
SELECT
    p.category,
    SUM(oli.line_amount) as revenue,
    SUM(oli.quantity * p.cost_price) as cogs,
    SUM(oli.line_amount - oli.quantity * p.cost_price) as gross_profit,
    (SUM(oli.line_amount - oli.quantity * p.cost_price) * 100.0 /
     NULLIF(SUM(oli.line_amount), 0)) as margin_pct
FROM order_line_items oli
JOIN products p ON oli.product_id = p.product_id
GROUP BY p.category
ORDER BY gross_profit DESC
```

---

## 👥 4. CUSTOMER METRICS & CHARTS

### A. Customer Acquisition

#### Chart: New vs Returning Customers (Stacked Bar)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| month | DATE | Tháng (đầu tháng) |
| new_customers | INTEGER | Số khách hàng mới |
| returning_customers | INTEGER | Số khách hàng quay lại |

```sql
SELECT
    DATE_TRUNC('month', o.created_on) as month,
    COUNT(CASE WHEN c.created_on >= o.created_on - INTERVAL '30 days'
          THEN 1 END) as new_customers,
    COUNT(CASE WHEN c.created_on < o.created_on - INTERVAL '30 days'
          THEN 1 END) as returning_customers
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY month
```

**Metric Cards:**

```
┌─────────────────────────────────────────────────────────────┐
│  New Customers        Active Customers    Churned Customers │
│     1,234                 8,901               456            │
│     +12% vs LM            -3% vs LM          +8% vs LM      │
└─────────────────────────────────────────────────────────────┘
```

---

### B. Customer Segmentation

#### Chart: RFM Analysis (Scatter Plot)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| customer_id | INTEGER | ID khách hàng |
| recency | INTEGER | Số ngày kể từ đơn hàng cuối |
| frequency | INTEGER | Số lượng đơn hàng |
| monetary | DECIMAL(15,2) | Tổng giá trị đơn hàng |
| r_score | INTEGER | Điểm recency (1-5) |
| f_score | INTEGER | Điểm frequency (1-5) |
| m_score | INTEGER | Điểm monetary (1-5) |

```sql
WITH rfm AS (
    SELECT
        customer_id,
        DATEDIFF(day, MAX(created_on), CURRENT_DATE) as recency,
        COUNT(*) as frequency,
        SUM(total) as monetary
    FROM orders
    GROUP BY customer_id
)
SELECT
    customer_id,
    recency,
    frequency,
    monetary,
    NTILE(5) OVER (ORDER BY recency DESC) as r_score,
    NTILE(5) OVER (ORDER BY frequency) as f_score,
    NTILE(5) OVER (ORDER BY monetary) as m_score
FROM rfm
```

#### Table: Customer Segments

```
┌──────────────┬───────────┬────────┬──────────┬──────────┬────────┐
│ Segment      │ Customers │ % Tot  │ Avg CLV  │ Avg Freq │ Revenue│
├──────────────┼───────────┼────────┼──────────┼──────────┼────────┤
│ Champions    │ 1,234     │ 15%    │ $2,500   │ 12       │ $3.1M  │
│ Loyal        │ 2,345     │ 28%    │ $1,800   │ 8        │ $4.2M  │
│ Potential    │ 1,890     │ 22%    │ $950     │ 4        │ $1.8M  │
│ At Risk      │ 890       │ 11%    │ $1,200   │ 6        │ $1.1M  │
│ Lost         │ 2,012     │ 24%    │ $450     │ 2        │ $0.9M  │
└──────────────┴───────────┴────────┴──────────┴──────────┴────────┘
```

#### Chart: Customer Lifetime Value Distribution (Histogram)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| clv_bucket | VARCHAR(20) | Phân nhóm CLV |
| customer_count | INTEGER | Số lượng khách hàng |

```sql
SELECT
    CASE
        WHEN total_sales < 100 THEN '$0-100'
        WHEN total_sales < 500 THEN '$100-500'
        WHEN total_sales < 1000 THEN '$500-1,000'
        WHEN total_sales < 5000 THEN '$1,000-5,000'
        ELSE '$5,000+'
    END as clv_bucket,
    COUNT(*) as customer_count
FROM (
    SELECT
        customer_id,
        SUM(total) as total_sales
    FROM orders
    GROUP BY customer_id
) customer_sales
GROUP BY clv_bucket
ORDER BY MIN(total_sales)
```

---

### C. Customer Retention

#### Chart: Cohort Analysis (Heatmap)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| cohort_month | DATE | Tháng cohort (tháng đầu tiên mua) |
| month_number | INTEGER | Số tháng kể từ cohort |
| customers | INTEGER | Số khách hàng còn active |

```sql
WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', MIN(created_on)) as cohort_month,
        DATE_TRUNC('month', created_on) as order_month
    FROM orders
    GROUP BY customer_id, DATE_TRUNC('month', created_on)
)
SELECT
    cohort_month,
    DATEDIFF(month, cohort_month, order_month) as month_number,
    COUNT(DISTINCT customer_id) as customers
FROM cohorts
GROUP BY cohort_month, month_number
ORDER BY cohort_month, month_number
```

#### Chart: Retention Curve (Line Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| month_number | INTEGER | Số tháng kể từ cohort |
| avg_retention | DECIMAL(5,2) | Tỷ lệ retention trung bình (%) |

```sql
SELECT
    month_number,
    AVG(retention_rate) as avg_retention
FROM (
    SELECT
        cohort_month,
        month_number,
        customers * 100.0 / FIRST_VALUE(customers)
            OVER (PARTITION BY cohort_month ORDER BY month_number)
            as retention_rate
    FROM cohort_analysis
) cohort_retention
GROUP BY month_number
ORDER BY month_number
```

---

### D. Customer Demographics

#### Chart: Customer Distribution by Group (Bar Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| group_name | VARCHAR(200) | Tên nhóm khách hàng |
| customer_count | INTEGER | Số lượng khách hàng |
| total_revenue | DECIMAL(15,2) | Tổng doanh thu |
| avg_customer_value | DECIMAL(15,2) | Giá trị TB/khách hàng |

```sql
SELECT
    cg.group_name,
    COUNT(DISTINCT c.customer_id) as customer_count,
    SUM(so.total_sales) as total_revenue,
    AVG(so.total_sales) as avg_customer_value
FROM customers c
JOIN customer_groups cg ON c.customer_group_id = cg.customer_group_id
LEFT JOIN sale_orders so ON c.customer_id = so.customer_id
GROUP BY cg.group_name
ORDER BY total_revenue DESC
```

#### Chart: Top Customers (Horizontal Bar)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| customer_name | VARCHAR(200) | Tên khách hàng |
| email | VARCHAR(255) | Email khách hàng |
| total_orders | INTEGER | Tổng số đơn hàng |
| total_spent | DECIMAL(15,2) | Tổng chi tiêu |
| last_order_date | TIMESTAMP | Ngày đặt hàng cuối |

```sql
SELECT
    c.customer_name,
    c.email,
    COUNT(o.order_id) as total_orders,
    SUM(o.total) as total_spent,
    MAX(o.created_on) as last_order_date
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name, c.email
ORDER BY total_spent DESC
LIMIT 20
```

---

## 📦 5. PRODUCT METRICS & CHARTS

### A. Product Performance

#### Table: Top Selling Products

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| product_name | VARCHAR(500) | Tên sản phẩm |
| sku | VARCHAR(100) | Mã SKU |
| units_sold | INTEGER | Số lượng bán được |
| revenue | DECIMAL(15,2) | Doanh thu |
| orders | INTEGER | Số đơn hàng chứa sản phẩm |
| avg_price | DECIMAL(15,2) | Giá bán trung bình |
| total_discount | DECIMAL(15,2) | Tổng giảm giá |

```sql
SELECT
    p.product_name,
    p.sku,
    SUM(oli.quantity) as units_sold,
    SUM(oli.line_amount) as revenue,
    COUNT(DISTINCT oli.order_id) as orders,
    AVG(oli.price) as avg_price,
    SUM(oli.discount_amount) as total_discount
FROM order_line_items oli
JOIN products p ON oli.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.sku
ORDER BY revenue DESC
LIMIT 50
```

#### Chart: Product Revenue Contribution (Treemap)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| category | VARCHAR(200) | Danh mục sản phẩm |
| product_name | VARCHAR(500) | Tên sản phẩm |
| revenue | DECIMAL(15,2) | Doanh thu |
| quantity | INTEGER | Số lượng bán |

```sql
SELECT
    p.category,
    p.product_name,
    SUM(oli.line_amount) as revenue,
    SUM(oli.quantity) as quantity
FROM order_line_items oli
JOIN products p ON oli.product_id = p.product_id
GROUP BY p.category, p.product_name
```

---

### B. Product Categories

#### Chart: Revenue by Category (Stacked Bar)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| month | DATE | Tháng |
| category | VARCHAR(200) | Danh mục sản phẩm |
| revenue | DECIMAL(15,2) | Doanh thu |

```sql
SELECT
    DATE_TRUNC('month', o.created_on) as month,
    p.category,
    SUM(oli.line_amount) as revenue
FROM orders o
JOIN order_line_items oli ON o.order_id = oli.order_id
JOIN products p ON oli.product_id = p.product_id
GROUP BY month, p.category
ORDER BY month, revenue DESC
```

#### Table: Category Performance

```
┌────────────┬──────────┬────────┬──────┬──────────┬─────────┐
│ Category   │ Revenue  │ Units  │ AOV  │ Margin % │ Growth  │
├────────────┼──────────┼────────┼──────┼──────────┼─────────┤
│ Electronics│ $450K    │ 2,345  │ $192 │ 35%      │ +18%    │
│ Clothing   │ $380K    │ 8,901  │ $43  │ 52%      │ +12%    │
│ Home       │ $290K    │ 1,234  │ $235 │ 41%      │ +8%     │
│ Beauty     │ $180K    │ 3,456  │ $52  │ 48%      │ +22%    │
└────────────┴──────────┴────────┴──────┴──────────┴─────────┘
```

---

### C. Product Trends

#### Chart: Product Lifecycle (Line Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| product_name | VARCHAR(500) | Tên sản phẩm |
| week | DATE | Tuần (đầu tuần) |
| units_sold | INTEGER | Số lượng bán |
| revenue | DECIMAL(15,2) | Doanh thu |

```sql
SELECT
    p.product_name,
    DATE_TRUNC('week', o.created_on) as week,
    SUM(oli.quantity) as units_sold,
    SUM(oli.line_amount) as revenue
FROM orders o
JOIN order_line_items oli ON o.order_id = oli.order_id
JOIN products p ON oli.product_id = p.product_id
WHERE p.product_id IN (SELECT product_id FROM top_products)
GROUP BY p.product_name, week
ORDER BY p.product_name, week
```

#### Table: Product Velocity

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| product_name | VARCHAR(500) | Tên sản phẩm |
| total_sold | INTEGER | Tổng số lượng bán |
| avg_per_order | DECIMAL(10,2) | TB số lượng/đơn hàng |
| days_sold | INTEGER | Số ngày có bán |
| daily_velocity | DECIMAL(10,2) | Vận tốc bán hàng/ngày |

```sql
SELECT
    p.product_name,
    SUM(oli.quantity) as total_sold,
    AVG(oli.quantity) as avg_per_order,
    COUNT(DISTINCT DATE(o.created_on)) as days_sold,
    SUM(oli.quantity) * 1.0 /
        COUNT(DISTINCT DATE(o.created_on)) as daily_velocity
FROM orders o
JOIN order_line_items oli ON o.order_id = oli.order_id
JOIN products p ON oli.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY daily_velocity DESC
```

---

### D. Inventory Metrics

#### Chart: Stock Status (Gauge/Progress Bar)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| in_stock | INTEGER | Số sản phẩm còn hàng |
| low_stock | INTEGER | Số sản phẩm sắp hết |
| out_of_stock | INTEGER | Số sản phẩm hết hàng |
| total_products | INTEGER | Tổng số sản phẩm |

```sql
SELECT
    COUNT(CASE WHEN inventory_status = 'in_stock' THEN 1 END) as in_stock,
    COUNT(CASE WHEN inventory_status = 'low_stock' THEN 1 END) as low_stock,
    COUNT(CASE WHEN inventory_status = 'out_of_stock' THEN 1 END) as out_of_stock,
    COUNT(*) as total_products
FROM products
```

#### Table: Slow-Moving Inventory

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| product_name | VARCHAR(500) | Tên sản phẩm |
| sku | VARCHAR(100) | Mã SKU |
| current_stock | INTEGER | Tồn kho hiện tại |
| units_sold_30d | INTEGER | Số lượng bán trong 30 ngày |
| inventory_value | DECIMAL(15,2) | Giá trị tồn kho |
| days_of_supply | DECIMAL(10,2) | Số ngày tồn kho đủ bán |

```sql
SELECT
    p.product_name,
    p.sku,
    pv.quantity as current_stock,
    COALESCE(SUM(oli.quantity), 0) as units_sold_30d,
    pv.quantity * p.cost_price as inventory_value,
    CASE
        WHEN COALESCE(SUM(oli.quantity), 0) = 0 THEN 999
        ELSE pv.quantity * 30.0 / COALESCE(SUM(oli.quantity), 1)
    END as days_of_supply
FROM products p
JOIN product_variants pv ON p.product_id = pv.product_id
LEFT JOIN order_line_items oli ON pv.variant_id = oli.variant_id
    AND oli.created_on >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY p.product_id, p.product_name, p.sku, pv.quantity, p.cost_price
HAVING days_of_supply > 90
ORDER BY inventory_value DESC
```

---

## 🚚 6. OPERATIONAL METRICS & CHARTS

### A. Order Fulfillment

#### Chart: Order Status Funnel

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| status | VARCHAR(50) | Trạng thái đơn hàng |
| order_count | INTEGER | Số lượng đơn hàng |
| total_value | DECIMAL(15,2) | Tổng giá trị |

```sql
SELECT
    status,
    COUNT(*) as order_count,
    SUM(total) as total_value
FROM orders
GROUP BY status
ORDER BY
    CASE status
        WHEN 'draft' THEN 1
        WHEN 'pending' THEN 2
        WHEN 'confirmed' THEN 3
        WHEN 'processing' THEN 4
        WHEN 'completed' THEN 5
        WHEN 'cancelled' THEN 6
    END
```

#### Table: Fulfillment Performance

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| date | DATE | Ngày |
| total_fulfillments | INTEGER | Tổng số fulfillment |
| avg_processing_hours | DECIMAL(10,2) | Giờ xử lý TB |
| fulfillment_rate | DECIMAL(5,2) | Tỷ lệ hoàn thành (%) |
| same_day_fulfillment_rate | DECIMAL(5,2) | Tỷ lệ ship trong ngày (%) |

```sql
SELECT
    DATE_TRUNC('day', f.created_on) as date,
    COUNT(*) as total_fulfillments,
    AVG(EXTRACT(EPOCH FROM (f.shipped_on - f.created_on))/3600) as avg_processing_hours,
    COUNT(CASE WHEN f.status = 'shipped' THEN 1 END) * 100.0 / COUNT(*) as fulfillment_rate,
    COUNT(CASE WHEN f.shipped_on <= f.created_on + INTERVAL '24 hours' THEN 1 END) * 100.0 /
        COUNT(*) as same_day_fulfillment_rate
FROM fulfillments f
GROUP BY date
ORDER BY date DESC
```

---

### B. Shipping Performance

#### Chart: Delivery Time Distribution (Histogram)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| delivery_time_bucket | VARCHAR(20) | Nhóm thời gian giao hàng |
| shipment_count | INTEGER | Số lượng đơn giao |

```sql
SELECT
    CASE
        WHEN delivery_days <= 1 THEN '0-1 days'
        WHEN delivery_days <= 2 THEN '1-2 days'
        WHEN delivery_days <= 3 THEN '2-3 days'
        WHEN delivery_days <= 5 THEN '3-5 days'
        ELSE '5+ days'
    END as delivery_time_bucket,
    COUNT(*) as shipment_count
FROM (
    SELECT
        s.shipment_id,
        EXTRACT(DAY FROM (s.delivered_at - o.created_on)) as delivery_days
    FROM shipments s
    JOIN fulfillments f ON s.fulfillment_id = f.fulfillment_id
    JOIN orders o ON f.order_id = o.order_id
    WHERE s.status = 'delivered'
) delivery_times
GROUP BY delivery_time_bucket
```

#### Table: Carrier Performance

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| provider_name | VARCHAR(200) | Tên đơn vị vận chuyển |
| total_shipments | INTEGER | Tổng số đơn giao |
| avg_delivery_days | DECIMAL(10,2) | Số ngày giao TB |
| success_rate | DECIMAL(5,2) | Tỷ lệ giao thành công (%) |
| avg_shipping_cost | DECIMAL(15,2) | Chi phí ship TB |

```sql
SELECT
    dsp.provider_name,
    COUNT(*) as total_shipments,
    AVG(EXTRACT(DAY FROM (s.delivered_at - s.created_on))) as avg_delivery_days,
    COUNT(CASE WHEN s.status = 'delivered' THEN 1 END) * 100.0 / COUNT(*) as success_rate,
    AVG(s.delivery_fee) as avg_shipping_cost
FROM shipments s
JOIN delivery_service_providers dsp
    ON s.delivery_service_provider_id = dsp.provider_id
GROUP BY dsp.provider_id, dsp.provider_name
ORDER BY total_shipments DESC
```

---

### C. Returns & Refunds

#### Chart: Return Rate Trend (Line Chart)

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| week | DATE | Tuần (đầu tuần) |
| total_orders | INTEGER | Tổng số đơn hàng |
| orders_with_returns | INTEGER | Số đơn có trả hàng |
| return_rate | DECIMAL(5,2) | Tỷ lệ trả hàng (%) |

```sql
SELECT
    DATE_TRUNC('week', created_on) as week,
    COUNT(DISTINCT order_id) as total_orders,
    COUNT(DISTINCT CASE WHEN return_status != 'unreturned'
          THEN order_id END) as orders_with_returns,
    COUNT(DISTINCT CASE WHEN return_status != 'unreturned'
          THEN order_id END) * 100.0 / COUNT(DISTINCT order_id) as return_rate
FROM orders
GROUP BY week
ORDER BY week
```

#### Table: Return Reasons

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| reason | VARCHAR(500) | Lý do trả hàng |
| return_count | INTEGER | Số lượng trả hàng |
| total_refunded | DECIMAL(15,2) | Tổng hoàn tiền |
| avg_refund | DECIMAL(15,2) | Hoàn tiền TB |

```sql
SELECT
    reason,
    COUNT(*) as return_count,
    SUM(refund_amount) as total_refunded,
    AVG(refund_amount) as avg_refund
FROM order_returns
GROUP BY reason
ORDER BY return_count DESC
```

---

### D. Staff Performance

#### Table: Sales by Staff

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| account_name | VARCHAR(200) | Tên nhân viên |
| role | VARCHAR(100) | Vai trò |
| total_orders | INTEGER | Tổng số đơn hàng |
| total_revenue | DECIMAL(15,2) | Tổng doanh thu |
| avg_order_value | DECIMAL(15,2) | Giá trị đơn TB |
| unique_customers | INTEGER | Số khách hàng unique |

```sql
SELECT
    a.account_name,
    a.role,
    COUNT(DISTINCT o.order_id) as total_orders,
    SUM(o.total) as total_revenue,
    AVG(o.total) as avg_order_value,
    COUNT(DISTINCT o.customer_id) as unique_customers
FROM orders o
JOIN accounts a ON o.account_id = a.account_id
GROUP BY a.account_id, a.account_name, a.role
ORDER BY total_revenue DESC
```

---

## 🎯 7. SPECIALIZED REPORTS

### A. Daily Sales Report

#### Comprehensive Daily Summary

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| order_date | DATE | Ngày đặt hàng |
| total_orders | INTEGER | Tổng số đơn hàng |
| gross_revenue | DECIMAL(15,2) | Doanh thu gộp |
| net_revenue | DECIMAL(15,2) | Doanh thu ròng |
| avg_order_value | DECIMAL(15,2) | Giá trị đơn TB |
| unique_customers | INTEGER | Số khách hàng unique |
| tax_collected | DECIMAL(15,2) | Thuế thu |
| discounts_given | DECIMAL(15,2) | Giảm giá |

```sql
WITH daily_stats AS (
    SELECT
        DATE(created_on) as order_date,
        COUNT(*) as total_orders,
        SUM(total) as gross_revenue,
        SUM(total - total_discount - COALESCE(return_amount, 0)) as net_revenue,
        AVG(total) as avg_order_value,
        COUNT(DISTINCT customer_id) as unique_customers,
        SUM(total_tax) as tax_collected,
        SUM(total_discount) as discounts_given
    FROM orders
    WHERE DATE(created_on) = CURRENT_DATE - INTERVAL '1 day'
)
SELECT * FROM daily_stats
```

#### Hourly Breakdown

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| hour | INTEGER | Giờ trong ngày (0-23) |
| orders | INTEGER | Số lượng đơn hàng |
| revenue | DECIMAL(15,2) | Doanh thu |

```sql
SELECT
    EXTRACT(HOUR FROM created_on) as hour,
    COUNT(*) as orders,
    SUM(total) as revenue
FROM orders
WHERE DATE(created_on) = CURRENT_DATE - INTERVAL '1 day'
GROUP BY hour
ORDER BY hour
```

#### Top Products of the Day

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| product_name | VARCHAR(500) | Tên sản phẩm |
| units_sold | INTEGER | Số lượng bán |
| revenue | DECIMAL(15,2) | Doanh thu |

```sql
SELECT
    p.product_name,
    SUM(oli.quantity) as units_sold,
    SUM(oli.line_amount) as revenue
FROM order_line_items oli
JOIN products p ON oli.product_id = p.product_id
JOIN orders o ON oli.order_id = o.order_id
WHERE DATE(o.created_on) = CURRENT_DATE - INTERVAL '1 day'
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 10
```

---

### B. Monthly Business Review

#### Monthly KPIs

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| month | DATE | Tháng (đầu tháng) |
| total_orders | INTEGER | Tổng số đơn hàng |
| revenue | DECIMAL(15,2) | Doanh thu |
| customers | INTEGER | Số khách hàng |
| aov | DECIMAL(15,2) | Giá trị đơn TB |
| discounts | DECIMAL(15,2) | Tổng giảm giá |
| returns | INTEGER | Số đơn trả hàng |

```sql
SELECT
    DATE_TRUNC('month', created_on) as month,
    COUNT(*) as total_orders,
    SUM(total) as revenue,
    COUNT(DISTINCT customer_id) as customers,
    AVG(total) as aov,
    SUM(total_discount) as discounts,
    COUNT(CASE WHEN return_status != 'unreturned' THEN 1 END) as returns
FROM orders
WHERE created_on >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 months')
GROUP BY month
ORDER BY month
```

#### YoY Comparison

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| month | INTEGER | Tháng (1-12) |
| year | INTEGER | Năm |
| revenue | DECIMAL(15,2) | Doanh thu |
| prev_year_revenue | DECIMAL(15,2) | Doanh thu năm trước |
| yoy_growth | DECIMAL(5,2) | Tăng trưởng YoY (%) |

```sql
SELECT
    EXTRACT(MONTH FROM created_on) as month,
    EXTRACT(YEAR FROM created_on) as year,
    SUM(total) as revenue,
    LAG(SUM(total)) OVER (PARTITION BY EXTRACT(MONTH FROM created_on)
                          ORDER BY EXTRACT(YEAR FROM created_on)) as prev_year_revenue,
    (SUM(total) - LAG(SUM(total)) OVER (PARTITION BY EXTRACT(MONTH FROM created_on)
                                        ORDER BY EXTRACT(YEAR FROM created_on))) * 100.0 /
    NULLIF(LAG(SUM(total)) OVER (PARTITION BY EXTRACT(MONTH FROM created_on)
                                  ORDER BY EXTRACT(YEAR FROM created_on)), 0) as yoy_growth
FROM orders
GROUP BY month, year
ORDER BY year, month
```

---

### C. Customer Lifetime Analysis

#### CLV Calculation

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| customer_id | INTEGER | ID khách hàng |
| customer_name | VARCHAR(200) | Tên khách hàng |
| customer_group | VARCHAR(100) | Nhóm khách hàng |
| first_order_date | TIMESTAMP | Ngày đơn đầu tiên |
| last_order_date | TIMESTAMP | Ngày đơn cuối |
| total_orders | INTEGER | Tổng số đơn |
| total_spent | DECIMAL(15,2) | Tổng chi tiêu |
| avg_order_value | DECIMAL(15,2) | Giá trị đơn TB |
| customer_age_days | INTEGER | Tuổi KH (ngày) |
| annualized_value | DECIMAL(15,2) | Giá trị hàng năm |
| purchase_frequency | DECIMAL(10,2) | Tần suất mua/năm |
| value_segment | VARCHAR(20) | Phân khúc giá trị |

```sql
WITH customer_metrics AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.customer_group,
        MIN(o.created_on) as first_order_date,
        MAX(o.created_on) as last_order_date,
        COUNT(o.order_id) as total_orders,
        SUM(o.total) as total_spent,
        AVG(o.total) as avg_order_value,
        DATEDIFF(day, MIN(o.created_on), MAX(o.created_on)) as customer_age_days
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.customer_name, c.customer_group
)
SELECT
    *,
    total_spent / NULLIF(customer_age_days, 0) * 365 as annualized_value,
    total_orders * 1.0 / NULLIF(customer_age_days, 0) * 365 as purchase_frequency,
    CASE
        WHEN total_spent > 5000 THEN 'VIP'
        WHEN total_spent > 1000 THEN 'High Value'
        WHEN total_spent > 500 THEN 'Medium Value'
        ELSE 'Low Value'
    END as value_segment
FROM customer_metrics
ORDER BY total_spent DESC
```

---

### D. Inventory Health Report

#### Stock Status Summary

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| inventory_status | VARCHAR(50) | Trạng thái tồn kho |
| product_count | INTEGER | Số lượng sản phẩm |
| inventory_value | DECIMAL(15,2) | Giá trị tồn kho |

```sql
SELECT
    inventory_status,
    COUNT(*) as product_count,
    SUM(quantity * cost_price) as inventory_value
FROM products
GROUP BY inventory_status
```

#### Aging Inventory

**Query Output Schema:**
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| product_name | VARCHAR(500) | Tên sản phẩm |
| sku | VARCHAR(100) | Mã SKU |
| current_stock | INTEGER | Tồn kho hiện tại |
| last_sold_date | TIMESTAMP | Ngày bán cuối |
| days_since_last_sale | INTEGER | Số ngày kể từ lần bán cuối |
| inventory_value | DECIMAL(15,2) | Giá trị tồn kho |

```sql
SELECT
    p.product_name,
    p.sku,
    pv.quantity as current_stock,
    MAX(o.created_on) as last_sold_date,
    DATEDIFF(day, MAX(o.created_on), CURRENT_DATE) as days_since_last_sale,
    pv.quantity * p.cost_price as inventory_value
FROM products p
JOIN product_variants pv ON p.product_id = pv.product_id
LEFT JOIN order_line_items oli ON pv.variant_id = oli.variant_id
LEFT JOIN orders o ON oli.order_id = o.order_id
GROUP BY p.product_id, p.product_name, p.sku, pv.quantity, p.cost_price
HAVING days_since_last_sale > 90 OR MAX(o.created_on) IS NULL
ORDER BY inventory_value DESC
```

---

## 📅 8. COMMON DASHBOARD LAYOUTS

### Executive Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                    EXECUTIVE DASHBOARD                       │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ Revenue      │ Orders       │ AOV          │ Customers     │
│ $1.2M (+15%) │ 15,234 (+8%) │ $79 (+6%)    │ 8,901 (+12%)  │
├──────────────┴──────────────┴──────────────┴───────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Revenue Trend (Last 30 Days)                    │    │
│  │     [Line Chart: Daily Revenue]                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │ Top Products        │  │ Channel Performance        │   │
│  │ [Table]             │  │ [Pie Chart]                │   │
│  └─────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Customer Segments (RFM)                              │   │
│  │ [Scatter Plot]                                       │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Operations Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                   OPERATIONS DASHBOARD                       │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ Pending      │ Processing   │ Shipped      │ Avg Delivery  │
│ 234 orders   │ 156 orders   │ 89 today     │ 2.3 days      │
├──────────────┴──────────────┴──────────────┴───────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Order Status Funnel                             │    │
│  │     [Funnel Chart]                                  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │ Fulfillment Queue   │  │ Shipping Performance       │   │
│  │ [Table: Priority]   │  │ [Bar Chart: Carriers]      │   │
│  └─────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Inventory Alerts                                     │   │
│  │ [Table: Low Stock, Out of Stock]                     │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Marketing Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                   MARKETING DASHBOARD                        │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ CAC          │ CLV          │ ROAS         │ Conv Rate     │
│ $45          │ $450         │ 3.2x         │ 2.3%          │
├──────────────┴──────────────┴──────────────┴───────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Customer Acquisition Trend                      │    │
│  │     [Stacked Bar: New vs Returning]                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │ Campaign ROI        │  │ Channel Attribution        │   │
│  │ [Table]             │  │ [Sankey Diagram]           │   │
│  └─────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Cohort Retention                                     │   │
│  │ [Heatmap]                                            │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Tổng Kết

### Top 20 Must-Have Charts cho E-commerce

1. **Daily/Weekly/Monthly Revenue Trend** (Line Chart)
2. **Revenue by Channel** (Pie/Donut Chart)
3. **Order Status Funnel** (Funnel Chart)
4. **Top Products by Revenue** (Bar Chart)
5. **Customer Acquisition Trend** (Stacked Bar)
6. **RFM Segmentation** (Scatter Plot)
7. **Cohort Retention** (Heatmap)
8. **Product Category Performance** (Treemap)
9. **Hourly Sales Pattern** (Heatmap)
10. **Year-over-Year Comparison** (Line Chart)
11. **Revenue Waterfall** (Waterfall Chart)
12. **Payment Methods Distribution** (Pie Chart)
13. **Delivery Time Distribution** (Histogram)
14. **Return Rate Trend** (Line Chart)
15. **Inventory Status** (Gauge Chart)
16. **Sales by Location** (Map Chart)
17. **Discount Impact** (Combo Chart)
18. **Profit Margin by Category** (Bar Chart)
19. **Customer Lifetime Value Distribution** (Histogram)
20. **Fulfillment Performance** (KPI Cards + Line Chart)

### Top 15 Must-Have Tables

1. **Daily Sales Summary**
2. **Top Performing Products**
3. **Customer Segments Analysis**
4. **Channel Performance Comparison**
5. **Top Customers by Revenue**
6. **Category Performance**
7. **Staff Performance**
8. **Carrier Performance**
9. **Return Reasons Analysis**
10. **Promotion Performance**
11. **Slow-Moving Inventory**
12. **Order Fulfillment Queue**
13. **Revenue Components Breakdown**
14. **Customer Cohort Analysis**
15. **Product Velocity Report**

---

**Note:** Tất cả các metrics, charts và tables này đều có thể build được từ data schema của Sapo system. Mỗi SQL query đều có table mô tả output schema để dễ dàng mapping vào visualization tools (Metabase, Tableau, Power BI, etc.)
