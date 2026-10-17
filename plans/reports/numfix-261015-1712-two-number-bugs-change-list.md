# Danh sách thay đổi: sửa hai lỗi số (Rill scope, giá vốn thiếu) — chờ duyệt trước khi deploy

Ngày 15/10/2026, giờ Asia/Saigon. Worktree `/home/vantt/app/fg-dw-numfix`, nhánh `fix/number-bugs`, gốc `d31d51f2` (= main prod). **Chưa commit, chưa deploy.** Số đo trên shadow: lake-base từ backup `20261015-010441` + `20261014-010406`, lake-A build lại từ baseline `d31d51f2` hôm nay.

## 1. Tóm tắt

| # | Lỗi | Sửa | Đổi số ở đâu |
|---|---|---|---|
| 1 | Rill tự tính `scope_sales/retail/b2b` từ `is_sales_channel`, `status`, `customer_type` của `dim_customers` thay vì dùng cột mart | `orders_enriched` và `sales_items_enriched` lấy `fact_orders.scope_*` AND `fact_orders.is_active_order` | Chỉ Rill. Không đổi bảng dbt nào, không đổi card Metabase nào |
| 2 | `channel_net_profit`, `channel_net_margin_pct` dùng `COALESCE(cogs_amount, 0)`: đơn không có giá vốn hiện cả doanh thu thành lãi | Hai cột này (và `fully_loaded_net_profit`, `fully_loaded_margin_pct`, cùng lỗi) NULL khi `has_cogs` FALSE; thêm cột `cogs_coverage_status` | `fact_order_economics` (4 cột + 1 cột mới), `int_customer_economics`/`dim_customers.avg_order_contribution_margin_pct`; 1 card Metabase đổi số trên dữ liệu hiện tại |

`gross_profit`, `gross_margin_pct`: đã NULL khi `has_cogs` FALSE, không đổi. Còn một kẽ hở khác cùng họ (đơn có dòng giá vốn nhưng tổng 0), **không sửa** trong đợt này, xem mục 7.1, cần user quyết.

## 2. File thay đổi

| File | Thay đổi |
|---|---|
| `rill/models/orders_enriched.sql` | `scope_*` = `COALESCE(o.scope_* AND o.is_active_order, false)`; thêm cột `is_active_order`; bỏ công thức tự tính |
| `rill/models/sales_items_enriched.sql` | Cùng lỗi: thêm `LEFT JOIN src_fact_orders` theo `order_id`, lấy cờ của đơn (fact_sales không có cột scope) |
| `rill/metrics/orders_core_metrics.yaml`, `rill/metrics/sales_items_core_metrics.yaml`, `rill/README.md` | Mô tả scope theo cột mart |
| `transformation/models/packs/finance/marts/sales/fact_order_economics.sql` | Cổng `has_cogs` cho `channel_net_profit`, `channel_net_margin_pct`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`; cột mới `cogs_coverage_status` |
| `transformation/models/packs/finance/marts/sales/_finance__models.yml` | Mô tả các cột trên; test `not_null` + `accepted_values` cho `cogs_coverage_status`; unit test dbt `fact_order_economics_missing_cogs_is_not_zero_cost` (3 ca: missing, zero_cost, covered có phí Shopee và overhead); sửa mô tả `promo_goods_cost`/`fully_loaded_net_profit` từng ghi sai là "trừ promo_goods_cost" (code và thiết kế không trừ: `docs/architecture/order-pl/promo-count-once-reconciliation.md`) |
| `transformation/models/packs/finance/marts/intermediate/int_customer_economics.sql` | Chỉ comment (AVG nay chỉ trên đơn `has_cogs`) |
| `transformation/models/core/marts/_core__models.yml`, `transformation/models/packs/hug/marts/_hug__models.yml` | Mô tả `avg_order_contribution_margin_pct`, `redemption_margin_vnd` |
| `transformation/models/packs/finance/README.md` | Mục "Quy tắc giá vốn thiếu" |
| `docs/analytics-handbook/semantic/metrics.md` | `channel_net_profit`, `channel_net_margin_pct` (anti-pattern ghi sai chiều), `fully_loaded_net_profit` |

`pack_contracts()`: không đổi. Lõi chỉ đọc `has_cogs`, `has_platform_fees` của `fact_order_economics` và các cột `int_customer_economics` (tên, kiểu giữ nguyên); test `pack_contract` pass.

## 3. Bảng/cột đổi (golden gate S, lake-A vs nhánh)

| Bảng | Khác biệt | Có chủ đích |
|---|---|---|
| `fact_order_economics` | schema: thêm `cogs_coverage_status` (VARCHAR, sau `cogs_source`); giá trị: `channel_net_profit`, `channel_net_margin_pct`, `fully_loaded_net_profit`, `fully_loaded_margin_pct` | Có |
| `int_customer_economics` | `avg_order_contribution_margin_pct` | Có (AVG bỏ qua đơn NULL) |
| `dim_customers` | `avg_order_contribution_margin_pct` | Có (truyền qua) |
| 80 bảng public còn lại | Không khác | |

Cùng 4 khác biệt ở build thường, build rolling rỗng và `--full-refresh`. Không bảng nào khác đổi: `mart_data_quality`, `mart_customer_tier`, `mart_customer_action_queue`, `mart_hug_attribution`, `dim_customers.lifetime_*` giữ nguyên.

## 4. Số trước/sau

### 4.1 Lỗi 1: Rill (tính bằng DuckDB trên lake-A, chạy chính SQL cũ và mới của Rill)

Rill không build được trong shadow (image không có Rill), nên chạy SQL `orders_enriched`/`sales_items_enriched` bản cũ và mới bằng DuckDB trên parquet rolling mới nhất của lake-A (đúng các file `publish_rill_assets.py` publish). Số đơn, doanh thu thuần (`net_revenue`, VND):

| Tháng | scope_sales đơn | scope_sales DT | scope_retail đơn | scope_retail DT | scope_b2b đơn | scope_b2b DT |
|---|---|---|---|---|---|---|
| 08/2026 | 76 → 76 | 288.856.404 → 288.856.404 | 63 → 61 | 148.570.652 → 142.729.772 | 13 → 15 | 140.285.752 → 146.126.632 |
| 09/2026 | 94 → 93 | 265.462.164 → 262.918.704 | 65 → 62 | 134.873.769 → 132.486.969 | 29 → 31 | 130.588.395 → 130.431.735 |
| 10/2026 (đến 15/10) | 55 → 55 | 176.452.117 → 176.452.117 | 50 → 48 | 108.139.734 → 109.984.040 | 4 → 7 | 51.645.716 → 66.468.077 |
| Toàn bộ | 9.710 → 9.704 | 32.081.217.688 → 32.076.857.932 | 6.547 → 6.310 | 11.245.641.123 → 10.391.734.570 | 3.064 → 3.374 | 20.493.855.362 → 21.650.411.223 |

Sau sửa, scope_sales 09/2026 của Rill = 262.918.704, khớp số "Net sales M" của Weekly Pulse trong QĐ-14.

Từng đơn đổi scope trong 3 tháng (cả 9 đơn):

| Tháng | Đơn | Đổi | Lý do |
|---|---|---|---|
| 08 | 2 đơn COMPLETED, 5.840.880 | retail → b2b | Kênh `Đại Lý` (`channel_format = 'B2B'`), khách còn gắn RETAIL. Mart loại khỏi retail, đưa vào b2b (TAXONOMY Known divergences #2, #3) |
| 09 | 2 COMPLETED + 1 OPEN, 2.386.800 | retail → b2b | Như trên |
| 09 | 1 đơn DRAFT, 2.543.460 (WHOLESALE, kênh Đại Lý) | ra khỏi sales và b2b | Rill cũ chỉ loại `CANCELLED`/`Voided` (`Voided` không tồn tại trong dữ liệu); mart `is_active_order` loại cả `DRAFT` |
| 10 | 1 COMPLETED + 2 OPEN, 14.822.361 | retail → b2b | Kênh Đại Lý như trên |
| 10 | 1 đơn OPEN, 16.666.667, kênh Social | không scope → retail | `dim_customers` gắn khách là CROSSBORDER (tín hiệu "có đơn kênh US"), mart `fact_orders` không có tín hiệu này nên là RETAIL (Known divergences #6) |

Toàn bộ lịch sử: 262 đơn retail → b2b (kênh Đại Lý, khách RETAIL); 50 đơn khách CROSSBORDER trên kênh B2B vào b2b; 29 đơn khách CROSSBORDER theo `dim_customers` vào retail; 6 đơn DRAFT ra khỏi scope.

`sales_items_enriched` (doanh thu dòng): retail 08 154.628.905 → 146.639.305, 09 139.903.043 → 136.231.043, 10 110.852.106 → 110.547.692; b2b 08 186.336.585 → 194.326.185, 09 173.363.072 → 174.491.612, 10 76.817.812 → 93.788.893; sales 09 313.266.115 → 310.722.655 (đơn DRAFT), 08 và 10 không đổi.

### 4.2 Lỗi 2: `channel_net_profit` (lake-A vs lake build từ nhánh)

Độ phủ giá vốn (`cogs_coverage_status`), toàn bộ 15.994 đơn: `covered` 13.173 (DT 45,32 tỷ), `missing` 1.754 (3,75 tỷ), `zero_cost` 1.067 (0,51 tỷ).

| Tập đơn | Đơn | Đơn nay NULL | Tổng `channel_net_profit` trước | Sau |
|---|---|---|---|---|
| Mọi đơn (không lọc) | 15.994 | 1.754 (10,97%) | −1.708.314.180 | −5.457.696.353 |
| Đơn hiệu lực (`is_active_order`) | 13.880 | 86 (0,62%) | −5.758.395.990 | −5.976.946.784 |
| `scope_sales AND is_active_order` | 9.704 | 54 (0,56%) | 12.884.347.463 | 12.743.396.669 (−140.950.794, −1,09%) |

1.668 trong 1.754 đơn NULL là đơn huỷ/nháp (chưa xuất kho nên không có giá vốn); trước đây chúng cộng cả doanh thu vào lãi ở mọi truy vấn không lọc `is_active_order`. Tổng "mọi đơn" âm vì đơn kênh nội bộ (không `scope_sales`) có giá vốn lớn mà doanh thu nhỏ, có từ trước, không liên quan sửa đổi này.

Theo tháng (3 tháng gần nhất):

| Tháng | Mọi đơn: NULL / tổng | Mọi đơn: trước → sau | scope_sales hiệu lực: NULL | scope_sales hiệu lực: trước → sau |
|---|---|---|---|---|
| 08/2026 | 24 / 117 (20,5%) | 160.401.572 → 93.998.046 | 0 | 172.279.111 → 172.279.111 |
| 09/2026 | 31 / 137 (22,6%) | 264.887.388 → 186.853.792 | 4 | 167.145.016 → 147.830.726 |
| 10/2026 | 10 / 66 (15,2%) | 113.982.535 → 96.298.808 | 2 | 99.612.929 → 96.298.808 |

Theo kênh, 3 tháng gần nhất, đơn hiệu lực bị NULL: Đại Lý 09/2026 4 đơn (lãi bị bỏ 19.314.290); Shopee - Fine Japan Vietnam 10/2026 1 đơn (1.908.565); Shopee - thehealthyus 10/2026 1 đơn (1.405.556). Đơn huỷ/nháp bị NULL: Shopee - Fine Japan Vietnam (31 đơn, 90,0 tr), Shopee - JPC SHOP (22 đơn, 40,2 tr), Shopee - thehealthyus (3 đơn, 4,2 tr), Web (2 đơn, 2,5 tr), Đại Lý (1 đơn, 2,5 tr). Toàn lịch sử, lãi bị bỏ lớn nhất: Shopee - Fine Japan Vietnam 556 đơn (1,02 tỷ), Đại Lý 109 đơn (0,72 tỷ), Web 191 đơn (0,37 tỷ), US 76 đơn (0,32 tỷ).

`channel_net_margin_pct`: 1.589 đơn đổi thành NULL (đơn có `net_revenue` = 0 vốn đã NULL). `fully_loaded_net_profit`: 37 đơn đổi; `scope_sales` hiệu lực toàn bộ 263.538.202 → 158.565.632; mọi đơn −100.299.348 → −282.817.621.

Cột phía sau:

| Cột | Trước → sau |
|---|---|
| `dim_customers.avg_order_contribution_margin_pct` (= `int_customer_economics`) | 33/7.738 khách đổi, 11 khách thành NULL; trung bình của 33 khách 69,65% → 43,94% |
| `dim_customers.lifetime_contribution_margin` | Không đổi: tổng −5.976.946.722 cả hai, 0 khách đổi (đã lọc `has_cogs` từ trước) |
| `mart_customer_tier.lifetime_contribution_margin` | Không đổi |
| `mart_hug_attribution.redemption_margin_vnd` | Logic đổi (NULL khi đơn đổi voucher thiếu giá vốn); shadow có 1 voucher chưa đổi, số không đổi |
| `mart_data_quality` | Không đổi (`has_cogs` giữ nguyên) |

## 5. Ảnh hưởng nơi đọc

| Nơi đọc | Số có đổi? |
|---|---|
| Rill `orders_core`, `sales_items_core` | Có, mục 4.1 (chỉ lỗi 1; Rill không đọc `fact_order_economics`) |
| detailView `order_header.sql` (tab tài chính của đơn) | Có: đơn thiếu giá vốn hiện "chưa xác định" (template đã xử lý NULL) thay vì lãi = doanh thu; thanh cơ cấu không còn ô "Net profit" 100%. `customer_value_metrics.sql`, `customer_order_history.sql` chỉ đọc `gross_*`: không đổi |
| CRM `order_sql.py` (tab tài chính của đơn) | Có, nhưng mapper `_i()` đổi NULL thành 0: đơn thiếu giá vốn hiện "lãi 0 ₫", tông trung tính (trước: lãi = doanh thu). Nhánh "Chưa thể tính lãi/lỗ" (`tone == "mute"`) không bao giờ chạy vì `verdict_tone` không trả `mute`. Nên sửa CRM sau (ngoài phạm vi), mục 7.3 |
| CRM sync (`crm/sync/duckdb_reader.py`) | Đọc `lifetime_contribution_margin`: không đổi |
| Evidence `ceo-weekly-pulse` | Lọc `has_cogs`: không đổi |
| `scripts/build_approach_prompts.py` (lọc `COALESCE(avg_order_contribution_margin_pct,0) > 0`) | Tập khách đủ điều kiện 4.052 → 4.041 (−11) |
| Serving `olap.duckdb` | Cột mới tự xuất hiện (`union_by_name`, cột thêm không bị coi là schema drift); giá trị như mart |

## 6. Card Metabase đổi số

Nguồn: danh sách card coordinator quét (`metabase-card-usage.json`, chỉ có tên cột khớp, không có SQL). Phân loại theo SQL trong blueprint `docs/analytics-handbook/blueprints/metabase/*.md`; cần đối chiếu SQL card live trước khi báo user chắc chắn.

**Đổi số trên dữ liệu hiện tại:**

| Dashboard | Card | Vì sao | Trước → sau (shadow, xem ngày 15/10) |
|---|---|---|---|
| CEO Monthly Scorecard [All] (44) | 1590 Channel Profitability Breakdown | `SUM(channel_net_profit) WHERE scope_sales`, không lọc `has_cogs`, không lọc `is_active_order` | "Tháng này" (09/2026) 232.395.808 → 154.362.212; "Tháng trước" (08/2026) 242.145.147 → 175.741.621. Kênh đổi: Shopee - Fine Japan Vietnam 09: 113,7 → 68,7 tr, 08: 120,3 → 81,1 tr; Shopee - JPC SHOP 09: 30,1 → 21,1 tr, 08: 31,7 → 9,0 tr; Đại Lý 09: 78,7 → 56,9 tr; Shopee - thehealthyus 09: 6,3 → 4,1 tr, 08: 3,2 → 1,2 tr; Web 08: 2,5 tr → không còn |

Phần giảm phần lớn là đơn huỷ chưa xuất kho; card vẫn còn tính đơn huỷ có giá vốn (thiếu `is_active_order`), xem mục 7.2.

**Logic đổi nhưng số hiện tại không đổi:** Marketing Monthly Analysis [Retail] (13) / 1641 Channel Profit Contribution vs Spend (không lọc `has_cogs`; 08 98.492.195 và 09 91.477.742 giữ nguyên vì không có đơn retail hiệu lực thiếu giá vốn; sẽ đổi khi có).

**Không đổi:**
- Card lọc `has_cogs` (NULL chỉ xảy ra khi `has_cogs` FALSE): Order Profitability [All] 1132, 1134, 1138; CEO Weekly Pulse [All] 1705, 1707; Finance P&L [All] 2187, 2188 (cả `fully_loaded_net_profit`); Channel Profitability Monthly [Cross] 2394, 2395; Channel P&L Deep Dive [Cross] 1504, 1505, 1506, 1507, 1509, 1510, 1511, 1988, 2388, 2390; Sales Monthly Business Review [All] 2109, 2112; Marketing Monthly Analysis [Retail] 1640; Monthly · Customer Profitability [Retail] 2245, 2247.
- Loss-Order Alert: Sales Ops Weekly Review [Retail] 1672, Sales Ops Monthly Summary [Retail] 1674 (đếm `channel_net_profit < 0`; đơn thiếu giá vốn trước đây có lãi ≥ 0 nên chưa từng được đếm).
- Card `lifetime_contribution_margin`: Daily · Customer Action Queue [Retail] 2175, 2243; Monthly · Customer Profitability [Retail] 2249, 2253.
- Card chỉ đọc `gross_profit`, `cogs_amount`, `has_cogs` của `fact_order_economics`: không đổi.
- Lỗi 1 không ảnh hưởng Metabase: card lọc `scope_*` đọc cột mart, mart không đổi.

Coordinator nên quét SQL live tìm thêm: `fully_loaded_net_profit`, `fully_loaded_margin_pct`, `avg_order_contribution_margin_pct`, `redemption_margin_vnd` (không có trong danh sách term đã quét; blueprint chỉ dùng `fully_loaded_*` ở card đã lọc `has_cogs`).

## 7. Phát hiện thêm, không sửa trong đợt này

### 7.1 Đơn `zero_cost`: cùng họ lỗi, cần user quyết

1.067 đơn có dòng giá vốn nhưng tổng bằng 0 (`has_cogs` TRUE, `cogs_amount` NULL do `NULLIF(…, 0)`): `gross_profit` = `channel_net_profit` = doanh thu. Trong `scope_sales` hiệu lực: 396 đơn, 188 đơn có doanh thu (410.391.131), lãi bị thổi phồng đúng bằng số đó. Theo năm, đơn có doanh thu: 2021 5, 2022 17, **2023 153 (356,4 tr)**, 2024 8, 2025 4, 2026 1 (350.000). Ba tháng gần nhất: 1 đơn (09/2026).

Phương án: (a) giữ, dùng `cogs_coverage_status = 'covered'` khi cần độ phủ chặt (đã có sau đợt này); (b) coi `zero_cost` như thiếu: đổi cổng lãi/biên sang `cogs_coverage_status = 'covered'` (đổi `gross_profit`, `gross_margin_pct`, `channel_net_*` lịch sử 2023, và nếu đổi luôn `has_cogs` thì đổi `mart_data_quality.cogs_rate_pct` và độ phủ QĐ-14). Đề xuất: (a) cho đợt này, (b) xét khi chốt `coverage_metric` của registry.

### 7.2 Card 1590 thiếu `is_active_order`

Card cộng `channel_net_profit` của cả đơn huỷ. Sau đợt này đơn huỷ chưa xuất kho tự rơi ra; đơn huỷ có giá vốn vẫn còn. Nên thêm `AND e.is_active_order` (ngoài phạm vi, phải deploy blueprint).

### 7.3 CRM hiển thị NULL thành 0

`crm/src/adapters/outbound/duckdb/order_mappers.py` `_i()` đổi NULL thành 0, nên đơn thiếu giá vốn hiện "lãi 0 ₫"/"Fully-loaded 0 ₫". Nên để `channel_net_profit`/`fully_loaded_net_profit` là `None` và cho `verdict_tone` trả `mute` khi `has_cogs` FALSE.

### 7.4 Khác

- Giá vốn thiếu một phần trong đơn: đo số lượng xuất kho so với số lượng bán (2026, 905 đơn `has_cogs`): 0 đơn xuất ít hơn bán, nên cờ cấp đơn (`has_cogs`) đủ; ghép theo `sku` giữa `fact_sales` và `int_order_cogs_reconciled` lệch mã (lots/combo) nên không dùng được làm tỷ lệ phủ cấp dòng.
- Shadow: lúc 17:11 có thư mục `checks-JhBZgE` (do `scripts/checks/run-all.sh` của phiên khác tạo), không phải của phiên này, để nguyên.

## 8. Nên ghi vào `plans/261014-2225-report-productization/definition-decisions.md` (phiên planning ghi)

- R-1: đã sửa trên nhánh `fix/number-bugs` (chưa deploy), số trước/sau ở báo cáo này.
- QĐ-14: độ phủ = tỷ lệ đơn (hoặc tỷ lệ `net_revenue`) có `has_cogs` trên cùng tập đơn với chỉ tiêu lãi; sau đợt này mọi cột lãi/biên NULL khi `has_cogs` FALSE, nên "lãi" và "độ phủ" luôn cùng tập. `fact_order_economics.cogs_coverage_status` là cột nguồn cho `coverage_metric` của registry.
- Quyết định mới cần user: xử lý `zero_cost` (mục 7.1).
- Rill scope = mart `scope_*` AND `is_active_order` (loại DRAFT, khác Rill cũ).

## 9. Gate S

Chạy từ worktree: `scripts/shadow/gate.sh S --allow-new --allow-code-change`, baseline `d31d51f2` (dời từ `9c25d02a`, build lại lake-A, golden, `dbt-main.json`, `dagster-main.json`, xoá lake-AF). Chạy 2 lần; lần 2 trên code cuối (thêm unit test, docs).

| Bước | Kết quả | Ghi chú |
|---|---|---|
| 1 build nhánh | ok | `PASS=775 WARN=1` (warn `assert_overhead_accounts_classified`, có sẵn ở prod); unit test mới pass |
| 1b labels_mapped | ok | 6/6 |
| 2 golden | FAIL (dự kiến) | Đúng 4 khác biệt mục 3, chỉ các bảng/cột dự kiến |
| 3 dbt inventory | FAIL (dự kiến) | Checksum `fact_order_economics`, `int_customer_economics` (INFO); 2 test mới (INFO); DIFF danh sách cột khai báo của `fact_order_economics` (thêm `cogs_coverage_status`) |
| 3 compiled SQL | ok | 2 model đổi (INFO) |
| 3b ranh giới module | ok | 0 vi phạm mới |
| 3c taxonomy inventory | 0 warning | 3 INFO "moved" ở `mart_product_health.sql` có sẵn từ baseline |
| 4 dagster inventory | ok | +2 asset check (test mới) |
| 4b dbt qua Dagster | ok | |
| 5 pytest | lần 1 ok (405 passed); lần 2 FAIL hai lần ở `test_concurrent_writes_no_lock_error` | Test flaky đã biết (khoá SQLite). Chạy lại ngay sau: test đó 3/3 pass, cả bộ 405 passed 2/2. Không đổi file Python nào |
| 6 lake rolling rỗng | build ok; golden 4 khác biệt như bước 2 | |
| 6b bare-core | ok | Khác biệt đúng danh sách dự kiến trong `scripts/shadow/README.md` |
| 7 `--full-refresh` | build ok; golden 4 khác biệt như bước 2 | |

Kết luận: chỉ các bảng/cột dự kiến đổi; mọi bước build/wiring pass.

## 10. Deploy (sau khi duyệt) và rollback

Deploy: commit nhánh, theo `docs/operations/deployment.md`. dbt cần build lại `fact_order_economics` và phía sau (`int_customer_economics`, `dim_customers`, `mart_customer_tier`, `mart_hug_attribution`, `mart_data_quality`…) — lần chạy dbt kế tiếp làm việc này, không cần `--full-refresh` (không model incremental nào đổi). Rill: file `rill/models/*.sql` đổi, cần Rill nạp lại project (kiểm tra Rill dev có tự nạp khi file đổi không, nếu không thì restart container `rill`, chỉ làm khi được phép); `fact_orders.parquet` publish đã có sẵn `scope_*`, `is_active_order`.

Rollback: revert commit, chạy lại dbt cho `fact_order_economics+` (bảng tự build lại giá trị cũ; cột `cogs_coverage_status` biến mất, không model/card nào đọc nó); Rill nạp lại SQL cũ. Không có migration dữ liệu, không seed đổi.

---

## Deploy 15/10/2026 17:25 (user duyệt danh sách thay đổi 17:25)

`main` fast-forward `d31d51f2` → `69e021f4` theo runbook: stop `data_platform` 17:25:13, merge, start
17:25:25 (không đổi `docker-compose.yml`, nên `start` là đủ). Rollback point `d31d51f2`; dải revert
`d31d51f2..69e021f4`.

Sau deploy:
- Healthy; instigator 26/26 `diff` 0; log không lỗi; không run FAILURE/CANCELED từ 17:25.
- Rill tự nạp lại `orders_enriched` và `sales_items_enriched` (17:25–17:26), không lỗi.
- Nightly chạy tay `24b759ee-04ad-4512-9ac3-3cd041091d31`: SUCCESS, 55/55 step, 564 check, 0 đỏ mới so
  với `93ad3580`.
- **Card 1590 "Channel Profitability Breakdown" (CEO Monthly Scorecard), số thật sau deploy.**
  Đính chính: card hiển thị "Tháng này" và "Tháng trước", tức **tháng 10 (tới 15/10)** và **tháng 9**,
  không phải T9/T8 như bảng ở trên ghi.
  - Tháng 10 (tới 15/10): 232,4 → **154,4 triệu**.
  - Tháng 9: 242,1 → **175,7 triệu**.
  - Theo kênh, tháng 10: Shopee Fine Japan Vietnam 68,7 tr; Đại Lý 56,9 tr; Shopee JPC SHOP 21,1 tr;
    Shopee thehealthyus 4,1 tr; Telesale 1,8 tr; Facebook 1,3 tr; Zalo 0,5 tr.

Việc tiếp (user chốt 15/10 ~17:25): QĐ-18 (đơn có tổng giá vốn bằng 0 coi là thiếu giá vốn, cả
`gross_profit`) và QĐ-20 (màn hình đơn CRM ghi "không tính được (thiếu giá vốn)") làm ở một thay đổi
sau qua gate S; QĐ-19 (card 1590/1641 lọc đơn còn hiệu lực) đi cùng nhóm B ở phase 09 của plan report.
