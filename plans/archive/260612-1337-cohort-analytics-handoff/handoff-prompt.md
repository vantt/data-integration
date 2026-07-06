# Handoff Prompt — Deep / Multi-Dimensional Cohort Analytics

> **Cách dùng:** paste toàn bộ file này làm prompt mở đầu cho 1 session mới (hoặc đọc trực tiếp).
> Mục tiêu phiên đó: **thảo luận + thiết kế + xây** một khung cohort linh hoạt vượt khỏi "first-order-date".
> Giai đoạn 1 là DISCUSS (chốt design), chưa code. Theo pattern đã dùng cho customer/product: domain → pipeline → boards, có checkpoint.

---

## 1. Bối cảnh (đọc trước khi bàn)

- Repo: `D:\Vantt\app\data-integration` (dbt + Dagster + DuckDB serving + Metabase tại https://bi.lan.fwg.vn). Đọc `AGENTS.md`, `transformation/AGENTS.md`, `docs/analytics-handbook/domains/customer.md` (context Retention & Engagement), `plans/260604-1125-retail-reactivation/02-understand/retention-leak.md` (§2.3 có SQL cohort first-order-date + finding 71.8% one-timer, M1 3-17%).
- Skills: `/ck:analytics-design` (Phase 0-6 thiết kế), `/ck:metabase-automation` (Phase 7-10 deploy). Query/materialize patterns: xem các plan `260611-2250-customer-margin-activation-build` + `260612-1059-product-health-analytics` (cách build mart + real Dagster run + bootstrap_serving_views).
- **Bài học bắt buộc:** L122 (đừng re-derive metric đã pre-computed), L125 (dùng `realized_margin_pct` không `gross_margin_pct`), L123 (date field-filter vỡ trên SQL aliased), [[feedback_dim_customers_incremental_full_refresh]], [[feedback_metabase_redeploy_use_skill]].

## 2. Hiện trạng cohort

- **Đã có (1 dạng):** cohort theo **first-order month** × retention M+n — "Cohort Retention Heatmap" trong dashboard #105 (`blueprints/customer_retention_cohorts.md`) + layer-cake revenue-by-cohort. Logic gốc ở `retention-leak.md §2.3`.
- Đó là cohort 1 chiều (acquisition date). User muốn **nhiều dạng cohort + cohort tổ hợp nhiều tiêu chí**.

## 3. Tầm nhìn — khung cohort đa chiều

Một "cohort" = (CÁCH GOM khách thành nhóm tại điểm vào) × (METRIC theo dõi theo thời gian). Cần mở rộng cả 2 trục:

### 3a. Cohort AXIS (tiêu chí gom — "entry key")
- ✅ first-order **date** (đã có)
- first **product / category / brand** mua đầu (entry SKU)
- **acquisition channel** đầu (Shopee/Web/Zalo/Offline)
- **value tier tại lúc vào** (first-order AOV band)
- **discount-sensitivity** lúc vào (mua đầu có KM không)
- **basket cohort:** thành phần giỏ hàng đơn đầu — entry-SKU đơn lẻ, hay combo SKU (basket signature), hay số SKU/đơn đầu
- **composite** (≥2 tiêu chí): vd `first_category × acquisition_channel`, `behavior segment × product affinity`, `entry-basket × value tier`

### 3b. Cohort METRIC (theo dõi theo M+n)
- retention rate (% quay lại) — đã có
- revenue retention / cumulative LTV theo cohort
- repeat rate, second-order conversion
- **margin** theo cohort (dùng realized_margin_pct — L125)
- **basket expansion:** số SKU/đơn tăng theo thời gian? cross-category adoption (khách vào bằng Cordyceps có mua thêm dòng khác không)
- time-to-2nd-order, churn curve

### 3c. Ví dụ cohort user muốn
- "Khách **vào bằng sản phẩm X** + **kênh Shopee** → retention/LTV ra sao so với vào bằng X qua Web?" (product × channel)
- "Khách **mua đầu có giỏ ≥2 SKU** vs **1 SKU** → repeat rate?" (basket size)
- "Khách vào bằng **gateway SKU** (Gaba/Chondroitin) → tỷ lệ chuyển sang **hero SKU** (Cordyceps/Fucoidan)?" (cross-product path — liên quan product affinity ở retail-reactivation)

## 4. Data nền (đã verify)

- `fact_orders` — customer_key, ordered_at, channel_key, status, totals. (đơn-grain)
- `fact_sales` — **order_line grain** (6582 dòng / 3456 đơn / 1515 khách): product_key, customer_key, channel_key, quantity, net_revenue, discount_amount, ordered_at → **đủ cho basket + product cohort**.
- `dim_customers` — behavior cols: value_group, discount_sensitivity, acquisition_source, product_affinity, channel_preference, lifecycle, first/last_order_date.
- `dim_products` — category, brand, is_packsize; `mart_product_health` — health_class/lifecycle.
- `mart_sku_economics_monthly` — **realized_margin_pct** (margin cohort, đã fix H010).
- **Gap đã biết:** chưa có model **market-basket / frequently-bought-together** (data-backlog retail-reactivation ghi). Basket-signature cohort có thể cần build từ fact_sales.
- Lưu ý: ~1.515 khách có sale; cohort theo composite dễ **vỡ vụn cardinality** (mỗi nhóm vài khách) → cần ngưỡng min-cohort-size.

## 5. Decisions CHỐT (2026-06-12) — đây là spec v1

1. **Kiến trúc:** `mart_cohort_retention` **long-format** — cột `cohort_dimension`, `cohort_value`, `period_n`, `cohort_size`, `active`, `retention_pct` (+ revenue_retention, repeat). 1 bảng cho mọi axis; Metabase filter `cohort_dimension` → ra ma trận tương ứng. Build từ `int_customer_entry_attributes` (1 dòng/khách) + 1 CTE `activity` (tính 1 lần) + UNION ALL mỗi axis (đổi cohort_value). KHÔNG re-derive (L122).
2. **Composite:** chỉ combo DUYỆT TRƯỚC + **min cohort size ≥ 10 khách** (ẩn nhóm nhỏ hơn). v1 = **2 composite**:
   - ⭐ `entry_product × acquisition_channel` (gateway × kênh)
   - ⭐ `basket_size × entry_value_band` (đơn đầu nhiều SKU + giá trị → retention?)
3. **First basket:** (a) entry-SKU đơn lẻ + (b) **basket_size band** (1 vs ≥2 SKU đơn đầu). Basket-signature combo SKU = HOÃN.
4. **Window: CẢ HAI** — relative **M0/M1/M2…** (chính, cohort triangle) + **calendar month** (xem mùa vụ/sự kiện). Thêm cột `window_type` ('relative'/'calendar') vào long-format, hoặc 2 metric column.
5. **Metric v1:** retention_pct + revenue_retention + repeat_rate. Margin (realized) + basket-expansion/cross-category = v2.
6. **Market-basket (FBT): PHASE SAU** (build lớn riêng — cross-sell/bundle). Không chặn cohort v1.
7. **Viz: TABLE** (giống "Cohort Retention Heatmap" #105 — table + conditional formatting), KHÔNG heatmap riêng. Scope **retail** (customer_type='RETAIL'). Dashboard "Cohort Explorer" trong Marketing & Customers › 👥 Customer, filter: cohort_dimension + window_type + metric.

### Single axes v1
first_order_month (đã có, port qua) · entry_product · entry_category · acquisition_channel · basket_size (1 vs ≥2) · entry_value_band · + 2 composite ở trên.

## 6. Đề xuất phased (để thảo luận)
- **P0 discuss** (file này) → chốt §5.
- **P1 domain:** thêm context "Cohort Framework" vào `domains/customer.md` — định nghĩa axis/metric/min-size.
- **P2 pipeline:** `int_customer_entry_attributes` (entry product/category/channel/basket-size/value-band cho mỗi khách) + `mart_cohort_retention` (long-format, parameterized) [+ market-basket model nếu chốt].
- **P3 boards:** "Cohort Explorer" trong Marketing & Customers › 👥 Customer — filter chọn cohort axis + metric; heatmap M+n; layer-cake.
- **P4 validate → P5** (nếu thay/gộp board cũ).

## 7. Nguyên tắc (giữ nhất quán session trước)
- Build new alongside → validate → retire (gate user). Real Dagster run + verify olap.duckdb. Reuse pre-computed (L122). Margin = realized (L125). Scope retail mặc định. Tool-agnostic playbook tách khỏi blueprint.

## Status
Design CHỐT xong (§5). Sẵn sàng khởi động **P1 (domain doc cohort framework)** → P2 (int_customer_entry_attributes + mart_cohort_retention long-format) → P3 (Cohort Explorer table board). Min cohort size = 10. Không còn open question chặn — chạy được ngay.
