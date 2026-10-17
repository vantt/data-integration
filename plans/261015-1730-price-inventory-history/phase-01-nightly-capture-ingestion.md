# Phase 1: chụp hằng đêm vào raw

**Effort:** 0.75d · **Phụ thuộc:** phase 0 (Q3 gọn/đầy đủ, Q5 giờ deploy) · **Gate:** `scripts/shadow/gate.sh S --allow-new` · **Deploy:** D1, giờ user duyệt

## Bối cảnh

- Batch sản phẩm hiện có lấy theo `modified_on DESC`, dừng sớm khi gặp `min_overlap_items` sản phẩm cũ liên tiếp (`ingestion/src/sapo/products.py:84-96,192,238`), ghi vào `product` (`:67-82`, `write_disposition="append"`).
- Phần lấy trang (retry, làm mới phiên khi gặp 401/403, chờ khi gặp 429) là hàm lồng `fetch_page_with_retry` (`products.py:125-175`).
- Runner: `ingestion/run_sapo_v2_products_batch.py:11-26`, gọi `run_pipeline` (`ingestion/src/utils/pipeline_runner.py`).
- Asset: `ingest_sapo_v2_products_batch_asset` (`orchestration/connectors/sapo_v2/assets.py:239-280`).
- Các export của connector (`orchestration/connectors/sapo_v2/__init__.py:16-89`):
  - `ASSETS`
  - `CHECK_ASSET_DEFS` (`:27-34`)
  - `NIGHTLY_ASSETS` (`:37-43`, vào `_nightly_batch_selection` ở `orchestration/definitions.py:94-101`)
  - `DIGEST_ASSETS` / `DIGEST_DISPLAY` (`:46-64`)
  - `DBT_SOURCE_KEYS` (`:74-82`)
- SLA: `orchestration/config/ingestion_sla.yaml:30-31` (`freshness_hours: 28`).

## Yêu cầu

1. Mỗi đêm có một run quét **mọi** trang `products.json`, không dùng cursor và không dừng sớm. Kết quả ghi vào resource dlt mới `product_daily_snapshot` (`write_disposition="append"`, không có `primary_key` để dlt không merge).
2. Envelope mỗi dòng:
   - `entity_id`, `entity_type='product'`
   - `ingest_method='daily_snapshot'`
   - `captured_at`: timestamp UTC lúc bắt đầu run, **một giá trị cho cả run**
   - `capture_run_id`
   - `modified_on`
   - `payload_hash`
   - `payload`: gọn hoặc đầy đủ theo Q3
   - `year`, `month`: theo `captured_at` giờ ICT, là cột partition theo `layout` chung
3. Trong một run, khử trùng `entity_id`, giữ `modified_on` lớn nhất.
4. Tất cả hoặc không có gì: lỗi giữa chừng thì run fail và không load gì. Generator ném lỗi trước khi dlt load, nên không có package nào hoàn tất. Kiểm điều này bằng test.
5. Metadata của asset ghi: số sản phẩm, số trang, tổng Sapo, `coverage_ratio`. Nếu `coverage_ratio < 0.98` thì ghi `WARN` vào log, kèm check (yêu cầu 7).
6. Asset `ingest_sapo_v2_product_daily_snapshot_asset` (key `sapo/ingest_sapo_v2_product_daily_snapshot_asset`) được thêm vào `ASSETS`, `NIGHTLY_ASSETS`, `CHECK_ASSET_DEFS` và `DIGEST_ASSETS`/`DIGEST_DISPLAY` (nhãn "Sapo ảnh chụp giá/tồn", loại `batch`, đơn vị "sản phẩm"). SLA `freshness_hours: 28`. Asset ghi `ingestion_health` qua `record_run` như các asset batch khác.
7. Check độ phủ: dùng cơ chế check có sẵn theo SLA nếu nó đọc được metadata. Nếu không, thêm một `asset_check` nhỏ trong `orchestration/connectors/sapo_v2/` đọc `coverage_ratio` của lần materialize gần nhất, severity WARN. Phase 0 xác nhận cơ chế nào áp dụng được; chọn cách ít code nhất.
8. **Không đổi hành vi batch sản phẩm hiện có.** Chỉ tách `fetch_page_with_retry` thành hàm cấp module `fetch_products_page(client, session, page, page_size)` trong `products.py` và gọi lại từ cả hai resource. Tham số, thứ tự sắp xếp, retry và log giữ nguyên.

## File

- Sửa: `ingestion/src/sapo/products.py` (tách hàm lấy trang, không đổi logic), `orchestration/connectors/sapo_v2/assets.py` (asset mới), `orchestration/connectors/sapo_v2/__init__.py` (bốn danh sách export), `orchestration/config/ingestion_sla.yaml` (một mục).
- Tạo: `ingestion/src/sapo/products_daily_snapshot.py` (source/resource), `ingestion/run_sapo_v2_product_daily_snapshot.py` (runner, cùng mẫu với `run_sapo_v2_products_batch.py`), `ingestion/tests/test_sapo_products_daily_snapshot.py`.
- Tài liệu (cùng commit):
  - `docs/architecture/modules.md` §5.2: thêm nhánh capture vào sơ đồ và bảng asset, số asset sapo_v2 thành 8.
  - `docs/analytics-handbook/semantic/freshness.md`: thêm một dòng cho raw ảnh chụp, ghi rõ "không dựng lại được, mất ngày nếu lỡ nightly".
  - `orchestration/connectors/README.md` nếu nó liệt kê asset.

## Các bước

1. Tạo worktree `feat/price-inventory-history` từ `main`.
2. Tách `fetch_products_page`. Viết pytest cho batch hiện có trước khi tách: session giả trả 2 trang rồi trang rỗng, xác nhận dừng sớm và envelope không đổi. Sau khi tách, chạy lại cùng test.
3. Viết `products_daily_snapshot.py` và runner. Pipeline name riêng (`sapo_v2_product_daily_snapshot`), `dataset_name="sapo_v2_raw"`.
4. Viết asset, các export và SLA.
5. Chạy pytest (`ingestion/tests`, `orchestration`), rồi `scripts/shadow/gate.sh S --allow-new`.
6. Deploy D1 theo runbook (bước 1–7). Bước 6: chạy tay **một** lần asset mới trong Dagster UI (ngoài 02:30–04:00) và xác nhận có file raw. Sau đó theo dõi nightly kế tiếp.

## Ma trận test

| Mức | Nội dung |
|---|---|
| Unit (pytest, session HTTP giả, sản phẩm giả) | Quét tới trang rỗng, không dừng sớm. Sản phẩm trùng giữa hai trang chỉ còn một, giữ `modified_on` lớn nhất. Mọi dòng có cùng `captured_at` và `capture_run_id`. `year`/`month` tính theo ICT (run 23:30 UTC ngày 31 → tháng sau). Payload gọn giữ đủ `variant_prices` và `inventories`. Lỗi HTTP ở trang 3 thì không có dòng nào được yield ra load. Hàm `coverage_ratio` đúng |
| Unit (batch cũ) | Hành vi `products` không đổi sau khi tách hàm (cùng fixture, cùng envelope, cùng điểm dừng) |
| Tích hợp (gate S) | Golden 0 khác biệt (dbt không đổi). Dagster inventory: một asset mới, selection của `pipeline_batch_nightly_job` và `pipeline_batch_fullrefresh_job` có thêm asset đó, các job khác không đổi. pytest xanh |
| Prod (sau D1) | Lần chạy tay: một file trong `sapo_v2_raw/product_daily_snapshot/ingest_method=daily_snapshot/year=2026/month=10/`, số sản phẩm ≈ tổng Sapo. Nightly kế tiếp: asset xanh, có thêm file, nightly vẫn xong trước 03:20 (p95 cũ khoảng 03:14, F-Q12). Digest có dòng mới |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Tách hàm làm đổi hành vi batch sản phẩm | Thấp × Cao | Test trước/sau khi tách; diff chỉ là dời code; theo dõi `sapo_products` trong digest đêm đầu |
| Thêm khoảng 12 request mỗi đêm làm chạm rate limit | Thấp × Thấp | Dùng lại `request_delay` và xử lý 429 có sẵn |
| Nightly dài hơn, lấn khung backup hoặc off-site 03:30 | Thấp × Trung bình | Đo thời lượng ở lần chạy tay. Nếu > 2 phút thì báo lại trước khi để vào nightly |
| Shadow không có mạng nên không chạy thật được asset | Chắc chắn × Thấp | Test với fixture, chạy tay một lần sau deploy (harness §10) |

## Rollback

Theo runbook: `git revert` phạm vi đã deploy, rồi `docker compose start data_platform`. Phần còn lại sau rollback:
- Thư mục `sapo_v2_raw/product_daily_snapshot/`: **giữ nguyên**, vì không ai đọc và đó là lịch sử đã chụp.
- State pipeline dlt `sapo_v2_product_daily_snapshot` trong `_dlt_pipeline_state`: vô hại.
- Dòng `ingestion_runs` của asset mới: vô hại, hết sau 90 ngày.
