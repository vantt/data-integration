# Migrate data-integration: Windows → vantt-mactu

**Status**: Phase 1-5, 7, 8 ĐÃ CHẠY THẬT và PASS 100% (2026-08-05) — TOÀN BỘ 8 service (kể cả CRM) sống trên vantt-mactu, Cloudflare Tunnel đã cutover, `crm.fwg.vn`/`bi.fwg.vn`/`hermes.fwg.vn`/`fgos.fwg.vn` verify OK qua CF Access, user đã tự đăng nhập CRM thật công thành công. Windows Cloudflared service đã dừng (user tự làm, cần admin). **Toàn bộ 8 container trên Windows đã dừng** (`docker compose stop`, KHÔNG xoá — vẫn là rollback path). Phase 6 (Caddy) deferred. Phase 9 (pre-wipe checklist) chưa chạm tới — đây là bước còn lại duy nhất trước khi cho phép uninstall Windows.
**Ngày**: 2026-07-30 (khởi tạo) / 2026-08-04 (chốt quyết định)
**Nguồn kinh nghiệm**: `D:\Vantt\app\nu-data-pipeline\plans\reports\migration-260728-1450-windows-to-vantt-mactu-dry-run-report.md` (dry-run cùng target host, 70% giống cấu trúc, 9 bài học đã áp dụng vào plan này — xem mục "Bài học áp dụng" cuối file)

## Tóm tắt khác biệt so với nu-data-pipeline (quan trọng)

| | nu-data-pipeline | data-integration |
|---|---|---|
| Services | 5 | **7** (+ crm_drill_runner có docker.sock) |
| Named volumes | 2 | **6** |
| Data thật cần transfer | ~1.4G | **~12.2G live** (xem breakdown) |
| Production public exposure | Không | **Có — CRM qua Cloudflare Tunnel (Windows service), nhân viên dùng thật** |
| Reverse proxy | Không dùng | **Caddy (`caddy_net` external network) + DNS-01 cert cho `*.lan.fwg.vn`** |
| Git state nguồn | Sạch | **`docker-compose.yml` đang có uncommitted fix áp dụng đúng lesson #1 của report kia (dagster_home bind-mount → named volume, đổi 2026-07-27)** |
| Target host pre-existing state | Sạch (tưởng vậy, hoá ra không) | **Đã kiểm tra TRƯỚC: có checkout cũ `~/projects/data-integration` (HEAD `c37ca166`, 2026-04-08) nhưng KHÔNG có data, KHÔNG có container chạy — an toàn hơn nu case** |

→ Rủi ro chính không phải "host bẩn" (đã loại trừ bằng recon trước) mà là: **(1) uncommitted code phải transfer đúng, (2) CRM production cutover, (3) dung lượng đĩa đích chỉ còn 31G.**

---

## Recon đã thực hiện (kết quả, không phải giả định)

### 1. Target host vantt-mactu

- Đã tồn tại `/home/vantt/projects/data-integration`: git checkout cũ, HEAD `c37ca166` (2026-04-08, ~3.5 tháng cũ, remote `github.com/vantt/data-integration`), **không có `app_data/`, không có container nào chạy** (`docker compose ps -a` rỗng). An toàn để ghi đè hoặc archive-rồi-xoá — không có data sống ở đây, khác hẳn tình huống Metabase-volume-trùng-tên của nu-data-pipeline.
- Docker volumes hiện có trên host: `nu_admin_data`, `nu_dagster_home`, `nu_metabase_data` (từ project kia), `portainer_portainer_data`, `marketing-cockpit_agent-*`. **Không có volume nào tên trùng với data-integration** (data-integration dùng project-name prefix `data-integration_*` nên không đụng `nu_*`).
- Ports đang LISTEN: `13000-13004` (nu-data-pipeline), `5432` (postgres local), `22`, `3389` (xrdp), `8000/9000/9443/7946/2377` (portainer swarm), tailscale internal. **Port 3000-3007 (dải port gốc của data-integration) đang TRỐNG.** Port `80/443` cũng trống — chưa có Caddy nào chạy trên host này.
- Đĩa trống: `31G` / `110G` (71% used). **Đây là giới hạn cứng — xem breakdown dung lượng bên dưới.**
- SSH tới `vantt-mactu` hoạt động, không cần mật khẩu (đã test).

### 2. Dung lượng dữ liệu cần transfer (đo thật bằng PowerShell + docker run alpine du, không dùng BusyBox `du -sb` — lesson #7)

**Bind-mount (`app_data/`) — sống, đang được compose sử dụng:**

| Thư mục | Size | Ghi chú |
|---|---|---|
| `data_lake` | 1.10G / 14,485 files | **Critical** — Parquet + warehouse/serving DuckDB |
| `metabase_data` | 0.73G | **Critical** — H2 dashboards/questions |
| `input_source` | 0.05G | Low |
| `secrets` | ~0 (1 file, `gsheets-service-account.json`) | Critical nhưng nhỏ |
| `analysis` | 1.1M | Nice-to-have |
| `logs`, `rill`, `crm_verify_tmp` | 0 | Rỗng, bỏ qua |

**Named volumes — sống, đang được container mount (đo bằng `docker run alpine du -sh`, nhớ `MSYS_NO_PATHCONV=1` trên Git Bash — lesson #8):**

| Volume | Size | Ghi chú |
|---|---|---|
| `dagster_home` | 9.8G | Run history — **chỉ mới 3 ngày tuổi** (xem mục 3, cutover 2026-07-27) |
| `crm_backups` | 303M | Backup SQLite CRM đã verify |
| `agent_codex_config` | 119.5M | Codex CLI OAuth session — **không transfer được, phải `codex login` lại trên host mới** |
| `crm_data` | 57.5M | `crm.db` + `cache.db` — **production CRM data, không được mất** |
| `monitoring_db` | 54.9M | Health-check DB |
| `crm_verify_data` | ~0 | Scratch của drill runner, không cần transfer |

**Live-essential total: ~1.9G (bind) + ~10.3G (volumes) ≈ 12.2G.**

**Không sống / optional — KHÔNG nằm trong compose mount hiện tại:**

| Thư mục | Size | Là gì |
|---|---|---|
| `app_data/backups` | **11.75G / 183,363 files** | Robocopy mirror snapshots từ `scripts/backup/backup.ps1` (nhiều bản chụp lịch sử, mỗi bản gần như full copy `data_lake`+`dagster_home`+`metabase_data`). Backup-của-backup, KHÔNG phải nguồn dữ liệu chính thức. |
| `app_data/dagster_home` (thư mục host, KHÔNG phải named volume) | **12.05G / 643 files** | **Orphaned.** Đây là bind-mount CŨ trước khi đổi sang named volume ngày 2026-07-27 (mtime file mới nhất = đúng thời điểm cutover, `docker-compose.yml` cũng sửa giờ đó — xem `git diff docker-compose.yml`). Chứa run-history TRƯỚC 27/7, đã bị compose comment ghi rõ "old run-history metadata was disposable". |
| `app_data/metabase_data.backup.20260423-145815` | 0.14G | Ad-hoc backup cũ 23/4, thấp ưu tiên |
| `app_data/crm_data_safety` | 0.05G | Snapshot thủ công (crm.db, cache.db, hug.db...) từ trước khi có `crm_data` named volume — không rõ ai tạo/khi nào |

**Optional total: ~23.9G.**

### ⚠️ Ràng buộc đĩa: `12.2G (essential) + 23.9G (optional) = 36.1G` > `31G trống trên vantt-mactu`.

Nếu transfer TẤT CẢ (essential + optional) sẽ **không đủ chỗ**. Phải quyết định loại bỏ ít nhất phần "optional" (xem Open Question 1).

### 3. Git / code state (KHÔNG sạch — khác nu-data-pipeline)

- Branch `main`, có **uncommitted changes**: `docker-compose.yml` (10 dòng — dagster_home bind→named volume fix), `orchestration/definitions.py` (1 dòng), `.claude/settings.local.json`, và ~14 file `.skills/ui-spec/**` (đang phát triển dở feature khác, không liên quan migration).
- Có nhiều file **untracked**: `.skills/ui-spec/tools/wireframe/{client/render-content.js, layout-schema.mjs, layout-schema.test.mjs, styles-content.mjs}`, toàn bộ `plans/260713-*`, `plans/260714-*`, và ~10 report file trong `plans/reports/`.
- **`git clone` trên target sẽ THIẾU các thay đổi này** — đặc biệt fix `dagster_home` (đúng bài học đắt giá nhất từ vụ outage 9 ngày trước, per memory `feedback_duckdb_not_for_concurrent-write.md` + `feedback_docker-wsl2-9p-mount-fix.md`). Bỏ sót fix này khi migrate = tái tạo lại chính cái bug đã gây outage.
- **Không có session/cookie state file nào cho Sapo login** (đã grep `ingestion/`, không thấy storage_state pattern) — khác Atlas SSO của nu-data-pipeline, nên không có rủi ro "session hết hạn từ trước, tưởng do migration" ở khoản này. Sapo dùng `SOURCES__SAPO__USERNAME/PASSWORD` trực tiếp trong `.env.docker`, không phải cookie sống lâu.

### 4. Kiến trúc phụ thuộc ngoài repo (chưa từng xuất hiện ở nu-data-pipeline)

- **`caddy_net`**: external Docker network, PHẢI tạo trước khi `docker compose up` bất kỳ service nào (kể cả data-integration lẫn `caddy-global/`). Trên vantt-mactu: network này CHƯA tồn tại.
- **`caddy-global/`**: repo con nằm ngay trong `data-integration/caddy-global/`, chạy Caddy với `caddy-docker-proxy` + Cloudflare DNS-01 để cấp cert cho `*.lan.fwg.vn`. Cần `CLOUDFLARE_API_TOKEN` (đã bị flag rò rỉ plaintext trong `app_data/backups/*/config/.env.docker` — audit report `260623-1843`, chưa rõ đã rotate chưa — **cần hỏi user trước khi transfer bất kỳ file `.env.docker` cũ nào**).
- **Cloudflare Tunnel (CRM production)**: chạy như **Windows Service** (`Cloudflared`, đang Running), config tại `C:\Users\Vantt\.cloudflared` + `C:\ProgramData\cloudflared`, trỏ origin về `http://127.0.0.1:3007` (CRM). Đây là service **duy nhất internet-facing** (per memory `project_crm_only_internet_facing_hardening.md`) — nhân viên dùng CRM thật qua domain public + Lark/Cloudflare Access. Di chuyển CRM sang vantt-mactu **bắt buộc phải cutover tunnel origin** — đây là bước rủi ro cao nhất toàn bộ kế hoạch, cần cửa sổ bảo trì + rollback rõ ràng.

---

## Cơ chế Folder Mapping (yêu cầu review riêng)

### Hiện tại — Windows (`docker-compose.yml`)

```
HOST (Windows, D:\Vantt\app\data-integration\)          CONTAINER
──────────────────────────────────────────────────────────────────────────────
./transformation                          (bind, rw)  → /app/transformation
./transformation/target                   (bind, rw)  → /app/transformation/target
./ingestion                               (bind, rw)  → /app/ingestion
./orchestration                           (bind, rw)  → /app/orchestration
./scripts                                 (bind, rw)  → /app/scripts
./plans                                   (bind, ro)  → /app/plans
./app_data/data_lake                      (bind, rw*) → /app/var/data_lake        [data_platform: rw; metabase/rill/evidence/detail_view/crm: ro]
[named volume] monitoring_db                          → /app/var/data_lake/monitoring   (overlay TRÊN data_lake, cô lập khỏi Windows scan)
[named volume] dagster_home                           → /app/var/dagster_home          (mới đổi 27/7, XEM mục 3)
./app_data/backups                        (bind, rw)  → /app/var/backups
./app_data/input_source                   (bind, rw)  → /app/var/input_source
./app_data/secrets                        (bind, ro)  → /app/var/secrets
[named volume] crm_data                   (ro cho data_platform, rw cho crm)     → /app/var/crm_data | /data
[named volume] agent_codex_config                     → /root/.codex
./app_data/metabase_data                  (bind, rw)  → /home/metabase/data   (service: metabase)
./rill                                    (bind, rw)  → /app/rill              (service: rill)
./app_data/rill                           (bind, rw)  → /app/rill/.rill        (service: rill)
./evidence/*                              (bind)      → /app/*                 (service: evidence)
./app_data/data_lake/serving/standalone   (bind, ro)  → /data                  (service: fileserver)
./crm/src, ./crm/ops, ./crm/migrations    (bind)      → /app/crm/*             (service: crm)
[named volume] crm_backups                (ro drill / rw crm)                 → /backups
[named volume] crm_verify_data                        → /verify_data           (service: crm_drill_runner)
/var/run/docker.sock                      (bind)      → /var/run/docker.sock  (service: crm_drill_runner — ĐẶC BIỆT: docker socket, blast-radius cô lập ở sidecar này, KHÔNG cho data_platform)
```

**Nguyên tắc mapping hiện tại** (rút ra từ đọc code, không suy diễn):
1. **Code** (`transformation/`, `ingestion/`, `orchestration/`, `scripts/`) → bind-mount trực tiếp, để dev live-reload không cần rebuild image.
2. **Data cần lock ổn định** (SQLite/DuckDB ghi liên tục: `dagster_home`, `monitoring_db`, `crm_data`, `crm_backups`) → **named volume** (Docker VM storage), tránh đúng lỗi 9p/Windows-filesystem-lock đã gây outage 9 ngày.
3. **Data lớn, ít ghi đồng thời** (`data_lake` Parquet+DuckDB) → vẫn bind-mount (chưa migrate sang named volume — có thể là rủi ro tồn đọng, không nằm trong scope migrate lần này nhưng đáng note).
4. **Secrets** → bind-mount `:ro` từ `app_data/secrets/`.
5. Named volume gắn theo **compose project name prefix** (`data-integration_dagster_home` trên Windows, không phải bare `dagster_home`) — do compose tự thêm prefix từ tên thư mục project. **Đây là điểm khác nu-data-pipeline's lesson #3**: miễn là target host dùng project-name khác nhau cho mỗi app, không có rủi ro đụng tên volume như vụ Metabase.
   **⚠️ Trên vantt-mactu, prefix sẽ là `fg-data-warhouse_*`** (chốt path 2026-08-05, khác tên thư mục Windows) — phase 4 đã cập nhật đúng, không dùng lại `data-integration_*` ở phía đích.

### Đề xuất — vantt-mactu

```
HOST (Linux, /home/vantt/projects/fg-data-warhouse/)     CONTAINER   (Y HỆT — không đổi path trong container)
──────────────────────────────────────────────────────────────────────────────
./transformation, ./ingestion, ./orchestration, ./scripts, ./plans   → giữ nguyên, chỉ đổi root path
./app_data/{data_lake,backups*,input_source,secrets,metabase_data,rill}  → giữ nguyên cấu trúc con
[named volumes] dagster_home, monitoring_db, crm_data, crm_backups,
                agent_codex_config, crm_verify_data                 → tạo mới trên vantt-mactu, LOAD data từ Windows named volumes
                                                                        (agent_codex_config: KHÔNG load — phải `codex login` lại, OAuth session không portable)
```

**Không đổi path bên trong container** — chỉ đổi root path phía host (`D:\Vantt\app\data-integration` → `/home/vantt/projects/fg-data-warhouse`, chốt 2026-08-05 — path MỚI, khác `~/projects/data-integration` cũ (checkout tháng 4, không đụng)). Toàn bộ `docker-compose.yml` KHÔNG cần sửa path vì dùng path tương đối (`./app_data/...`) — đây là điểm thuận lợi lớn, khác nu-data-pipeline không cần custom `DATA_ROOT` env var kiểu đó vì data-integration không có logic tương tự (đã grep, không thấy `DATA_ROOT` trong compose file này).

---

## Phases (chi tiết đầy đủ — xem phase file riêng, chưa thực thi bước nào)

**Thứ tự thực thi thật (đã re-sequence 2026-08-04 — số phase ≠ thứ tự chạy)**: 1 → 2 → 3 → 4 → 5 → **7** (deploy + verify 6 service non-CRM, qua Tailscale IP) → **8** (CRM + Cloudflare Tunnel cutover — mang `bi.fwg.vn`/`crm.fwg.vn` sống lại) → **6** (Caddy `*.lan.fwg.vn`, DEFERRED/optional, làm sau cùng nếu cần) → **9** (pre-wipe checklist, GATE cứng).

| Phase | File | Thứ tự chạy | Trạng thái |
|---|---|---|---|
| 1 | `phase-01-target-prep.md` | 1 | ✅ ĐÃ CHẠY, PASS (2026-08-05) |
| 2 | `phase-02-code-transfer.md` | 2 | ✅ ĐÃ CHẠY, PASS — git tree đã sạch từ trước (commit hết) nên clone thẳng đủ, không cần transfer diff |
| 3 | `phase-03-bind-mount-data-transfer.md` | 3 | ✅ ĐÃ CHẠY, PASS — vá bug tar exclude giữa chừng (lesson #13), file-count/byte-count/sha256 khớp tuyệt đối sau vá |
| 4 | `phase-04-named-volume-transfer.md` | 4 | ✅ ĐÃ CHẠY, PASS — integrity_check ok cho dagster runs.db/schedules.db + crm.db/cache.db |
| 5 | `phase-05-secrets-env-transfer.md` | 5 | ✅ ĐÃ CHẠY, PASS — đã sửa `DAGSTER_URL` sang Tailscale IP vantt-mactu |
| 7 | `phase-07-verify-non-crm-services.md` | 6 | ✅ ĐÃ CHẠY, PASS — vá 2 bug giữa chừng (UID mismatch lesson #14, `--env-file` lesson #15), 6/6 container healthy, data parity khớp tuyệt đối |
| 8 | `phase-08-crm-production-cutover.md` | 7 | ✅ ĐÃ CHẠY, PASS (2026-08-05) — connector chuyển sang vantt-mactu, CRM cutover xong, 4 domain verify OK qua CF Access. Còn 2 việc user tự làm (xem file) |
| 6 | `phase-06-caddy-global-reverse-proxy.md` | 8 | **DEFERRED** — optional, làm sau phase 8 nếu vẫn muốn domain `*.lan.fwg.vn` |
| 9 | `phase-09-decommission-windows.md` | 9 | **GATE cứng — Windows sẽ bị uninstall+cài lại, không phải "chờ N ngày".** Checklist xác nhận an toàn trước khi cho phép wipe, không có rollback sau đó |

Tóm tắt nhanh mỗi phase (chi tiết lệnh thật trong từng file):

1. **Chuẩn bị đích**: tạo path mới `~/projects/fg-data-warhouse` (không đụng checkout cũ `~/projects/data-integration`); tạo `caddy_net` network.
2. **Transfer code**: `git clone` (đồng bộ tới `main`) + **patch/transfer riêng phần uncommitted** (docker-compose.yml, orchestration/definitions.py, .skills/ui-spec/** — qua `git diff | ssh ... apply` + tar untracked, KHÔNG dùng git clone đơn thuần vì sẽ thiếu fix dagster_home).
3. **Transfer data (bind-mount)**: dừng `data_platform`/`metabase` (writer) → tar mirror `data_lake`, `metabase_data`, `input_source`, `secrets`, `analysis` qua ssh (loại `backups`, `dagster_home` orphaned — đã quyết định bỏ) → verify checksum sha256.
4. **Transfer named volumes**: dừng container tương ứng → `docker run alpine cp -a` từng volume vào staging → tar qua ssh → load vào named volume mới trên vantt-mactu. `agent_codex_config`: bỏ qua, login lại thủ công (phase 4.5, làm ở đầu phase 7).
5. **Secrets & env**: scp `.env`, `.env.local`, `.env.docker` riêng (KHÔNG qua git, KHÔNG qua `app_data/backups`) — token Cloudflare đã rotate, an toàn copy thẳng.
6. **[Chạy sau, thứ tự 6]** Deploy + verify 6 service non-CRM qua port trực tiếp/Tailscale IP (`phase-07`), Dagster full run-history check.
7. **[Chạy sau, thứ tự 7 — GATE]** CRM + Cloudflare Tunnel cutover (`phase-08`): chuyển connector locally-managed sang vantt-mactu chạy Docker standalone, transfer `crm_data`/`crm_backups` lần cuối, start CRM, verify `crm.fwg.vn`/`bi.fwg.vn` từ ngoài. `vnflow.fwg.vn` bỏ theo quyết định user, `hermes.fwg.vn`/`fgos.fwg.vn` giữ nguyên.
8. **[DEFERRED, thứ tự 8]** Caddy/DNS-01 `*.lan.fwg.vn` (`phase-06`) — optional, làm sau nếu vẫn cần domain nội bộ đẹp.
9. **[GATE cứng, thứ tự 9]** Pre-wipe checklist (`phase-09`) — Windows sẽ bị uninstall+cài lại, không phải "chờ N ngày rồi quyết". Checklist đầy đủ trước khi cho phép wipe, KHÔNG có rollback sau đó.

---

## Bài học áp dụng từ nu-data-pipeline (đã bake vào plan, không phải để phát hiện giữa chừng)

1. Dừng writer trước khi copy SQLite/DuckDB — áp dụng ở phase 3, 4, 8.
2. Recon pre-existing state target TRƯỚC — **đã làm xong** (mục "Recon đã thực hiện").
3. Named volume trùng tên — **đã loại trừ** (project-name prefix khác nhau).
4. Volume "coi như không cần" vẫn phải hỏi user tường minh — áp dụng cho `app_data/backups` (11.75G) và `app_data/dagster_home` orphaned (12.05G) — xem OQ1, OQ2, KHÔNG tự quyết.
5. Tra toàn bộ lịch sử run trước khi đổ lỗi migration — áp dụng ở phase 7.
6. Không có rsync trên Git Bash Windows → dùng tar over ssh, mirror + exclude.
7. BusyBox `du -sb` không đáng tin → đã dùng PowerShell `Measure-Object` + `docker run alpine du -sh` (đúng, không bị lệch).
8. `MSYS_NO_PATHCONV=1` khi gọi docker/ssh path đơn ký tự qua Git Bash — đã áp dụng khi đo volume, sẽ áp dụng lại ở phase 4.
9. Mirror toàn bộ + exclude, không liệt kê subdir thủ công — áp dụng phase 3.

**Bài học MỚI rút ra riêng cho lần recon này** (bổ sung, chưa có trong report gốc):
10. Nếu git working tree không sạch, `git clone` trên target sẽ thiếu fix quan trọng — PHẢI kiểm tra `git status`/`git diff` trước khi chọn transfer method, không mặc định clone là đủ.
11. Khi thấy `docker-compose.yml` sửa gần đây, luôn `git diff` để hiểu ý đồ (ở đây: đúng là đang fix lại chính bug đã gây outage 9 ngày) — tránh vô tình transfer "backwards" (dùng bản compose cũ hơn, tái tạo lại bug).
12. Kiểm tra dung lượng đĩa đích SỚM, trước khi lên kế hoạch transfer chi tiết — 31G trống là ràng buộc cứng, quyết định luôn cả việc backups/orphaned data có transfer hay không.

**Bài học rút ra khi CHẠY THẬT phase 2-7 (2026-08-05, không có trong dry-run nu-data-pipeline vì project đó không có service non-root)**:
13. `tar --exclude=PATTERN` không có `/` khớp BASENAME bất kỳ đâu trong cây thư mục, không chỉ top-level — suýt xoá mất `data_lake/export/rill/current/*.parquet` (data thật) khi định loại `app_data/rill/` (rỗng). Luôn anchor bằng prefix `./` (`--exclude=./rill`) khi chỉ muốn loại top-level. Sau transfer, `diff` danh sách file 2 bên — đừng chỉ tin byte-count tổng khớp (có thể trùng hợp khớp dù thiếu/thừa khác file).
14. **UID mismatch trên Linux native khác hẳn Windows/Docker Desktop** — service chạy non-root (`rill` UID 1001, `metabase` UID 999) không ghi được vào bind-mount thuộc UID 1000 (`vantt`, user SSH/clone) → crash-loop (`mkdir: permission denied`, hoặc H2 "Connection has timed out" khó đoán nguyên nhân hơn nhiều). Windows Docker Desktop KHÔNG enforce Unix permission trên bind-mount nên bug này không lộ ra bao giờ ở đó. Trước khi deploy bất kỳ service non-root nào lên host Linux thật: kiểm tra `USER`/`useradd` trong Dockerfile, nếu có → `chmod o+w` (hoặc `chown`) bind-mount tương ứng TRƯỚC khi start. Đã kiểm tra: `crm`/`crm_drill_runner` chạy root, không dính bug này.
15. `docker compose --env-file X` ghi đè HẲN nguồn đọc `.env` mặc định cho biến `${VAR}` cấp compose-file (KHÁC với `env_file:` bên trong từng service, không liên quan tới cờ CLI này) — nếu secrets cần cho `${VAR}:?...}` nằm ở file khác (ở đây: root `.env`, không phải `.env.docker`), dùng `--env-file` sẽ làm toàn bộ lệnh fail dù chỉ định service không liên quan (compose validate hết services trước khi chọn service để start). Không dùng `--env-file` khi không thật sự cần đổi nguồn `.env`.
16. `Error: mkdir ... permission denied` và `SQLException: Connection has timed out` (H2) là 2 triệu chứng RẤT khác nhau của CÙNG MỘT nguyên nhân gốc (UID mismatch) — đừng debug 2 hướng riêng biệt, kiểm tra UID/ownership trước khi đào sâu vào error message cụ thể của từng service.
17. `has-user-setup` (không phải `setup-token`) là field đáng tin để xác nhận Metabase đã load đúng H2 DB có data thật — `setup-token` luôn xuất hiện trong `/api/session/properties` kể cả khi đã setup xong, dễ gây hoảng nhầm là "fresh instance".

---

## Decisions chốt (2026-08-04)

| # | Quyết định | Chọn |
|---|---|---|
| 1 | `app_data/backups` (11.75G) | **Bỏ qua hoàn toàn** — không transfer |
| 2 | `app_data/dagster_home` orphaned (12.05G) | **Bỏ hẳn** — không transfer |
| 3 | Path đích vantt-mactu | **Chốt 2026-08-05**: `~/projects/fg-data-warhouse` (path MỚI, giữ nguyên checkout cũ `~/projects/data-integration` tháng 4 không đụng, dọn sau nếu cần) |
| 4 | Caddy/DNS-01 | **Replicate `caddy-global` đầy đủ ngay từ đầu** — deploy trước phase 7, cấp cert thật cho `*.lan.fwg.vn` trên vantt-mactu |
| 5 | `CLOUDFLARE_API_TOKEN` | **Đã rotate, token hiện tại an toàn** — copy thẳng `.env.docker` hiện tại, không cần rotate lại trước |
| 6 | CRM production cutover timing | Chưa hỏi trực tiếp — giữ mặc định trong plan: **tách phase riêng (phase 8), gate bằng go-ahead rõ ràng của user**, không gộp chung dry-run các service còn lại |

→ Với quyết định #1+#2, tổng dung lượng cần transfer giảm còn **~12.2G** (live essential only) — thoải mái so với 31G trống trên vantt-mactu, không còn ràng buộc đĩa cứng nữa.

→ Với quyết định #4, phase 6 (reverse proxy) đổi từ "tạm thời port trực tiếp" thành "deploy `caddy-global` thật, verify cert issuance qua DNS-01" — cần chạy TRƯỚC phase 7 (verify services qua domain, không phải qua port thô).

**Chưa quyết** (giữ nguyên đề xuất mặc định trong plan cho tới khi user phản đối): timing CRM cutover (#6). Path đích (#3) đã chốt 2026-08-05: `~/projects/fg-data-warhouse`.

## Cập nhật phase 8 sau recon Cloudflare Tunnel (2026-08-04)

Phase 8 đã viết lại đầy đủ sau khi phát hiện tunnel thật là **locally-managed** (không phải token-based như scaffold comment trong `docker-compose.yml`), dùng chung cho 5 domain (`crm.fwg.vn`, `bi.fwg.vn`, `vnflow.fwg.vn`, `hermes.fwg.vn`, `fgos.fwg.vn`), không riêng data-integration. Quyết định:
- Chuyển nguyên cụm connector sang vantt-mactu, chạy Docker (`network_mode: host`), **standalone compose riêng** tại `~/cloudflared-tunnel/` — KHÔNG nhúng vào `data-integration/docker-compose.yml` (tránh coupling vòng đời với route của project khác).
- `vnflow.fwg.vn` (origin `192.168.20.175`, hiện offline, không phải design-lap/vantt-mactu) — **user chấp nhận bỏ qua**, ưu tiên `bi.fwg.vn`/`crm.fwg.vn`.
- `hermes.fwg.vn`/`fgos.fwg.vn` (origin `100.66.22.20` = design-lap, qua Tailscale) — tiếp tục hoạt động bình thường, không cần đổi gì.
- Máy Windows sẽ bị **uninstall và cài lại** sau khi migrate thành công (mốc cứng, không phải "giữ song song vô thời hạn") — phase 9 cần review lại theo mốc này thay vì "chờ ≥7 ngày ổn định rồi mới quyết".
- User cũng đã hạ ưu tiên `*.lan.fwg.vn` (Caddy DNS-01, phase 6) — tạm không cần, chỉ cần `bi.fwg.vn`/`crm.fwg.vn` hoạt động trước. Phase 6 cần re-sequence xuống sau phase 8, hoặc gộp làm optional.

Xem chi tiết đầy đủ trong `phase-08-crm-production-cutover.md` (đã viết lại toàn bộ).
