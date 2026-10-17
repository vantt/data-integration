# Deploy 14/10 13:27: kiểm kê taxonomy và seed `seeds/taxonomy/` lên prod

Kết luận: **prod `main` = `111f1386` (kiểm kê taxonomy, seed dời vào `seeds/taxonomy/`, `seed_paths.py`), deploy đạt.** Instigator 0 khác biệt, run trên code mới SUCCESS, nightly chạy tay sau deploy xanh và không có check mới đỏ, serving 152 view. Một run realtime bị đánh lỗi do trùng lúc container khởi động lại, không do code (chi tiết bên dưới). Rollback chưa cần.

Lần deploy này đưa lên prod ba commit: `75894f81` (docs harness), `31ae829e` (kiểm kê taxonomy, dời seed), `111f1386` (sửa câu "giống từng ký tự" trong tài liệu).

## Bối cảnh

- User duyệt (14/10 ~12:40, qua session lập plan, xác nhận bằng việc tự chạy lệnh): kiểm chứng phase 5 bằng nightly chạy tay, nếu xanh thì deploy phase 4 ngay, không đợi 03:00; sau deploy chạy tay nightly thêm một lần để kiểm phần đọc/ghi seed.
- Gate M của phase 4 do coordinator chạy lại lúc 11:56 với baseline `b718befc` build cùng ngày: PASS sạch, không cờ allow.
- Bộ phân loại an toàn chặn agent chạy lệnh stop/merge/start ("Production Deploy") và lệnh launch job; user tự chạy các lệnh đó, agent làm toàn bộ phần kiểm tra trước và sau.

## Kiểm chứng phase 5 trước khi deploy

Nightly chạy tay `efb41501-ce3f-410f-87a4-9453747c5abb` (12:43:02 → 12:48:10, prod `b718befc`): SUCCESS, 55/55 step, 487 check, 10/10 `std_column_contract_*` pass, 7 check đỏ, đúng 7 check đã đỏ ở lần chạy 09:49 (`856bd0ee`), không check mới. Serving 152 view, 26/26 instigator.

## Các bước deploy

| Giờ | Bước | Kết quả |
|---|---|---|
| ~12:50 | Kiểm tra trước | HEAD `b718befc`; chỉ `.claude/settings.json` bị sửa (của user), không seed nào bị job ghi đè; `111f1386` là hậu duệ; serving 152; instigator 26/26 (chụp `instigators-before-p4.json`) |
| ~13:26 | User chạy `docker compose stop data_platform && git merge --ff-only 111f1386e3e10fdf17054feb79697aaf0ca00cdf && docker compose start data_platform` | fast-forward `b718befc..111f1386`, 44 file, 8 seed đổi tên 100% |
| 13:27:01 | Container khởi động | code location `definitions.py` LOADED lúc 13:27:20 (start command chạy `dbt parse` trước `dagster dev`, nên parse với `seeds/taxonomy/` thành công) |
| 13:27:20 | Diff instigator | 26/26 running, 0 khác biệt |

Run trước lúc dừng (hourly 13:25:09, realtime 13:24:13, hug 13:24:59) đều SUCCESS.

## Kiểm tra sau deploy

| Run | Job | Bắt đầu | Kết quả |
|---|---|---|---|
| 75beba65 | `pipeline_hug_realtime_job` | 13:27:22 | SUCCESS |
| 07365e89 | `pipeline_sapo_v2_incremental_job` | 13:30:12 | SUCCESS |
| 289f0cd4 | `pipeline_hug_realtime_job` | 13:30:58 | SUCCESS |
| 35cf8470 | `pipeline_hug_realtime_job` | 13:33:03 | SUCCESS |
| 6760a3b1 | `pipeline_sapo_v2_realtime_job` | tạo 13:27:00 | FAILURE: "Run timed out due to taking longer than 300 seconds to start" |
| 070bea03 | `pipeline_sapo_v2_realtime_job` | 13:36:14 | SUCCESS |

`6760a3b1`: schedule tick 13:27:00 tạo run đúng lúc container đang khởi động (start 13:27:01, nạp code xong 13:27:20). Run không bao giờ được launch, không có step nào chạy; run monitoring của Dagster đánh lỗi sau 300 giây chờ bắt đầu (13:33:15). Lượt kế tiếp SUCCESS. Không do code. Bài học cho runbook: tránh start container sát mốc phút chia hết cho 3 của `pipeline_sapo_v2_realtime_schedule`, hoặc chấp nhận một run timeout như vậy.

- Serving view: 152. Log container từ lúc start: không có `error`/`exception`/`traceback`. Không có seed trùng tên trong `transformation/seeds/`.

## Nightly chạy tay sau deploy (kiểm phần đọc/ghi seed)

Run `4c9d9ce6-d230-4909-a07d-da5adb0ede45` (14:27:58 → 14:33:08, prod `111f1386`): SUCCESS, 55/55 step, 487 check, 10/10 `std_column_contract_*` pass. 6 check đỏ, đều đã có ở lần chạy 12:43; `orders_batch` `row_count_within_trend` hết đỏ. Không check mới.

- **Đọc seed qua `seed_path()`: đã chạy trên prod.** Step `sheets_marketing_spend_asset` gọi `gsheet_marketing_spend.run()` → `fetch_and_save_marketing_spend()`, hàm này đọc `ref_spend_category`, `ref_order_sources`, `ref_branch_locations` qua `seed_path()` trước mọi việc khác và ném lỗi nếu đọc hỏng; step SUCCESS.
- **dbt seed từ `seeds/taxonomy/`:** `dbt build` trong nightly chạy xanh, các model đọc 8 seed đã dời không lỗi.
- **Ghi seed: chưa được kiểm trên prod.** `budget_sheet_sync_job` (ghi `seed_cashflow_budget.csv`, `seed_cash_allocation_policy.csv`) vẫn dừng trước khi ghi vì Google Sheet BUDGET_ITEMS dòng 17–18 dùng mã TK cha `112`, `334` không có trong `dim_gl_account`; `scripts/maintenance/sync_seeds.py` (ghi `ref_order_sources`, `ref_branch_locations` trong `seeds/taxonomy/`) là script bảo trì chạy tay, không nằm trong nightly. Cả hai đường ghi đã được kiểm end-to-end trong shadow (báo cáo `phase-04-worker-report.md`). Đường ghi budget sẽ chạy thật lần đầu khi sheet được sửa.

## Rollback (nếu nightly 03:00 hoặc check sau này đỏ do phase 4)

```bash
docker compose stop data_platform
cd /home/vantt/app/fg-dataware-house
git status --short   # commit nội dung seed do job ghi trước, như bước 3 của runbook
git revert --no-edit b718befce25263b67d8f5a20b7aeede6189e1bda..111f1386e3e10fdf17054feb79697aaf0ca00cdf
docker compose start data_platform
```

Không dùng `reset --hard`. Nếu job đã ghi seed vào `seeds/taxonomy/` trước khi revert, chép nội dung đó về đường dẫn cũ trước khi start.

## Theo dõi

- Nightly 15/10 03:00 là lần xác nhận cuối cho phase 5 và phase 4 (lịch kiểm tra một lần lúc 03:17 trong session thực thi). Check `customers_batch` `freshness` và `products_batch` `freshness` đã đỏ từ trước, không do deploy.

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
