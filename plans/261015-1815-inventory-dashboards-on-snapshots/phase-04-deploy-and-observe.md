# Phase 4: deploy, cập nhật card, theo dõi 3 đêm, đóng plan

**Effort:** 0.25d + 3 đêm theo dõi · **Phụ thuộc:** phase 3 đã được user duyệt; prod có **7 đêm chụp liên tiếp**, mỗi đêm `coverage_ratio ≥ 0,98`; nightly gần nhất xanh · **Đụng prod:** có · **Cần user:** duyệt giờ deploy (ngoài 02:30–04:00)

## Bối cảnh

- Runbook: "Refactor deploys (shadow-verified)", `docs/operations/deployment.md:668-748`. Bước 1: chụp trạng thái schedule/sensor. Bước 2: dừng `data_platform`. Bước 3: làm sạch checkout. Bước 4: ghi SHA rollback và `merge --ff-only`. Bước 5: khởi động. Bước 6: kiểm trạng thái và chạy tay một `pipeline_sapo_v2_realtime_job`. Bước 7: theo dõi nightly.
- `pipeline_sapo_v2_realtime_job` build mọi model dbt trừ `NIGHTLY_ONLY_ASSETS`, rồi `build_serving_db` (`orchestration/connectors/sapo_v2/jobs.py:15-21`). `fact_inventory_snapshot`, `mart_inventory_health` và `mart_product_health` không nằm trong `NIGHTLY_ONLY_ASSETS` (`orchestration/job_support.py:26-30`). Vì vậy lần chạy tay ở bước 6 đã đưa số mới lên serving, không cần materialize riêng.
- Kiểm tra số dòng (`row_trend_checks`) chỉ áp cho asset ingestion (`orchestration/definitions.py:288`). Số dòng `fact_inventory_snapshot` tăng từ 2.052 lên khoảng 2.052 × số đêm, và điều này không làm check nào đỏ.

## Các bước

1. **Trước giờ deploy:**
   - Xác nhận điều kiện 7 đêm: đếm `as_of_date` khác nhau, liên tiếp nhau, trong `fact_inventory_position_daily` trên prod.
   - Chụp hai dashboard bằng `capture_dashboard.js` vào `reports/metabase-before/` (bản rollback).
   - Báo người dùng dashboard tồn kho và CRM rằng số sẽ đổi, kèm tóm tắt `change-list.md`.
2. **Deploy dbt** theo runbook bước 1–6, với `BRANCH=feat/inventory-on-daily-snapshots`. Nhánh không đổi `docker-compose.yml`, nên dùng `docker compose start`.
3. **Kiểm ngay sau bước 6** (chỉ đọc, chỉ số tổng hợp):
   - `MAX(snapshot_date)` = ngày hôm qua (ICT). Số cặp ở ngày đó bằng số cặp của `fact_inventory_position_daily` cùng ngày.
   - 0 dòng trước ngày chụp đầu tiên (nếu QĐ-TK-02 = (a)).
   - Chạy lại script đo của phase 3 trên prod với `snapshot_date = as_of_pin`. Số card phải bằng số đã duyệt. Nếu khác, chỉ chấp nhận khi chứng minh được Sapo đã sửa dữ liệu ngày đó; nếu không chứng minh được thì rollback.
   - Asset check `assert_inventory_snapshot_onhand_matches_ledger` xuất hiện trên `fact_inventory_snapshot` trong Dagster và đã chạy.
   - Serving `serving/olap.duckdb` có view `fact_inventory_snapshot` với ba cột mới.
4. **Deploy card Metabase** ngay sau khi bước 3 đạt:
   - `node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/product_inventory_stock_health.md`, rồi làm tương tự với `product_health_overview.md` nếu blueprint này có đổi.
   - Log chỉ được có "updating", không có card mới.
   - Mở dashboard trên UI: thẻ "Chu kỳ báo cáo" hiện ngày hôm qua; card OOS khớp số đã duyệt; thử bộ lọc kho.
5. **CRM:** sau lần sync kế tiếp, đếm dòng `wh_deadstock_target` và số sản phẩm có `oos_risk` trong cache. Chúng phải khớp số "sau" trong `change-list.md` (cùng ngày).
6. **Theo dõi 3 đêm.** Mỗi sáng ghi vào `reports/observation.md`:
   - Nightly xanh.
   - `MAX(snapshot_date)` tăng đúng một ngày.
   - Số cặp theo `on_hand_recon_status`.
   - Asset check đối soát xanh, hoặc lý do nếu vàng.
   - Thời gian build của `fact_inventory_snapshot` và `mart_inventory_health` trong job realtime.
7. **Đóng plan:**
   - Chuyển các QĐ sang `đã áp: <commit>` trong [definition-decisions.md](definition-decisions.md).
   - Báo coordinator cho plan report-productization (INV-D phase 12, INV-W/INV-M phase 14) rằng nguồn tồn kho đã đúng, kèm định nghĩa OOS đã chốt.
   - Chạy `ak plan --help`, rồi đổi trạng thái plan bằng CLI. Không sửa tay.

## Kiểm chứng (tiêu chí chấp nhận 1, 2, 3, 6, 7 của plan.md)

| Kiểm | Đạt khi |
|---|---|
| Ngày dữ liệu | `MAX(snapshot_date)` = hôm qua, ở ngày deploy và cả 3 đêm sau |
| Độ phủ | Số cặp ngày mới nhất = số cặp của `fact_inventory_position_daily` |
| Số đã duyệt | Script đo ở `as_of_pin` trên prod cho chênh 0 |
| Đối soát | Asset check chạy mỗi build; số cặp `mismatch` ≤ ngưỡng, hoặc có ghi chú nguyên nhân |
| Card | Không có card mới; ba card "Chu kỳ báo cáo" hiện ngày dữ liệu |
| Hiệu năng | Mỗi model dưới 5 giây/run trong job realtime; nếu vượt thì mở việc đưa vào `NIGHTLY_ONLY_ASSETS` |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Người dùng thấy số nhảy và nghĩ là lỗi | Cao × Trung bình | Báo trước (bước 1); thẻ "Chu kỳ báo cáo" hiện ngày dữ liệu; text nguồn giải thích |
| Có dashboard đọc dữ liệu mới trong khoảng giữa lúc deploy dbt và lúc deploy card | Chắc chắn × Thấp | Deploy card ngay sau bước 3, trong cùng khung giờ |
| Nightly đầu tiên sau deploy đỏ vì lý do khác | Thấp × Trung bình | Luật đóng băng của runbook: không deploy khi nightly đang đỏ |

## Rollback

Thứ tự ngược với lúc deploy:
1. **Metabase:** deploy lại blueprint ở commit trước deploy (PUT tại chỗ), hoặc khôi phục theo `reports/metabase-before/`.
2. **dbt:** runbook Rollback (`deployment.md:733-748`): dừng `data_platform`, `git revert` phạm vi đã deploy, rồi khởi động. Lần chạy realtime kế tiếp build lại `fact_inventory_snapshot` từ `int_sapo_inventories` (không đổi), nên trả về đúng số cũ. Kiểm bằng golden lake-A hoặc bằng số "trước" trong `change-list.md`.
3. **CRM:** lần sync kế tiếp tự lấy lại số cũ.

Phần còn lại sau rollback:
- File parquet rolling có ba cột mới vẫn nằm trong `export/marts/rolling/fact_inventory_snapshot/` cho tới khi GC giữ 3 bản mới nhất đẩy chúng ra. Vô hại, vì serving đọc file mới nhất.
- Không có gì cần dọn trong raw.
