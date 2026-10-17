# Phase 0: kiểm tiền điều kiện, hiệu chỉnh đối soát, kiểm kê card thật

**Effort:** 0.25d · **Phụ thuộc:** plan lịch sử giá/tồn đã deploy D2, prod có ≥ 2 đêm chụp · **Đụng prod:** chỉ đọc · **Cần user:** chốt QĐ-TK-01 đến 05 trước khi sang phase 1

## Bối cảnh

- Plan lịch sử giá/tồn tạo `fact_inventory_position_daily` với grain (`variant_id`, `location_id`, `as_of_date`) và các cột `on_hand`, `available`, `committed`, `incoming`, `onway`, `min_value`, `max_value`, `mac`, `location_name`, `location_code`, `captured_at` (`plans/261015-1730-price-inventory-history/phase-02-history-models.md:335,341`). Danh sách đó **không có** `bin_location` và `wait_to_pack`, trong khi `fact_inventory_snapshot` hiện có hai cột này (`fact_inventory_snapshot.sql:52-53,144-145`).
- Sổ kho: `fact_inventory_movements` có `onhand` sau từng giao dịch và `issued_at` (`transformation/models/core/marts/inventory/fact_inventory_movements.sql:32,65`), build mỗi giờ (tag `hourly`, `transformation/models/core/marts/inventory/_core__models.yml:58`; job `pipeline_sapo_v2_hourly_job`, `orchestration/connectors/sapo_v2/jobs.py:38-46`).
- dagster-dbt trong container là 0.29.17. dbt test được đưa vào Dagster thành asset check của model mà test ref tới. Với singular test, việc gắn vào đúng model cần được xác nhận **[UNVERIFIED]**.

## Việc

1. **Tiền điều kiện:** xác nhận `fact_inventory_position_daily` có trên `main` và trên prod, và đếm số `as_of_date` khác nhau. Ghi ngày chụp đầu tiên (`first_capture_date`) và dự kiến ngày đủ 7 đêm.
2. **Kiểu cột:** đọc kiểu của mọi cột `fact_inventory_snapshot` hiện tại (`DESCRIBE` trên parquet rolling) và kiểu của `fact_inventory_position_daily`. Lập bảng cast cần thiết. Dự kiến: `variant_id` BIGINT, `location_id` VARCHAR, các cột tồn DECIMAL(18,4), `snapshot_date` DATE, `source_timestamp` TIMESTAMPTZ. Lấy theo số đo thật, không theo dự kiến.
3. **Hai cột còn thiếu:** nếu `fact_inventory_position_daily` chưa có `bin_location` và `wait_to_pack`, hỏi chủ plan lịch sử (qua coordinator) có thêm được không. Nếu không, phase 1 thêm vào ba model của chuỗi đó (chỉ thêm cột ở cuối).
4. **Hiệu chỉnh đối soát:** với mỗi đêm đã chụp, đếm theo ba trạng thái (`match`, `no_ledger_history`, `mismatch`), dùng đúng quy tắc của phase 1 (số dư sổ kho tại `captured_at`). Ghi phân bố số cặp `mismatch` theo đêm, p50/p95/max, và số cặp lệch hai đêm liên tiếp. Đề xuất ngưỡng theo QĐ-TK-07. Chỉ ghi số tổng hợp.
5. **Kiểm kê card thật trên Metabase** (chỉ đọc qua API): lấy mọi card mà SQL native nhắc tới `fact_inventory_snapshot`, `mart_inventory_health`, `mart_product_health`, `mart_product_action_queue` hoặc `mart_deadstock_target_queue`, cùng mọi card query builder trỏ tới các bảng đó (theo `table_id`). Ghi id card, tên, dashboard, collection. Chụp hai dashboard bằng `node .skills/metabase-automation/scripts/capture_dashboard.js <id> reports/metabase-before/<slug>.md` và so với blueprint, để thấy drift giữa bản thật và blueprint.
6. **Người dùng khác:** grep lại Evidence (`evidence/pages`, `evidence/areas`), Rill (`rill/models`, `rill/dashboards`), `analytics/registry`, `detailView`, `crm/sync`. Ngày 15/10/2026 chỉ có CRM (`crm/sync/duckdb_reader.py:100-110,470-500`) đọc các bảng này; Evidence và Rill chưa có trang tồn kho.
7. **Asset check:** trên shadow, thêm thử một singular test chỉ ref `fact_inventory_snapshot`, chạy `scripts/checks/dagster_inventory.py export` và xác nhận check xuất hiện dưới asset `fact_inventory_snapshot`. Nếu nó không gắn vào model, chuyển sang generic test khai báo trong YAML của model (gắn chắc chắn) với cùng logic.
8. **Gửi user** [definition-decisions.md](definition-decisions.md), thay số "ước lượng" bằng số đo trên các đêm đã chụp nếu đã có.

## Đầu ra

`reports/phase-00-baseline.md` gồm: ngày chụp đầu tiên, số đêm, bảng kiểu cột, kết quả hai cột còn thiếu, phân bố đối soát và ngưỡng đề xuất, danh sách card thật (id, tên, dashboard), drift so với blueprint, cách gắn asset check đã xác nhận.

## Tiêu chí xong

- Mọi mục trên có số đo hoặc kết quả, không còn `[UNVERIFIED]`.
- QĐ-TK-01 đến 05 có trạng thái `đã chốt`.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Card thật khác blueprint (đã sửa tay trên UI) | Trung bình × Trung bình | Bước 5 lấy SQL từ API, không từ blueprint; phase 2 sửa blueprint theo bản thật trước rồi mới đổi |
| Truy vấn API Metabase vô tình ghi | Thấp × Cao | Chỉ dùng GET; `capture_dashboard.js` chỉ đọc |

## Rollback

Không có thay đổi. Card thử trên shadow bị xoá cùng worktree.
