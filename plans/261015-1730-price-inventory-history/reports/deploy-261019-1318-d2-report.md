# Deploy D2 (lịch sử giá/tồn) + công tắc tắt sinh kịch bản tiếp cận — 19/10/2026 13:18

## Kết quả

D2 đã lên prod và chạy xanh, cùng một lần dừng với công tắc `APPROACH_SCRIPT_AUTOGEN_ENABLED`
(user duyệt 19/10 13:12, "làm luôn"). `main` fast-forward `aa3a5cfb` → `371461cf` theo runbook
§ Refactor deploys: stop `data_platform` 13:18:38, `git merge --ff-only`, start 13:19:01 (không đổi
`docker-compose.yml`). Rollback point `aa3a5cfb`; dải revert `aa3a5cfb..371461cf`. Sau rollback còn
lại (vô hại): 3 thư mục rolling và 6 view serving của các bảng mới, các bảng staging mới trong
warehouse.

| Commit | Nội dung |
|---|---|
| `d2c65b2e` | Model lịch sử: `fact_variant_price_daily`, `fact_variant_price_changes` (SCD2), `fact_inventory_position_daily` và staging/cdm |
| `1c4c1235` | Gate: asset bắt đầu đại diện cho một dbt source mới chỉ báo INFO (user chấp nhận 18/10) |
| `b6afc53b` | Golden: thêm 3 bảng vào `public_models.yaml` |
| `371461cf` | Công tắc tenant tắt `approach_script_autogen` (Fine Japan: tắt); lỗi codex giữ 500 ký tự cuối của stderr |

## Trước deploy

- Ba commit lịch sử giá: rebase lên `main`, diff code so với bản đã qua gate S (`66de4202`) giống hệt
  từng dòng.
- Công tắc: `run-all.sh` PASS (dbt parse, boundaries, Dagster definitions, pytest 489 + 137 test,
  selftest phân loại 43). Dagster inventory giữa `b6afc53b` và `371461cf`: 0 khác biệt (asset, check,
  job, schedule giữ nguyên). Không đổi dbt nên không cần golden.

## Sau deploy

- Healthy; instigator 28/28 `diff` 0; log không lỗi. Run đầu tiên trên code mới lúc 13:28 (khởi
  động chạy lại `dbt deps` và `dbt parse`); không run FAILURE/CANCELED từ 13:19.
- Materialize một lần 12 asset nightly-only (9 model mới, 2 seed capability, `mart_capabilities`),
  run `afaf0b36`: SUCCESS, 58 check xanh. Không chạy tay nightly (theo phase 2 bước 9).
- `build_serving_db` (run `284ed758`): SUCCESS, rolling 98 bảng. View mới cần
  `bootstrap_serving_views.py`: dừng Metabase 13:32:23, chạy, bật lại 13:32:27, healthy.
  Serving từ 152 lên 158 view (3 bảng × `main` và `main_marts`); "dropped=19" là các thư mục rỗng,
  không mất view nào.
- Số liệu:
  - `fact_variant_price_daily` có `as_of_date` 15–18/10, mỗi ngày khoảng 9.750 dòng, 1.459–1.460 cặp
    có giá (số đo 15/10: 1.460).
  - `fact_inventory_position_daily` 15–18/10, 2.046–2.052 dòng mỗi ngày (số đo 15/10: 2.052).
  - Tiêu chí 4: giá hiện hành của 1.459 cặp có giá khớp `fact_variant_prices_snapshot`, 0 cặp lệch.
    Một cặp chỉ có trong snapshot (variant `179685988`, SKU `VTCP22166T001`, bảng giá BANLE): variant
    không có trong lần chụp 19/10 nên khoảng giá đóng ở 17/10, đúng thiết kế (variant biến mất thì
    khoảng đóng).
- Công tắc: trong container `autogen_enabled()` = False; nightly 20/10 sẽ ghi `disabled` cho
  `approach_script_autogen` thay vì 3 phút gọi codex.

## Theo dõi nightly 20/10

- Nightly xanh; `approach_script_autogen` trả về `disabled`.
- `fact_variant_price_daily` và `fact_inventory_position_daily` có thêm đúng một `as_of_date` (19/10).
