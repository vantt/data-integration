# Kiểm kê Analytics Handbook và đề xuất Standard Report Catalog

> Ngày 2026-10-14. Do agent Explore lập (chỉ đọc), controller ghi ra file. Phân loại dựa trên dòng Audience, tiêu đề, mô tả và grep bảng nguồn; không đọc toàn văn từng file. Các ô "cần xác minh" cần kiểm tra thêm.

Đường dẫn gốc: `docs/analytics-handbook/`

Quy ước: **STD** = STANDARD (mọi SME), **STD-cfg** = STANDARD-with-config (cần target/budget/scope mapping), **FJ** = FJ-only, **DUP** = trùng lặp. Engine: MB = Metabase, EV = Evidence, RL = Rill, PB = playbook, DS = design spec.

Số lượng: designs 21 spec + README; playbooks 34 (+ `playbooks/rill/` 3 + README); blueprints/metabase 45; blueprints/evidence 2; blueprints/rill 4 yaml; evidence/pages 4.

## 1. Bảng kiểm kê (gom theo họ báo cáo)

| # | Họ báo cáo (artifact) | Persona | Câu hỏi | Data cần | Phân loại | Engine |
|---|---|---|---|---|---|---|
| 1 | CEO Weekly Pulse (`designs/`, `playbooks/`, `blueprints/metabase/ceo_weekly_pulse`, `evidence/pages/ceo-weekly-pulse`) | CEO | Doanh thu tuần so target, sức khỏe kinh doanh | sapo; target; MISA vài tile; loại US | STD-cfg | DS, PB, MB, EV |
| 2 | CEO Monthly Scorecard | CEO, Board | KPI tháng so kế hoạch | sapo, misa, target | STD-cfg | DS, PB, MB |
| 3 | Sales Monthly Review | Sales Dir, CFO | Đánh giá tháng theo kênh/vùng | sapo, target | STD-cfg | DS, PB, MB |
| 4 | Finance P&L | CFO, CEO | Biên lợi nhuận gộp, chi phí sàn | sapo + misa + shopee | STD tầng finance (cần xác minh) | DS, PB, MB |
| 5 | Channel Profitability Monthly | CEO, Finance | Lợi nhuận theo kênh | sapo, misa, shopee | STD-cfg | DS, PB, MB |
| 6 | Channel P&L Deep Dive (`finance_channel_pl`, `channel_p_l_deep_dive`) | Finance Dir | Kênh nào lỗ sau mọi chi phí | sapo, misa, shopee, ads | **DUP** với #5 | PB, MB ×2 |
| 7 | Finance Cashflow | CEO, CFO, KTT | Dòng tiền, thanh khoản | misa, ngân hàng, sapo | STD-cfg | DS, PB, MB, EV |
| 8 | Budget vs Actual (`finance_cashflow_budget`) | CFO | Thực tế so ngân sách | budget, misa | STD-cfg | MB |
| 9 | Cost Ledger | CFO, Kế toán | Phân rã chi phí | `fact_order_costs` | STD (finance) | PB, MB |
| 10 | Accounting Recon | CFO, Kế toán | Sapo/MISA/Shopee khớp không | sapo, misa, shopee | STD (finance) | PB, MB |
| 11 | Return Impact | CEO, CFO | Ảnh hưởng hoàn trả | sapo, misa | STD | PB, MB |
| 12 | Services Revenue | CFO | Doanh thu dịch vụ DV* | sapo + mapping | **FJ** (cần xác minh) | PB, MB |
| 13 | Order Profitability | CFO, Sales Ops | Lợi nhuận từng đơn | sapo, misa, shopee | STD-cfg; DUP một phần #5/#6 | DS, PB, MB |
| 14 | Product Profitability & Cost | Merch + Finance | Margin theo SKU | misa COGS | STD-cfg | MB |
| 16 | Marketing ROI | CMO | ROAS | sapo + ads, budget | STD-cfg | DS, PB, MB |
| 17 | Marketing Monthly Analysis | Marketing Mgr | Phân tích tháng | sapo, ads, dim_customers | STD-cfg | DS, PB, MB |
| 18 | Marketing Weekly Tracker | Marketing Mgr | Doanh thu theo nền tảng tuần | sapo, ads (tùy chọn) | STD | DS, PB, MB |
| 19 | Sales Promotion Analysis | Marketing, Finance | ROI khuyến mãi | sapo (`dim_promotions`) | STD | DS, PB, MB |
| 20 | Customer Retention & Cohorts | Marketing, CS | Giữ chân theo cohort | sapo | STD | PB, MB |
| 21 | Cohort Explorer / Calendar Trend | Analyst | Cohort chi tiết | sapo | **DUP** với #20 | MB ×2 |
| 22 | Customer Intelligence | CEO, CMO | Giá trị, phân khúc, hành vi | sapo | STD | PB, MB |
| 23 | Customer Profitability | CMO, Finance | Lợi nhuận theo khách | sapo, misa | STD-cfg | PB, MB |
| 24 | Customer Daily Action Queue | CS, Sales | Khách cần chăm hôm nay | sapo, action queue | STD | PB, MB |
| 25 | CRM Outreach Effort Weekly | Sales/CS Lead | Nỗ lực gọi ra | crm | STD-cfg hoặc FJ (cần xác minh) | MB |
| 26 | Social Commerce Ops | CS Lead | Doanh thu social, NV bán tốt | sapo | STD-cfg | DS, PB, MB |
| 27 | Shopee Channel Economics | Sales Ops, Finance | Chi phí sàn Shopee | sapo, shopee | STD (tầng sàn) | DS, PB, MB |
| 28 | Sales Daily Ops (4 biến thể: daily_operation, yesterday_operation, sales_daily_retail, sales_today_operation + EV) | Store Mgr, Sales | Hôm nay/hôm qua bán gì | sapo | **DUP**; STD-cfg | DS, PB, MB, EV |
| 29 | Sales Ops Weekly Review | Sales Ops | Review tuần | sapo | STD-cfg | DS, PB, MB |
| 30 | Sales Ops Monthly Summary | Sales Ops | Tóm tắt tháng | sapo, misa | **DUP** một phần #3, #29 | DS, PB, MB |
| 31 | Order Listing Reconciliation | Store Mgr, Data | BI khớp Sapo admin không | sapo | STD | DS, PB, MB |
| 32 | Order Detail View | CS, Finance | Tra cứu một đơn | sapo, misa, shopee | STD | DS |
| 33 | Order Revenue Explorer | Analyst | Khám phá doanh thu | sapo | **DUP** một phần #31/#32 | PB, MB |
| 34 | Order Lifecycle Transitions | Ops | Chuyển trạng thái đơn | sapo | STD | MB |
| 35 | Logistics Ops Center | Ops Mgr | Xử lý đơn hằng ngày | sapo, shipments | STD | DS, PB, MB |
| 36 | Shipping & Returns / Carrier | Warehouse, CS | Hiệu quả carrier, COD | sapo, shipment | **DUP** một phần #35 | PB, MB |
| 37 | Product Performance & Velocity | PM | Tốc độ bán SKU | sapo | STD | MB |
| 38 | Product Health Overview | Merchandising | Sức khỏe sản phẩm | sapo, misa | STD-cfg | MB |
| 39 | Inventory & Stock Health | Inventory/Ops | Tồn kho, OOS | sapo | STD | MB |
| 40 | B2B Daily Sales & Orders Tracking (+ Rill `orders_b2b_ops`) | B2B Account Mgr | Đơn B2B/đại lý | sapo | **FJ** (PARTNER/KY_GUI) | PB, MB, RL |
| 41 | US Cross-border Ops | US Ops | Kênh US | sapo + us_shipment | **FJ** | PB, MB |
| 42 | Ingestion Health Monitor | Data engineer | SLA pipeline | Dagster | Hạ tầng, ngoài catalog | DS, PB, MB |
| 43 | Rill Executive | CEO | Tổng quan đơn | sapo | STD | RL |
| 44 | Rill Retail Ops | Sales Ops | Khám phá đơn retail | sapo | **DUP** một phần #28 | RL |
| 45 | Rill Sales Items Product | Product | Sản phẩm bán | sapo | STD (README nhắc playbook không tồn tại) | RL |
| 46 | Evidence `theme-mvp` (678 dòng) | Mixed | Tổng hợp | cần đọc | Chưa phân loại | EV |
| 47 | Welcome landing ("ChợPulse BI") | All | Mở folder nào | — | **FJ** (branding) | MB |

Tóm tắt (ước lượng): khoảng 45 họ báo cáo gom từ ~110 artifact; STD ~22, STD-cfg ~13, FJ 4 (#12, #40, #41, #47), 7 cụm trùng (#6, #21, #28, #30, #33, #36, #44).

## 2. Đề xuất Standard Catalog (14 báo cáo)

Tầng mở khoá: T1 Sapo-only; T2 + phí sàn; T3 + pack finance (giá vốn, lợi nhuận); T4 + quảng cáo; T5 + CRM/HUG.

| Persona | Báo cáo | Tầng | Artifact dùng lại |
|---|---|---|---|
| CEO | R1 Weekly Pulse | T1 (+target) | ceo_weekly_pulse (DS, MB, EV) |
| CEO | R2 Monthly Scorecard | T3 | ceo_monthly_scorecard |
| CFO | R3 P&L | T3 | finance_pl |
| CFO | R4 Cashflow | T3 | finance_cashflow (MB, EV) |
| CFO | R5 Channel Profitability (gộp #5 + #6) | T2+T3 | channel_profitability_monthly, channel_p_l_deep_dive |
| CFO | R6 Cost Ledger | T3 | finance_cost_ledger |
| CFO | R7 Return Impact | T3 | finance_return_impact |
| CFO | R8 Accounting Recon | T3 | finance_accounting_recon |
| Marketer | R9 Marketing ROI | T4 | marketing_roi |
| Marketer | R10 Marketing Monthly (kèm weekly) | T4 | marketing_monthly_analysis, marketing_weekly_tracker |
| Marketer | R11 Promotion Analysis | T1 | sales_promotion_analysis |
| Marketer | R12 Cohort & Retention | T1 | customer_retention_cohorts (gộp 2 cohort blueprint) |
| Ops | R13 Daily Sales Ops (gộp 4 biến thể) | T1 | sales_daily_operation, sales_daily_retail |
| Ops | R14 Logistics + Shopee Economics | T1/T2 | logistics_operations, shopee_channel_economics |

Bổ sung cho Ops/CS (ngoài 14): order listing, order detail, product health, inventory, customer action queue, CRM, social commerce. Ingestion health là hạ tầng.

Quy tắc: báo cáo chuẩn chỉ nhóm theo giá trị canonical (`*_std`); nhãn tenant chỉ dùng drill-down.

## 3. Đánh giá metric layer

- `semantic/metrics.md` có 56 metric (Sales, Finance, Logistics, Customer, Product & Inventory, Marketing, Composite).
- **Chưa máy đọc được:** văn xuôi markdown, công thức trong khối SQL có chú thích, không schema, không kiểu, không dialect, không tham số tenant; ràng buộc scope là "quy ước" trong văn bản.
- Hai nguồn máy đọc được nhưng tách rời: `rill/metrics/orders_core_metrics.yaml` (53 measure, chỉ Rill) và `schema.yml` của dbt (cột, test; không có block `metrics:`).
- Rule FJ nhúng trong `semantic/`: VAT 8/10% và "~60% đơn vat_amount=0 do US export"; KY_GUI = PARTNER; `filter_us`; MISA COGS sourcing; MISA Channel Classification; Overhead Tier-3; Promo Goods Cost; Shopee Service Fee No Double-Count; "Fine Japan" xuất hiện 8 lần.
- Khoảng trống: schema có kiểu (id, label, category, unit, grain, scope, requires_connectors, tier, status), công thức biên dịch được, tham số tenant (ngưỡng margin, target, scope mapping); `fact_marketing_spend` còn "planned".
- Đề xuất: một registry YAML duy nhất (metric + scope + tier + connector + tham số tenant), script sinh measure Rill, SQL Metabase, query Evidence. dbt Semantic Layer/MetricFlow khả thi nhưng Metabase không tích hợp native (cần xác minh).

## 4. Nội dung FJ chuyển sang tenant overlay

- Playbook/blueprint: `b2b_sales_daily`, `b2b_orders_tracking`, `us_crossborder_operations`, `finance_services_revenue`, `welcome_landing`, `rill/orders_b2b_ops`.
- Evidence: `theme-mvp` (cần xác minh), `finance-cashflow` (cấu hình tài khoản ngân hàng).
- Rules/segments: KY_GUI/PARTNER, VAT US export, MISA Channel Classification, `filter_us`, `filter_internal`.
- `domains/finance.md` (1893 dòng, nhiều phần FJ).
- Config tenant: target (`dim_channel_targets`), ngưỡng margin, mapping scope retail/b2b, mapping kênh social.

## Câu hỏi còn mở

- dbt Semantic Layer hay YAML tự định nghĩa + codegen?
- HUG không xuất hiện trong handbook (0 kết quả grep); chưa có report HUG.
- "Sprint gọi ra" (CRM) có phải FJ-only?
- `evidence/pages/theme-mvp` cần đọc toàn văn để phân loại.
