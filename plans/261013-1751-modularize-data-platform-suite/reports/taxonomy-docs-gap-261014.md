# Báo cáo khoảng trống: phase 4 (taxonomy) so với rà soát tài liệu phân loại

- Ngày: 14/10/2026 (Asia/Saigon)
- Phạm vi: nhánh `refactor/modularize-suite`, worktree `/home/vantt/app/fg-dw-modular`, HEAD `75894f81`
- Cách làm: chỉ đọc (git log/status, grep, đọc file). Không sửa gì trong worktree.
- Plan liên quan: [phase-04-taxonomy-module.md](../phase-04-taxonomy-module.md), mục "Điều chỉnh sau rà soát tài liệu phân loại (14/10/2026)".

## Kết luận nhanh

**Tại thời điểm kiểm tra, phase 4 chưa có commit hay thay đổi nào trên nhánh.** 15 commit gần nhất dừng ở `75894f81 docs(ops): the shadow baseline is the last accepted commit` (phase 5 và harness). `git status` sạch. Chưa có `transformation/macros/taxonomy/`, chưa có `transformation/seeds/taxonomy/` (mọi seed vẫn phẳng trong `transformation/seeds/`), chưa có `transformation/docs/TAXONOMY.md`. `docs/architecture/modules.md` §9 (L441-460) chỉ là sơ đồ đích viết từ trước, và bảng trạng thái (L17) ghi "Tenant overlay, taxonomy module: ⏳ Đích".

Vì vậy cả năm điểm đều **chưa có trên nhánh**. Vì phase chưa bắt đầu, phiên đang thực thi có thể áp dụng các điều chỉnh này **ngay trong commit phase 4** thay vì làm commit bổ sung sau deploy. Nếu phiên kia đã làm xong cục bộ mà chưa commit, các mục "Việc còn phải làm" dưới đây vẫn dùng được làm danh sách kiểm.

| Điểm | Trạng thái trên nhánh | Ghi chú |
|---|---|---|
| 1. Kiểm kê thiếu domain | Thiếu | Chưa có `TAXONOMY.md`; inventory trong plan còn tên không tồn tại |
| 2. Dạng luật kết hợp, phân cấp; cột "đã là dữ liệu / còn trong SQL" | Thiếu | `modules.md` §9 L459-460 chỉ có bảng "Thuộc sản phẩm / Thuộc tenant" |
| 3. Known divergences doc và code | Thiếu | Lệch vẫn còn nguyên ở cả tài liệu và seed |
| 4. Đánh dấu giá trị tenant | Một phần (ở mức kiến trúc) | `modules.md` §10 L500 có ghi hook CROSSBORDER/kênh US của `dim_customers`; các literal khác chưa được liệt kê |
| 5. Đường dẫn seed trong tài liệu | Thiếu | Tất cả đường dẫn cũ còn nguyên (danh sách ở mục 5) |

## 1. Kiểm kê còn thiếu domain

**Trạng thái:** thiếu. Inventory trong plan (phase-04 L84) có `customer_value_tier` và `recency_status`; grep trong `transformation/models` và `transformation/macros` không ra kết quả nào.

**Bằng chứng trên nhánh (đường dẫn tương đối `transformation/models/`):**

| Domain | Vị trí | Dạng luật |
|---|---|---|
| `channel_category` | `core/marts/dim_channels.sql` L114-125; hằng `'Internal'` ở L160 | Phân cấp (`channel_format` → Tier 1) |
| `is_sales_channel` | `core/marts/dim_channels.sql` L138; hằng `false` ở L166 | Kết hợp |
| Cây kênh 4 tầng | `dim_channels.sql` L114-131 (Tier 1 `channel_category`, Tier 2 `channel_format`, Tier 3 `platform`, `channel_name`) | Phân cấp; Tier 2-3 là dữ liệu trong `ref_order_sources` |
| `source_type` | `dim_channels.sql` L51, L72, L90, L135; hằng `'channel'` L165 | Ánh xạ trực tiếp, đã là dữ liệu (`ref_order_sources`) |
| `scope_sales`, `scope_retail`, `scope_b2b` | `core/marts/sales/fact_orders.sql` L206-219 | Kết hợp |
| `channel_preference` | `core/marts/intermediate/int_customer_metrics.sql` L92-103 (CASE), mặc định `'CHANNEL_OTHER'` lặp ở L413 và `core/marts/dim_customers.sql` L252 | Ánh xạ trực tiếp còn trong SQL |
| `product_affinity` | `int_customer_metrics.sql` L287-296, mặc định L414 và `dim_customers.sql` L255 | Chia ngưỡng (share > 0.6) theo tên thương hiệu |
| `payment_behavior` | `int_customer_metrics.sql` khoảng L320-329, mặc định L415 | Chia ngưỡng |
| `geo_region` | `dim_customers.sql` L286-294 | Ánh xạ trực tiếp (tỉnh → vùng) còn trong SQL |
| `acquisition_source` | Định nghĩa `int_customer_metrics.sql` L115 (kênh của đơn đầu); luật loại trừ `'Đại Lý'` ở `core/marts/intermediate/int_customer_benchmarks.sql` L79 và `core/marts/mart_deadstock_target_queue.sql` L203 | Kết hợp (loại trừ) |
| `value_group` | `dim_customers.sql` L232-238; `int_customer_benchmarks.sql` L55-61 (thêm `COALESCE`, nên không giống từng ký tự → hai macro) | Chia ngưỡng |
| `lifecycle_stage` (khách) | `dim_customers.sql` L240-246 | Chia ngưỡng |
| `primary_discount_type` | `core/marts/sales/fact_orders.sql` L47-70 (10 loại), L78 (`MAX_BY`); bản sao ở `core/marts/sales/fact_order_costs.sql` khoảng L110-140 | Dò mẫu có ưu tiên + chia ngưỡng |
| 4 nhóm giảm giá | `core/marts/intermediate/int_customer_discount_metrics.sql` L7-12 (mô tả), L89, L109, L129-130 (lọc theo `primary_discount_type`) | Phân cấp (10 loại → 4 nhóm) |
| Mã kênh MISA | `transformation/seeds/ref_misa_channel_codes.csv` (5 dòng) | Ánh xạ trực tiếp, đã là dữ liệu |
| Gán team | `fact_orders.sql` L32-37, L161-163 (email người bán → `std_team_members` SCD2 → `std_teams`); nguồn Google Sheet qua `connectors/gsheet/staging/stg_team_members.sql` | Luật đặc thù (theo thời gian hiệu lực) |

**Việc còn phải làm:**

- `transformation/docs/TAXONOMY.md` (tạo mới): thêm một dòng cho mỗi domain/biến thể ở bảng trên, cùng các domain cũ trong inventory của plan đã grep lại.
- `plans/.../phase-04-taxonomy-module.md`: đã ghi chú bỏ `customer_value_tier`, `recency_status` (đã sửa trong lần này).
- `transformation/macros/taxonomy/`: thêm macro cho `channel_category`, `is_sales_channel`, `scope_*`, `channel_preference`, `product_affinity`, `payment_behavior`, `geo_region`, `value_group` (hai biến thể), `lifecycle_stage` (khách và sản phẩm là hai macro ở hai domain khác nhau), `discount_type` (kiểm tra bằng diff xem `fact_orders` và `fact_order_costs` có giống hệt không). Gán team là join, không phải CASE: chỉ ghi vào `TAXONOMY.md`, không macro hoá.

## 2. Dạng luật kết hợp, phân cấp và cột "đã là dữ liệu / còn trong SQL"

**Trạng thái:** thiếu. `modules.md` §9 L443-460 chỉ có sơ đồ và bảng "Thuộc sản phẩm / Thuộc tenant"; plan liệt kê bốn dạng luật (phase-04 L36).

**Việc còn phải làm:**

- `transformation/docs/TAXONOMY.md`: phần "Dạng luật" có sáu dạng: ánh xạ trực tiếp, dò mẫu có ưu tiên, chia ngưỡng, luật đặc thù (chéo bảng), **luật kết hợp** (ví dụ `scope_*`, `is_sales_channel`, `order_nature` đề xuất), **luật phân cấp** (ví dụ cây kênh 4 tầng, 10 loại giảm giá → 4 nhóm).
- Bảng kiểm kê thêm cột **"Đã là dữ liệu / còn trong SQL"**:
  - Đã là dữ liệu, ánh xạ trực tiếp: `ref_order_sources` (cột `channel_format`, `platform`, `channel_brand`, `market`, `source_type`), `ref_brands` (`vendor_raw` → `brand_name`, `brand_code`), `ref_misa_channel_codes` (`channel_code` → `channel_group`).
  - Đã là dữ liệu, dò mẫu có ưu tiên: `ref_tag_categories` (`pattern`, `category`, `match_type`, `priority`).
  - Còn trong SQL: mọi khối `CASE WHEN` ở mục 1.
- `docs/architecture/modules.md` §9: thêm một câu dưới bảng L459-460 trỏ tới phần "Dạng luật" của `TAXONOMY.md`.

## 3. Known divergences giữa tài liệu và code

**Trạng thái:** thiếu. Các lệch vẫn còn nguyên:

| Chủ đề | Bằng chứng tài liệu | Bằng chứng code/seed |
|---|---|---|
| Mã kênh MISA | `docs/analytics-handbook/semantic/rules.md` L523-525 (`DAILY → 'POS'`, `CS → 'B2B'`) và L542-544 | `transformation/seeds/ref_misa_channel_codes.csv`: `DAILY,Đại lý,B2B_DEALER`; `CS,Chăm sóc khách hàng,DIRECT_B2C` |
| `scope_retail` | `docs/analytics-handbook/semantic/segments.md` L86-96 (chỉ `customer_type = 'RETAIL'`); L14, L59 | `fact_orders.sql` L207-214 còn `AND channel_format <> 'B2B'` (comment: ~92 đại lý gắn RETAIL); staff guide `docs/context/order-customer-classification-staff-guide.md` L133, L313, L317 nói `customer_type` đã tin được từ 2026-06-05 |
| `source_type` của CS, Telesale | `docs/context/data-model-overview.md` L113; `docs/context/sales-segmentation-guide.md` L471, L481, L640 (`team`) | `transformation/seeds/ref_order_sources.csv` L5 (`CS`), L18 (`Telesale`): `channel` |
| `lifecycle_stage` hai nghĩa | | `dim_customers.sql` L240-246 (`LIFECYCLE_NEW/ACTIVE/AT_RISK/CHURNED`); `mart_product_health.sql` L170-178 (`NEW/DORMANT/DECLINING/GROWING/MATURE`) |
| CROSSBORDER ba định nghĩa | đã biết | `dim_customers.sql` L212-226, L324-331 (có tín hiệu kênh US); `fact_orders.sql` L115; `int_customer_benchmarks.sql` L52 |
| `'Active'` vs `'ACTIVE'` | đã biết | Grep `'Active'\|'ACTIVE'` ra `mart_customer_status_snapshot_monthly.sql`, `mart_retention_waterfall_monthly.sql`, `dim_customers.sql`, `mart_deadstock_target_queue.sql` |

**Việc còn phải làm:**

- `transformation/docs/TAXONOMY.md`, mục "Known divergences": một dòng cho mỗi chủ đề trên, gồm "tài liệu nói", "code làm", "số bị ảnh hưởng nếu thống nhất", "người quyết định". Không đổi SQL, không đổi seed trong phase 4.
- `docs/analytics-handbook/semantic/rules.md` L523-544, `segments.md` L86-96, `data-model-overview.md` L113, `sales-segmentation-guide.md` L471/L481/L640: **không sửa nội dung** trong phase 4 (chờ nghiệp vụ trả lời mục "Câu hỏi cho nghiệp vụ"). Chỉ thêm một dòng ghi chú "Đang lệch với code, xem `transformation/docs/TAXONOMY.md#known-divergences`" ngay dưới đoạn liên quan, để người đọc không làm theo bản sai.

## 4. Giá trị tenant viết cứng trong SQL

**Trạng thái:** một phần, ở mức kiến trúc. `docs/architecture/modules.md` §10 L500 ghi hook CROSSBORDER dùng đơn kênh US của `dim_customers`. Các literal khác chưa được liệt kê ở đâu.

**Danh sách literal (giữ nguyên SQL trong phase 4):**

| Literal | Vị trí |
|---|---|
| `CTN00014` | `dim_customers.sql` L226, L331; `fact_orders.sql` L115; `int_customer_benchmarks.sql` L52 |
| `KY_GUI` | `dim_customers.sql` L219; `fact_orders.sql` L112; `int_customer_benchmarks.sql` L49 |
| `BANBUON` (nhóm cũ tên `WHOLESALE`) | `dim_customers.sql` L204-217 |
| Kênh `'US'` | `dim_customers.sql` L35; `intermediate/us_shipment/int_us_shipment_line_prices.sql` L25 |
| Tên thương hiệu `'Fine Japan Vietnam'`, `'FG Care'`, `'Fine Care'` | `int_customer_metrics.sql` L291-293 |
| `'Đại Lý'` | `int_customer_benchmarks.sql` L79; `mart_deadstock_target_queue.sql` L203 |
| Từ khoá giảm giá tiếng Việt (`đại lý`, `hợp đồng`, `nhà thuốc`, `mỹ`, `ctkm`, `nhân viên`, `ctv`, `hoa hồng`...) | `fact_orders.sql` L48-62; bản sao trong `fact_order_costs.sql` |

**Việc còn phải làm:**

- `transformation/docs/TAXONOMY.md`: thêm cột hoặc nhãn **"giá trị tenant"** cho các biến thể chứa literal trên, kèm câu "đầu vào cho tenant overlay (phase 6)".
- `docs/architecture/modules.md` §10, bảng "Tenant hooks" L494-500: thêm một dòng tổng "Literal Fine Japan trong macro taxonomy" trỏ về `TAXONOMY.md`. Không cần thêm vào `boundary_allowlist.yaml` vì đây không phải cạnh `ref`.

## 5. Dời seed làm gãy đường dẫn trong tài liệu

**Trạng thái:** thiếu. Seed chưa dời, mọi đường dẫn cũ còn nguyên. Grep `seeds/ref_` trên nhánh (bỏ `plans/`, vốn là bản ghi lịch sử):

| File | Dòng | Sửa thành |
|---|---|---|
| `docs/context/order-customer-classification-staff-guide.md` | L220, L288 | `transformation/seeds/taxonomy/ref_order_sources.csv` |
| `docs/context/sales-segmentation-guide.md` | L125, L588 (`ref_order_sources`), L646 (`ref_brands`), L676 (`ref_branch_locations`) | thêm `taxonomy/` vào đường dẫn |
| `docs/analytics-handbook/guides/channel_classification_implementation_prompt.md` | L19 (`ref_brands`) | thêm `taxonomy/` |
| `transformation/docs/TAG_HANDLING.md` | L524, L555, L689, L702 (`ref_tag_categories`) | thêm `taxonomy/` (L555, L702 là lệnh `git add`) |
| `.skills/data-pipeline/SKILL.md` | L184 (cây thư mục `seeds/ref_*.csv`) | `seeds/taxonomy/ref_*.csv` và thêm dòng `seeds/seed_*.csv` (tenant, dời ở phase 6) |
| `.skills/data-pipeline/references/lessons-learned.md` | L2952 (`ref_order_sources.csv:31`) | thêm `taxonomy/`; số dòng 31 có thể giữ vì nội dung seed không đổi |
| `transformation/models/monitoring/monitor_uncategorized_tags.sql` | L10 (comment) | thêm `taxonomy/`. Lưu ý: comment nằm trong SQL biên dịch, nên bước so sánh compiled SQL của gate S sẽ báo khác ở model này; ghi rõ là khác do comment, hoặc để comment này lại cho commit sau gate |

Các đường dẫn `seeds/seed_*` (`crm/src/tests/helpers_action_queue_fixtures.py` L19, `crm/docs/ui-spec/panels/P07-suggestion-settings-panel.md` L27, `orchestration/docs/ASSETS.md` L126, `orchestration/docs/SCHEDULES.md` L160, `orchestration/connectors/sheets/assets.py` L271, `lessons-learned.md` L3832) trỏ tới seed tenant, không dời trong phase 4, nên **không sửa** lúc này. `orchestration/connectors/sheets/assets.py` đã nằm trong danh sách sửa Python của plan qua `seed_paths.py`.

**SQL chép trong tài liệu nghiệp vụ** (số khối ```` ```sql ````): `docs/analytics-handbook/semantic/segments.md` (16), `docs/analytics-handbook/guides/report_segmentation.md` (8), `docs/context/customer-segmentation.md` (5), `docs/context/order-customer-classification-staff-guide.md` (4), `docs/context/sales-segmentation-guide.md` (1). Khối nào chép nguyên luật phân loại (CASE của `customer_type`, `scope_*`, `value_group`, `lifecycle_stage`, `discount_type`) kèm tên file thì thay bằng link tới mục tương ứng trong `TAXONOMY.md` và giữ câu mô tả nghiệp vụ. Khối nào là truy vấn mẫu cho người dùng report (ví dụ `WHERE scope_retail AND is_active_order`) thì giữ nguyên.

## Ngoài phạm vi phase 4 (chỉ ghi nhận, Đợt 4)

`order_nature`; seed `ref_customer_tags`; 36 khách sỉ đang ẩn chờ Sales xác nhận; lưu trữ kênh không còn hoạt động; cờ `likely_wholesale`.

## Câu hỏi cho nghiệp vụ

1. **Mã kênh MISA:** `DAILY` là "Đại lý" (B2B_DEALER, như seed) hay "bán lẻ tại quầy/POS" (như `rules.md`)? `CS` là "Chăm sóc khách hàng" (DIRECT_B2C, như seed) hay "Doanh nghiệp/B2B" (như `rules.md`)? Bên nào sai thì sửa bên đó; nếu seed sai thì số theo nhóm kênh MISA sẽ đổi.
2. **`scope_retail`:** sau khi `customer_type` đã tin được từ 2026-06-05, còn cần loại thêm đơn trên kênh `channel_format = 'B2B'` không? Nếu bỏ điều kiện này, đơn của đại lý vẫn còn gắn RETAIL sẽ vào lại doanh thu retail; cần đếm lại số đại lý bị gắn sai (con số ~92 là từ trước 06/2026).
3. **`source_type` của CS và Telesale:** là `team` (theo tài liệu) hay `channel` (theo seed)? Giá trị này hiện chưa đổi số liệu doanh thu nhưng ảnh hưởng cách đọc kênh.
4. **`lifecycle_stage`:** có đồng ý đổi tên một trong hai cột (vd. `product_lifecycle_stage`) ở Đợt 4 không? Đổi tên là đổi hợp đồng cột với Metabase/Evidence.
