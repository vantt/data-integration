# Phase 1: báo cáo của worker (chụp hằng đêm vào raw)

> 15/10/2026 ~18:30 ICT. Worktree `/home/vantt/app/fg-dw-price`, nhánh `feat/price-inventory-history`, gốc `f7b59ef2` (= main trên prod). **Chưa commit**: coordinator commit và deploy. Kết quả phase 0: [phase-00-findings.md](phase-00-findings.md).

## Kết quả

Code sẵn sàng deploy. Gate `scripts/shadow/gate.sh S --allow-new` **PASS**: golden 0 khác biệt, dbt inventory và compiled SQL không đổi, dagster inventory chỉ có phần thêm, pytest 470 passed, lake rỗng, lõi trần và full refresh đều xanh. Lần chạy thử thật (chỉ GET, không ghi) code quét mới trên Sapo: **33,6 giây**, 12 trang, 560/560 sản phẩm, `coverage_ratio = 1.0`.

`scripts/checks/run-all.sh` báo FAIL ở bước 6 vì một lỗi **có sẵn trên main**, không do nhánh này gây ra: bước 6 gọi `scripts/checks/check_analytics_registry.py`, file này chưa từng được commit (không có trên mọi nhánh, cũng không có trong checkout prod). Phần pytest của bước 6 vẫn xanh (137 passed trên cả nhánh lẫn baseline). Bước 1–5 PASS.

## File đã sửa hoặc tạo (trong worktree)

| File | Thay đổi |
|---|---|
| `ingestion/src/sapo/products.py` | Tách hàm lồng `fetch_page_with_retry` thành hàm cấp module `fetch_products_page(client, session, page, page_size)`. Chỉ dời code: retry, tham số, thứ tự sắp xếp và log giữ nguyên |
| `ingestion/src/sapo/products_daily_snapshot.py` (mới) | `scan_catalogue` (quét tới trang rỗng, không cursor, không dừng sớm, khử trùng giữ `modified_on` lớn nhất, lỗi thì ném ra), `compact_product`, `build_envelopes`, `ict_partition`, `coverage_ratio`, resource dlt `product_daily_snapshot` (append, không có primary key) |
| `ingestion/run_sapo_v2_product_daily_snapshot.py` (mới) | Đọc toàn bộ danh mục trước, rồi mới gọi `pipeline.run` một lần. Pipeline `sapo_v2_product_daily_snapshot`, dataset `sapo_v2_raw`. Destination tự dựng với `extra_placeholders` = `daily_snapshot` + năm/tháng ICT của `captured_at`. Không có `--full-refresh` hay `--reset-cursor`. Từ chối ghi khi danh mục rỗng |
| `ingestion/tests/test_sapo_products_batch.py` (mới) | Ghim hành vi batch cũ: tham số request, envelope, dừng ở trang rỗng (thử lại một lần), dừng sớm theo cursor. Chạy xanh **trước và sau** khi tách hàm |
| `ingestion/tests/test_sapo_products_daily_snapshot.py` (mới) | 17 test, chỉ dùng sản phẩm giả: quét tới trang rỗng; khử trùng; lỗi trang 3 thì ném ra; cùng `captured_at`/`capture_run_id`; payload gọn; phân vùng theo ICT (31/10 23:30 UTC → tháng 11, 31/12 → 2027/1); `coverage_ratio`; qua dlt với layout của prod: một file ở `ingest_method=daily_snapshot/year=2026/month=10/`; run lỗi không ghi gì và run sau ghi đủ; run thứ hai thêm file và giữ file cũ; độ phủ thấp vẫn ghi kèm cảnh báo; danh mục rỗng bị từ chối |
| `orchestration/connectors/sapo_v2/assets.py` | Asset `ingest_sapo_v2_product_daily_snapshot_asset` (key `sapo/…`, group `sapo_ingestion`, `RetryPolicy(max_retries=2, delay=120)`). Metadata: số sản phẩm, số trang, `sapo_total`, `coverage_ratio`, `capture_run_id`, `captured_at`. Log `WARN` khi độ phủ < 0,98. Không có package nào được load thì fail. Ghi `ingestion_health` qua `record_run` (metadata gồm độ phủ) |
| `orchestration/connectors/sapo_v2/__init__.py` | Thêm asset vào `ASSETS`, `CHECK_ASSET_DEFS`, `NIGHTLY_ASSETS`, `DIGEST_ASSETS`/`DIGEST_DISPLAY` (`sapo_product_snapshot`, "Sapo ảnh chụp giá/tồn", `batch`, "sản phẩm"). `DBT_SOURCE_KEYS` để phase 2 |
| `orchestration/config/ingestion_sla.yaml` | `freshness_hours: 28`, `trend_min_ratio: 0.98` |
| `docs/architecture/modules.md` §5 | Số asset và runner sapo_v2 thành 8; nhánh chụp trong sơ đồ §5.2; đoạn mô tả asset, envelope, cơ chế tất cả hoặc không, theo dõi, "không dựng lại được, không xoá" |
| `docs/analytics-handbook/semantic/freshness.md` | Thêm một dòng SLA và mục "Price and Stock Position History — Nightly Capture" (tiếng Anh, theo ngôn ngữ của file) |

`orchestration/connectors/README.md` không liệt kê asset, nên không sửa. Tên file test theo phase file (`test_sapo_products_daily_snapshot.py`; `plan.md` ghi `test_products_daily_snapshot.py`). Có thêm `test_sapo_products_batch.py` cho bước 2 (test trước/sau khi tách hàm).

## Khác với phase file

1. **Check độ phủ** (yêu cầu 7): dùng check SLA có sẵn `row_count_within_trend` với `trend_min_ratio: 0.98`, không thêm `asset_check` riêng. Lý do ở phase-00 mục Tóm tắt 2:
   - Check gắn trong asset làm vỡ `health_checks_asset_job` (đã thử).
   - Check riêng phải sửa `definitions.py` hoặc hợp đồng connector, cả hai nằm ngoài quyền sở hữu file.

   Hệ quả:
   - Check so với trung vị 7 ngày, không so với tổng Sapo, và chỉ bật sau 7 ngày có dữ liệu.
   - Độ phủ so với tổng Sapo có trong metadata asset, `ingestion_health` và log `WARN`, nhưng không làm đỏ check nào.

   Nếu cần check so thẳng với tổng Sapo: thêm export `ASSET_CHECKS` vào hợp đồng connector (`definitions.py`, `connectors/__init__.py`, `test_load_enabled.py`, `modules.md` §5.1). Khoảng 30 dòng, có thể làm cùng phase 2.
2. **Thử lại trong cùng run:** thêm `RetryPolicy(max_retries=2, delay=120)` vì mất một đêm là mất vĩnh viễn. Trường hợp xấu nhất kéo dài step thêm khoảng 5 phút; trường hợp thường không ảnh hưởng.
3. **Bố cục file:** phải tự dựng destination với `extra_placeholders` (phase-00 mục Tóm tắt 1); `layout` của config không đổi.

## Runbook deploy D1

Theo "Refactor deploys (shadow-verified)" (`docs/operations/deployment.md:667-748`). Giờ deploy: chờ user duyệt, ngoài 02:30–04:00. Nên deploy **trước 02:30 đêm nay** để nightly 03:00 chụp được ngày 15/10.

**`docker-compose.yml` không đổi** (code được bind-mount: `./ingestion`, `./orchestration`), nên bước 5 dùng `docker compose start data_platform`. Không cần rebuild image: dlt 1.29.1, Dagster 1.13.17, `zoneinfo` và pyarrow đều đã có trong image.

0. Coordinator commit trên nhánh (code và tài liệu cùng một commit). Lưu ý: checkout prod hiện có thay đổi đã track sẵn từ trước (`.claude/settings.json` và 3 file `plans/*/plan.md`). Bước 3 của runbook yêu cầu xử lý chúng trước; nhánh này không đụng các file đó.
1. `python3 scripts/checks/instigator_state.py capture --out /tmp/instigators-before.json`
2. `docker compose stop data_platform`
3. `git -C /home/vantt/app/fg-dataware-house status --short` (commit nội dung seed đang sống nếu có)
4. ```bash
   BRANCH=feat/price-inventory-history
   git -C /home/vantt/app/fg-dataware-house rev-parse HEAD > /tmp/deploy-rollback-sha
   git -C /home/vantt/app/fg-dataware-house rev-parse "$BRANCH" > /tmp/deploy-branch-sha
   git -C /home/vantt/app/fg-dataware-house merge --ff-only "$BRANCH"
   git diff "$(cat /tmp/deploy-rollback-sha)" "$(cat /tmp/deploy-branch-sha)" -- docker-compose.yml   # phải rỗng
   ```
5. `docker compose start data_platform`
6. `instigator_state.py capture --out /tmp/instigators-after.json` rồi `diff`, phải không đổi. Chạy một `pipeline_sapo_v2_realtime_job` trong UI, phải xanh.
7. **Chạy tay lần đầu** (ngoài 02:30–04:00): trong Dagster UI, Assets → `sapo/ingest_sapo_v2_product_daily_snapshot_asset` → Materialize. Asset này không có upstream, nên chỉ chạy đúng nó, không kéo theo dbt. Lần chạy này ghi cho `as_of_date` = ngày deploy (chụp giữa ngày); nightly 03:00 kế tiếp sẽ thay nó cho cùng ngày. Kiểm tra:
   ```bash
   docker exec data_platform sh -c 'ls -la /app/var/data_lake/sapo_v2_raw/product_daily_snapshot/ingest_method=daily_snapshot/year=2026/month=10/'
   docker exec -i data_platform python - <<'EOF'
   import duckdb
   p = "/app/var/data_lake/sapo_v2_raw/product_daily_snapshot/ingest_method=daily_snapshot/*/*/*.parquet"
   print(duckdb.sql(f"""select capture_run_id, min(captured_at) captured_at, count(*) rows,
       count(distinct entity_id) products, count(distinct captured_at) n_ts
       from read_parquet('{p}') group by 1 order by 2""").fetchall())
   EOF
   docker exec -i data_platform python - <<'EOF'
   import sqlite3
   con = sqlite3.connect("file:/app/var/data_lake/monitoring/ingestion_health.db?mode=ro", uri=True)
   print(con.execute("""select status, rows_written, json_extract(metadata_json,'$.coverage_ratio'),
       json_extract(metadata_json,'$.sapo_total'), duration_s from ingestion_runs
       where asset_key='sapo/ingest_sapo_v2_product_daily_snapshot_asset'
       order by run_started_at desc limit 3""").fetchall())
   EOF
   ```
   Kỳ vọng:
   - Đúng một file parquet, `rows = products` ≈ 560, `n_ts = 1`.
   - Metadata asset: `coverage_ratio` ≥ 0,98, `pages` = 12.
   - `ingestion_runs`: `success`, thời lượng khoảng 30–60 giây.
   - Trong UI, chạy check `freshness` của asset (hoặc chờ `health_checks_asset_job`): phải xanh. `row_count_within_trend` sẽ báo "insufficient history" trong 7 ngày đầu (bình thường).
8. **Nightly kế tiếp** (03:00):
   - Asset xanh và có thêm một file.
   - Batch `sapo_products` trong digest vẫn bình thường (kiểm việc tách hàm).
   - Nightly xong trước khoảng 03:20.
   - Digest buổi sáng có dòng "Sapo ảnh chụp giá/tồn".

## Rollback

Theo runbook (`deployment.md:732-748`): `docker compose stop data_platform`; `git revert --no-edit "$(cat /tmp/deploy-rollback-sha)".."$(cat /tmp/deploy-branch-sha)"`; `docker compose start data_platform` (compose không đổi nên `start` là đủ). Phần còn lại sau rollback:

- `app_data/data_lake/sapo_v2_raw/product_daily_snapshot/`: **giữ nguyên, không xoá**. Đó là lịch sử đã chụp, và không có ai khác đọc nó.
- State dlt `sapo_v2_product_daily_snapshot` trong `sapo_v2_raw/_dlt_pipeline_state` và `_dlt_loads`: vô hại.
- Các dòng `ingestion_runs` của asset: vô hại, hết sau 90 ngày.

## Ghi chú DR

`app_data/data_lake/sapo_v2_raw/product_daily_snapshot/` là dữ liệu **không dựng lại được** (append-only, giữ vĩnh viễn). Nó đã có dòng riêng trong bảng phân loại của plan DR (`plans/261015-1140-backup-restore-dr/design.md:85`, lên off-site, "không chạy lại full refresh đè lên"). Thư mục cha `sapo_v2_raw` lên off-site nguyên thư mục (dòng 83), nên không cần đổi danh sách include.

Cho tới khi DR phase 2 (off-site) chạy, lịch sử chỉ nằm trên cùng ổ, cộng 7 bản backup cục bộ. Đây là rủi ro tạm đã được chấp nhận trong `plan.md`.

## Shadow

- Baseline đã dời từ `69e021f4` sang `f7b59ef2`. lake-A được build lại, golden capture lại 83/83 bảng, `dbt-main.json` và `dagster-main.json` export lại từ worktree baseline (harness §9.2).
- Gate xoá lake của nhánh khi xong. Lake tạm `lake-T` (dùng chạy pytest) đã xoá. `/home/vantt/app/fg-dw-shadow` vẫn 0700; không có dữ liệu nào được chép ra ngoài.
- Còn lại: `lake-A`, `lake-AF`, `lake-base`, `inventory/` cho các gate sau.

---

## Deploy D1 (15/10/2026 18:52, user duyệt 18:25)

`main` fast-forward `f7b59ef2` → `b0931f33` (`7c11ddfb` theo dõi `check_analytics_registry.py` +
`b0931f33` phase 1) theo runbook: stop `data_platform` 18:52:05, merge, start 18:52:16 (không đổi
`docker-compose.yml`). Rollback point `f7b59ef2`; khi revert **giữ nguyên**
`sapo_v2_raw/product_daily_snapshot/` (lịch sử không chụp lại được).

Sau deploy: healthy; instigator 28/28 `diff` 0; log không lỗi. Chạy asset một lần
(`dagster asset materialize --select sapo/ingest_sapo_v2_product_daily_snapshot_asset`, 18:52):
SUCCESS; một file `product_daily_snapshot/ingest_method=daily_snapshot/year=2026/month=10/*.parquet`,
**560 dòng, 560 sản phẩm, một `captured_at`**; `ingestion_runs` `success`, 560 dòng; check
`freshness` và `not_empty_when_expected` pass, `row_count_within_trend` tạm tắt (cần 7 ngày lịch sử).
`main` đã push. Lần chụp theo lịch đầu tiên: nightly 16/10 03:00 (tính cho ngày 15/10 theo mốc 06:00).

## Lần chụp theo lịch đầu tiên (16/10 03:01, kiểm 09:23): đạt

- Trong nightly `3af400cf-2333-46db-a2f6-580655158eb8` (SUCCESS 03:01, 5,3 phút), step
  `sapo__ingest_sapo_v2_product_daily_snapshot_asset` SUCCESS; các check `freshness`,
  `not_empty_when_expected`, `row_count_within_trend` SUCCESS.
- `product_daily_snapshot/ingest_method=daily_snapshot/year=2026/month=10/` có 2 file: 15/10 18:52
  (560 dòng, 560 sản phẩm) và 16/10 03:01 (560 dòng, 560 sản phẩm), mỗi file một `captured_at`,
  ~437 KB mỗi file.
- Backup 17/10 01:04 sẽ chứa cả hai lần chụp, đủ điều kiện chạy gate phase 2 (lịch 17/10 09:47).
