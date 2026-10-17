# Deploy 14/10 10:34: connector packages lên prod

Kết luận: **prod `main` = `b718befc` (connector packages), deploy đạt.** Instigator 0 khác biệt, realtime/hug/incremental trên code mới SUCCESS, serving 152 view, log container không có lỗi. Rollback chưa cần.

## Bối cảnh

- User cho phép deploy lúc 10:34 sau khi nightly chạy tay 09:49 kiểm chứng phase 3 (xem `nightly-manual-261014-0949-phase-3-validation.md`).
- SHA ghim `b718befc` (không phải đầu nhánh `75894f81`, commit đó chỉ là docs harness); phase 4 bị hoãn theo quyết định user, nên không có code phase 4 nào trên nhánh.
- Agent tự chạy mọi bước theo runbook `docs/operations/deployment.md` § Refactor deploys.

## Các bước

| Giờ | Bước | Kết quả |
|---|---|---|
| 10:34:29 | Kiểm tra trước | HEAD `25b6be42`; chỉ `.claude/settings.json` bị sửa (của user); `b718befc` là hậu duệ; diff 34 file, không đụng `.claude/` hay seed; không run nào đang chạy |
| 10:34:29 | Chụp instigator | 26/26 running |
| 10:34:45 | `docker compose stop data_platform` (chỉ khi không có run nào đang chạy) | dừng 10:34:56 |
| 10:34:56 | `git merge --ff-only b718befce25263b67d8f5a20b7aeede6189e1bda` | fast-forward `25b6be42..b718befc` |
| 10:35:02 | `docker compose start data_platform` | healthy 10:35:22; code location `definitions.py` LOADED lúc 10:38:25 |
| 10:38:25 | Diff instigator | 26/26 running, 0 khác biệt |

## Kiểm tra sau deploy

| Run | Job | Bắt đầu | Kết quả |
|---|---|---|---|
| b59d63cb | `pipeline_sapo_v2_realtime_job` | 10:36:11 | SUCCESS |
| fb4f4748 | `pipeline_hug_realtime_job` | 10:36:56 | SUCCESS |
| 729cb513 | `pipeline_sapo_v2_realtime_job` | 10:39:11 | SUCCESS |
| a8de0b02 | `pipeline_hug_realtime_job` | 10:39:57 | SUCCESS |
| ef524b80 | `pipeline_sapo_v2_incremental_job` | 10:40:17 | SUCCESS |

- Serving view: 152 (đếm trên bản sao `olap.duckdb`, `read_only`).
- Log container từ 10:34: không có dòng `error`/`exception`/`traceback`.

## Rollback (nếu nightly hoặc check sau này đỏ do phase 5)

```bash
docker compose stop data_platform
cd /home/vantt/app/fg-dataware-house
git status --short   # commit nội dung seed do job ghi trước, như bước 3 của runbook
git revert --no-edit 25b6be42da201964361b863e2dd5fac7b150a828..b718befce25263b67d8f5a20b7aeede6189e1bda
docker compose start data_platform
```

## Theo dõi

- Nightly 15/10 03:00 là lần chạy thật đầu tiên của `pipeline_batch_nightly_job` được lắp từ connector packages: phải xanh, không check mới đỏ (ngoại trừ `ingest_sapo_v2_customers_batch_asset` `freshness` nếu customers batch tiếp tục `skipped`, xem báo cáo nightly chạy tay), serving 152 view.
- Các job khác theo lịch trong ngày (sheets, MISA, Shopee, budget 02:30) chạy lần đầu trên code mới; kiểm tra danh sách run sáng 15/10.

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
