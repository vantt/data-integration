# Deploy phase 6 (pack sản phẩm + tenant Fine Japan) — 14/10/2026 22:28

## Kết quả

Phase 6 đã lên prod và đang chạy xanh. `main` fast-forward `82368d21` → `64103e50` theo runbook
§ Refactor deploys, user cho phép deploy tối nay (cắt ở 02:15). Không có dấu hiệu cần rollback.

| Mốc | Giờ (ICT) |
|---|---|
| Snapshot instigator (26/26 running), không run đang chạy | 22:28:0x |
| `docker compose stop data_platform` (sau tick realtime 22:27) | 22:28:09 |
| `git merge --ff-only refactor/modularize-suite` | 22:28 |
| `docker compose start data_platform` | 22:28:19 |

Rollback point: `82368d21`; dải revert nếu cần: `82368d21..64103e50`.

## Trước deploy

- Phase 6 (`95e6d1d7`) rebase lên `main` `82368d21` (thêm ghim Evidence và backup Metabase,
  không file chung) → `64103e50`.
- Baseline gate dời lên `82368d21`, lake-A build lại 22:23 cùng ngày.
- Gate M PASS: golden 83/83 0 diff (cả trên rolling trống), dbt inventory 186/186 0 diff,
  compiled SQL 0/172 đổi, boundaries 33 known (dbt-ref 16, dbt-source 12, orch-import 5) 0 mới
  0 thừa, taxonomy 79 khối/46 domain 0 warning, Dagster inventory 0 diff, dbt subset qua Dagster
  PASS, pytest 237 pass.
- Checkout prod sạch về seed (chỉ `.claude/settings.json` và một file plan của user đổi; nhánh
  không đụng `plans/`).

## Sau deploy

- Container healthy; instigator 26/26, `instigator_state.py diff`: 0 difference.
- Log `data_platform` 10 phút đầu: không lỗi, không `TenantConfigError`; không seed trùng tên.
- Run trên code mới: `pipeline_sapo_v2_incremental_job`, `pipeline_sapo_v2_realtime_job`
  (nhiều lượt), `pipeline_hug_realtime_job` (22:28, 22:30) đều SUCCESS; không run FAILURE/CANCELED
  nào từ 22:28.
- Serving: 152 view (bản chép `olap.duckdb`, đã xoá sau khi đếm).
- **Nightly chạy tay** `2646613e-cc52-4d78-9664-44d4b7e70287` (22:32–22:37): SUCCESS, 55/55 step,
  487 check. So với `4c9d9ce6` (sau phase 4): **0 check đỏ mới**. Đỏ ở cả hai (có từ trước):
  `ingest_sapo_v2_customers_batch_asset` row_count_within_trend (WARN),
  `ingest_sapo_v2_products_batch_asset` freshness (ERROR),
  `sheets_{marketing_spend,targets,team_config}_asset` not_empty_when_expected (WARN).
  `ingest_sapo_v2_customers_batch_asset` freshness lần này xanh.
- **CRM:** `crm_cache_refresh` SUCCESS trong các run realtime và nightly, dùng URL từ
  `orchestration/tenants/fine_japan/config.py`; container `crm` nhận `POST /admin/refresh` 202;
  7 lượt reverse-ETL hoàn tất từ sau deploy, cả 11 bảng `wh_*` "ok". 11 asset `crm_*_export`
  (writeback) và `approach_script_autogen` SUCCESS trong nightly.
- **HUG:** `pipeline_hug_realtime_job` SUCCESS; model pack hug build trong nightly.

## Chưa kiểm / theo dõi tiếp

- Nightly theo lịch 15/10 03:00 trên `64103e50`: lần đầu theo lịch cho cả phase 4, 5 và 6 (lịch
  kiểm tra chỉ đọc lúc 03:17 vẫn còn trong session thực thi).
- `crm_backup_job` (02:00 hằng ngày) chạy lần đầu với URL backup/drill từ tenant config lúc 02:00
  ngày 15/10.
- Ghi seed thật trên prod qua `seed_paths.py` sau khi seed dời sang `seeds/tenants/fine_japan/`
  (budget sync dừng trước bước ghi cho tới khi sheet BUDGET_ITEMS được sửa).

## Nightly 15/10 03:00 (kiểm 15/10 ~09:55, chỉ đọc)

Lần chạy theo lịch đầu tiên trên code cuối của Đợt 1 (`8eb9920f`, gồm phase 4, 5, 6, 7): **xanh**.

- `pipeline_batch_nightly_job` `ffb92b66-47f7-4bc2-a2a9-b08b89efbfea` (03:00): SUCCESS, 55/55 step,
  487 check. So với nightly chạy tay sau phase 7 (`7e91d01c`): **0 check đỏ mới**, 0 hết đỏ; 5 đỏ có
  từ trước giữ nguyên (`customers_batch` row_count_within_trend WARN, `products_batch` freshness
  ERROR, `sheets_{marketing_spend,targets,team_config}` not_empty_when_expected WARN).
- Serving 152 view; instigator 26/26, không khác so với sau deploy phase 7.
- Mọi job từ 14/10 22:49 tới 15/10 09:55 SUCCESS (realtime 216, hug realtime 216, incremental 60,
  hourly 10, health, `maintain_backup_platform_job`, `maintain_cleanup_job`), trừ
  `budget_sheet_sync_job` 02:30 FAILURE (lỗi đã biết: sheet BUDGET_ITEMS dùng mã TK cha 112/334).
- `crm_backup_job` SUCCESS: lần đầu chạy với URL backup/drill lấy từ
  `orchestration/tenants/fine_japan/config.py`. **Đính chính (15/10, phase 0 plan DR):** job chạy lúc
  **09:00 giờ VN**, không phải 02:00 — schedule `0 2 * * *` thiếu `execution_timezone` nên chạy theo UTC.
- Backup 01:04 có bước export Metabase đầu tiên: 43 dashboard, 888 card, 23 collection, 0 cảnh báo.
