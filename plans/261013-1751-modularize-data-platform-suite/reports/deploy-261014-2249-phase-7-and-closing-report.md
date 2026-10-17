# Deploy phase 7 và đóng Đợt 1 — 14/10/2026

## Kết quả

Phase 7 đã lên prod lúc 22:49 và chạy xanh. Đợt 1 (module hoá suite data platform) đã đóng:
cả 8 phase trên prod, dữ liệu shadow và worktree đã dọn. Còn một xác nhận: nightly theo lịch
03:00 ngày 15/10 trên code cuối (`8eb9920f`), do lịch kiểm tra 03:17 của session thực thi ghi vào
các báo cáo deploy.

## Deploy phase 7

`main` fast-forward `64103e50` → `8eb9920f` (`refactor/phase-7`: `89d9fb14` ADR + rule dbt-seed +
URL sheet chỉ từ env + `run-all.sh`; `8eb9920f` dời tools offline ra `~/.cache/fg-dw-tools/deps`),
theo runbook, user cho phép deploy tối nay.

| Mốc | Giờ (ICT) |
|---|---|
| Snapshot instigator 26/26, không run đang chạy | 22:49 |
| Stop `data_platform` (sau tick realtime 22:48) | 22:49:06 |
| `git merge --ff-only refactor/phase-7` | 22:49 |
| Start `data_platform` | 22:49:17 |

Rollback point `64103e50`; dải revert nếu cần `64103e50..8eb9920f`.

Trước deploy:

- Gate M trên `89d9fb14` và lại trên `8eb9920f` (baseline `64103e50`, build cùng ngày): PASS,
  golden 83/83 0 diff (cả rolling trống), dbt inventory 186/186 0 diff, compiled SQL 0/172,
  boundaries 36 known (dbt-ref 16, dbt-seed 3, dbt-source 12, orch-import 5) 0 mới 0 thừa, taxonomy
  0 warning, Dagster inventory 0 diff, pytest 271.
- `run-all.sh` với `SHADOW_ROOT` chưa tồn tại: `RUN-ALL: PASS`.
- Kiểm trên prod (chỉ in match/MISMATCH): `.env.docker` không có `SHEETS_SENSOR_*`; ID sheet trong
  3 biến `SOURCES__SPREADSHEET_URL__*` khớp URL sensor đang theo dõi, nên sensor hành xử y hệt.

Sau deploy:

- Healthy; instigator 26/26, `instigator_state.py diff` 0; serving 152 view; log không lỗi, không
  `SpreadsheetUrlNotConfigured`/`TenantConfigError`.
- Không run FAILURE/CANCELED nào từ 22:49.
- Sensor `ingest_sheets_modified_sensor`: không bắn run thừa.
- **Nightly chạy tay** `7e91d01c-bf42-4ac8-abec-ab9cb8fbaeb1`: SUCCESS, 55/55 step, 487 check, so với
  `2646613e` (sau phase 6): 0 đỏ mới, 0 hết đỏ. 5 đỏ có từ trước: `customers_batch`
  row_count_within_trend (WARN), `products_batch` freshness (ERROR),
  `sheets_{marketing_spend,targets,team_config}` not_empty_when_expected (WARN).

## Đóng Đợt 1

- `scripts/shadow/cleanup.sh --all`: `/home/vantt/app/fg-dw-shadow` (lake, golden, inventory, có PII)
  đã xoá. Tools offline ở `~/.cache/fg-dw-tools/deps` giữ lại cho `run-all.sh`.
- Worktree `fg-dw-modular`, `fg-dw-baseline`, `fg-dw-phase7` đã gỡ (đều sạch). Nhánh
  `refactor/modularize-suite`, `refactor/phase-7` đã merge vào `main` và có trên origin.
- `main` đã push: `origin/main` = `8eb9920f`.

### Acceptance Criteria (`plan.md`)

| # | Tiêu chí | Kết quả |
|---|---|---|
| 1 | Gate mọi phase sạch trên shadow trước deploy | Đạt: gate M/S PASS trước mọi deploy (báo cáo từng phase) |
| 2 | Sau mỗi deploy nightly kế tiếp xanh, không check mới đỏ, serving view đủ, schedule/sensor không đổi | Đạt: nightly chạy tay sau mỗi deploy và nightly theo lịch 15/10 03:00 (`ffb92b66`) đều xanh, 152 view, 26/26 instigator |
| 3 | `check_boundaries.py` pass trên main, fail khi cố ý vi phạm | Đạt: pass trên `8eb9920f`; test cho ref core → `stg_*`, import chéo, seed trùng tên, URL cứng trong connectors/packs, và các rule mới (core → pack, connector → pack, dbt-seed) |
| 4 | Bỏ một connector khỏi `modules.yaml` chỉ cần sửa file đó | Đạt: `orchestration/connectors/__tests__/test_load_enabled.py` |
| 5 | `TAXONOMY.md` + `check_taxonomy_inventory.py` + seed phân loại ở `seeds/taxonomy/` | Đạt (phase 4) |
| 6 | Shadow lake và worktree đã xoá khi đóng plan | Đạt (14/10 ~23:00) |

## Phát hiện có từ trước (không do deploy)

- `ingest_sheets_modified_sensor` chưa từng phát hiện sheet đổi: 400 tick gần nhất (từ 13/10 13:33)
  đều "Cold start — recorded baseline for []", tức không lấy được hash sheet nào (nhiều khả năng link
  export CSV công khai không còn truy cập được sau khi chuyển sang service account). Việc sync sheet
  vẫn chạy theo lịch, chỉ mất phần phát hiện thay đổi tức thì. Cần một việc riêng.

## Việc theo dõi tiếp

- 03:17 ngày 15/10: kiểm nightly theo lịch (phase 4–7), `crm_backup_job` 02:00 (lần đầu dùng URL từ
  tenant config), `budget_sheet_sync_job` 02:30 (lỗi đã biết do sheet BUDGET_ITEMS).
- Sửa hai lỗi số liệu qua gate S (đã xếp hàng, chờ user cho bắt đầu): `rill/models/orders_enriched.sql`
  dùng cột `scope_*` của mart; `fact_order_economics` để NULL lợi nhuận/biên khi thiếu COGS và thêm
  cột độ phủ COGS. Shadow sẽ dựng lại từ backup mới nhất khi bắt đầu.

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
