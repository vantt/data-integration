---
title: Order Detail View
archetype: Operational Cockpit
status: final
last_modified: 2026-04-11
domain_refs: [domains/sales.md, domains/finance.md]
---

## Design Spec: Order Detail View

### Brief

- **Audience:** CS Reps, Sales Ops, Store Managers, Finance — tra cuu on-demand
- **Time budget:** 30s tim don, 1 min doc detail
- **Primary question:** Don hang X trang thai gi, chi tiet ra sao, loi/lo the nao?
- **Decision enabled:** Xu ly khieu nai, doi soat tai chinh, escalate don pending
- **Comparison frame:** Khong co — day la lookup, khong phai trend analysis
- **Archetype:** Operational Cockpit (lookup variant)
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/finance.md](../domains/finance.md)
- **Playbook:** [order_detail_view.md](../playbooks/order_detail_view.md)

### Architecture

Dashboard nay khac voi dashboard analytics thong thuong — no gom **2 phan rieng biet**:

1. **Order Listing** (Dashboard) — bang danh sach don hang voi filters, click-through link
2. **Order Detail** (Dashboard) — nhan `order_id` parameter, hien thi full detail

Ly do tach 2 dashboard: Metabase khong ho tro master-detail trong 1 dashboard. Pattern la: listing card co custom column link dan sang detail dashboard voi `?order_id={{value}}`.

### Constraints & Filters

**Part 1 — Order Listing:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Today | All cards | Gioi han pham vi tim kiem |
| Order Code | string/contains | (empty) | Listing | Tim nhanh theo ma don |
| Channel | string/= | All | Listing | Loc theo kenh ban |
| Status | string/= | All | Listing | Loc theo trang thai |
| Branch | string/= | All | Listing | Loc theo chi nhanh |

**Part 2 — Order Detail:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| order_id | id (hidden, passed via URL) | (required) | All cards | Xac dinh don hang can xem |

### Views

**Part 1 — Order Listing:** Single view, 1 card (data table)

**Part 2 — Order Detail:** Single view, 4 sections

---

### Part 1: Order Listing

#### Composition

| # | Row | Card | Role | Viz Type | Size | Communication |
|---|-----|------|------|----------|------|---------------|
| 1 | A | Order Listing | detail | data-table | full-width x tall | Bang don hang, click de xem chi tiet |

**Listing Columns:**

| Column | Source | Note |
|--------|--------|------|
| Order Code | fact_orders.order_code | Link sang detail dashboard |
| Date | fact_orders.ordered_at | Format: DD/MM HH:mm |
| Channel | dim_channels.channel_name | |
| Branch | dim_branch_location.branch_location_name | |
| Status | dim_order_status.status_code | Conditional formatting |
| Payment | fact_orders.payment_status | |
| Fulfillment | fact_orders.fulfillment_status | |
| Net Revenue | fact_orders.net_revenue | Format: currency VND |
| Total Collected | fact_orders.total_collected | Format: currency VND |
| Staff | dim_staff.full_name | |
| Detail | (custom column) | Link icon → Order Detail dashboard |

**Click-through:** Column "Order Code" hoac "Detail" link sang: `/dashboard/XX?order_id={{order_id}}`

---

### Part 2: Order Detail

#### SQL Data Sources

Moi card la 1 native SQL question nhan `{{order_id}}` parameter.

#### Composition

| # | Row | Card | Role | Viz Type | Size | Communication |
|---|-----|------|------|----------|------|---------------|
| 1 | A | "Order Summary" | annotation | text-annotation | full-width x minimal | Section heading |
| 2 | B | Order Header | hero | data-table (single row, pivoted) | full-width x medium | Thong tin chinh cua don |
| 3 | C | "Financials" | annotation | text-annotation | full-width x minimal | Section heading |
| 4 | D | Order Economics | supporting | data-table (single row, pivoted) | full-width x medium | Metrics tai chinh rieng cho don |
| 5 | E | "Line Items" | annotation | text-annotation | full-width x minimal | Section heading |
| 6 | F | Line Items Table | detail | data-table | full-width x tall | Danh sach san pham trong don |
| 7 | G | "Payments" | annotation | text-annotation | full-width x minimal | Section heading |
| 8 | H | Payments Table | detail | data-table | full-width x medium | Cac giao dich thanh toan |

#### Card Details

**Card 2 — Order Header** (pivoted single-row table)

| Field | Source | Format |
|-------|--------|--------|
| Order Code | fact_orders.order_code | |
| Order Date | fact_orders.ordered_at | DD/MM/YYYY HH:mm |
| Status | dim_order_status.status_code | |
| Payment Status | fact_orders.payment_status | |
| Fulfillment Status | fact_orders.fulfillment_status | |
| Channel | dim_channels.channel_name | |
| Branch | dim_branch_location.branch_location_name | |
| Staff | dim_staff.full_name | |
| Province | dim_geography.province | |
| District | dim_geography.district | |
| First Shipped At | fact_orders.first_shipped_at | DD/MM/YYYY HH:mm |
| Hours to First Ship | DATEDIFF(hour, ordered_at, first_shipped_at) | |
| Hours to Complete | fact_orders.time_to_complete_hours | |

**Card 4 — Order Economics** (pivoted single-row table)

| Field | Source | Format |
|-------|--------|--------|
| Gross Revenue | fact_orders.gross_revenue | VND |
| Discount | fact_orders.discount_amount | VND |
| Discount Rate | discount_amount / NULLIF(gross_revenue, 0) | % |
| Net Revenue | fact_orders.net_revenue | VND |
| Tax | fact_orders.vat_amount | VND |
| Total Collected | fact_orders.total_collected | VND |
| COGS | fact_order_economics.cogs_amount | VND, NULL = chua co |
| Gross Profit | fact_order_economics.gross_profit | VND |
| Gross Margin | fact_order_economics.gross_margin_pct | % |
| Shopee Platform Fees | fact_order_economics.shopee_platform_fees | VND, NULL = non-Shopee |
| Channel Net Profit | fact_order_economics.channel_net_profit | VND |
| Channel Net Margin | fact_order_economics.channel_net_margin_pct | % |

**Card 6 — Line Items Table**

| Column | Source | Format |
|--------|--------|--------|
| Product | dim_products.product_name | |
| Variant | dim_products.variant_name | |
| SKU | dim_products.sku | |
| Qty | fact_sales.quantity | |
| Unit Price | fact_sales.net_revenue / fact_sales.quantity | VND |
| Revenue | fact_sales.net_revenue | VND |
| Discount | fact_sales.discount_amount | VND |
| Distributed Discount | fact_sales.distributed_discount_amount | VND |
| Weight (g) | fact_sales.weight_grams | |

**Card 8 — Payments Table**

| Column | Source | Format |
|--------|--------|--------|
| Payment Method | dim_payment_methods.payment_method_name | |
| Amount | fact_payments.amount | VND |
| Status | fact_payments.status | |
| Payment Time | fact_payments.payment_timestamp | DD/MM/YYYY HH:mm |
| Paid On | fact_payments.paid_on | DD/MM/YYYY HH:mm |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Order Header | Pending lau | status=OPEN, hours > 48 | Escalate van chuyen |
| Order Header | Cancelled | status=CANCELLED | Xac minh ly do, lien he khach |
| Order Economics | Discount cao | discount_rate > 30% | Kiem tra chinh sach promotion |
| Order Economics | Margin am | channel_net_margin_pct < 0 | Review kenh, bao cao Finance |
| Order Economics | Chua co COGS | cogs_amount IS NULL | Doi MISA sync hoac kiem tra mapping |
