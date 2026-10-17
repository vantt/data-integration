---
phase: 3
title: "Công cụ khôi phục restore.sh: extract, verify, apply, full, drill mode"
status: pending
priority: P1
effort: "1.25d"
dependencies: [2]
---

# Phase 3: `restore.sh` cho Linux

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/backup-and-recovery.md` mục **Khôi phục** (lệnh, từng thành phần: dừng gì, ghi gì, kiểm gì, bản an toàn ở đâu, cách quay lại; kéo bù sau khôi phục; chế độ drill); `crm/docs/backup-restore-runbook.md` (thêm khôi phục CRM từ bản off-site, trỏ về tài liệu chung; mục 5 "Offsite automation" đánh dấu đã có); `docs/operations/deployment.md` mục "Restore the H2 file" (thêm đường `restore.sh apply --component metabase-h2`).

## Mục tiêu

Khôi phục được từng thành phần hoặc toàn bộ từ repo off-site trên Linux, luôn qua thư mục scratch và gate `verify` trước khi ghi vào prod. Làm và kiểm trên worktree; **không đụng prod**.

## Thiết kế

Giao diện theo design §8.1. Thực thi:

- `extract`: chạy trong sidecar (`docker compose --profile ops run --rm -v <scratch>:/restore backup restore-extract ...`), `restic restore <snap> --target /restore --include <đường dẫn ổn định của thành phần>`, rồi `chown -R <uid>:<gid>` theo `--owner` (mặc định uid/gid của người gọi), nên không cần `sudo` khi đọc hay xoá scratch.
- `verify` (gate A, dùng chung với T2): `scripts/backup/sidecar/restore_verify.py` đọc manifest của từng thành phần (bản cục bộ, CRM, Metabase) và kiểm sha256, số dòng, `PRAGMA integrity_check`, đọc được mọi file parquet raw (DuckDB `read_parquet` đếm dòng, so số trong manifest nếu có) và mở được mọi bảng Delta (`deltalake.DeltaTable(...).files()` đều có trong bản giải nén), vì dlt ghi parquet thẳng vào tên cuối nên file chụp dở chỉ bắt được bằng cách đọc (F-Q14). Kết quả `verify.json` trong scratch; `apply`/`full` đòi file này `ok=true` và cùng snapshot id.
- `apply --component <c> --confirm`:

| Thành phần | Dừng | Ghi | Kiểm sau |
|---|---|---|---|
| `raw-lake` (gồm `data_lake/backup`), `input`, `analysis` | `data_platform` | Đổi tên thư mục hiện tại thành `.before-restore-<ts>`, chép bản khôi phục vào | Start, chạy tiếp ingestion từ cursor trong snapshot (`restore.sh catch-up`), nightly drill hoặc thật |
| `exports` (bảng `monitor_taxonomy_parity_log`) | `data_platform` | Sau khi `sapo_warehouse.duckdb` tồn tại (dựng lại hoặc rỗng): `CREATE TABLE ... AS SELECT * FROM read_parquet(...)` vào `main` nếu bảng chưa có, hoặc `INSERT` các dòng có `run_at` chưa có. Phải làm **trước** lần `dbt build` đầu tiên (`full_refresh=false` nên build sau đó chỉ thêm dòng) | Số dòng ≥ manifest |
| `monitoring` | `data_platform`, `metabase` (cả hai mount volume) | Ghi `ingestion_health.db` vào **named volume** `<project>_monitoring_db` qua container tạm, không vào `app_data/data_lake/monitoring` (lớp host bị che, F-Q5); bản an toàn trước | `integrity_check`, số dòng `ingestion_runs` ≥ manifest |
| `seeds` | — (checkout) | Đè `transformation/seeds/` bằng bản khôi phục **sau khi** `git checkout <git sha của snapshot>` | `git status` khớp `repo-state/status` của snapshot |
| `secrets` | — | `.env`, `.env.docker`, `app_data/secrets/` với quyền 0600, chỉ khi file đích chưa tồn tại hoặc có `--overwrite-secrets`. `.env.local` không có trong backup (user chốt) | sha256 khớp manifest |
| `cloudflared` | — | **Chỉ `--mode real`** (từ chối ở drill): credentials vào `${FG_CLOUDFLARED_DIR}`, owner theo uid container `cloudflared` (65532) hoặc theo quyết định câu hỏi mở 6 của plan.md | sha256 khớp manifest; chỉ start `cloudflared` khi máy cũ chắc chắn đã chết (một tunnel hai connector sẽ chia traffic) |
| `dagster-home` | `data_platform` | `schedules/schedules.db` (+ `dagster.yaml`) vào volume qua container tạm `alpine` (mẫu runbook CRM), bản an toàn trước. Không có `history/`, `storage/`: UI mất "last materialized" tới lần chạy kế, chấp nhận | Start, `scripts/checks/instigator_state.py capture` so với trạng thái trong snapshot |
| `metabase-h2` | `metabase` | Như `docs/operations/deployment.md` "Restore the H2 file", bản an toàn `.before-restore`; giữ owner uid của container (file trên prod thuộc uid của container, không phải `vantt`) | `/api/health`, đếm card/dashboard/collection so manifest |
| `crm` | `crm` | Đúng các bước 2–6 của `crm/docs/backup-restore-runbook.md` §3 (bản an toàn, chép vào `crm_data`, start, refresh cache) | `/healthz`, diễn tập CRM trên bản vừa khôi phục |
| `config` | — | Chỉ so sánh `docker-compose.yml` với bản trong snapshot, in khác biệt; không ghi đè (code lấy từ git) | — |

- `full --from <dir> --confirm --mode drill|real`: thứ tự secret → checkout đúng sha → seed → build image từ git ở đúng sha (không lưu image, D12) → volume (dagster, monitoring, crm) → H2 → raw/input/analysis → warehouse rỗng + bảng exports → `docker compose up -d` (trừ `cloudflared` khi drill) → `dbt build` + serving qua job Dagster → kéo bù → kiểm. Mỗi bước ghi thời điểm bắt đầu/kết thúc vào `restore-timeline.json` (đầu vào cho đo RTO ở phase 6). Nhánh `--mode real` trên máy mới làm ở phase 6; phase này làm `--mode drill` và các thành phần đơn lẻ.
- `--mode drill` (design §8.2): sinh `.env.drill` từ `.env.docker` khôi phục với các biến ra ngoài đặt rỗng (design §8.2: `WORKER_URL`, `WORKER_POLL_TOKEN`, `HUG_WORKER_URL`, `LARK_ALERT_WEBHOOK`, `LARK_ALERT_SECRET`, `GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH`, `CLOUDFLARE_API_TOKEN`, `SOURCES__SAPO__*`; không mount `app_data/secrets`; không start `cloudflared`, `caddy-global`); tắt schedule/sensor consumer webhook Sapo/HUG trước mọi thứ khác, vì ack xoá hàng đợi trên Worker của prod; Metabase chạy với biến tắt email; sau khi `data_platform` lên, tắt mọi schedule/sensor (GraphQL `stopRunningSchedule`/`stopSensor`) trước khi bất kỳ tick nào chạy (start container với `DAGSTER_...` tắt daemon trước, hoặc dùng `dagster.yaml` drill không chạy scheduler, phase này chọn cách đơn giản nhất qua thử nghiệm và ghi lại).
- `catch-up` (design §8.3, đã chốt sau phase 0): chạy lần lượt các job ingestion (batch Sapo, MISA/Shopee file drop, Sheets) để mỗi pipeline lấy tiếp từ cursor trong snapshot; state dlt ghi sau dữ liệu nên không có khoảng hở, chỉ có thể ghi trùng (staging khử trùng). Không có cơ chế lùi cursor theo giờ (F-Q15); **không** thêm `--since`/`--rewind-hours` trong phase này trừ khi diễn tập T3 hoặc phase 6 cho thấy thiếu dữ liệu. In cảnh báo: sự kiện webhook HUG đã ack sau thời điểm snapshot không lấy lại được.
- **CRM drill trỏ vào bản off-site:** thêm `--backups-dir <dir>` cho `crm/ops/restore_verify_crm.py` ở chế độ host (`:262-265` hiện có `--backup`, `--negative`), để T2 dùng lại nguyên gate A/B của CRM trên bản đã giải nén thay vì volume `crm_backups`.

## Files

- Create: `scripts/backup/restore.sh`, `scripts/backup/sidecar/{restore_extract.sh,restore_verify.py}`, `scripts/backup/drill.env.keys` (danh sách tên biến bị tắt khi drill, không có giá trị), test `scripts/tests/test_restore_verify.py`.
- Modify: `crm/ops/restore_verify_crm.py` (`--backups-dir`), test CRM tương ứng; tài liệu ở khối đầu.

## Verification

- pytest `restore_verify.py`: manifest khớp → PASS; xoá một file parquet, sửa một byte DB, đổi một số trong manifest → FAIL với thông báo đúng thành phần.
- Tích hợp trên worktree với repo test của phase 2: `extract` từng thành phần và toàn bộ vào scratch, `verify` PASS, scratch thuộc user gọi (không root).
- `apply` từng thành phần trên **một stack shadow riêng** (compose project khác, volume khác, thư mục khác prod; kiểm bằng `scripts/checks/guard_not_prod.py` như `prepare-shadow.sh:24`): sau `apply`, service lên, kiểm sau của bảng trên đều PASS; rollback bằng bản `.before-restore` trả về trạng thái trước.
- `full --mode drill` trên stack shadow: không có container nào có mạng ra `hug.fjp.vn`/Lark (kiểm bằng biến môi trường trong `docker inspect` rỗng), mọi schedule/sensor ở trạng thái dừng, `restore-timeline.json` đủ bước.
- `restore_verify_crm.py --backups-dir` PASS trên bản giải nén, và `--negative value` FAIL như cũ.

**Đụng prod:** không. **Đổi số:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Người vận hành chạy `apply` nhầm vào prod khi chỉ định diễn tập | `apply` in rõ project compose và đường dẫn đích, đòi `--confirm`; stack shadow có tên project khác; `guard_not_prod.py` cho mọi lệnh drill |
| Tắt schedule chậm, một tick chạy trên bản drill và gọi ra ngoài | Biến ra ngoài đã rỗng trước khi start; tick chỉ còn ghi cục bộ |
| `catch-up` kéo trùng dữ liệu | Raw là `append` nên có thể trùng; staging `delete+insert` theo khoá nghiệp vụ khử trùng (F-Q3); kiểm số dòng bảng public không tăng bất thường trên shadow |

## Rollback

Không deploy prod. Thay đổi `restore_verify_crm.py` chỉ thêm tham số tuỳ chọn; revert độc lập được.
