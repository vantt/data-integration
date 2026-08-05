# Phase 7 — Deploy + Verify (không gồm CRM)

**Mục tiêu**: đưa `data_platform`, `metabase`, `rill`, `evidence`, `fileserver`, `detail_view` lên chạy trên vantt-mactu, xác nhận dữ liệu khớp Windows, TRƯỚC KHI đụng vào CRM (phase 8, tách riêng). **Không phụ thuộc Caddy** (phase 6 đã deferred) — verify qua port trực tiếp + Tailscale IP.

**Lesson áp dụng**: tra toàn bộ lịch sử run (không chỉ vài run gần nhất) trước khi kết luận lỗi là do migration (lesson #5).

## Bước

0. Deploy stack chính (loại trừ `crm`, `crm_drill_runner` — giữ CRM trên Windows tới phase 8):
   ```bash
   ssh vantt-mactu "cd ~/data-integration/app && docker compose --env-file .env.docker up -d --build data_platform metabase rill evidence fileserver detail_view"
   ```
1. Container health:
   ```bash
   ssh vantt-mactu "cd ~/data-integration/app && docker compose ps"
   ```
   Kỳ vọng: 6 service trên healthy/running. `crm`, `crm_drill_runner` KHÔNG chạy.
2. `codex login` thủ công (cần trước vì `data_platform` command chain gọi `generate_approach_scripts.py` dùng session này):
   ```bash
   ssh vantt-mactu "cd ~/data-integration/app && docker compose exec data_platform codex login"
   ```
3. Dagster: validate definitions + check TOÀN BỘ run history theo từng job (không filter mặc định 200-run-tổng):
   ```bash
   ssh vantt-mactu "docker compose -f ~/data-integration/app/docker-compose.yml exec data_platform dagster definitions validate"
   ```
   Nếu có job fail ngay sau migrate → tra lịch sử run TRƯỚC ngày migrate của CHÍNH job đó, xác nhận lỗi mới hay lỗi có sẵn.
4. Data parity — so sánh row-count vài mart quan trọng giữa Windows (vẫn chạy song song) và vantt-mactu:
   ```bash
   docker compose exec data_platform python -c "
   import duckdb
   con = duckdb.connect('/app/var/data_lake/sapo_warehouse.duckdb', read_only=True)
   for t in ['fact_orders', 'dim_customers']:
       print(t, con.execute(f'SELECT COUNT(*) FROM main_marts.{t}').fetchone())
   "
   ```
5. HTTP endpoint check qua **port trực tiếp + Tailscale IP** (`100.94.42.82`, KHÔNG qua Caddy domain — phase 6 chưa chạy):
   ```bash
   curl -sI http://100.94.42.82:3000/server_info   # data_platform / Dagster
   curl -sI http://100.94.42.82:3001/api/health    # metabase
   curl -sI http://100.94.42.82:3002               # rill
   curl -sI http://100.94.42.82:3006               # evidence
   curl -sI http://100.94.42.82:3005               # detail_view
   curl -sI http://100.94.42.82:3004               # fileserver (basic_auth, 401 kỳ vọng nếu không có credential)
   ```
6. Metabase dashboards — mở UI thật qua `http://100.94.42.82:3001`, xác nhận dashboards/questions còn nguyên (H2 file đã transfer phase 3), không phải màn hình setup-from-scratch (đúng vấn đề #2 mà nu-data-pipeline gặp).

## Rollback
Không đổi gì trên Windows (vẫn chạy song song). Nếu vantt-mactu có vấn đề, `docker compose down`, sửa, làm lại — Windows vẫn là nguồn sống chính cho tới khi user xác nhận cutover.

## Acceptance
- Toàn bộ 6 container healthy.
- `dagster definitions validate` pass.
- Row-count các mart khớp Windows (chênh nhỏ do lag chấp nhận được, chênh lớn thì điều tra).
- Metabase mở đúng dashboards cũ, không phải trang setup.
- 6 port đều trả response hợp lệ qua Tailscale IP.
