# Phase 2: báo cáo của worker (model lịch sử, check độ phủ, tài liệu)

> 15/10/2026 ~19:20 ICT. Worktree `/home/vantt/app/fg-dw-price`, nhánh `feat/price-inventory-history` tại `b0931f33` (= main, đã có phase 1). **Chưa commit.** **Gate S chưa chạy**, theo chỉ dẫn của coordinator: chờ có backup 16/10 và lần chụp 03:00 thật thứ hai. Mọi bước khác đã làm và kiểm trên shadow, với dữ liệu chụp tổng hợp (mục "Đã kiểm").

## Kết quả

- Code, test và tài liệu của phase 2 đã xong, gồm hai quyết định của user ngày 15/10:
  1. `fact_inventory_position_daily` có `bin_location` và `wait_to_pack`. Bảng mới nên hai cột nằm ở vị trí tự nhiên, cạnh các cột vận hành. Plan dashboard tồn kho chỉ cần "có cột", và yêu cầu này thoả.
  2. Check độ phủ so thẳng với tổng Sapo, qua export mới `ASSET_CHECKS` của hợp đồng connector.
- `scripts/checks/run-all.sh`: **PASS** (dbt parse, boundaries 0 vi phạm mới và allowlist không đổi, Dagster validate, pytest 474, selftest, analytics 137).
- Dagster inventory so với baseline: **0 khác biệt**, chỉ có phần thêm. Chỉ selection của `pipeline_batch_nightly_job` và `pipeline_batch_fullrefresh_job` lớn thêm. Tập dbt của các job realtime (*/3), incremental (*/10), hourly (:25), shopee, sheets và misa **không đổi** (tiêu chí 2).
- dbt inventory so với baseline: 0 khác biệt với `--allow-new --allow-code-change`. Compiled SQL chỉ đổi ở 3 model:
  - `fact_inventory_snapshot`, `fact_variant_prices_snapshot`: chỉ sửa comment.
  - `mart_capabilities`: thêm 2 probe.
- Golden: **83/83 bảng public hiện có giống hệt** lake-A (baseline `f7b59ef2`). Ba bảng mới là "only in B".

## File (trong worktree)

Tạo mới:
- `transformation/macros/source_or_empty.sql`: lúc parse trả `source()`, giữ nguyên cạnh lineage, boundary và `DBT_SOURCE_KEYS`. Lúc chạy, nó đếm file khớp glob lấy từ chính `external_location` của source (không chép lại layout). Không có file thì trả quan hệ rỗng đúng cột.
- `transformation/macros/history_as_of_date.sql`: quy tắc `as_of_date` nằm một chỗ, dùng ở ba model.
- Connector sapo_v2: `src_sapo_v2_product_daily_snapshots.sql` (incremental theo `_dlt_load_id`, `unique_key [_dlt_load_id, entity_id]`), `stg_sapo_v2_variant_price_captures.sql`, `stg_sapo_v2_inventory_position_captures.sql`, `stg_sapo_v2_variant_price_versions.sql` (mọi phiên bản `product`, không khử trùng).
- CDM: `std_variant_price_observations.sql` (union hai nguồn, `evidence_source`), `std_inventory_position_captures.sql`.
- Core: `marts/sales/fact_variant_price_daily.sql`, `marts/sales/fact_variant_price_changes.sql`, `marts/inventory/fact_inventory_position_daily.sql`.
- `transformation/tests/assert_price_changes_no_overlap.sql`: không chồng khoảng, mỗi cặp tối đa một khoảng `is_current`.
- `orchestration/connectors/sapo_v2/checks.py`: check `capture_coverage`.
- `orchestration/connectors/__tests__/test_sapo_v2_capture_coverage.py`.

Sửa:
- `_sources.yml` (bảng `product_daily_snapshot`), `_sapo_v2__models.yml`, `_cdm__models.yml` (gồm `std_column_contract` mức warn), `core/marts/sales/_core__models.yml`, `core/marts/inventory/_core__models.yml`. Hai file core có YAML, test và **3 unit test** (as_of và giờ chốt, bản mới nhất trong ngày thắng, giá 0; chuỗi A, A, B, A cho 3 khoảng; cặp bị gỡ thì đóng khoảng; tồn theo ngày lấy bản mới nhất).
- `dbt_project.yml`: biến `history_day_cutoff_hour: 6`.
- `fact_variant_prices_snapshot.sql`, `fact_inventory_snapshot.sql`: chỉ sửa comment, SQL không đổi. Mô tả YAML của hai model cũng được sửa.
- Seed khả năng: `price_history`, `inventory_position_history` (core) cùng hai dòng `sapo_v2`. Thêm probe trong `models/monitoring/mart_capabilities.sql` và một dòng trong `seeds/capabilities/README.md`. **Ngoài danh sách sở hữu của phase:** mọi khả năng trong catalog phải có probe, nếu không thì `mart_capabilities` fail lúc build. `mart_capabilities` không thuộc bảng public trong golden.
- `orchestration/job_support.py`: thêm **cả 9 model mới** vào `NIGHTLY_ONLY_ASSETS` (phase file chỉ nêu 4 model nặng; lý do ở mục "Khác với phase file" 1). Cập nhật test `test_after_serving.py` theo.
- `orchestration/connectors/sapo_v2/__init__.py`: thêm `DBT_SOURCE_KEYS["product_daily_snapshot"]` và `ASSET_CHECKS`.
- Hợp đồng `ASSET_CHECKS`:
  - `orchestration/definitions.py`: thêm vào `asset_checks`.
  - `orchestration/connectors/__init__.py`: docstring.
  - `shopee`, `misa_amis`, `sheets`, `hug`: `ASSET_CHECKS: list = []`.
  - `test_load_enabled.py`: kiểm có export và kiểm kiểu.
  - `orchestration/connectors/README.md`: bảng hợp đồng, "eight names", và lý do check phải đứng riêng.
- `scripts/checks/model_buckets.yaml`: 9 model mới (cdm 26, connector:sapo_v2 32, core 69). Allowlist không thêm mục nào.
- Tài liệu:
  - `docs/architecture/modules.md`: số bucket ở §3, `ASSET_CHECKS` ở §5.1, check ở §5.2, sơ đồ và đoạn lịch sử ở §7, sửa câu sai về "bảng public tích luỹ ảnh chụp hằng ngày" (nay khoảng dòng 500), `NIGHTLY_ONLY_ASSETS` ở §4 và §11b.
  - `docs/architecture/data-model.md`: `fact_inventory_snapshot` đổi từ "planned" sang mô tả đúng; thêm 3 bảng mới và `fact_variant_prices_snapshot`.
  - `docs/analytics-handbook/semantic/entities.md`: sửa Inventory Snapshot; thêm hai entity Inventory Position Daily và Variant Price History.
  - `docs/analytics-handbook/semantic/freshness.md`: dòng Mart SLA.
  - `docs/analytics-handbook/domains/product.md`: mục "Price and Stock Position History" (cách đọc "as of", giới hạn backfill).

`scripts/checks/public_models.yaml` **cố ý chưa sinh lại**; xem "Việc còn lại" bước 3.

## Khác với phase file

1. **Cả 9 model mới đều chỉ build ở nightly**, không chỉ 4. Nếu chỉ trừ 4 model nặng:
   - 5 view mới sẽ vào job */3, */10. Điều đó trái tiêu chí 2 (tập `unique_id` của các job này phải không đổi).
   - Các view đó đọc bảng `src_` mà chỉ nightly tạo. DuckDB kiểm bảng lúc tạo view, nên ngay sau D2 (hoặc khi cài mới hay dựng lại DR), job realtime sẽ fail cho tới nightly đầu tiên.
2. **Cột thêm** ngoài danh sách ở phase file:
   - `fact_variant_price_changes`: `valid_to_at` (đầu khoảng sau, không tính; test không chồng khoảng dùng cột này), `last_observed_at`, `is_configured`, `sku`, `product_id`, `price_list_code`, `price_list_name`, `is_cost`.
   - `fact_inventory_position_daily`: `product_id`, `sku`.
   - Không có cột biên hay giá trị tồn.
3. **Ngày của khoảng SCD2:** với ảnh chụp, `valid_from_date` = `as_of_date` (có giờ chốt). Với phiên bản sản phẩm, nó là ngày ICT của `modified_on`. Một giá bị thay ngay trong ngày bắt đầu có `valid_to_date < valid_from_date`: nó không giữ tới cuối ngày nào, nên phép `BETWEEN` bỏ qua nó. Điều này có ghi trong tài liệu.
4. **Kiểu id:** bảng giá dùng `BIGINT` như `fact_variant_prices_snapshot`. `fact_inventory_position_daily` dùng `VARCHAR` như `int_sapo_inventories`/`fact_inventory_snapshot`, để plan dashboard tồn kho đổi nguồn mà không phải ép kiểu.
5. **`product.md` và `entities.md`** viết tiếng Anh, theo ngôn ngữ của từng file.

## Đã kiểm (shadow, trước gate)

Lake tạm sao từ `lake-base`, build bằng `build-lake.sh` với code của nhánh. Đã xoá sau khi dùng.

| Kiểm | Kết quả |
|---|---|
| Build trên lake **chưa có** `product_daily_snapshot` (tiêu chí 6) | PASS 834, ERROR 0. Log có `source_or_empty: no file ...`. 3 unit test và test không chồng khoảng PASS. `fact_variant_price_changes` vẫn có 9.844 khoảng từ phiên bản sản phẩm (backfill) |
| Backfill (tiêu chí 4, trên dữ liệu lake-base 15/10) | 1.427/1.460 cặp đang có giá > 0 (97,7%) có khoảng từ ≤ 28/05/2026, đạt ngưỡng ≥ 95%. Giá hiện hành khớp `fact_variant_prices_snapshot` ở **1.460/1.460** cặp |
| Hai lần chụp **tổng hợp** (dựng trong lake tạm từ chính raw `product` của lake-base: payload lần tải đủ 13/06; đêm 2 đổi một giá và bỏ một sản phẩm; không lấy gì từ prod) rồi build incremental | `fact_variant_price_daily`: 2 `as_of_date` (14/10, 15/10), mỗi ngày khoảng 9.745 dòng (gồm giá 0), khoảng 1.445 dòng `is_configured`. `fact_inventory_position_daily`: 2.052 rồi 2.046 dòng (6 dòng của sản phẩm bị bỏ biến mất). Giá đổi: khoảng cũ đóng 14/10, khoảng mới từ 15/10, `price_change_pct` 0,02. Sản phẩm bị bỏ: 28 cặp đóng ở 14/10, `is_current = false` |
| Xác định (deterministic) | Build lại cùng lake rồi so golden 86 bảng: **0 khác biệt**. Lần chạy `src_` incremental không có gì mới cũng không đổi gì |
| `--full-refresh` | Ba bảng mới giống hệt bản incremental (dựng lại toàn bộ từ raw) |
| Lõi trần (`build-profile.sh`, mọi pack tắt) | dbt build rc=0. Khác biệt in ra là các khác biệt đã biết khi tắt pack |
| Dagster inventory, dbt inventory, compiled SQL, golden 83 bảng | Như mục "Kết quả" |
| Check `capture_coverage` | 4 pytest: chưa có lần chụp thì bỏ qua; đủ độ phủ thì xanh; lần chụp mới nhất thiếu thì WARN dù lần trước đủ (run `failed` bị bỏ qua); không có tổng thì WARN. Check đọc `ingestion_health` (giữ 90 ngày), không đọc event log của Dagster (bị purge sau 1 ngày) |

Ghi chú về con số dòng mỗi ngày: tiêu chí 3 của `plan.md` lấy mốc 1.460 dòng giá/ngày, là số cặp có **giá > 0** (`is_configured`). Bảng daily còn giữ cả giá 0 (khoảng 9.745 dòng/ngày), đúng design §4. Khi theo dõi, nên so mốc 1.460 với số dòng `is_configured`, không so với tổng số dòng.

Ghi chú về bảng rỗng: một model `external` không có dòng nào được dbt-duckdb ghi thành **một dòng toàn NULL**. View dbt trong warehouse lọc dòng này đi, nhưng view serving đọc thẳng parquet thì vẫn thấy nó. Đây là hành vi có sẵn với mọi bảng external rỗng. Trên prod nó không xảy ra cho 3 bảng mới, vì raw đã có ảnh chụp từ 15/10.

## Việc còn lại (theo thứ tự)

1. **Khi coordinator báo đã có backup 16/10 và lần chụp 16/10 03:00:**
   - `prepare-shadow.sh` với hai backup mới (raw có ≥ 2 lần chụp thật).
   - Dời baseline lên `b0931f33` (harness §9.2), build lại lake-A, capture golden, export lại `dbt-main.json` và `dagster-main.json`, xoá `lake-AF`.
2. `scripts/shadow/gate.sh S --allow-new --allow-code-change` (ngoài 02:30–04:00).
3. **Chỉ sau khi gate PASS**, sinh lại `scripts/checks/public_models.yaml` (thêm 3 bảng với khoá đã kiểm) rồi đưa vào cùng commit:
   ```bash
   cd /home/vantt/app/fg-dw-price
   scripts/checks/run-all.sh        # bước 1 chạy dbt parse, ghi manifest của nhánh vào transformation/<target>/
   T=targ; scripts/shadow/run-shadow.sh $PWD /home/vantt/app/fg-dw-shadow \
     python scripts/checks/golden_snapshot.py init --manifest "/app/transformation/${T}et/manifest.json" --out scripts/checks/public_models.yaml
   git diff --stat scripts/checks/public_models.yaml   # kỳ vọng: +21 dòng, 3 bảng
   ```
   Lý do làm sau gate: gate capture golden của lake-A (code baseline) bằng `public_models.yaml` **của nhánh**, và `compare` không có `--allow-new`. Nếu sinh lại trước gate, lake-A sẽ báo thiếu 3 bảng và bước golden fail, dù đó không phải lỗi. Đây là một chỗ hở của harness khi thêm bảng public. Sửa đúng cách là cho `golden_snapshot.py compare` nhận `--allow-new` và để `gate.sh` truyền cờ đó xuống (ngoài phạm vi plan này). Nội dung sinh lại đã được kiểm: 3 mục, khoá `(variant_id, location_id, as_of_date)`, `(variant_id, price_list_id, valid_from_at)`, `(variant_id, price_list_id, as_of_date)`. Hai lần build cho kết quả giống hệt, nên không có cột volatile.
4. Coordinator commit (code và tài liệu cùng commit), rồi deploy D2.

## Runbook deploy D2

Theo "Refactor deploys (shadow-verified)" (`docs/operations/deployment.md:667-748`), giờ user duyệt, ngoài 02:30–04:00. **`docker-compose.yml` không đổi**, nên dùng `docker compose start`.

1. `instigator_state.py capture --out /tmp/instigators-before.json`
2. `docker compose stop data_platform`
3. Checkout prod sạch (seed đang sống thì commit trước)
4. Ghi SHA rollback và SHA nhánh, rồi `git merge --ff-only feat/price-inventory-history`; kiểm `git diff ... -- docker-compose.yml` rỗng
5. `docker compose start data_platform`. Lệnh start chạy `dbt parse`, nên manifest có 9 model mới.
6. So instigator state; chạy một `pipeline_sapo_v2_realtime_job`, phải xanh (job này không chứa model mới).
7. **Build lần đầu, không chạy cả nightly:**
   - Trong Dagster UI, materialize một lần các asset nightly-only mới: `staging/src_sapo_v2_product_daily_snapshots`, `staging/stg_sapo_v2_variant_price_captures`, `staging/stg_sapo_v2_inventory_position_captures`, `staging/stg_sapo_v2_variant_price_versions`, `staging/std_variant_price_observations`, `staging/std_inventory_position_captures`, `marts/fact_variant_price_daily`, `marts/fact_variant_price_changes`, `marts/fact_inventory_position_daily`. Thêm `mart_capabilities` và hai seed khả năng nếu muốn báo cáo khả năng cập nhật ngay.
   - Sau đó materialize `build_serving_db`.
   - Kiểm tra:
     - Ba view mới có trong `serving/olap.duckdb`.
     - `fact_variant_price_daily` có `as_of_date` = 15/10 (lần chụp 18:52 ngày 15/10) và các đêm đã chụp sau đó.
     - Giá hiện hành của các cặp > 0 khớp `fact_variant_prices_snapshot` (tiêu chí 4).
     - Check `capture_coverage` xanh (chạy tay check, hoặc chờ `health_checks_asset_job`).
8. Theo dõi nightly kế tiếp:
   - Xanh, và mỗi bảng daily thêm đúng một `as_of_date`.
   - `row_trend_checks` không đỏ.
   - Digest bình thường.

## Rollback

`git revert` khoảng đã deploy rồi `docker compose start data_platform`. Phần còn lại sau rollback (dọn khi `data_platform` đã dừng, hoặc để nguyên vì vô hại và không ai đọc):

- Trong `sapo_warehouse.duckdb`:
  - Bảng `main_staging.src_sapo_v2_product_daily_snapshots`.
  - 3 view `stg_*` và 2 view `std_*` trong `main_staging`.
  - View dbt của 3 bảng core.
  - Dọn bằng `DROP TABLE` / `DROP VIEW`.
- `export/marts/rolling/{fact_variant_price_daily,fact_variant_price_changes,fact_inventory_position_daily}/`: xoá file; `bootstrap_serving_views.py` sẽ bỏ view của thư mục rỗng.
- `mart_capabilities` mất 2 dòng ở lần build kế tiếp.
- Raw `product_daily_snapshot`: **giữ**.

## Câu hỏi còn mở

1. Coordinator có muốn sửa harness (`golden_snapshot.py compare --allow-new`, truyền từ `gate.sh`) trước gate phase 2, thay cho bước sinh lại `public_models.yaml` sau gate không?
2. Backup 01:04 ngày 16/10 chạy **trước** lần chụp 03:00, nên chỉ chứa lần chụp 15/10 18:52. Để lake-base có ≥ 2 lần chụp thật, cần backup 17/10 01:04 (hoặc một bản chụp tay sau 03:00 ngày 16/10). Coordinator chọn cách nào?

---

## Gate phase 2 (17/10/2026, 09:47–10:05 ICT)

**Kết quả: `gate.sh S --allow-new --allow-code-change` PASS** ở lần chạy thứ hai, trên commit `15054360` cộng các sửa harness nhỏ chưa commit (mục "Sửa trong lần gate này").

### Chuẩn bị

- `prepare-shadow.sh 20261017-010719 20261016-010722`. Raw lấy từ backup 17/10, có `product_daily_snapshot` với 2 file: lần chụp 15/10 18:52 và 16/10 03:01 (mỗi file 560 sản phẩm).
- Bước `prepare-deps.sh` bên trong **lỗi**. `pip download pytest==8.3.3` nay kéo bản pluggy mới nhất (1.7.0), trong khi bước cài offline ghim `pluggy==1.6.0`. Đã sửa bằng cách ghim cùng phiên bản khi tải (xem mục sửa), chạy lại `prepare-deps.sh`, rồi chạy tay `chmod -R go-rwx` (bước cuối mà `prepare-shadow.sh` bị bỏ do lỗi). lake-base không bị ảnh hưởng.
- Baseline dời lên `b0931f33`. lake-A build lại (PASS 775, ERROR 0), golden 83/83, export lại `dbt-main.json` và `dagster-main.json`, xoá lake-AF.

### Các dòng gate (lần chạy PASS)

| Bước | Kết quả |
|---|---|
| 1 Build lake-B | ok |
| 1b `labels_mapped` | ok |
| 2 Golden lake-A vs lake-B | 83 vs 83 bảng, **0 khác biệt** |
| 3 dbt inventory | 212 vs 221 node, 0 khác biệt, 17 INFO: 9 model mới; checksum và mô tả của `fact_inventory_snapshot` và `fact_variant_prices_snapshot` (chỉ comment); `mart_capabilities` (2 probe, thêm 2 cạnh tới `std_*`); 2 seed khả năng |
| 3 Compiled SQL | 3 model đổi: hai model sửa comment và `mart_capabilities`. 0 thiếu |
| 3b Boundaries | 21 đã biết, 0 vi phạm mới, allowlist không đổi |
| 3c Taxonomy | 3 dòng `INFO moved` trong `mart_product_health.sql` (có sẵn trên main, không do nhánh này) |
| 4 Dagster inventory | 0 khác biệt, 60 INFO: 9 asset dbt mới; selection của `pipeline_batch_nightly_job` và `pipeline_batch_fullrefresh_job` có thêm đúng 9 model đó; check `capture_coverage` mới; asset ingest ảnh chụp nay đại diện cho source dbt mới. **Mọi job khác không đổi** (tiêu chí 2) |
| 4b dbt subset qua Dagster | ok |
| 5 pytest | 476 passed |
| 6 Lake rỗng rolling | build ok, golden 83 vs 83, 0 khác biệt |
| 6b Lõi trần | build ok. 114 khác biệt in ra để xem, cùng tập với lần đo 15/10 (cột và bảng của pack khi tắt pack) |
| 7 Full refresh lake-AF vs lake-BF | build ok, golden 83 vs 83, 0 khác biệt |

**Lần chạy đầu FAIL ở bước 4**, chỉ một dòng:

```
DIFF assets.sapo/ingest_sapo_v2_product_daily_snapshot_asset: {'dbt_unique_id': None, ...} -> {'dbt_unique_id': 'source.sapo_warehouse.sapo_v2_raw.product_daily_snapshot', ...}
```

Đây là hệ quả **có chủ đích** của `DBT_SOURCE_KEYS["product_daily_snapshot"]` (phase file yêu cầu). Mọi asset ingest batch đều đại diện cho source dbt mà nó nạp, ví dụ `products_batch` có `source...product` ở baseline. `--allow-new` trước đây chỉ chấp nhận asset mới và selection lớn thêm, chưa chấp nhận trường hợp "asset có sẵn bắt đầu đại diện cho một node dbt mới". Lần chạy đầu cũng có một test flaky đã biết (`test_concurrent_writes_no_lock_error`), chạy lại thì qua.

### Sửa trong lần gate này (chưa commit)

| File | Sửa |
|---|---|
| `scripts/checks/dagster_inventory.py` | Với `--allow-new`, một asset có sẵn mà thay đổi **duy nhất** là `dbt_unique_id` từ trống sang một node dbt **không có ở baseline** (không ở asset nào, không ở selection job nào) được in là `INFO ... now stands for new dbt node`. Đổi sang node mà baseline đã có, hay đổi bất kỳ trường nào khác, vẫn là `DIFF` |
| `scripts/tests/test_dagster_inventory.py` | 2 test: gắn vào source mới thì là INFO với `--allow-new` và DIFF nếu không có cờ; gắn hoặc đổi sang node đã có thì là DIFF |
| `docs/operations/refactor-safety-harness.md` (mục dagster inventory), `scripts/shadow/README.md` | Mô tả quy tắc mới của `--allow-new` |
| `scripts/shadow/prepare-deps.sh` | `pip download "pytest==8.3.3" "pluggy==1.6.0" "iniconfig==2.3.1"`, khớp với phiên bản ghim khi cài |
| `scripts/checks/public_models.yaml` | Sinh lại sau khi gate PASS (`golden_snapshot.py init` trên manifest của nhánh): 86 bảng, thêm `fact_inventory_position_daily`, `fact_variant_price_changes`, `fact_variant_price_daily` với khoá như design (+21 dòng, không đổi mục cũ) |

Sau các sửa: `scripts/checks/run-all.sh` PASS (dbt parse, boundaries, Dagster validate, pytest 476, selftest, analytics 137).

Kiểm thêm theo harness §9.2 "Thêm bảng public mới": build nhánh hai lần liên tiếp trên lake tạm sao từ lake-base mới, capture golden bằng danh sách 86 bảng. Kết quả **86 vs 86, 0 khác biệt**: ba bảng mới không có cột volatile, không cần `volatile_columns`.

Lưu ý cho gate sau: lake-A dựng từ `b0931f33` không có ba bảng mới. Cho tới khi baseline dời lên commit chứa phase 2, capture golden của lake-A theo danh sách 86 bảng sẽ báo thiếu ba bảng đó. Vì vậy gate kế tiếp (ví dụ của plan dashboard tồn kho) phải dời baseline lên commit phase 2 trước (§9.2), như thường lệ.

### Số liệu trên 2 đêm chụp thật (lake tạm từ lake-base 17/10, build nhánh, đã xoá)

| Đo | Kết quả |
|---|---|
| Raw | 2 lần chụp: `captured_at` 15/10 11:52:38 UTC (18:52 ICT) và 15/10 20:01:35 UTC (16/10 03:01 ICT), mỗi lần 560 sản phẩm |
| `as_of_date` | Cả hai lần chụp cùng ứng với **15/10**: 18:52 ICT trừ 6 giờ vẫn là 15/10, và 03:01 ngày 16/10 trừ 6 giờ là 15/10. Lần 03:01 thắng (mọi `captured_at` trong bảng = 20:01:35 UTC). Đúng quy tắc design §4. Lần chụp 17/10 03:00 chưa có trong backup 01:07 nên chưa thấy `as_of_date` 16/10 |
| `fact_variant_price_daily` | 9.769 dòng cho 15/10; **1.460** dòng `is_configured` (đúng mốc 1.460 của tiêu chí 3) |
| `fact_inventory_position_daily` | **2.052** dòng (đúng mốc 2.052), 684 variant, 3 kho. `bin_location` có giá trị ở 26 dòng; `wait_to_pack` tổng 0. `available = on_hand − committed` đúng ở 2.044/2.052 dòng |
| So với `fact_inventory_snapshot` cũ | `on_hand` bằng nhau ở 1.947/2.052 cặp. **105 cặp khác**, đúng vấn đề nguồn cũ mà plan dashboard tồn kho (Q6) xử lý |
| `fact_variant_price_changes` | 9.844 khoảng trên 9.769 cặp. 58 cặp có hơn một khoảng. Tối đa 1 khoảng `is_current` mỗi cặp; test không chồng khoảng PASS. 2 khoảng bị thay trong cùng ngày (`valid_to_date < valid_from_date`, từ `history_log`) |
| Đổi giá giữa hai lần chụp | 0: không có khoảng `daily_capture` mới, hai lần chụp nối dài khoảng có sẵn. Giá ở lần chụp khớp phiên bản sản phẩm mới nhất |
| Tiêu chí 4 | 1.427/1.460 cặp đang có giá > 0 (**97,7%**, ngưỡng ≥ 95%) có khoảng từ ≤ 28/05/2026. Giá hiện hành khớp `fact_variant_prices_snapshot` ở **1.460/1.460** cặp |
| Daily so với snapshot cũ | Ngày mới nhất, giá > 0: 1.460/1.460 khớp |

### Trạng thái shadow

- `/home/vantt/app/fg-dw-shadow` 0700, gồm `lake-A` (b0931f33), `lake-AF`, `lake-base` (backup 17/10 và 16/10), `inventory/`.
- Lake tạm (`lake-S2`, `lake-T`) đã xoá. Không chép dữ liệu ra ngoài.
- Baseline worktree `fg-dw-baseline` ở `b0931f33`.
