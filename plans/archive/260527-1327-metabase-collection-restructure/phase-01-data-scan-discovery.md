# Phase 01: Data Scan & Discovery — P&L Domain Opportunities

> **Status:** ✅ DONE (scan completed)
> **Tool:** Explore agent — quét `transformation/marts/`, `docs/analytics-handbook/blueprints/`, `docs/analytics-handbook/domains/`
> **Output:** Driver cho Finance top-level collection mới

---

## Context

User flag: "rất nhiều data mới liên quan đến P&L". Trước khi restructure cần biết:
1. Có mart P&L mới chưa có dashboard không?
2. Có audience chưa được serve không (CFO/FP&A/Accounting)?
3. Top dashboard nên thêm để tận dụng data mới?

## Findings

### 1. Marts P&L hiện có

| Mart | Mô tả | Tuổi |
|:---|:---|:---|
| `fact_order_economics` | Per-order P&L: Sapo revenue + MISA COGS + Shopee platform fees | NEW (2026-05-27) |
| `fact_order_costs` | Long-format cost ledger (1 row/order/cost_type): COGS, platform fees, taxes, vouchers | **NEW (2026-05-27)** |
| `fact_order_returns` | Return events với refund impact | **NEW (2026-05-27)** |
| `fact_orders` | Base revenue facts | Core |
| `int_misa_sales_lines` | Per-invoice-line COGS + margin breakdown | Core |

### 2. Coverage gap (mart → dashboard)

| Mart | Dashboard hiện có | Status |
|:---|:---|:---|
| `fact_order_economics` | Finance P&L Dashboard, Order Profitability | ✅ |
| `int_misa_sales_lines` | Product Profitability, Channel Profitability Monthly | ✅ |
| `fact_order_costs` | — | **⚠️ UNCOVERED** |
| `fact_order_returns` | — | **⚠️ UNCOVERED** |

→ 2 mart mới (cost ledger + returns) chưa có dashboard nào tận dụng. Cost breakdown và return impact là **blind spot** hiện tại.

### 3. Audience chưa được serve

Hiện 36 dashboards cover: CEO, Marketing, Store Manager, Sales Ops, B2B.

| Audience | Tín hiệu | Hiện được serve? |
|:---|:---|:---|
| **CFO** | Có Finance P&L Dashboard nhưng ở Executive (lẫn CEO board) | ⚠️ Partial — không có folder riêng |
| **FP&A / Planning** | Không có budget vs actuals, variance, headcount cost | ❌ |
| **Accounting (Recon)** | Có recon assets (`recon_sapo_orders_daily`, `recon_misa_daily`) nhưng không có dashboard | ❌ |
| **Merchandising/Inventory** | COGS per SKU có sẵn nhưng không có view inventory-cost combined | ❌ |
| **Cost Center owners** | Không có breakdown by org unit | ❌ |

### 4. Top 5 dashboard đề xuất

| P | Dashboard | Audience | Mart Source | Value |
|:---|:---|:---|:---|:---|
| P0 | Cost Ledger Analyzer | CFO, Accounting | `fact_order_costs` | Explode platform fees, COGS, voucher impact by channel |
| P0 | Return Impact Analysis | CEO, CFO, Sales Ops | `fact_order_returns` | Refund liability + return rate trends + impact on channel profit |
| P1 | Channel P&L Deep Dive | Finance, Sales Director | `fact_order_economics + int_misa_sales_lines` | Gross margin vs fees vs net per channel — identify loss-making |
| P1 | Product Cost-to-Margin Heatmap | Merchandising, Finance | `int_misa_sales_lines` | SKU margin với COGS variance |
| P2 | Accounting Reconciliation Cockpit | Accounting, CFO | `fact_orders` + recon | Daily Sapo↔MISA↔Shopee reconciliation |

(Chi tiết spec ở [phase-05](./phase-05-new-finance-dashboards.md))

---

## Quyết định kiến trúc rút ra từ scan

### Tạo `Finance` top-level collection (NEW)

**Lý do:**
1. **Trigger từ doc gốc:** `collection_organization.md` §6 quy định "Xuất hiện domain mới (Finance, Logistics) có audience riêng → Tạo top-level collection mới". Đủ điều kiện.
2. **Mart explosion:** 3 mart mới cùng ngày + 5 dashboard tiềm năng → đã quá đủ critical mass.
3. **Audience tách biệt:** CFO ≠ CEO (CEO strategic, CFO financial detail). Hiện đang lẫn vào Executive.
4. **Loose threshold rule:** Executive hiện 10 boards, sẽ vẫn còn 6 sau khi tách 4 profitability boards.

**Finance collection sẽ chứa (8 boards eventual):**
- Existing (move từ Executive):
  - Finance P&L Dashboard [All]
  - Order Profitability [All]
  - Product Profitability [All]
- New (Phase 05 backlog):
  - Cost Ledger Analyzer [All]
  - Return Impact Analysis [All]
  - Channel P&L Deep Dive [Cross]
  - Product Cost-to-Margin Heatmap [Cross]
  - Accounting Reconciliation Cockpit [Internal]

### Channel Profitability Monthly → Analytics

Là cross-segment comparison thuần → Layer 3 → `Analytics` collection (theo `report_segmentation.md`).

---

## Unresolved questions

1. **CFO có thực sự exist trong team?** Hay Finance owner là Founder/CEO kiêm? → Ảnh hưởng việc Finance collection có dedicated owner hay không.
2. Recon assets có bao giờ được hỏi đến qua dashboard? Hay Accounting team hiện đang dùng raw query?
3. FP&A budget data có ở dbt không? (Scan chưa tìm thấy budget/target/forecast tables) — nếu có thì thêm 1 board nữa.

## Next Steps

→ Phase 02: archive duplicates (cần xong trước khi move qua Finance)
→ Phase 03: tạo `Finance` collection + 2 sub-collection mới `Operations > Logistics` và `Operations > Data Platform`
