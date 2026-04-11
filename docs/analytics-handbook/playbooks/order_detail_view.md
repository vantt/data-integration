# Order Detail View Playbook

> **Domain:** [Sales](../domains/sales.md), [Finance](../domains/finance.md)
> **Audience:** Sales Ops, CS Reps, Store Managers, Finance
> **Cadence:** On-demand (reactive lookup, not scheduled review)
> **Time Budget:** 30s to find order, 1 min to read detail

## Purpose

Cho phep tra cuu nhanh bat ky don hang nao: xem toan bo thong tin don, line items, thanh toan, va cac metrics kinh doanh rieng cho don do (margin, discount rate, thoi gian xu ly).

## Use Cases

1. **Khach hang hoi trang thai don** — CS tra order_code, xem status + payment + fulfillment
2. **Doi soat tai chinh** — Finance tra don, xem gross/net/discount/tax/COGS/margin
3. **Kiem tra van hanh** — Ops xem thoi gian xu ly, ship same day hay khong
4. **Phan tich don le** — Manager xem 1 don cu the de hieu context (vi sao discount cao, vi sao cancelled)

## Reading Flow

1. **Tim don** — Dung filters (date range, order code, channel, status) de loc listing
2. **Xem listing** — Scan bang don hang, tim don can xem
3. **Click vao don** — Chuyen sang detail view cua don do
4. **Doc detail** — 3 phan: Order Summary (header metrics), Line Items (san pham), Payments + Economics

## Action Triggers

| Signal | Condition | Owner | Action |
|--------|-----------|-------|--------|
| Don cancelled | status = CANCELLED | CS Lead | Xac minh ly do huy, lien he khach |
| Discount > 30% gross | discount_rate > 0.3 | Sales Mgr | Kiem tra co dung chinh sach khong |
| Pending > 48h | status = OPEN, age > 48h | Ops Lead | Escalate, lien he van chuyen |
| Negative margin | channel_net_margin_pct < 0 | Finance | Review channel economics, bao cao CFO |

## Data Sources

- `fact_orders` — Order header
- `fact_sales` — Line items (product grain)
- `fact_payments` — Payment transactions
- `fact_order_economics` — COGS, margin, platform fees
- `dim_channels`, `dim_branch_location`, `dim_staff`, `dim_products`, `dim_order_status`, `dim_geography`
