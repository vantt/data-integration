# Báo cáo thực thi phase 4 (kiểm kê taxonomy, dời seed): worker

- Ngày: 14/10/2026 (Asia/Saigon)
- Worktree: `/home/vantt/app/fg-dw-modular` (nhánh `refactor/modularize-suite`, HEAD `75894f81`). **Chưa commit, chưa stash, chưa push.** Mọi thay đổi để ở working tree.
- Kết quả: **gate M PASS sạch** (không cờ allow), seed writer chạy được end-to-end, `dbt parse` OK.
- Không đụng `/home/vantt/app/fg-dataware-house` (ngoài file báo cáo này), không đụng docker/`data_platform`/Dagster prod, không sửa SQL model, không tách macro.

## 1. File thay đổi

Không commit. Seed được dời bằng `mv` (không `git mv`): khi commit hãy `git add -A` để git nhận ra đổi tên.

### Tạo mới

| File | Nội dung |
|---|---|
| `transformation/docs/TAXONOMY.md` (1.287 dòng) | Bản đặc tả: 46 domain, 79 khối kiểm kê, Known divergences, tenant literal, model incremental, rủi ro prod, câu hỏi nghiệp vụ |
| `scripts/checks/check_taxonomy_inventory.py` | Check chỉ cảnh báo (exit 0). `--list` in file:dòng, cột, sha256 |
| `scripts/checks/taxonomy_inventory.yaml` | Inventory máy đọc (đường dẫn, dòng, alias, loại `case`/`expr`, sha256 đầy đủ, `snippet` cho biểu thức) |
| `scripts/tests/test_check_taxonomy_inventory.py` | 15 test: im lặng khi không đổi / chỉ đổi khoảng trắng và comment; WARN khi sửa ngưỡng; WARN khi có CASE mới; cột scoped; moved là INFO; biểu thức đổi; file mất; quét không lệch vì chuỗi/comment/CASE lồng; exit 0 kể cả khi có WARN; inventory khớp code trên nhánh; mọi khối CASE nằm trong cột đã khai; **hash trong TAXONOMY.md khớp inventory** |
| `ingestion/src/utils/seed_paths.py` | `seed_path(name, seeds_dir=None) -> Path`, quét `transformation/seeds/**/<name>.csv`, `SeedNotFoundError` nếu 0, `AmbiguousSeedError` nếu >1, từ chối tên có `/` hoặc `.csv` |
| `ingestion/tests/test_seed_paths.py` | 8 test |
| `docs/architecture/taxonomy-engine.md` | Bản v2 chép từ `taxonomy-engine-design.md`, sửa front matter và link cho đúng trong repo (bỏ link tới plan/reports), thêm con trỏ tới TAXONOMY.md |
| `docs/reference/taxonomy/{china,shopify,standards-and-patterns,vietnam-sources}.md` | Chép nguyên văn, chỉ sửa 3 link trỏ về plan thành link `taxonomy-engine.md`, và một đường dẫn seed trong `vietnam-sources.md` |
| `transformation/seeds/taxonomy/` | 8 seed dời vào: `ref_order_sources`, `ref_brands`, `ref_misa_channel_codes`, `ref_payment_methods`, `ref_spend_category`, `ref_tag_categories`, `ref_gl_accounts`, `ref_branch_locations` (tên giữ nguyên; nội dung không đổi) |

### Sửa

| File | Thay đổi |
|---|---|
| `transformation/dbt_project.yml` | `+column_types` của `ref_order_sources`, `ref_brands`, `ref_misa_channel_codes` đặt lại dưới khoá `taxonomy:` (khoá theo thư mục) |
| `ingestion/src/gsheet_budget_sync/fetch.py`, `__init__.py` | Dùng `SEEDS_DIR` của `seed_paths` và `seed_path("seed_cashflow_budget"/"seed_cash_allocation_policy", SEEDS_DIR)`; tên `SEEDS_DIR` giữ nguyên để test monkeypatch cũ vẫn chạy |
| `ingestion/src/gsheet_marketing_spend.py`, `ingestion/src/generate_dropdown.py`, `scripts/maintenance/generate_dropdown_data.py`, `scripts/maintenance/sync_seeds.py` | Mọi đọc/ghi seed đi qua `seed_path` (sync_seeds vẫn nhận `DBT_PROJECT_DIR`) |
| `orchestration/connectors/sheets/assets.py` | Chỉ sửa docstring của `budget_sheet_sync_asset` (file này không có đường dẫn seed cứng; việc ghi nằm ở `gsheet_budget_sync`) |
| `scripts/shadow/gate.sh` | Bước mới 3c gọi `check_taxonomy_inventory.py` (in WARN, không làm gate fail) |
| `.gitignore` | Thêm ngoại lệ `!scripts/checks/check_taxonomy_inventory.py`: pattern `check_*.py` ở dòng 42 đang chặn file mới (check_boundaries.py cũng cần ngoại lệ như vậy). **Nếu không có dòng này file sẽ không được `git add`.** |
| `transformation/AGENTS.md` | Mục "Classification rules (taxonomy)": TAXONOMY.md, `seed_path`, `+column_types`, check kiểm kê |
| `scripts/checks/README.md`, `scripts/shadow/README.md`, `docs/operations/refactor-safety-harness.md` | Thêm check mới (bảng, mục 6.3b, bước 3c trong sơ đồ gate, thời gian) |
| `docs/architecture/modules.md` | Bảng trạng thái; §9 viết lại (đặc tả + seed + công cụ, link `taxonomy-engine.md`, `reference/taxonomy/`, TAXONOMY.md, `seed_paths.py`, ai ghi seed nào); sơ đồ các mục khác không còn nhắc macro taxonomy; thêm dòng literal Fine Japan vào bảng Tenant hooks (§10) |
| Đường dẫn seed trong tài liệu | `docs/context/order-customer-classification-staff-guide.md` (L220, L288), `docs/context/sales-segmentation-guide.md` (L125, L588, L646, L676), `docs/analytics-handbook/guides/channel_classification_implementation_prompt.md` (L19), `transformation/docs/TAG_HANDLING.md` (L524, L555, L689, L702), `.skills/data-pipeline/SKILL.md` (cây thư mục), `.skills/data-pipeline/references/lessons-learned.md` (L2952) |
| Bản chép SQL trong tài liệu nghiệp vụ | `order-customer-classification-staff-guide.md` mục 9: thay ba khối SQL (`is_sales_channel`, `customer_type`, `value_group`) bằng mô tả ngắn + link `TAXONOMY.md#...` (bản chép `customer_type` cũ đã lệch với code: dùng blob `customer_group`, không có `customer_group_code/name`). `customer-segmentation.md`: thêm một lưu ý đầu trang rằng các khối SQL là minh hoạ, không có tên file |
| Ghi chú "đang lệch với code" | `rules.md` (MISA DAILY/CS), `segments.md` (`scope_retail`/`scope_b2b`), `data-model-overview.md` và `sales-segmentation-guide.md` (`source_type` CS/Telesale), mỗi chỗ một dòng trỏ về `TAXONOMY.md#known-divergences`; không sửa nội dung nghiệp vụ |

Không sửa: `monitor_uncategorized_tags.sql` (comment L10 ghi vào mục "Việc sau" của TAXONOMY.md), mọi model SQL, mọi macro, `plans/` (bản ghi lịch sử).

## 2. Tóm tắt domain và biến thể

46 domain (79 khối: 53 CASE, 26 biểu thức) chia 6 nhóm: kênh và gian hàng (9), đơn hàng (5), khách hàng (17), giảm giá (4), sản phẩm (5), thời gian/kế toán/chi phí (6). Domain là dữ liệu thuần (seed, 0 khối SQL): `channel_format`, `platform`, `source_type`, `channel_brand`, `branch_location`, `payment_method_type`, `product_brand`, `spend_category`.

Số biến thể thật (có chứng minh):

- **`customer_type`: 2 logic, 3 khối.** `fact_orders.sql:110` và `int_customer_benchmarks.sql:47` **không giống từng ký tự như brief/thiết kế viết**: bản benchmarks có tiền tố bí danh `c.customer_group`. Bỏ tiền tố `c.` thì chuỗi chuẩn hoá và sha256 trùng (đã chạy script chứng minh). Hai hash trong inventory khác nhau (`cd3b4336…` và `cdba7656…`), TAXONOMY.md ghi rõ điều này. `dim_customers.sql:215` là logic thứ hai (cột `customer_group_code/name` đã parse + tín hiệu đơn kênh US). Thứ tự ưu tiên xác nhận: WHOLESALE > PARTNER > STAFF > KOL > CROSSBORDER > RETAIL (ELSE); `%KY_GUI%` có `_` là wildcard; nhóm NULL thành RETAIL.
- **`value_group`: 2 khối văn bản, 1 logic.** Chứng minh bằng lập luận NULL/ngưỡng dương và **chạy DuckDB trên lưới 40 tổ hợp (có NULL, 0, sát ngưỡng): 0 khác biệt**.
- **`customer_status`: 3 logic** (`dim_customers` Title-case `Active/At Risk/Churned/New/Unknown`; hai mart tháng `ACTIVE/AT_RISK/CHURNED`, đầu vào khác nhau). `'Active'` vs `'ACTIVE'` đã ghi.
- **`next_purchase_signal`: 2 logic** (hôm nay so với cuối tháng).
- **`discount_type`: 1 logic, 2 bản chép giống hệt** (`fact_orders:47` và `fact_order_costs:118` cùng sha256 `7ea0802e…`); `primary_discount_type` có 2 cách chọn (`MAX_BY` theo đơn so với theo `(đơn, cost_type)`). Ghi: `discount_rate` NULL và lý do NULL thành `negotiated_deep`.
- **`contact_result`: 2 tập "reached"** (hẹp `{answered, replied, met}`, rộng thêm `callback, refused, purchased`), hai cột cùng tên `is_reached` khác nghĩa. **Phát hiện mới, ngoài danh sách của brief.**
- `lifecycle_stage`: tách thành `customer_lifecycle_stage` và `product_lifecycle_stage` (hai nghĩa). `scope_*`, `channel_category` (ELSE `Internal`), `geo_region` (ELSE `GEO_OTHER`) và các domain còn lại: 1 biến thể.
- Tên scout cũ không có trong code đã ánh xạ về cột thật (mục 2.4 của TAXONOMY.md): `promo_dependency` là `discount_sensitivity` + `discount_dependency`; `entry_basket`, `product_matrix`, `product_lifecycle`; `gl_cashflow_line` là cột `cashflow_line` của `dim_gl_account`, **không có seed tên đó**.
- Hai nhãn ELSE đáng chú ý: `lifecycle_stage` gán `LIFECYCLE_CHURNED` cho khách chưa có đơn (trong khi `customer_status` ra `New/Unknown`).

Theo yêu cầu thêm của user:
- `storefront` (`channel_name`, tầng 4) và `channel_brand` là domain riêng. Số liệu đếm lại từ seed: Shopee 8 gian + nguồn cha, Lazada 7, Tiki 2 (+ Tiki, Tiki Cross Border), TikTok 1, Grab 1, 3 nguồn Facebook; 6 thương hiệu kênh (Fine World Group 7 dòng, JPC 6, Fine Japan Vietnam 4, The Healthy Us 2, FG Care 2, Fine Care 2). **Số này lệch với thiết kế v2 §5.1 ("ít nhất 9 gian Shopee, 2 Lazada, 4 Tiki")**; đó là cách đếm theo `platform` (gồm cả nguồn cha), TAXONOMY.md ghi theo đếm dòng seed. Nhận diện gian hàng là `LIKE '%' || mapping_tag || '%'` trên tag đơn (chuỗi con, phân biệt hoa/thường, `_` wildcard, không có phá hoà; đo trên baseline 14/10: `stg_sapo_v2_orders` 15.988 dòng = 15.988 `order_id`).
- Đơn Shopee về từ hai nguồn: mục riêng trong TAXONOMY.md (Sapo cho kênh/khách/tag/giảm giá; connector Shopee, file Income Excel, cho phí/thuế/vận chuyển, ghép bằng `order_code`, `fact_order_costs` dùng `JOIN` nên đơn Shopee không có trong Sapo bị loại; bảng Income không có cột gian hàng nên kênh của phí luôn lấy từ Sapo). Chưa có quy tắc "nguồn chính".
- Phát hiện kỹ thuật khác: `dim_customers.sql` có nhánh `{% if is_incremental() %}` nhưng materialization là `external` (theo manifest) nên nhánh không chạy. Model incremental thực sự lưu nhãn: `int_customer_metrics`, `int_customer_entry_attributes`, `int_customer_discount_metrics` (bảng ở mục 7 TAXONOMY.md). Thiết kế v2 §6 nói `dim_customers_base` lưu nhãn: thực tế nó chỉ lưu blob/mã nhóm thô.

Chỉ ghi lại, không sửa (mục 8 TAXONOMY.md): 28 dòng `ref_tag_categories` priority 10 + `int_order_tags` không khoá phụ. **Đo trên baseline 14/10: 565 tag khác nhau, 0 tag tranh chấp khác nhóm ở mức ưu tiên tốt nhất**, tức rủi ro tiềm ẩn, chưa gây lệch số. Thêm: `ref_brands` có các dòng chỉ khác hoa/thường và join `UPPER`: `dim_products` hiện 699 dòng = 699 `variant_id` (không nhân đôi).

## 3. Gate M (từng bước)

1. **Baseline**: `git -C /home/vantt/app/fg-dw-baseline checkout --detach b718befc`; `clone-lake.sh lake-A`, `build-lake.sh <baseline> lake-A` (PASS=649 WARN=1 ERROR=0), capture golden 83/83 bảng, `cleanup.sh lake-AF`, export `dbt-main.json` (186 node) và `dagster-main.json` (254 asset, 502 check, 21 job, 17 schedule, 9 sensor) từ worktree baseline. Build bắt đầu 04:31Z = 11:31 ICT, cùng ngày. Shadow root giữ mode 0700, không copy dữ liệu ra ngoài.
2. `scripts/shadow/gate.sh M` (không cờ allow): **GATE M: PASS**.
   - dbt build nhánh: PASS=649 ERROR=0
   - golden: 83 vs 83 bảng, 0 khác biệt
   - dbt inventory: 186 vs 186 node, 0 khác biệt, 0 info (dù seed đổi đường dẫn và `+column_types` đổi khoá, relation/config giữ nguyên)
   - compiled SQL: 172 vs 172 model, 0 changed, 0 missing
   - module boundaries: 46 known, 0 new violation (gồm luật `seed-duplicate`)
   - 3c taxonomy inventory: 79 khối, 46 domain, **0 warning**
   - dagster inventory: 0 khác biệt
   - dagster dbt subset: PASS=7 ERROR=0
   - pytest: 222 passed, không FLAKY
   - lake trống: build OK, golden 0 khác biệt
   - lake của nhánh (B, D, E) đã xoá sau gate (chứa PII)
3. `python3 scripts/checks/check_boundaries.py` pass (xem trên); `check_taxonomy_inventory.py` im lặng (0 warning).

Sau gate chỉ có thay đổi tài liệu và sinh lại `TAXONOMY.md`/inventory (hash không đổi): đã chạy lại `pytest scripts/tests ingestion/tests` (138 passed) và `check_taxonomy_inventory.py` (0 warning).

## 4. Kiểm tra seed writer end-to-end (shadow, không mạng)

Chạy trong container shadow (`--network none`) trên **bản sao** của code (đặt ở thư mục tạm, đã xoá), lake tạm `lake-verify` (đã xoá). Worktree không bị ghi.

| Phép thử | Kết quả |
|---|---|
| `budget_sheet_sync_asset` (Dagster `materialize`, ba tab sheet thay bằng CSV mẫu của test, `refresh_ref_accounts` giả) | Asset success; ghi vào `transformation/seeds/seed_cash_allocation_policy.csv` đúng chỗ (seed của tenant, không dời); **không tạo file mới** |
| `scripts/maintenance/sync_seeds.py` với bảng `sapo_raw.order` tổng hợp | Ghi vào `transformation/seeds/taxonomy/ref_order_sources.csv` và `.../ref_branch_locations.csv`, **không tạo file trùng tên**, không có file mới ngoài `taxonomy/` |
| Basename sau khi ghi | Vẫn duy nhất (14 file CSV) |
| `dbt parse` sau khi seed bị ghi | rc=0 |

Ghi chú: ở bảng mẫu `sync_seeds` coi cả hai nguồn là "mới" vì truy vấn gốc `WHERE id NOT IN (...)` có thể trỏ tới cột `id` của bảng thay vì alias; đây là hành vi sẵn có của script (không đổi), không liên quan phase này. Script cũng thêm 7 cột vào CSV có 10 cột (sẵn có).

## 5. Đối chiếu ngẫu nhiên TAXONOMY.md với code (≥ 5)

| # | Mục | Kiểm | Kết quả |
|---|---|---|---|
| 1 | `customer_type` `fact_orders.sql:110` | Đọc code: thứ tự WHOLESALE, PARTNER (`TYPE_PARTNER`/`KY_GUI`), STAFF, KOL, CROSSBORDER (`TYPE_CROSSBORDER`/`CTN00014`), ELSE RETAIL; dòng và hash khớp bảng | Khớp |
| 2 | `customer_type` hai bản benchmarks vs fact_orders | Chuẩn hoá bỏ `c.`, so sha256 | Trùng (tuyên bố "giống từng ký tự" trong brief chỉ đúng sau khi bỏ bí danh) |
| 3 | `channel_category` `dim_channels.sql:115` | 8 nhánh `WHEN` + `ELSE 'Internal'`; `Unknown` literal `'Internal'` ở L160 | Khớp |
| 4 | `scope_retail`/`scope_b2b` `fact_orders.sql:207-219` | Điều kiện kênh B2B có thật; `STAFF/KOL/CROSSBORDER` không thuộc scope nào ngoài `scope_sales` | Khớp |
| 5 | `geo_region` | Đếm tên: HCMC 5, HANOI 3, MEKONG 13, CENTRAL 14, ELSE `GEO_OTHER` | Khớp |
| 6 | `ref_tag_categories` | 61 dòng, 26 nhóm, priority 10 có 28 dòng; `prefix` và `contains` cùng `LIKE` | Khớp |
| 7 | `discount_type` hai bản | Cùng sha256 `7ea0802e…` | Khớp |
| 8 | Lấy ngẫu nhiên 8 khối từ inventory (seed=14) | Dòng `line` trong file đúng chữ bắt đầu khối; dòng bảng "Vị trí và hash" có trong TAXONOMY.md | 8/8 khớp |
| 9 | `value_group` | Lưới 40 tổ hợp trên DuckDB | 0 khác biệt |

## 6. Câu hỏi mở và cần quyết định

1. **`.gitignore`**: tôi thêm ngoại lệ cho `check_taxonomy_inventory.py` (file bị `check_*.py` chặn). Nếu coordinator muốn xử lý khác (ví dụ đổi tên file), cần báo; test, gate, tài liệu đều gọi tên này.
2. **"Giống từng ký tự"** trong brief, thiết kế v2 §6 và gap report cho `fact_orders` và `int_customer_benchmarks`: không chính xác theo nghĩa đen (khác tiền tố `c.`). Có muốn sửa câu này trong `docs/architecture/taxonomy-engine.md` §6 không? Tôi chưa sửa vì đó là bản thiết kế đã duyệt.
3. Số gian hàng trong thiết kế v2 §5.1 (9/2/4) lệch với đếm dòng seed (8/7/2 gian con). Giữ thiết kế nguyên văn; TAXONOMY.md là nguồn số liệu.
4. Phát hiện mới cần nghiệp vụ trả lời (đã đưa vào mục "Câu hỏi cho nghiệp vụ" 5 và 6 của TAXONOMY.md): khách chỉ có tín hiệu kênh US nên là CROSSBORDER ở mọi nơi hay chỉ `dim_customers`? tập `is_reached` hẹp hay rộng?
5. Mục "Số bị ảnh hưởng" trong Known divergences ghi cách đo, **chưa đo** (cần truy vấn trên dữ liệu shadow có PII; tôi không đưa số ra ngoài shadow).
6. Cột `+column_types` của ba seed đã đổi khoá nhưng dbt inventory báo 0 khác biệt, nên relation/config không đổi.
7. Rollback (nhắc cho runbook deploy): nếu job sheets 02:30 đã ghi `ref_*` vào `seeds/taxonomy/`, chuyển nội dung về lại trước khi start container; hiện chỉ `sync_seeds.py` chạy tay ghi seed phân loại, job 02:30 chỉ ghi hai seed ngân sách (không dời).

Status: DONE_WITH_CONCERNS
Summary: Đã làm đủ 5 mục của brief và yêu cầu thêm của user, gate M PASS sạch, seed writer đã kiểm end-to-end và `dbt parse` OK; chưa commit.
Concerns: `.gitignore` phải có ngoại lệ cho `check_taxonomy_inventory.py` (đã thêm); brief nói `fact_orders` và `int_customer_benchmarks` "giống từng ký tự" nhưng thực ra chỉ khác tiền tố `c.` (đã ghi đúng trong TAXONOMY.md); seed dời bằng `mv`, cần `git add -A` khi commit.
