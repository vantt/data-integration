# Playbook: Orders List Reconciliation

## Overview

- **Audience:** Store Managers, Sales Ops, Data Team
- **Goal:** Verify BI order data matches Sapo source — detect missing orders, amount mismatches, and anomalies. KPIs with DoD trends, status/payment breakdowns, channel distribution, flagged alerts, and full detail table.
- **Cadence:** Daily morning/evening, 10-15 min
- **Archetype:** Operational Cockpit
- **Tool:** metabase
- **Collection:** `Operations` > `Daily Monitoring`
- **Design Spec:** [Order Listing](../designs/order_listing.md)
- **Blueprint:** [Order Listing](../blueprints/metabase/order_listing.md)

## Key Questions

1. **Count match:** Tong so don trong BI co khop voi Sapo khong?
2. **Revenue match:** Net Revenue, Gross Revenue, Total Collected co dung so voi Sapo?
3. **Status distribution:** Phan bo trang thai don co bat thuong (qua nhieu CANCELLED/OPEN)?
4. **Channel completeness:** Tat ca kenh ban deu co du lieu — kenh nao bi mat don?
5. **Anomalies:** Co don 100% discount, revenue am, don completed nhung chua thanh toan?

## Dashboard Structure (3 Tabs)

All 3 tabs share **byte-identical layout** — only the date predicate differs. This is a non-negotiable invariant (Tab Parity rule — see design spec).

| Tab | Date Scope | Comparison | Filter |
|-----|-----------|------------|--------|
| **Today** | `current_date` (VN tz) | vs Hôm qua (DoD) | None (fixed) |
| **Yesterday** | `current_date - 1` (VN tz) | vs Hôm trước (DoD) | None (fixed) |
| **By Date** | User-selected | vs previous day (DoD) | Date picker (default: today) |

**Drift prevention:** Any add/edit/delete on one tab MUST be mirrored on the other two in the same commit. The blueprint deploy script is the single source of truth — never hand-edit in the Metabase UI. A drift incident was identified and fixed on 2026-04-09 (Today had section annotations, Yesterday and By Date did not).

## Tab Layout (identical per tab)

### Section: Reconciliation Affordance (Row A)

| Card | Type | Notes |
|------|------|-------|
| **Reconciliation Checklist** | Text callout (bordered) | Explicit 5-step reconciliation workflow on-screen — user never has to remember the playbook |
| **Data Freshness** | Single-value-label (scalar) | `MAX(fact_orders.updated_at)` age, conditional color: green <2h, amber 2-6h, red >6h |

### Section: Tong Quan Don Hang (KPIs)

**Row B — Primary KPIs (with DoD trend):**

| Card | Type | Metric Reference | Color | Notes |
|------|------|------------------|-------|-------|
| **Total Orders** | Scalar + DoD | [Total Orders](../domains/sales.md#4-total-orders) | primary | All orders including cancelled |
| **Net Revenue** | Scalar + DoD | [Net Revenue](../domains/sales.md#2-net-revenue) | primary | Excludes CANCELLED/Voided |
| **Total Collected** | Scalar + DoD | [Total Collected](../domains/sales.md) | primary | Accounting reconciliation — actual cash received |
| **Gross Revenue** | Scalar + DoD | [Gross Revenue](../domains/sales.md#1-gross-revenue) | muted | Pre-discount reference total |

**Row C — Alert KPIs (with DoD trend):**

| Card | Type | Metric Reference | Color | Notes |
|------|------|------------------|-------|-------|
| **Total Discount** | Scalar + DoD | [Discount Impact](../domains/sales.md#13-discount-impact) | warning | Monitor discount spending |
| **Cancelled Orders** | Scalar + DoD | — | negative | Exception count, `status = 'CANCELLED'` |
| **Returns** | Scalar + DoD | [Return Count](../domains/sales.md#3-return-rate--count) | negative | `fulfillment_status = 'RETURNED'` |

### Section: Phan Bo Theo Chieu (Breakdowns)

| Card | Type | Notes |
|------|------|-------|
| **Orders by Status** | Donut (pie) | Part-to-whole status distribution — spot OPEN/CANCELLED spikes |
| **Orders by Payment Status** | Donut (pie) | Payment reconciliation — unpaid/refunded detection |
| **Orders by Channel** | Horizontal bar | Revenue by channel ranked — detect missing channels |

### Section: Canh Bao (Alerts)

| Card | Type | Notes |
|------|------|-------|
| **Flagged Orders** | Table | Anomalous orders: 100% Discount, Negative Revenue, Discount > Gross, Completed but Unpaid, Refunded. Columns: Order Code, Status, Channel, Gross, Discount, Net Revenue, Collected, Flag |

### Section: Chi Tiet Doi Soat (Detail)

| Card | Type | Notes |
|------|------|-------|
| **Order Detail List** | Table | Full order listing for line-by-line reconciliation. Columns: Order Code, Time, Status, Gross, Discount, Net Revenue, Tax, Collected, Channel, Payment, Fulfillment, Customer, Phone, Store |

## Filters

| Filter | Tab | Type | Default | Notes |
|--------|-----|------|---------|-------|
| Date | By Date only | `date/single` | today | Today/Yesterday tabs have fixed dates, no filter |

**Business constraint:** Revenue KPIs and Channel breakdown exclude `status NOT IN ('CANCELLED', 'Voided')`.

## Data Lineage

- **Core Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — order-level metrics (revenue, status, timestamps)
- **Dimensions:** `dim_channels` (channel names), `dim_customers` (customer name/phone), `dim_branch_location` (store/branch)

## Reconciliation Workflow

0. **Check Data Freshness first.** If > 2h, STOP — data may be mid-ingest. Check Dagster status before reconciling.
1. Open **Today** tab (or Yesterday for morning review of prior day).
2. Note **Total Orders** count and **Net Revenue** — compare with Sapo Admin > Đơn hàng for same date.
3. Check **DoD arrows** on all KPIs — unusual swings indicate data issues or business anomalies.
4. Scan **Orders by Status** donut — high CANCELLED % may signal ingestion or operational issues.
5. Scan **Orders by Channel** bar — missing channel = potential ingestion gap.
6. Review **Flagged Orders** table — investigate any 100% Discount, Negative Revenue, or Completed-but-Unpaid flags.
7. Use **Order Detail List** for line-by-line cross-check against Sapo if discrepancies found.
8. For historical dates, switch to **By Date** tab and select the target date.

## How to Read This Dashboard

1. **CONTEXT:** Dashboard doi soat don hang hang ngay — xac minh BI data khop Sapo.
2. **KEY FINDING:** Nhin Total Orders + Net Revenue (Row B) truoc. DoD arrow xanh = on dinh. Do = can kiem tra.
3. **EVIDENCE:** Donut charts cho biet phan bo trang thai. Bar chart cho biet phan bo kenh. Bat thuong = phan bo lech so voi ngay thuong.
4. **IMPLICATIONS:** Neu count lech > 0 voi Sapo → co ingestion gap. Neu Flagged Orders nhieu → can review tung don.
5. **ACTIONS:** Don bat thuong tu Canh Bao table → chuyen cho team xu ly. Ingestion gap → bao Data Team.
