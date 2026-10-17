# Phase 2: model lịch sử, sửa comment sai, tài liệu

**Effort:** 1.25d · **Phụ thuộc:** phase 1 đã deploy và đã có **≥ 2 đêm** raw thật trên prod. Baseline shadow làm mới theo `docs/operations/refactor-safety-harness.md` §9.2, để lake-base có raw mới · **Gate:** `scripts/shadow/gate.sh S --allow-new --allow-code-change` · **Deploy:** D2, giờ user duyệt

## Bối cảnh

- Source raw dùng chung `external_location` glob `sapo_v2_raw/{name}/ingest_method=*/**/*.parquet` (`transformation/models/connectors/sapo_v2/staging/_sources.yml:10`). Glob không khớp file nào thì DuckDB báo lỗi. Repo chưa có macro nào cho source tuỳ chọn (`transformation/macros/` không có lệnh `glob(`).
- Mẫu `src_` incremental theo `_dlt_load_id`: `src_sapo_v2_products.sql:1-49`.
- Mẫu unnest giá: `stg_sapo_v2_variant_prices.sql:24-56`. Mẫu unnest tồn: `int_sapo_inventories.sql:24-78`. Mẫu `std_` pass-through: `cdm/staging/std_variant_prices.sql:23-50`.
- Mẫu chỉ build ở nightly: `NIGHTLY_ONLY_ASSETS` (`orchestration/job_support.py:26-30`). Mọi job connector đều trừ tập này: sapo_v2 realtime và incremental (`connectors/sapo_v2/jobs.py:19,28`), shopee (`connectors/shopee/jobs.py:24`), sheets (`connectors/sheets/jobs.py:41`), misa (`connectors/misa_amis/jobs.py:42,57`). Riêng job hourly chỉ chọn model tag `hourly` (`sapo_v2/jobs.py:38-46`).
- Serving: model rolling được tự lên `serving/olap.duckdb` (`scripts/provisioning/bootstrap_serving_views.py`). Thư mục rolling rỗng thì view bị bỏ (`:134`).
- Comment sai cần sửa: `fact_variant_prices_snapshot.sql:6-8` ("historical snapshots accumulate") và `:16` ("Incremental: appends today's snapshot"); `fact_inventory_snapshot.sql:10-11` ("incremental append", "Retention: daily forever"); `docs/architecture/modules.md:487` ("bảng public tích luỹ ảnh chụp hằng ngày").

## Model mới

| Model | Bucket / thư mục | Vật liệu hoá | Grain / khoá | Ghi chú |
|---|---|---|---|---|
| `src_sapo_v2_product_daily_snapshots` | `connector:sapo_v2`, `models/connectors/sapo_v2/staging/` | incremental, `unique_key=['_dlt_load_id','entity_id']`, lọc `_dlt_load_id > max` | sản phẩm × run | Đọc qua `source_or_empty`; bỏ payload sau khi tách `variants_json` |
| `stg_sapo_v2_variant_price_captures` | như trên | view | variant × bảng giá × run | Cột như `stg_sapo_v2_variant_prices` + `captured_at`, `capture_run_id` |
| `stg_sapo_v2_inventory_position_captures` | như trên | view | variant × kho × run | `on_hand`, `available`, `committed`, `incoming`, `onway`, `min_value`, `max_value`, `mac` |
| `stg_sapo_v2_variant_price_versions` | như trên | view | variant × bảng giá × phiên bản (`_dlt_load_id`, `entity_id`) | Đọc `source('sapo_v2_raw','product')` **mọi phiên bản** (không khử trùng như `src_`), `observed_at = event_timestamp`; dùng cho backfill |
| `std_variant_price_observations` | `cdm`, `models/cdm/staging/` | view | quan sát | Union hai stg giá, `evidence_source ∈ {daily_capture, sapo_product_version}`, `source_system='sapo_v2'` |
| `std_inventory_position_captures` | `cdm` | view | variant × kho × run | Pass-through + `source_system` |
| `fact_variant_price_daily` | `core`, `models/core/marts/sales/` | external rolling | (`variant_id`, `price_list_id`, `as_of_date`) | Chỉ `daily_capture`. `as_of_date` theo design §4. Ảnh chụp mới nhất trong ngày. Cột: khoá, `sku`, `product_id`, `price_list_code`, `price_list_name`, `is_cost`, `price_value`, `price_incl_tax`, `is_configured`, `captured_at`. **Không** có cột biên |
| `fact_variant_price_changes` | `core`, `models/core/marts/sales/` | external rolling | (`variant_id`, `price_list_id`, `valid_from_at`) | Gộp các quan sát liên tiếp cùng (`price_value`, `price_incl_tax`). Cột: `valid_from_at`, `valid_from_date`, `valid_to_date` (NULL nếu đang hiệu lực), `previous_price_value`, `price_change_pct` (so với giá trước, không phải biên), `evidence_source`, `is_current` |
| `fact_inventory_position_daily` | `core`, `models/core/marts/inventory/` | external rolling | (`variant_id`, `location_id`, `as_of_date`) | Cột tồn như stg, `location_name`/`location_code` (từ `dim_branch_location` như `int_sapo_inventories`), `captured_at`. Không có giá trị tồn theo `mac` |

**Macro `source_or_empty(source_name, table_name, columns)`** (`transformation/macros/source_or_empty.sql`): lúc chạy (`execute`), dùng `run_query` đếm file khớp glob của source.
- Có file thì trả `source(...)`.
- Không có file thì trả `SELECT CAST(NULL AS <type>) AS <col>, ... WHERE false` đúng cột.
- Lúc parse thì trả `source(...)` để giữ cạnh lineage cho `check_boundaries.py` và `DBT_SOURCE_KEYS`.

**Biến** `history_day_cutoff_hour` (mặc định 6, hoặc theo Q4) trong `transformation/dbt_project.yml`.

**Khai báo khả năng:** thêm `price_history` và `inventory_position_history` (domain `core`) vào `transformation/seeds/capabilities/capability_catalog.csv`, kèm hai dòng `sapo_v2` trong `connector_capabilities.csv`. pytest `scripts/tests/test_capabilities_seeds.py` kiểm id.

**Orchestration:**
- Thêm khoá asset của 4 model nặng (`src_sapo_v2_product_daily_snapshots`, `fact_variant_price_daily`, `fact_variant_price_changes`, `fact_inventory_position_daily`) vào `NIGHTLY_ONLY_ASSETS`. View không cần. Phải cập nhật test `orchestration/connectors/__tests__/test_after_serving.py` nếu nó liệt kê tập này.
- Thêm `"product_daily_snapshot": AssetKey(["sapo","ingest_sapo_v2_product_daily_snapshot_asset"])` vào `DBT_SOURCE_KEYS`.

## Các bước

1. Rebase worktree lên `main`. Làm mới baseline shadow (lake-base copy từ prod sau ≥ 2 đêm chụp).
2. Thêm `product_daily_snapshot` vào `_sources.yml`, viết macro, biến, 4 model connector, 2 view cdm, 3 model core, và YAML: mô tả, test `unique_combination_of_columns`, `not_null`, `accepted_values` cho `evidence_source`, `std_column_contract` mức warn cho `std_*`.
3. Viết singular test `transformation/tests/assert_price_changes_no_overlap.sql`: không có hai khoảng chồng nhau theo (`variant_id`, `price_list_id`).
4. Viết dbt unit test (YAML `unit_tests:` như `_taxonomy__models.yml`) cho `fact_variant_price_daily`:
   - Chụp lúc 03:01 ICT ngày D+1 thì ra D.
   - Chụp lúc 10:00 ngày D rồi 03:01 ngày D+1 thì ra một dòng D, lấy bản 03:01.
   - Giá 0 thì `is_configured=false`.

   Thêm một unit test cho `fact_variant_price_changes`: chuỗi A, A, B, A cho ba khoảng, `valid_to_date` đúng. Unit test không chạy ở prod (`DBT_EXCLUDE_RESOURCE_TYPES=unit_test`); chúng chạy ở `scripts/checks/run-all.sh` và gate.
5. Sửa comment sai trong `fact_variant_prices_snapshot.sql` và `fact_inventory_snapshot.sql`: nói rõ chỉ giữ 3 bản rolling, lịch sử nằm ở các bảng mới, và nguồn có thể cũ theo `modified_on`. **Không đổi SQL.**
6. Cập nhật `NIGHTLY_ONLY_ASSETS`, `DBT_SOURCE_KEYS`, seed khả năng. Sinh lại `scripts/checks/model_buckets.yaml` và `public_models.yaml` bằng công cụ có sẵn (`golden_snapshot.py init`, `check_boundaries.py --write-allowlist` chỉ khi cần; allowlist phải **không** có mục mới).
7. Tài liệu cùng commit:
   - `docs/architecture/modules.md`: sơ đồ §7 (thêm 3 bảng), sửa dòng 487, bảng bucket §3 (số model).
   - `docs/architecture/data-model.md`: thêm 3 dòng bảng; sửa `fact_inventory_snapshot` từ "planned" thành mô tả đúng.
   - `docs/analytics-handbook/semantic/entities.md` và `freshness.md`.
   - `docs/analytics-handbook/domains/product.md`: cách đọc "as of" và các giới hạn backfill (design §4, §7).
8. Chạy `scripts/checks/run-all.sh`, rồi `scripts/shadow/gate.sh S --allow-new --allow-code-change`.
9. Deploy D2 theo runbook. Bước 6: chạy tay `pipeline_batch_nightly_job` thì **không** được (khung giờ và tải). Thay vào đó, materialize riêng 4 asset nightly-only trong Dagster UI một lần, ngoài 02:30–04:00, rồi chạy `build_serving_db`. Xác nhận ba view mới có trong `serving/olap.duckdb`.

## Ma trận test

| Mức | Nội dung |
|---|---|
| dbt unit | Quy tắc `as_of_date` và giờ chốt; bản mới nhất trong ngày thắng; giá 0; gộp khoảng SCD2 (A, A, B, A); variant biến mất thì khoảng đóng |
| dbt data test | Unique theo grain cho 3 bảng core và `src_`; không chồng khoảng; `not_null` cho khoá và `as_of_date`; `std_column_contract` (warn) |
| Gate S | Golden **0 khác biệt** trên mọi bảng public hiện có, kể cả `fact_variant_prices_snapshot` và `fact_inventory_snapshot` (chỉ đổi comment). Bảng mới hiện là INFO. Compiled SQL chỉ đổi ở 2 model sửa comment (đã cho phép bằng `--allow-code-change`) cộng model mới. Module boundaries: không có cạnh mới ngoài ma trận. Dagster inventory: tập `unique_id` của job realtime, incremental, shopee, sheets, misa **không đổi** (model mới bị trừ); nightly và full refresh có thêm. Lake rỗng rolling + lake-P lõi trần xanh. Full refresh lake-AF/BF khớp |
| Shadow bổ sung | Build trên lake **không có** `product_daily_snapshot` (xoá thư mục trong một lake tạm) thì xanh, 3 bảng mới rỗng (tiêu chí 6). Build hai lần liên tiếp thì golden của 3 bảng mới giống nhau (deterministic, không phụ thuộc giờ build) |
| Prod sau D2 | Ba view có trong serving. `fact_variant_price_daily` có `as_of_date` = các đêm đã chụp. Giá hiện hành ở các cặp > 0 khớp `fact_variant_prices_snapshot` (tiêu chí 4). Nightly kế tiếp xanh, `row_trend_checks` không đỏ |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| `source_or_empty` làm mất lineage hoặc sai cạnh boundary | Trung bình × Trung bình | Lúc parse vẫn gọi `source()`. Gate chạy `check_boundaries.py` |
| Unnest JSON của mọi phiên bản `product` làm nightly chậm | Thấp × Thấp | Raw `product` chỉ 2,3 MB. `src_` mới là incremental. Đo thời lượng dbt trong gate so với baseline |
| `as_of_date` lệch múi giờ | Trung bình × Cao | Dùng `timezone('Asia/Ho_Chi_Minh', ...)` tường minh; có unit test |
| Comment sửa làm đổi số | Rất thấp × Cao | Golden 0 khác biệt là điều kiện bắt buộc |
| Đưa nhầm cột biên vào core | Thấp × Trung bình | Danh sách cột tường minh trong YAML; review theo `modules.md` §7 |

## Rollback

`git revert` theo runbook. Phần còn lại sau rollback và cách dọn (chạy khi `data_platform` dừng):
- Bảng `main_staging.src_sapo_v2_product_daily_snapshots`, 2 view `std_*` và 3 view `stg_*` trong `sapo_warehouse.duckdb`: `DROP TABLE` / `DROP VIEW`, hoặc để nguyên (vô hại, không ai đọc).
- Thư mục `export/marts/rolling/{fact_variant_price_daily,fact_variant_price_changes,fact_inventory_position_daily}/`: xoá file trong đó. `bootstrap_serving_views.py` bỏ view của thư mục rỗng (`:134`).
- Raw `product_daily_snapshot`: **giữ**.
