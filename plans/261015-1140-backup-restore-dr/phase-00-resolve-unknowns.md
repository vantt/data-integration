---
phase: 0
title: "Chốt các ẩn số trước khi code + khung tài liệu, ADR"
status: completed
priority: P1
effort: "0.5d"
dependencies: []
---

# Phase 0: Chốt các ẩn số

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** tạo `docs/operations/backup-and-recovery.md` với khung mục (Phạm vi dữ liệu, Lịch, Chụp nhất quán, Off-site, Khôi phục, Diễn tập, Cảnh báo, Dựng lại từ con số 0, Khoá và bàn giao) và điền đầy đủ mục **Phạm vi dữ liệu** (bảng phân loại đã chốt); tạo `docs/decisions/019-offsite-backup-and-recovery.md` (trạng thái Proposed, ghi D1–D12 của design); cập nhật `design.md` §4, §5, §8.2, §8.3 theo kết quả (chỗ **[chưa xác minh]** thành đã xác minh hoặc đổi quyết định).

## Mục tiêu

Trả lời mọi câu hỏi còn mở của bản đánh giá và các điểm **[chưa xác minh]** trong design, để các phase sau không xây trên giả định. **Prod chỉ đọc**: không dừng service, không ghi file trong `app_data`, không chạy job. Không cần giờ user duyệt nhưng không chạy trong 02:30–04:00.

## Câu hỏi và cách trả lời

| # | Câu hỏi | Cách kiểm (chỉ đọc) | Kết quả ghi vào |
|---|---|---|---|
| Q1 | Mỗi thư mục cấp 1 của `app_data/data_lake` (`backup`, `crm_export`, `export`, `gsheet_raw`, `hug_raw`, `misa_raw`, `monitoring`, `sapo_raw_staging`, `sapo_v2_raw`, `serving`, `shopee_raw`, `test_raw`) là nguồn sự thật hay phái sinh? Ai ghi? | `grep` đường dẫn trong `ingestion/`, `orchestration/`, `scripts/`, `crm/`; chỉ `ls`/`du`, không mở file dữ liệu | design §4 |
| Q2 | Bảng tích luỹ không dựng lại được: model nào dùng `get_rolling_location()` và giữ lịch sử qua nhiều file (bắt đầu từ `fact_variant_prices_snapshot.sql:1-8`)? GC `ROLLING_KEEP_VERSIONS` (`scripts/provisioning/refresh_rolling.py` docstring) có xoá lịch sử của chúng không? | Đọc macro `get_rolling_location`, `refresh_rolling.py`; liệt kê model | design §4, quyết định D2 |
| Q3 | 17 model incremental: model nào **không** cho cùng kết quả khi build trên DB rỗng từ raw đầy đủ (vd. dữ liệu nguồn đã bị Sapo cắt lịch sử, xem memory dự án `project_sapo_history_log_truncation` được trích trong runbook completeness §2.1)? | Đọc từng model; đối chiếu bằng chứng gate S "full-refresh pass" của các đợt trước (`docs/operations/refactor-safety-harness.md` §6.7) | design §4 |
| Q4 | Mọi writer DuckDB có giữ `duckdb_lock` không? Đã thấy ứng viên: `scripts/maintenance/sync_seeds.py:31` (mở `sapo_warehouse.duckdb` ghi), `scripts/provisioning/bootstrap_serving_views.py:98`, các writer `monitoring` (ingestion health), connector Facebook dùng destination `duckdb` (`ingestion/run_facebook_ads_batch.py:24`, đang dormant) | Lần theo nơi gọi trong `orchestration/` và tag `dagster/concurrency_key` | design §5; quyết định thử lại trong `duckdb_snapshot.py` |
| Q5 | `monitoring_db` có trong bản backup đêm không? | `backup.sh` chạy trong container, `cp -a /app/var/data_lake` (nhánh Docker, `scripts/backup/backup.sh:158-166`) đi qua mount đè `docker-compose.yml:39` nên **có thể** đã chép; kiểm danh sách file trong bản backup mới nhất so với `docker run --rm -v <project>_monitoring_db:/b:ro alpine ls -la /b` (chỉ tên file và kích thước). Thư mục `app_data/data_lake/monitoring` trên host (6,6 MB) là lớp bên dưới bị che, có thể cũ | design §4 |
| Q6 | Lịch sử `monitoring` có cần giữ không, hay chấp nhận mất khi dựng lại? | Đọc ai đọc các bảng này (freshness, digest, row_trend) | design §4 (đề xuất mặc định: giữ, qua EXPORT) |
| Q7 | Kích thước named volume: `dagster_home`, `monitoring_db`, `crm_data`, `crm_backups`, `crm_verify_data`, `agent_codex_config` | `docker run --rm -v <vol>:/b:ro alpine du -sh /b` cho từng volume | design §10 chi phí |
| Q8 | Seed do job ghi: file nào trong `transformation/seeds/` bị job ghi đè (budget sync, `sync_seeds.py`)? Có seed nào chỉ có trên prod mà chưa commit? | `git log --format='%h %ad %s' -- transformation/seeds` + `git status --short transformation/seeds` trên prod (chỉ đọc) | design §4 |
| Q9 | File chỉ có trên máy: tập file bị gitignore ngoài `app_data/` cần để chạy (`git status --short --ignored`, hiện thấy `.env`, `.env.docker`, `.env.local`, `evidence/sources/datalake/olap-serving.duckdb`, `rill/tmp/`). `.env.local` dùng vào đâu? | `grep` tên file trong compose và script; **không mở nội dung** | `scripts/backup/offsite-include.txt` (bản nháp trong báo cáo phase) |
| Q10 | Cấu hình mức host: stack Caddy toàn cục (container `caddy-global`, image `caddy-global:dns01`), `cloudflared` (container chạy ngoài compose này, image `cloudflare/cloudflared:latest`), Tailscale, unit systemd user, crontab, cấu hình daemon Docker, linger. File compose của Caddy và cloudflared nằm đâu, token tunnel lưu ở đâu? | `docker inspect -f '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' caddy-global cloudflared`; `systemctl --user list-unit-files`; `crontab -l` | design §3.1 `host-state/`; phase 6 runbook |
| Q11 | Lần diễn tập CRM gần nhất có PASS không? | Dagster GraphQL chỉ đọc: run gần nhất của `crm_backup_job`, trạng thái asset `crm_restore_verify` | báo cáo phase |
| Q12 | Thời điểm kết thúc nightly 14 đêm gần nhất (p50, p95, max) | Dagster GraphQL chỉ đọc: run `pipeline_batch_nightly_job` | design §7 (giữ 03:30 hay dời 03:45) |
| Q13 | Thời gian backup cục bộ (`maintain_backup_platform_job`) 14 đêm gần nhất | Như trên | design §7 |
| Q14 | dlt ghi file parquet theo kiểu tạm rồi đổi tên không, và ghi state trước hay sau file dữ liệu? Thư mục tạm của dlt tên gì? | Đọc mã dlt đã cài trong image (`pip show dlt`, đọc module filesystem destination), không chạy pipeline | design §5, `--exclude-file` |
| Q15 | Có cách lùi cursor dlt theo khoảng thời gian (kéo bù 48 giờ) không, hay chỉ có `--reset-cursor` xoá toàn bộ (`ingestion/src/utils/pipeline_runner.py:83-111`)? | Đọc `pipeline_runner.py` và nguồn Sapo/Shopee/MISA | design §8.3; nếu thiếu thì phase 3 thêm |
| Q16 | `dagster_home` ngoài `history/` gồm gì, cái nào cần (schedules/sensor state, cursor, `dagster.yaml`)? | `docker run --rm -v <project>_dagster_home:/b:ro alpine find /b -maxdepth 3 -not -path '*/history/*'` | design §4 |
| Q17 | Danh sách đường ghi ra ngoài phải tắt khi diễn tập (tunnel, HUG, Lark, SMTP Metabase, Google Sheet, khác) | `grep` URL/biến môi trường trong `orchestration/`, `ingestion/`, `crm/src`; tên biến trong `.env.docker` lấy bằng `cut -d= -f1` (không in giá trị) | design §8.2 |
| Q18 | Kích thước image đang chạy (`docker image ls` cho các image `fg-dataware-house-*`) để ước chi phí D12 | `docker image ls` | design §10, câu hỏi mở 5 |
| Q19 | `app_data/analysis` là gì, ai ghi, có cần backup? | `grep` + `ls` | design §4 |

## Các bước

1. Tạo worktree `feat/backup-offsite-dr` từ `main`.
2. Trả lời Q1–Q19, ghi bằng chứng `file:dòng` hoặc lệnh đã chạy vào báo cáo `plans/261015-1140-backup-restore-dr/reports/phase-00-unknowns.md`.
3. Cập nhật `design.md` và ghi mọi thay đổi quyết định vào cuối `plan.md` (mục "Ghi nhận từ phase 0").
4. Viết bản nháp `scripts/backup/offsite-include.txt` (danh sách include/exclude có chú thích lý do từng dòng) trong báo cáo; file thật do phase 2 tạo.
5. Tạo khung `docs/operations/backup-and-recovery.md` và ADR 019 (Proposed).
6. Nếu Q2/Q3 cho thấy nhiều bảng không dựng lại được: dừng, trình user hai phương án (export từng bảng hay đưa cả `sapo_warehouse.duckdb` lên off-site hằng tuần), chờ quyết định trước phase 1.

## Verification

- Mọi dòng **[chưa xác minh]** trong `design.md` đã được thay.
- Báo cáo phase có đủ 19 câu trả lời, mỗi câu có bằng chứng.
- Không có lệnh nào đã chạy ghi vào `app_data` hay dừng container (tự kiểm lại lịch sử lệnh trong báo cáo).

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Lệnh `du` trên volume lớn gây I/O lúc người dùng làm việc | Chạy ngoài giờ cao điểm, từng volume một |
| Đọc nhầm nội dung secret khi kiểm `.env*` | Chỉ dùng `cut -d= -f1`; không `cat` |

## Rollback

Không có thay đổi prod. Tài liệu mới có thể xoá bằng `git revert`.

## Kết quả (15/10/2026)

- Báo cáo: [reports/phase-00-findings.md](reports/phase-00-findings.md) (đặt tên `phase-00-findings.md` thay cho `phase-00-unknowns.md` ở bước 2). Đủ Q1–Q19, mỗi câu có bằng chứng; mọi lệnh trên prod chỉ đọc (bản sao DB trong scratch đã xoá), không có lệnh ghi vào `app_data` hay dừng container.
- Bước 3: `design.md` đã sửa (§2 D2, D6, D12; §3, §3.1, §4, §5, §6, §7, §8.1–8.3, §9, §10, §11, §12, §13), không còn điểm "chưa xác minh"; `plan.md` có mục "Ghi nhận từ phase 0" và câu hỏi mở cập nhật; phase 1, 2, 3, 4, 6, 8 sửa theo.
- Bước 4: bản nháp `offsite-include.txt` trong báo cáo (sửa theo quyết định user ở `plan.md` mục "Đã chốt").
- Bước 5: `docs/operations/backup-and-recovery.md` (khung + mục "Phạm vi dữ liệu") và `docs/decisions/019-offsite-backup-and-recovery.md` (Proposed) trên nhánh `feat/backup-offsite-dr`.
- Bước 6: không kích hoạt: chỉ một bảng không dựng lại được (`monitor_taxonomy_parity_log`).
