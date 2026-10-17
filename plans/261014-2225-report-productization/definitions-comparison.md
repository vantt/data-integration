---
title: "Bảng so sánh định nghĩa chỉ tiêu: metrics.md, Rill, blueprint đang chạy"
phase: 0
status: "nhóm Weekly Pulse xong; các nhóm khác chưa đối chiếu (trước phase 10)"
updated: 2026-10-14
---

# Bảng so sánh định nghĩa chỉ tiêu

Tài liệu này là đầu vào của registry (phase 01). Nó ghi mỗi chỉ tiêu đang được tính thế nào ở ba nơi, chỗ nào ra số khác nhau, và số mẫu đo được. Mỗi chỗ lệch có một dòng riêng trong [definition-decisions.md](definition-decisions.md) chờ user chốt. Tài liệu không đổi code và không đổi số.

## Bản ghi trạng thái

| Nhóm | Trạng thái | Ghi chú |
|---|---|---|
| Weekly Pulse (30 question của `ceo_weekly_pulse.md`) | ✅ Đã đối chiếu, đã đo số mẫu | 24 question có dữ liệu, 6 question meta; 17 chỗ lệch (QĐ-01 → QĐ-17) |
| Bảng đổi tên theo quyết định 1 | ✅ | Mục "Bảng đổi tên" bên dưới |
| Hai lỗi số đã biết | Chỉ tham chiếu | Một dòng ở cuối sổ quyết định |
| Các nhóm còn lại (~40 chỉ tiêu `metrics.md`, ~45 measure Rill, 44 blueprint khác) | ⏳ Chưa đối chiếu | Làm song song với phase 01–05, xong trước phase 10 (danh sách ở cuối tài liệu) |

## Cách so

- **Ba nguồn:** `docs/analytics-handbook/semantic/metrics.md` (cùng `segments.md`, `rules.md` khi `metrics.md` trỏ tới), `rill/metrics/orders_core_metrics.yaml` + `rill/models/orders_enriched.sql`, và blueprint đang chạy `docs/analytics-handbook/blueprints/metabase/ceo_weekly_pulse.md`. Định nghĩa thật là cột mart (`transformation/models/core/marts/sales/fact_orders.sql:182-221`, `packs/finance/marts/sales/fact_order_economics.sql`, `core/marts/sales/fact_order_returns.sql`, `core/marts/fact_targets.sql`, `core/marts/intermediate/int_customer_metrics.sql:44-66` cho `first_order_date`).
- **Mốc so là blueprint**, không phải design spec (thiết kế §7). Phase 02 bước 1 kiểm blueprint có khớp bản đang chạy trên Metabase hay không.
- **Bản chụp:** chép file catalog `app_data/data_lake/serving/olap.duckdb` (catalog view trỏ tới parquet) vào thư mục tạm, mở `read_only=True` trong container `fg-dataware-house-data_platform` với `--network none`, `app_data/data_lake` mount chỉ đọc vào `/app/var/data_lake`, phiên DuckDB đặt `TimeZone='Asia/Ho_Chi_Minh'`. Chụp lúc 14/10/2026 23:12 ICT; truy vấn đo chạy 23:15 ICT. Không truy vấn nào mở `olap.duckdb` gốc; bản chụp tạm đã xoá sau khi đo.
- **Kỳ đo (chỉ kỳ đã đóng):** tuần đã đóng gần nhất **W = 05/10–11/10/2026** (thứ Hai–Chủ nhật), tháng đã đóng gần nhất **M = 09/2026**. Card theo cửa sổ tháng (Pace, Forecast, Run-rate) đo tại ngày giả định 15/09/2026 bằng cách thay `current_date` bằng literal.
- **Quy ước cột "Lệch?":** "Có" khi hai nguồn cho số khác nhau trên cùng dữ liệu (đã đo); "Văn bản" khi tài liệu sai so với mart nhưng không nguồn tính toán nào dùng định nghĩa sai; "Không" khi công thức tương đương.

## Ánh xạ 30 question của Weekly Pulse

`metabase` là tên question trong blueprint. "Chỉ tiêu" là id dự kiến cho registry (phase 01 chốt id cuối). Card ghi `inline_sql` là card không biểu diễn được trong giới hạn compiler.

| # | Tab | Question (blueprint) | Loại | Chỉ tiêu | Cửa sổ | Lệch liên quan |
|---|---|---|---|---|---|---|
| 1 | Doanh thu & Target | Chu kỳ báo cáo | meta | — | tuần này, tuần trước | QĐ-08 |
| 2 | Doanh thu & Target | Net Revenue | dữ liệu | `net_sales` | wtd vs trọn tuần trước | QĐ-08, QĐ-14 |
| 3 | Doanh thu & Target | Gross Revenue | dữ liệu | `gross_revenue` | wtd vs trọn tuần trước | QĐ-08 |
| 4 | Doanh thu & Target | Total Orders | dữ liệu | `orders_count` (mọi trạng thái) | wtd vs trọn tuần trước | QĐ-01 |
| 5 | Doanh thu & Target | AOV | dữ liệu | `aov` | wtd vs trọn tuần trước | QĐ-02, QĐ-03 |
| 6 | Doanh thu & Target | MTD GMV vs Target | dữ liệu | `gross_revenue` (mtd) + mục tiêu `gmv` | mtd (trừ hôm nay) | QĐ-05, QĐ-06, QĐ-07 |
| 7 | Doanh thu & Target | Pace Index | dữ liệu | `gross_revenue` mtd / mục tiêu theo ngày | mtd | QĐ-05, QĐ-07 |
| 8 | Doanh thu & Target | Daily Net Revenue (14 Days) | dữ liệu | `net_sales` theo ngày | đầu tuần trước → hôm nay | QĐ-09 |
| 9 | Doanh thu & Target | Đơn hàng tuần này | dữ liệu | bảng chi tiết (`inline_sql`) | wtd | QĐ-01 (không lọc trạng thái) |
| 10 | Doanh thu & Target | Forecasted Month-End GMV | dữ liệu | `gross_revenue` mtd ngoại suy | mtd | QĐ-06, QĐ-07 |
| 11 | Doanh thu & Target | Cần Đạt Mỗi Ngày | dữ liệu | (mục tiêu − mtd) / ngày còn lại | mtd | QĐ-05, QĐ-07 |
| 12 | Doanh thu & Target | Độ tươi dữ liệu | meta | — | 30 ngày | — |
| 13 | Kenh ban hang | Chu kỳ báo cáo | meta | — | — | — |
| 14 | Kenh ban hang | Revenue by Channel Category | dữ liệu | `net_sales` × `channel_category` | wtd | — |
| 15 | Kenh ban hang | Channel Category WoW Comparison | dữ liệu | `net_sales` × `channel_category` | wtd vs trọn tuần trước | — |
| 16 | Kenh ban hang | Top Channels by Revenue | dữ liệu | `net_sales` × `channel_name`, top 8 | wtd | — |
| 17 | Kenh ban hang | Channel Performance Table | dữ liệu | `net_sales`, đơn hiệu lực × `channel_name`, WoW % | wtd vs trọn tuần trước | QĐ-01 (cột Orders lọc hiệu lực, card 4 thì không) |
| 18 | Kenh ban hang | Độ tươi dữ liệu | meta | — | — | — |
| 19 | Khach hang & Canh bao | Chu kỳ báo cáo | meta | — | — | — |
| 20 | Khach hang & Canh bao | New Customers | dữ liệu | `new_customers` | wtd vs trọn tuần trước | QĐ-10 |
| 21 | Khach hang & Canh bao | Returning Revenue % | dữ liệu | doanh thu khách cũ / `net_sales` | wtd | QĐ-11 |
| 22 | Khach hang & Canh bao | Returning Customers | dữ liệu | `returning_customers` | wtd vs trọn tuần trước | QĐ-11, QĐ-12 |
| 23 | Khach hang & Canh bao | New vs Returning Orders (14 Days) | dữ liệu | `orders_count` theo ngày × mới/cũ | đầu tuần trước → hôm nay | QĐ-09, QĐ-11, QĐ-12 |
| 24 | Khach hang & Canh bao | Cancelled Orders | dữ liệu | `cancelled_orders` | wtd vs trọn tuần trước | QĐ-13 |
| 25 | Khach hang & Canh bao | Return Count | dữ liệu | `return_count` (trục ngày hoàn) | wtd vs trọn tuần trước | QĐ-14 |
| 26 | Khach hang & Canh bao | Discount Rate | dữ liệu | `discount_rate` | wtd | QĐ-04 |
| 27 | Khach hang & Canh bao | Weekly Net Profit | dữ liệu | `channel_net_profit` (đơn có giá vốn) | wtd vs trọn tuần trước | QĐ-14 (độ phủ), lỗi đã biết |
| 28 | Khach hang & Canh bao | Gross Margin % | dữ liệu | `gross_margin_pct` (tỉ số của tổng) | wtd vs trọn tuần trước | QĐ-14 (độ phủ) |
| 29 | Khach hang & Canh bao | Loss-Making Channel Count | dữ liệu | aggregate lồng (`inline_sql`) | wtd | — |
| 30 | Khach hang & Canh bao | Độ tươi dữ liệu | meta | — | 30 ngày | — |

24 question có dữ liệu, 6 meta (3 "Chu kỳ báo cáo", 3 "Độ tươi dữ liệu"). Hai card dự kiến `inline_sql` (9, 29) = 2/24 (8%).

## Định nghĩa theo chỉ tiêu (nhóm Weekly Pulse)

Bộ lọc chung của blueprint: `scope_sales` (= `dim_channels.is_sales_channel`, không phụ thuộc trạng thái; `fact_orders.sql:206`), cộng `is_active_order` (= `status NOT IN ('CANCELLED','DRAFT')`; `fact_orders.sql:221`) cho chỉ tiêu tiền. Cửa sổ tuần: `ordered_at >= date_trunc('week', current_date) AND ordered_at < current_date + 1 day` (gồm cả hôm nay), so với trọn tuần trước. Cửa sổ tháng: `ordered_at >= date_trunc('month', current_date) AND ordered_at < current_date` (**không** gồm hôm nay).

| Chỉ tiêu | metrics.md | Rill | Blueprint Weekly Pulse | NULL / tập rỗng | Lệch? |
|---|---|---|---|---|---|
| `net_sales` (tên cũ `net_revenue`) | `SUM(net_revenue)`, "sau chiết khấu, trừ VAT", scope any | `sum(net_revenue)`; `sales_revenue` lọc `scope_sales` của Rill | `COALESCE(SUM(net_revenue),0)`, `scope_sales AND is_active_order`, trục `ordered_at` | blueprint trả 0 khi rỗng | Không (công thức); tên đổi theo quyết định 1 |
| `gross_revenue` | `SUM(gross_revenue)`, trước chiết khấu, gồm VAT; "chỉ làm mẫu số discount_rate" | `sum(gross_revenue)` | `COALESCE(SUM(gross_revenue),0)`, scope + hiệu lực; dùng làm "GMV" so với mục tiêu | 0 | Văn bản (QĐ-05: metrics.md nói không dùng ngoài discount_rate) |
| `orders_count` | `COUNT(DISTINCT order_id)`, không nói trạng thái; `segments.md`: `WHERE scope_sales` đếm mọi đơn | `count(*)` (bảng một dòng/đơn: 15.994 = 15.994 distinct, tương đương) ; `sales_orders` dùng `scope_sales` của Rill (lỗi đã biết) | `COUNT(DISTINCT order_id)` chỉ `scope_sales`, **không** `is_active_order` | 0 | **Có** (QĐ-01) |
| `aov` | `SUM(net_revenue)/NULLIF(COUNT(DISTINCT order_id),0)`, bắt buộc `scope_retail` hoặc `scope_b2b`, không trộn | cùng công thức, không scope | cùng công thức trên `scope_sales` (trộn), hiệu lực; rỗng → 0 | metrics.md NULL, blueprint 0 | **Có** (QĐ-02 scope, QĐ-03 rỗng) |
| `discount_rate` | `SUM(discount_amount)/NULLIF(SUM(gross_revenue),0)`, bắt buộc `scope_retail` | cùng công thức, mô tả "BẮT BUỘC scope_retail" | `SUM(COALESCE(discount_amount,0))*100/NULLIF(SUM(gross_revenue),0)` trên `scope_sales`, làm tròn 1 | NULL | **Có** (QĐ-04 scope); ×100 và làm tròn là trình bày |
| Mục tiêu `gmv` / `target_achievement_rate` | `SUM(actual_revenue)/NULLIF(SUM(target_val),0) FROM fact_targets` (cột `actual_revenue` **không có** trong mart) | không có | `SUM(target_val)` của `metric_code='gmv'` trong chu kỳ chứa `current_date` (cộng 2 dòng nhóm CS + EC = 600 tr), so với `gross_revenue` mtd; `progress.goal = 600000000` cứng | NULL khi mục tiêu 0 | **Có** (QĐ-05 văn bản, QĐ-06 số cứng) |
| Pace / Forecast / Run-rate | không có | không có | mtd **trừ hôm nay** chia cho tỉ lệ ngày **tính cả hôm nay** | NULL khi mục tiêu 0 | **Có** (QĐ-07, lệch nội bộ blueprint) |
| `new_customers` | không có định nghĩa riêng (chỉ nhắc trong `cac`) | không có | `COUNT(DISTINCT customer_key) FROM dim_customers` theo `date(first_order_date)`; `first_order_date` = đơn hiệu lực đầu tiên ở **mọi** kênh (kể cả kênh nội bộ), không lọc scope | 0 | **Có** (QĐ-10) |
| Khách cũ / mới | `repeat_buyer_rate`: tỉ lệ **khách** có `first_order_date < window_start`, `scope_retail`, cửa sổ 7 ngày | không có | 3 cách trong cùng report: card 21 và 22 dùng `first_order_date < đầu kỳ`; card 23 dùng `date(first_order_date) = date(ordered_at)` là mới, còn lại (kể cả khách không có `first_order_date`) là cũ | — | **Có** (QĐ-11) |
| `returning_customers` | xem dòng trên | không có | `scope_sales`, **không** `is_active_order` | 0 | **Có** (QĐ-12) |
| `cancelled_orders` | `rules.md`: không hiệu lực = huỷ; `metrics.md:1313` ghi sai `is_active_order = status != 'CANCELLED'` | `count(*) filter (where status = 'CANCELLED')` | `NOT is_active_order` → gồm cả `DRAFT` | 0 | **Có** (QĐ-13) |
| `return_count` | `COUNT(DISTINCT order_id) FILTER (WHERE fulfillment_status = 'RETURNED') FROM fact_orders` | không có | `COUNT(DISTINCT return_id) FROM fact_order_returns`, `return_status='returned'`, kênh `is_sales_channel` (join kênh của đơn gốc), trục `returned_at` | 0 | **Có** (QĐ-15) |
| `returns_amount` (tên cũ `refund_amount`) | `SUM(refund_amount) FROM fact_order_returns`, trục ngày hoàn, mọi trạng thái | không có | Weekly Pulse không dùng; `finance_return_impact.md` dùng mọi trạng thái, mọi kênh | 0 | **Có** (QĐ-16, cần chốt trước phase 09) |
| `channel_net_profit` | `SUM(channel_net_profit) FILTER (WHERE has_cogs)` | không có | `COALESCE(SUM(e.channel_net_profit),0)`, `e.scope_sales AND e.has_cogs AND e.is_active_order`, trục `o.ordered_at` | 0 | Không (công thức). Độ phủ: QĐ-14. Lỗi `COALESCE(cogs,0)`: tham chiếu |
| `gross_margin_pct` | `SUM(gross_profit)/NULLIF(SUM(net_revenue),0) WHERE has_cogs` | không có (Rill không có measure giá vốn hay biên) | cùng công thức ×100, làm tròn 1, `has_cogs` | NULL | Không |
| Ranh giới ngày/tuần | ICT ngầm định | — | `date_trunc('week'/'month', current_date)` theo múi giờ phiên DuckDB | — | Rủi ro (QĐ-17) |

## Số mẫu đo được

Đo trên bản chụp 14/10/2026 23:12 ICT. "W" = tuần 05–11/10/2026, "M" = tháng 09/2026. Mọi số dưới đây là số đo, không ước lượng.

| Lệch | Đại lượng | Định nghĩa A (blueprint) | Định nghĩa B | Chênh tuyệt đối | Chênh tương đối |
|---|---|---|---|---|---|
| QĐ-01 | Tổng đơn W | 40 (mọi trạng thái) | 36 (hiệu lực) | 4 | +11,1% so với B |
| QĐ-01 | Tổng đơn M | 122 | 93 | 29 | +31,2% |
| QĐ-01 | AOV ngầm (net / Total Orders) W | 2.554.851 | 2.838.724 (AOV trên card) | 283.873 | −10,0% |
| QĐ-02 | AOV W: [All] / Retail / B2B | 2.838.724 | 2.401.698 / 7.646.008 (33 / 3 đơn) | 437.026 (All − Retail) | +18,2% so với Retail |
| QĐ-02 | AOV M: [All] / Retail / B2B | 2.827.083 | 2.136.887 / 4.207.475 (62 / 31 đơn) | 690.196 | +32,3% |
| QĐ-03 | Tuần 2026 có 0 đơn hiệu lực | 0/41 tuần | — | 0 | — (chưa từng xảy ra) |
| QĐ-04 | Discount rate W: [All] / Retail | 53,66% | 50,69% | 2,97 điểm % | +5,9% |
| QĐ-04 | Discount rate M | 56,38% | 46,10% | 10,28 điểm % | +22,3% |
| QĐ-05 | Đạt mục tiêu 09/2026: GMV (`gross_revenue`) / `net_sales` | 626.259.400 / 600 tr = 104,4% | 262.918.704 / 600 tr = 43,8% | 60,6 điểm % | — |
| QĐ-06 | Mục tiêu `gmv` trong `fact_targets` 08–11/2026 | 600.000.000 cứng trong viz | 600.000.000 (CS 300 tr + EC 300 tr) mỗi tháng | 0 | 0% (hôm nay) |
| QĐ-07 | Tại 15/09/2026: MTD GMV | 192.808.950 (đến hết 14/09) | 223.776.950 (gồm 15/09) | 30.968.000 | — |
| QĐ-07 | Pace Index | 0,64 (14 ngày dữ liệu / 15 ngày) | 0,69 (14/14) | 0,05 | −7,2% |
| QĐ-07 | Forecast cuối tháng | 385.617.900 | 413.162.036 | 27.544.136 | −6,7% |
| QĐ-07 | Cần đạt mỗi ngày | 27.146.070 (chia 15 ngày còn lại) | 25.449.441 (chia 16, gồm hôm nay) | 1.696.629 | +6,7% |
| QĐ-08 | Phần "hôm nay" trong card tuần (14/10, đến 17:22) | gồm 3 đơn, 4.040.047 net | Evidence "đến hết hôm qua": tuần đến nay 31.389.333 | 4.040.047 | +12,9% so với bản đến hết hôm qua |
| QĐ-09 | Số ngày trên trục card "14 Days" | 8–14 ngày tuỳ thứ (thứ Tư 14/10: 10 ngày) | 14 ngày | 4 ngày (hôm nay) | — |
| QĐ-10 | Khách mới W | 16 (`first_order_date`, mọi kênh) | 15 (đơn hiệu lực đầu tiên ở kênh bán) | 1 | +6,7% |
| QĐ-10 | Khách mới M | 31 | 26 | 5 | +19,2% |
| QĐ-11 | Đơn "mới" W, card 23 vs quy tắc đầu kỳ (đơn hiệu lực) | 16 (cùng ngày) | 16 (`first_order_date >= đầu tuần`) | 0 | 0% |
| QĐ-11 | Đơn "mới" M, cùng so sánh với đầu tháng | 26 | 29 | 3 | −10,3% |
| QĐ-11 | Đơn không có `first_order_date` bị tính là "cũ" ở card 23 | W 2, M 9 | 0 (quy tắc đầu kỳ không tính) | W 2, M 9 | — |
| QĐ-11 | Tỉ lệ doanh thu khách cũ W (card 21) / tỉ lệ khách cũ (`repeat_buyer_rate`, scope_sales) | 74,4% | 48,3% | — | đại lượng khác nhau, cùng chữ "returning" |
| QĐ-12 | Khách cũ W / M (card 22, không lọc hiệu lực) | 14 / 38 | 14 / 37 | 0 / 1 | 0% / +2,7% |
| QĐ-12 | Đơn trên card 23, W | 40 (17 mới + 23 cũ, mọi trạng thái) | 36 hiệu lực (16 mới + 20 cũ) | 4 | +11,1% |
| QĐ-13 | Đơn huỷ W / M | 4 / 29 (`NOT is_active_order`) | 4 / 28 (`status='CANCELLED'`, Rill) | 0 / 1 (`DRAFT`) | 0% / +3,6% |
| QĐ-14 | Độ phủ giá vốn: % đơn hiệu lực có `has_cogs`, W / M | 100,0% / 95,7% | — | — | — |
| QĐ-14 | Net sales mà card lợi nhuận dùng, M | 243.604.414 (đơn có giá vốn) | 262.918.704 (mọi đơn, card Net Revenue) | 19.314.290 | −7,3% |
| QĐ-14 | Tham khảo: Net Profit / Gross Margin W, M | W 61.529.035 / 60,2%; M 147.830.726 / 60,7% | — | — | — |
| QĐ-15 | Return Count W / M | 0 / 2 (`fact_order_returns`) | 0 / 0 (`fulfillment_status='RETURNED'`: 0 đơn mọi thời điểm) | 0 / 2 | — |
| QĐ-16 | Tiền hoàn M (kênh bán) | 3.694.779 (`return_status='returned'`) | 7.863.954 (mọi trạng thái: thêm 1 phiếu `returning` 4.169.175) | 4.169.175 | −53,0% so với B |
| QĐ-17 | Đơn hiệu lực / net W theo ranh giới ICT vs UTC | 36 / 102.194.053 | 36 / 102.194.053 | 0 | 0% |
| QĐ-17 | Cùng phép so, M | 93 / 262.918.704 | 94 / 263.594.904 | 1 / 676.200 | +0,26% |

## Bảng đổi tên (quyết định 1, không đổi số)

Đầu vào cho trường `legacy_names` của registry. Số mẫu: kênh bán (`scope_sales`), đơn hiệu lực, tháng 09/2026 và tuần 05–11/10/2026.

| Tên cũ | Ở đâu | Id mới | Nghĩa | Số mẫu M | Số mẫu W |
|---|---|---|---|---|---|
| `net_revenue` | cột mart `fact_orders.net_revenue`, `fact_order_economics.net_revenue`; `metrics.md#net_revenue`; measure Rill `net_revenue`, `sales_revenue`; 31/45 blueprint | `net_sales` | Doanh thu bán hàng sau chiết khấu, trừ VAT, **trước** hoàn | 262.918.704 | 102.194.053 |
| `refund_amount` | cột mart `fact_order_returns.refund_amount`; `metrics.md#refund_amount` (alias `refund_liability`); blueprint `finance_return_impact.md` | `returns_amount` | Tiền hoàn theo ngày hoàn (trục `returned_at`); bộ lọc trạng thái chờ QĐ-16 | 3.694.779 (`returned`) / 7.863.954 (mọi trạng thái) | 0 |
| `return_amount` | không xuất hiện ở ba nguồn (chỉ là biến thể tên trong thiết kế) | `returns_amount` | — | — | — |
| (chưa có) | — | `net_revenue` (mới) | `net_sales − returns_amount`, mỗi phần theo trục của nó (đơn: ngày tạo; hoàn: ngày hoàn) | 262.918.704 − 3.694.779 = 259.223.925 (nếu QĐ-16 chọn `returned`) | 102.194.053 |

Cột mart **không đổi tên** (bất biến không đổi tên cột public). `net_revenue` mới chỉ thêm ở phase 09.

## Các nhóm chưa đối chiếu (trước phase 10)

Đối chiếu theo cùng cách, mỗi nhóm một lần cập nhật tài liệu này và sổ quyết định:

| Nhóm | Chỉ tiêu `metrics.md` | Measure Rill | Blueprint đại diện |
|---|---|---|---|
| Doanh thu, VAT | `total_collected`, `discount_amount`, `vat_amount`, `realized_revenue`, `variance_to_target` | `total_collected`, `vat_amount`, `discount_amount`, `retail_*`, `b2b_*` | `ceo_monthly_scorecard`, `sales_monthly_review`, `sales_daily_retail`, `b2b_sales_daily`, `order_revenue_explorer` |
| Lợi nhuận, giá vốn | `cogs_amount`, `gross_profit`, `channel_net_margin_pct`, `fully_loaded_net_profit`, `cogs_variance*`, `is_high_cogs_variance`, `avg_gross_margin_pct` | — | `finance_pl`, `finance_channel_pl`, `channel_p_l_deep_dive`, `channel_profitability_monthly`, `order_profitability_all`, `product_profitability_cost` |
| Hoàn hàng, Shopee | `return_rate`, `post_ship_return_rate`, `shopee_net_settlement`, `shopee_platform_fee_rate` | — | `finance_return_impact`, `shopee_channel_economics` |
| Vận hành | `fulfillment_rate`, `same_day_ship_rate`, `avg_hours_to_first_ship`, `time_to_complete_hours` | `completed_orders`, `open_orders`, `fulfilled_orders`, `eligible_orders`, `fulfillment_rate`, `same_day_ship_*`, `pending_gt_*`, `avg_hours_*` | `sales_today_operation`, `logistics_operations`, `logistics_shipping`, `order_lifecycle_transitions` |
| Khách hàng | `mau`, `mau_repeat`, `retention_rate`, `churn_rate`, `repeat_buyer_rate`, `clv`, `arpu`, `cac` | — | `customer_intelligence`, `customer_retention_cohorts`, `customer_profitability`, `cohort_*`, `crm_outreach_effort_weekly` |
| Sản phẩm, tồn kho | `units_sold`, `basket_size`, `avg_selling_price`, `oos_rate`, `days_of_supply` | `sales_items_core_metrics.yaml` | `product_health_overview`, `product_inventory_stock_health`, `product_performance_velocity`, `sales_promotion_analysis` |
| Marketing | `marketing_spend`, `clicks`, `impressions`, `ctr`, `cpc`, `cpm`, `roas` | `marketing_spend_core_metrics.yaml` | `marketing_monthly_analysis`, `marketing_roi`, `marketing_weekly_tracker` |
| Tổng hợp, vận hành dữ liệu | `health_score`, `ingestion_freshness`, `recon_drift`, `run_success_rate` | — | `ingestion_health`, `finance_accounting_recon` |

Cột blueprint là gợi ý để chia việc; blueprint còn lại (`order_listing`, `customer_daily_action_queue`, `us_crossborder_operations`, `welcome_landing`…) xếp vào nhóm khi đối chiếu.
