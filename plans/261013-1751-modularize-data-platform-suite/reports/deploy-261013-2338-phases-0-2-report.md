status: complete

# Báo cáo deploy p90-a01 (SHA 97d05451d10146b1f059b0a5eb3f1f9019498180)

Deploy phase 0–2 lên production thành công và đã được kiểm chứng. Không phải rollback.

## Dòng thời gian (ICT, 2026-10-13)
- 23:35:55 — Pre-check: ngoài khung 02:30–04:00; HEAD e65ff978; chỉ `.claude/settings.json` bị sửa (cùng các thư mục untracked); fast-forward khả thi; 26 instigator / 26 running (`/tmp/p90-instigators-before.json`); 152 serving view; không có run đang chạy lúc đó.
- 23:36 — Gửi câu hỏi q-p90-a01-01; 23:37 coordinator duyệt, kèm điều kiện chờ khoảng trống không có run STARTED/STARTING.
- 23:38:06 — Hết run đang chạy (poll 10 s) → `docker compose stop data_platform` ngay; 23:38:16 container dừng (exit 137 do bị kill sau ~10 s, như coordinator đã báo trước).
- Ngay sau đó — `git merge --ff-only 97d05451...` thành công; `git log -1` = 97d05451. Rollback SHA lưu ở `/tmp/deploy-rollback-sha` (e65ff978), `/tmp/deploy-branch-sha`.
- 23:38:21 — `docker compose start data_platform`; 23:38:52 trạng thái healthy, GraphQL trả version 1.13.17.

## Kiểm tra
- Instigator diff: 26/26 running, **0 difference(s)**.
- Run sau restart (đều SUCCESS): sapo realtime 6a7e1943 (23:39:18), 3048bee5 (23:42:15), 99ad2941 (23:45:10); hug realtime e57934f2 (23:40:14), 44c1713d (23:43:00), 767f83ce (23:45:56); sapo incremental 62fdb263 (23:40:24).
- Bước dbt trong run realtime: `dbt parse` rồi `dbt build --select fqn:*` ("subsetted execution is not being performed"). Hành vi này giống hệt run trước deploy (2cae00d6), nên không phải regression.
- Serving view sau deploy: **152** (trước: 152).
- Log container: grep `Auto-Setup|rolling models|Error|ERROR|Traceback` (15 phút sau start) và grep error/traceback (20–25 phút) đều không có kết quả. Lưu ý: `docker logs` không chứa dòng "Running dbt command"; chúng nằm trong event log của Dagster (đọc qua GraphQL `logsForRun`).

## Việc coordinator cần theo dõi
- Nightly 03:00 (`pipeline_batch_nightly_schedule`) phải xanh, không có asset check mới đỏ, đủ 152 serving view, row count nằm trong ngưỡng `row_trend_checks`.
- Chưa thực hiện commit nào; prod checkout ở 97d05451, `.claude/settings.json` vẫn giữ nguyên trạng thái sửa của người dùng.

Câu hỏi chưa giải quyết: không có.
