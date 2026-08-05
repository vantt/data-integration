# Phase 7 — Deploy + Verify (không gồm CRM)

**Status: ĐÃ CHẠY THẬT 2026-08-05, PASS.** File này đã cập nhật lại đúng theo lệnh thật đã chạy (bản gốc có 2 bug — xem ghi chú ⚠️ từng bước).

**Mục tiêu**: đưa `data_platform`, `metabase`, `rill`, `evidence`, `fileserver`, `detail_view` lên chạy trên vantt-mactu, xác nhận dữ liệu khớp Windows, TRƯỚC KHI đụng vào CRM (phase 8, tách riêng). **Không phụ thuộc Caddy** (phase 6 đã deferred) — verify qua port trực tiếp + Tailscale IP.

**Lesson áp dụng**: tra toàn bộ lịch sử run (không chỉ vài run gần nhất) trước khi kết luận lỗi là do migration (lesson #5).

## Bước

-1. **[MỚI] Sửa quyền bind-mount TRƯỚC khi deploy** — Linux native chặn UID mismatch mà Windows/Docker Desktop âm thầm bỏ qua (lesson #14). `rill` chạy UID 1001, `metabase` chạy UID 999, nhưng file transfer/clone thuộc `vantt` (UID 1000) — không có write access → cả 2 container crash-loop nếu không sửa trước:
   ```bash
   ssh vantt-mactu "chmod -R o+w ~/projects/fg-data-warhouse/rill ~/projects/fg-data-warhouse/app_data/metabase_data"
   ```
   (`evidence` không cần chmod — đã sửa tận gốc trong `Dockerfile.evidence` bằng `ENV HOME=/app`, commit `01e4b5b3`, tự đúng khi image rebuild ở bất kỳ host nào.)

0. Deploy stack chính (loại trừ `crm`, `crm_drill_runner` — giữ CRM trên Windows tới phase 8).
   **⚠️ Bug đã gặp**: `--env-file .env.docker` che mất `${CRM_API_TOKEN}`/`${CRM_REFRESH_TOKEN}`/`${DRILL_TOKEN}` — các biến này compose đọc từ root `.env` (không phải `.env.docker`) để interpolate `${VAR}` cấp compose-file, `--env-file` ghi đè hẳn nguồn đó. Compose vẫn validate TOÀN BỘ services (kể cả `crm` không nằm trong danh sách deploy) trước khi start — thiếu token làm cả lệnh fail dù chỉ định service khác. **KHÔNG dùng `--env-file`**, để compose tự đọc `.env` mặc định trong cwd:
   ```bash
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && docker compose up -d --build data_platform metabase rill evidence fileserver detail_view"
   ```
1. Container health:
   ```bash
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && docker compose ps"
   ```
   Kỳ vọng: 6 service trên healthy/running. `crm`, `crm_drill_runner` KHÔNG chạy.
   Nếu `rill` restart-loop → check `docker logs rill`, lỗi `mkdir /app/rill/tmp: permission denied` = quên bước -1.
   Nếu `metabase` restart-loop với `Unable to connect to Metabase h2 DB` / `Connection has timed out` → cùng nguyên nhân, quên chmod `metabase_data`.
2. `codex login` thủ công — **KHÔNG chặn container start** (không nằm trong command chain khởi động của `data_platform`, chỉ cần trước khi job dùng `generate_approach_scripts.py` chạy thật — làm bất kỳ lúc nào sau khi `data_platform` healthy):
   ```bash
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && docker compose exec data_platform codex login"
   ```
3. Dagster: validate definitions (cần chỉ rõ `-f orchestration/definitions.py`, không có `pyproject.toml [tool.dagster]` block) + check TOÀN BỘ run history theo từng job (không filter mặc định 200-run-tổng):
   ```bash
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && docker compose exec data_platform dagster definitions validate -f orchestration/definitions.py"
   ```
   Nếu có job fail ngay sau migrate → tra lịch sử run TRƯỚC ngày migrate của CHÍNH job đó (vd `instance.get_runs(limit=N)` lọc theo `job_name`), xác nhận lỗi mới hay lỗi có sẵn. Thực tế đã gặp: `pipeline_sapo_v2_realtime_job` FAILURE — verify trên Windows baseline cũng FAILURE y hệt → lỗi có sẵn, không phải do migrate. `crm_backup_job` FAILURE — đúng kỳ vọng vì CRM chưa deploy.
4. Data parity — so sánh row-count vài mart quan trọng giữa Windows (vẫn chạy song song) và vantt-mactu:
   ```bash
   docker compose exec data_platform python -c "
   import duckdb
   con = duckdb.connect('/app/var/data_lake/sapo_warehouse.duckdb', read_only=True)
   for t in ['fact_orders', 'dim_customers']:
       print(t, con.execute(f'SELECT COUNT(*) FROM main_marts.{t}').fetchone())
   "
   ```
   Kết quả thật khớp tuyệt đối 2 bên: `fact_orders` 15686, `dim_customers` 7635.
5. HTTP endpoint check qua **port trực tiếp + Tailscale IP** (`100.94.42.82`, KHÔNG qua Caddy domain — phase 6 chưa chạy):
   ```bash
   curl -sI http://100.94.42.82:3000   # data_platform / Dagster
   curl -sI http://100.94.42.82:3001   # metabase
   curl -sI http://100.94.42.82:3002   # rill
   curl -sI http://100.94.42.82:3006   # evidence
   curl -s -o /dev/null -w "%{http_code}\n" http://100.94.42.82:3005/  # detail_view — dùng GET không HEAD, route có thể 405 trên HEAD
   curl -sI http://100.94.42.82:3004   # fileserver (basic_auth, 401 kỳ vọng nếu không có credential)
   ```
6. Metabase dashboards — **đừng chỉ tin health check hay mở UI bằng mắt**. `/api/session/properties` có field `setup-token` LUÔN xuất hiện (kể cả instance đã setup xong — KHÔNG phải dấu hiệu fresh instance, dễ gây hoảng nhầm). Field đáng tin là `has-user-setup`:
   ```bash
   curl -s http://100.94.42.82:3001/api/session/properties | grep -o '"has-user-setup":[a-z]*'
   ```
   → phải là `true`. Cũng có thể xác nhận qua log container lúc boot: `"No unrun migrations found"` / `"Database Migrations Current"` (Liquibase đọc `DATABASECHANGELOG` có sẵn) — DB fresh sẽ chạy hàng loạt migration mới, không phải "no unrun".

## Rollback
Không đổi gì trên Windows (vẫn chạy song song). Nếu vantt-mactu có vấn đề, `docker compose down`, sửa, làm lại — Windows vẫn là nguồn sống chính cho tới khi user xác nhận cutover.

## Acceptance
- Toàn bộ 6 container healthy. ✅ (2026-08-05)
- `dagster definitions validate` pass. ✅
- Row-count các mart khớp Windows. ✅ (15686 / 7635, khớp tuyệt đối)
- Metabase `has-user-setup: true`, không phải trang setup. ✅
- 6 port đều trả response hợp lệ qua Tailscale IP. ✅
