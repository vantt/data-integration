# Research: Off-site backup, restore verification và DR cho on-prem data platform

- Ngày: 2026-10-15 (Asia/Saigon). Người viết: researcher agent.
- Phạm vi: nghiên cứu và đề xuất. Không sửa code, không đọc `.env`/secrets.
- Ký hiệu: **[đã xác minh]** = có nguồn chính thức; **[chưa chắc]** = nguồn thứ cấp/diễn đàn hoặc suy luận; **[đánh giá]** = nhận định của tác giả.

---

## TL;DR

1. **Engine: restic** (0.19.1, 07/2026). Restic mã hóa phía client, dedup, có `check --read-data-subset` và hỗ trợ nhiều key cho một repo nên vendor và khách cùng giữ key được. Kopia đứng thứ hai (backend Google Drive và rclone vẫn ghi "experimental"). Borg 2.0 vẫn beta và không có backend cloud native. Duplicati có GUI nhưng có lịch sử lỗi local DB, nên loại.
2. **Đích mặc định: Google Drive qua rclone backend của restic** (`rclone:gdrive:fg-backup/<tenant>`). Đây là lựa chọn dễ nhất với SME Việt Nam vì khách đã có tài khoản Google. Có hai hệ quả cứng:
   - **Service account không có quota trên My Drive.** Service account chỉ dùng được với **Shared Drive**, tức khách phải có Google Workspace. Khách dùng Gmail cá nhân thì dùng OAuth.
   - **rclone sẽ ngừng cho dùng client_id chung trong 2026.** Vendor phải tạo OAuth client riêng và publish app, vì ở Testing mode token hết hạn sau 7 ngày. Nên dùng scope `drive.file`, là scope non-sensitive, chỉ cần verification cơ bản.
3. **Rủi ro pháp lý cần quyết trước khi chọn mặc định.** Decree 356/2025 coi việc lưu dữ liệu cá nhân thu thập ở VN trên "cloud của nhà cung cấp nước ngoài" là chuyển dữ liệu xuyên biên giới, nên có thể phải lập hồ sơ TIA nộp A05 trong 60 ngày. Không nguồn nào nói mã hóa phía client giúp miễn nghĩa vụ này **[chưa chắc]**. Vì vậy installer nên có lựa chọn thứ hai bằng một biến cấu hình: **S3 trong nước** (GreenNode/VNPT/Viettel...) hoặc **NAS Synology tại chỗ của khách**.
4. **Backup cái gì.** Chỉ backup nguồn sự thật (source of truth): raw Parquet, `dagster_home`, seeds, CRM SQLite (lấy từ snapshot đã qua gate), Metabase H2 (cold copy) kèm JSON export, `input_source`, và secrets (nằm trong repo restic đã mã hóa). Các file DuckDB phái sinh (`sapo_warehouse.duckdb`, `olap.duckdb`) **không đưa off-site hằng ngày** mà dựng lại bằng dbt. Điều này khớp với quyết định parquet-first trong `docs/operations/backup-restore-completeness-runbook.md`.
5. **Lịch và retention.** Off-site chạy hằng ngày lúc 03:30, sau backup cục bộ (01:04) và backup CRM (02:00). Retention: `--keep-daily 7 --keep-weekly 4 --keep-monthly 12`. Prune chạy hằng tuần. `check --read-data-subset=N/28` chạy hằng ngày nên mỗi ~4 tuần đọc lại toàn bộ repo. Restore drill (khôi phục vào thư mục tạm rồi chạy gate kiểm tra) chạy hằng tuần. Rebuild drill đầy đủ (dbt) chạy hằng tháng.
6. **Alert.** Dùng dead-man's switch (healthchecks.io, gói free 20 check) cộng với failure sensor Dagster đã có. Một backup mà không ai biết là đã ngừng chạy thì coi như không có backup.
7. **Chi phí.** Mỗi khách vài GB đến vài chục GB sau dedup. Google One 100 GB khoảng 45k VND/tháng **[chưa chắc, nguồn bán lẻ]**. B2 là $6.95/TB/tháng. R2 là $0.015/GB/tháng, miễn phí egress. S3 trong nước khoảng 400–1.000 VND/GB/tháng **[chưa chắc]**. Phần tốn nhất không phải tiền lưu trữ mà là **công setup OAuth/Shared Drive và quản lý key**.
8. **RPO 24h / RTO ≤ 1 ngày làm việc** là mục tiêu thực tế cho SME **[đánh giá]**. Muốn RTO ngắn hơn thì phải đưa thêm `olap.duckdb` off-site, xem §7.4.

---

## 1. Bối cảnh hiện tại (scout repo)

| Thành phần | Cơ chế hiện có | Khoảng trống |
|---|---|---|
| Data lake, `dagster_home`, input, config | `scripts/backup/backup.sh` qua Dagster `maintain_backup_platform_job`, chạy 01:04, giữ 7 bản | Chỉ cùng đĩa. Runbook ghi rõ các nhánh DB copy thô là **WAL-unsafe** |
| Metabase H2 (~191 MB ở dev, ~260 MB ở khách) | `metabase_cold_backup.sh` (systemd user timer, Chủ nhật 00:30) và `metabase_export.py` (JSON) | Chỉ cùng đĩa |
| CRM SQLite | `crm/ops/backup_crm.py` chạy chuỗi gate, rồi `restore_verify_crm.py` qua sidecar `crm_drill_runner`, 02:00 | Volume `crm_backups` cùng host |
| Warehouse DR | Plan `plans/260624-2010-warehouse-pipeline-dr-verified-restore/` (đang pending) | Chưa có off-site, chưa có alert về tuổi backup |
| Secrets | `app_data/secrets`, `.env`, `.env.docker` | `backup.sh` **không** copy `.env.docker`, nên hiện **không có** backup secrets |

Nhận xét: repo đã có sẵn phương pháp gate chain (manifest, so khớp source với snapshot, tamper test, drill cô lập). Việc còn thiếu là **chép ra ngoài máy, mã hóa, xác minh định kỳ từ bản off-site, và runbook dựng lại từ đầu**. Không cần thay phương pháp, chỉ cần nối thêm một chặng.

---

## 2. So sánh công cụ backup

### 2.1 Ma trận (điểm 1–5, 5 = tốt nhất cho bối cảnh này)

| Tiêu chí | **restic** | kopia | borg 1.4 | Duplicati 2.2 | rclone sync/crypt thuần |
|---|---|---|---|---|---|
| Mã hóa client-side | 5 (AES-256 + Poly1305, luôn bật) | 5 | 5 | 4 | 3 (rclone crypt, không có snapshot) |
| Dedup / incremental | 5 | 5 | 5 | 4 | 1 (chỉ sync file) |
| Google Drive | 4 (qua `rclone serve restic --stdio`, ổn định) | 3 (native và rclone đều **experimental**) | 1 (cần SSH/rsync.net hoặc rclone mount) | 4 (native) | 5 |
| S3/B2/R2 | 5 | 5 | 1 | 4 | 5 |
| Verify dữ liệu đã lưu | 5 (`check --read-data-subset`) | 4 (`snapshot verify --verify-files-percent`) **[chưa chắc tên cờ]** | 4 (`check --verify-data`) | 3 | 2 |
| Nhiều key cho một repo (escrow) | 5 (`key add`) | 4 | 2 (một passphrase) | 2 | 2 |
| Độ trưởng thành / rủi ro | 5 (0.19.x, format v2 từ 0.14) | 4 (0.23.1, có bản vá race condition gây mất dữ liệu 06/2026) | 4 (1.4 ổn định; 2.0 beta, "do not use in production") | 2 (local DB dễ lệch, nhiều báo cáo diễn đàn **[chưa chắc]**) | 4 |
| Footprint (single binary, dễ đóng vào Docker) | 5 | 5 | 3 (Python) | 2 (.NET, GUI) | 5 |
| **Tổng** | **39** | 35 | 25 | 25 | 27 |

### 2.2 Xếp hạng

1. **restic + rclone**: chọn làm mặc định. Một cặp binary dùng được cho mọi đích (Drive, S3, B2, R2, NAS qua SFTP/S3). Đổi đích chỉ cần đổi `RESTIC_REPOSITORY`.
2. **kopia**: đáng cân nhắc nếu cần GUI cho kỹ thuật viên. Không chọn vì backend Drive/rclone còn experimental, và năm 2026 có lỗi race gây mất dữ liệu (đã vá ở 0.23.1).
3. **borg 1.4**: mạnh nếu dùng rsync.net/BorgBase qua SSH. Không hợp với Google Drive. Borg 2 chưa GA.
4. **Duplicati / rclone sync thuần**: loại. Duplicati đã có báo cáo lệch local DB. rclone sync không có snapshot/retention nên ransomware hoặc lỗi xóa sẽ lan sang bản off-site.

**Backrest** (web UI cho restic) là tùy chọn sau này nếu kỹ thuật viên cần xem snapshot trên giao diện. Không đưa vào mặc định (KISS).

### 2.3 Đích lưu trữ

| Đích | Giá | Dễ setup cho SME | Pháp lý (§6) | Ghi chú kỹ thuật |
|---|---|---|---|---|
| **Google Drive (Gmail + Google One)** | ~45k VND/100 GB/tháng **[chưa chắc]** | 5 (khách đã có tài khoản) | Lưu ở nước ngoài | OAuth, cần client_id riêng; ~2 file/s; 750 GB/ngày; file tối đa 5 TB |
| **Google Workspace Shared Drive + service account** | Nằm trong gói Workspace | 4 | Lưu ở nước ngoài | Không token hết hạn, hợp với server. Item limit ~400k/Shared Drive **[chưa chắc]** |
| Backblaze B2 (S3 API) | $6.95/TB/tháng, 10 GB free, egress free tới 3x | 3 (thẻ quốc tế, tiếng Anh) | Lưu ở nước ngoài | restic khuyên dùng S3 API thay vì native B2. Có Object Lock |
| Cloudflare R2 | $0.015/GB/tháng, 10 GB free, egress $0 | 3 | Lưu ở nước ngoài | Repo restic nhỏ có thể nằm gọn trong free tier |
| **S3 trong nước** (GreenNode vStorage, VNPT, Viettel, Vietnix...) | ~400–1.000 VND/GB/tháng **[chưa chắc]** | 3 (cần hợp đồng/hóa đơn VN) | **Dữ liệu ở trong VN** | Phải test tương thích S3 với restic (path-style) |
| NAS Synology tại chỗ/chi nhánh | Phần cứng 8–15 triệu VND **[đánh giá]** | 2 (cần người lo phần cứng) | Trong VN | restic dùng qua SFTP hoặc MinIO/S3. Không chống cháy nổ nếu NAS ở cùng văn phòng |

---

## 3. Google Drive: các ràng buộc đã xác minh

| Ràng buộc | Chi tiết | Nguồn |
|---|---|---|
| Service account không có storage | "Standalone service accounts ... don't have personal Drive storage". Ghi vào My Drive sẽ bị 403. Giải pháp là Shared Drive với `supportsAllDrives=true` hoặc domain-wide delegation | Google Workspace Admin Help **[đã xác minh]** |
| Chia sẻ folder My Drive cho SA **không** giải quyết được | File do SA tạo vẫn tính vào quota của SA. Có báo cáo SA tạo sau 15/04/2025 có quota 0 | Fivetran docs, n8n forum **[chưa chắc với mốc 2025]** |
| 750 GB/ngày/user | Áp cho cả upload lẫn copy. Dùng `--drive-stop-on-upload-limit` để dừng sạch khi chạm giới hạn | Workspace Help, rclone docs **[đã xác minh]** |
| File tối đa 5 TB | Không ảnh hưởng vì restic chia pack 16–128 MiB | Workspace Help **[đã xác minh]** |
| Tốc độ ~2 file/s, quota mặc định 10 tps | Nên tăng `--pack-size` lên 64 MiB để giảm số file | rclone docs; restic forum **[đã xác minh / chưa chắc]** |
| Chunk upload | `--drive-chunk-size` mặc định 8 Mi, là lũy thừa của 2. Mỗi transfer đệm một chunk trong RAM | rclone docs **[đã xác minh]** |
| client_id dùng chung của rclone bị rút trong 2026 | "To avoid interruption you must create and use your own client_id" | rclone docs **[đã xác minh]** |
| Testing mode | "any grants will expire after a week". Phải publish app (production). App chưa verify vẫn dùng được, user chỉ thấy cảnh báo | rclone docs **[đã xác minh]** |
| Scope | `drive.file` là non-sensitive và chỉ cần verification cơ bản. Scope `drive` đầy đủ là restricted, cần verification và có thể cả security assessment (CASA) | Google Drive API "Choose scopes" **[đã xác minh]** |
| Headless | `rclone authorize "drive"` chạy trên máy có browser, rồi dán token vào máy chủ | rclone remote_setup **[đã xác minh]** |

**Hệ quả thiết kế:**

- Vendor tạo **một** GCP project "FG Backup" với OAuth client (Desktop app) và scope `drive.file`, rồi publish. Restic qua rclone chỉ đụng tới file do chính nó tạo nên `drive.file` là đủ. **Cần test**: khi restore trên máy mới, cùng OAuth client và cùng tài khoản phải thấy được các file đã tạo trước đó **[chưa chắc]**.
- Khách có Workspace: dùng service account với Shared Drive "FG Backup – <tenant>". Cách này không có token hết hạn và không có màn hình consent, nên là đường ưu tiên khi có điều kiện.
- Với Gmail cá nhân, OAuth refresh token có thể bị thu hồi khi khách đổi mật khẩu hoặc gỡ quyền app. Dead-man's switch (§5.4) sẽ bắt được trường hợp này **[đánh giá]**.

---

## 4. Backup nhất quán ở mức ứng dụng (app-consistent)

| Store | Kỹ thuật | Lý do |
|---|---|---|
| **Raw Parquet** (`data_lake/raw...`) | restic đọc trực tiếp từ thư mục live, mount `:ro` | Parquet là immutable/append-only nên không có torn write. Không cần staging, đỡ tốn 2x dung lượng đĩa |
| **DuckDB** (`sapo_warehouse.duckdb`, `olap.duckdb`, `monitoring`) | **Mặc định: không backup off-site, dựng lại bằng dbt.** Nếu cần (§7.4): giữ `duckdb_lock`, chạy `FORCE CHECKPOINT`, copy file khi writer đã dừng; hoặc `EXPORT DATABASE ... (FORMAT parquet)` | DuckDB không có online backup API. Docs chỉ nói `CHECKPOINT` đẩy WAL vào file chính và `FORCE CHECKPOINT` chặn transaction mới. Không có tài liệu chính thức nào bảo copy file khi writer đang chạy là an toàn **[chưa chắc]**. `EXPORT DATABASE` xuất schema, tables, views, sequences. Docs không nói gì về tính nhất quán khi có ghi đồng thời |
| **CRM SQLite** | Dùng snapshot đã qua gate trong `crm_backups` (online-backup API + manifest). **Không** copy `crm_data` live | SQLite docs: backup API và `VACUUM INTO` đều cho snapshot nhất quán của DB live. Repo đã dùng backup API |
| **Dagster `dagster_home`** (SQLite) | `sqlite3 <db> ".backup <staging>"` hoặc `VACUUM INTO` cho `runs.db`/`schedules.db`. File yaml copy thẳng | Tránh copy WAL dở dang (bài học L56/L68) |
| **Metabase H2** | Cold copy (Metabase dừng 1–2 phút) mà `metabase_cold_backup.sh` đã làm, kèm JSON export qua API | Metabase docs: dừng Metabase rồi copy `metabase.db.mv.db`. Docs cũng khuyên chuyển sang Postgres cho production. Serialization chính thức chỉ có ở bản trả phí **[chưa chắc]** nên JSON export qua API là bản bù |
| **Secrets** (`.env`, `.env.docker`, `app_data/secrets`) | restic đọc từ host, nên chỉ nằm trong repo đã mã hóa. Không bao giờ chép ra dạng plaintext | Đáp ứng yêu cầu "secrets chỉ được backup khi đã mã hóa" |
| **rclone.conf / restic password** | **Không** nằm trong repo (gà và trứng). Escrow riêng (§6.1) | Cần hai thứ này mới mở được repo |

**Thứ tự trong một lần chạy off-site (03:30):**
1. Pre-flight: kiểm tra tuổi của snapshot CRM (< 26h) và của bản cold copy Metabase mới nhất (< 8 ngày). Bản nào quá hạn thì FAIL.
2. Staging DB: `.backup` cho `dagster_home`, rồi ghi `manifest.json` (sha256, row count) theo đúng format CRM đang dùng.
3. `restic backup` các path dưới đây, với `--tag tenant=<id> --tag git=<sha> --tag compose=<digest>`:
   - `data_lake/raw`
   - seeds
   - staging
   - `crm_backups/latest`
   - `backups/metabase/latest.mv.db`
   - `metabase_export/latest`
   - `input_source`
   - secrets
   - `docker-compose*.yml`
   - `.env*`
4. `restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12`. Chỉ chạy `--prune` vào Chủ nhật vì prune khóa repo, và repack trên Drive chậm. Dùng `--max-unused 10%` để giảm repack.
5. `restic check --read-data-subset=$((DOM % 28 + 1))/28`.
6. Ping healthchecks: `/start` lúc bắt đầu, `/<exit-code>` lúc kết thúc.

---

## 5. Chạy trên Docker và trên Linux thuần

### 5.1 Đặt lịch ở đâu (xếp hạng)

1. **systemd timer trên host** gọi `docker compose run --rm backup offsite`. Ở chế độ Linux thuần, gọi thẳng `offsite_backup.sh`. Lý do chọn:
   - Timer vẫn chạy khi stack/Dagster hỏng, và đó chính là lúc cần backup nhất.
   - Repo đã dùng systemd user timer cho Metabase.
   - `OnFailure=` có thể gửi alert.
   - `Persistent=true` chạy bù nếu máy tắt đúng giờ hẹn.
2. **Dagster job** (như `maintain_backup_platform_job`). Phù hợp cho các bước cục bộ đã có. Không nên là điểm điều phối duy nhất cho off-site.
3. **supercronic trong sidecar**. Hợp cho cron trong container: giữ env, log ra stdout, dừng êm. Dùng khi khách không cho cài unit systemd.
4. **ofelia**: loại, vì cần Docker socket. Repo đã chủ động giới hạn socket chỉ ở `crm_drill_runner` (bài học L150).

### 5.2 Sidecar `backup` (image tự build, pin version)

```
FROM restic/restic:0.19.1          # pin; [chưa chắc] image có kèm rclone hay không → tự COPY rclone binary pin version
+ rclone vX.Y (pin) + sqlite3 + duckdb CLI (cùng version với pipeline)
volumes (tất cả :ro, trừ staging + cache):
  ./app_data/data_lake:/src/data_lake:ro
  ./app_data/input_source:/src/input:ro
  ./app_data/backups/metabase:/src/metabase:ro
  crm_backups:/src/crm_backups:ro
  dagster_home:/src/dagster_home:ro        # .backup đọc được ở ro? SQLite .backup cần mở DB; dùng ?mode=ro → [chưa chắc với WAL], fallback: chạy .backup trong data_platform
  ./app_data/secrets:/src/secrets:ro
  ./.env:/src/env/.env:ro  (host-only file)
  restic_cache:/cache   backup_staging:/staging
secrets: rclone.conf + RESTIC_PASSWORD_FILE qua docker secrets / file 0600 trên host
network: chỉ egress; không join caddy_net; không socket
```

### 5.3 Linux thuần

Dùng cùng `offsite_backup.sh` (POSIX sh) cùng binary restic/rclone đã pin, cài vào `/opt/fg-backup/bin`. Unit `fg-offsite-backup.service` dùng `Type=oneshot` và `EnvironmentFile=/etc/fg-backup/env` (quyền 0600). Timer dùng `OnCalendar=*-*-* 03:30` và `Persistent=true`. Thêm `fg-restore-drill.timer` chạy hằng tuần.

### 5.4 Thông báo lỗi

Cần có ít nhất hai kênh độc lập:
- **Dead-man's switch**: healthchecks.io, gói free gồm 20 check và 100 log entry mỗi check. Hỗ trợ cron/OnCalendar schedule và grace time. Có `/start`, `/fail`, `/<exitcode>`. Kênh này bắt được cả trường hợp **máy chết, job không chạy**, điều mà alert do job tự gửi không làm được. Có thể tự host nếu không muốn dùng SaaS.
- **Alert chủ động**: `OnFailure=fg-notify@%n.service` gửi Telegram/Zalo/email, hoặc dùng failure sensor Dagster đã có. Có Telegram integration của healthchecks hay không thì trang docs không xác nhận **[chưa chắc]**.
- Một check cho mỗi tenant và mỗi job (backup, check, drill). Vendor theo dõi tập trung tất cả tenant.

---

## 6. Bảo mật và pháp lý

### 6.1 Quản lý key (ai giữ key)

restic cho phép **nhiều key** trên một repo (`key add/list/remove/passwd`), và key nào cũng mở được repo. Đề xuất:

| Key | Người giữ | Lưu ở đâu |
|---|---|---|
| `key-customer` | Chủ doanh nghiệp | In ra "Recovery Sheet", niêm phong, cất két. Khách có thể giữ thêm bản trong password manager |
| `key-vendor` | Vendor (FG) | Password manager tổ chức (Bitwarden/1Password org vault), chỉ 2 người có quyền |
| `key-host` | Máy chủ (để chạy job) | `/etc/fg-backup/restic.pass` quyền 0600. Mất máy thì `key remove` key này |

- Recovery Sheet gồm: tenant id, `RESTIC_REPOSITORY`, cách lấy lại quyền Drive (tài khoản Google nào), restic key, git tag hoặc version của installer, và số điện thoại vendor.
- **Mất hết key thì mất dữ liệu** (restic docs). Cần ít nhất hai người giữ ở hai nơi tách biệt.
- Vendor giữ key nghĩa là vendor **có thể đọc PII của khách**. Điều này phải ghi trong hợp đồng xử lý dữ liệu (DPA), xem bên dưới.
- Chống ransomware: host có toàn quyền ghi/xóa trên Drive. Biện pháp là giữ thêm bản monthly ở một đích **append-only/Object Lock** (B2/S3 có Object Lock) mà vendor quản lý. Đây là tùy chọn cho khách cần mức an toàn cao **[đánh giá]**.

### 6.2 Luật 91/2025/QH15 và Decree 356/2025/ND-CP (hiệu lực 01/01/2026). Toàn bộ mục này **[chưa chắc, nguồn thứ cấp]**

- **Định nghĩa chuyển xuyên biên giới** bao gồm việc lưu dữ liệu cá nhân thu thập ở VN "to server systems located outside the territory of Vietnam, or to cloud computing services of foreign service providers" (Rajah & Tann). Google Drive, B2 và R2 đều thuộc trường hợp này.
- **TIA (đánh giá tác động chuyển dữ liệu xuyên biên giới)**:
  - Nộp trong **60 ngày** kể từ lần chuyển đầu tiên. A05 (Bộ Công an) thẩm định trước (ex-ante) trong 15 ngày. Hồ sơ dùng Form 09/10, kèm sơ đồ luồng dữ liệu và phương án bảo mật (EY, 03/2026).
  - Mức phạt nếu không lập TIA: tới 50 triệu VND theo Decree 330/2026 (VIR).
  - Mức phạt tổng thể cho vi phạm chuyển xuyên biên giới: tới 5% doanh thu (Tilleke).
- **Miễn trừ cho SME**: doanh nghiệp nhỏ và startup được miễn DPIA/TIA 5 năm, hộ kinh doanh và doanh nghiệp siêu nhỏ được miễn hoàn toàn. Miễn trừ **không áp dụng** nếu:
  - doanh nghiệp xử lý dữ liệu nhạy cảm;
  - số chủ thể dữ liệu cộng dồn **≥ 100.000** (một nhà bán lẻ có CRM vài năm dễ vượt ngưỡng này);
  - doanh nghiệp **cung cấp dịch vụ xử lý dữ liệu cá nhân**.
- **Vendor có thể bị coi là bên cung cấp dịch vụ xử lý dữ liệu.** Nếu FG vận hành backup và giữ key, FG có thể rơi vào nhóm "providing systems or automated software to process personal data on behalf of data controllers". Nhóm này là ngành nghề có điều kiện và cần chứng nhận của Bộ Công an (Rajah & Tann) **[chưa chắc, rủi ro cao]**.
- **Mã hóa**: EY nhắc mã hóa và ẩn danh như biện pháp bắt buộc khi chuyển dữ liệu nhạy cảm. Không nguồn nào nói **mã hóa phía client làm mất tính chất "chuyển"**. Không được giả định là được miễn.

**Hệ quả cho sản phẩm:**
1. Installer hỏi khách chọn đích: "Google Drive (dễ, lưu ở nước ngoài, có thể phải lập TIA)" hoặc "S3/NAS trong nước". Ghi nhận khách đã đồng ý.
2. Cung cấp sẵn bản mẫu sơ đồ luồng dữ liệu backup để khách đưa vào hồ sơ TIA.
3. **Phải có ý kiến luật sư VN** trước khi bán gói "managed backup" có vendor giữ key.

---

## 7. Restore verification và DR

### 7.1 Ba tầng xác minh

| Tầng | Tần suất | Nội dung | Khi FAIL |
|---|---|---|---|
| T1 Repo integrity | Hằng ngày, sau backup | `restic check --read-data-subset=n/28`, phủ toàn repo trong ~4 tuần, tốn ~1/28 dung lượng download mỗi ngày | Alert, sau đó `restic repair` theo docs |
| T2 Restore drill | Hằng tuần, Chủ nhật 05:00 | Restore `latest` từ **off-site** vào scratch volume, rồi chạy các gate dưới đây | Alert, giữ lại scratch để điều tra |
| T3 Rebuild drill | Hằng tháng | Theo plan warehouse-DR: restore raw → `dbt build` → serving → so recon/KPI invariant. Có tamper test (xóa một partition thì drill phải FAIL) | Alert |

Các gate trong T2 (restore drill hằng tuần):
- (a) so `manifest.json`: sha256 và row count;
- (b) SQLite `PRAGMA integrity_check` cho CRM và Dagster;
- (c) DuckDB mở `READ_ONLY` một file parquet mẫu hoặc chạy `read_parquet(...)` đếm dòng từng partition, so với manifest;
- (d) **Metabase boot test**: container Metabase tạm, cùng image digest, mount H2 đã restore, không route, không network prod; chờ `/api/health`, đếm card/dashboard bằng H2 hoặc API, so với `manifest.json` của JSON export;
- (e) CRM: tái dùng `restore_verify_crm.py` với nguồn là bản off-site;
- (f) assert prod không bị đụng tới (fingerprint trước và sau).

T2 tái dùng nguyên mẫu `crm_drill_runner`: sidecar giữ socket, nhận token, không có route. Chỉ cần mở rộng phạm vi. **Không** cấp socket cho `data_platform`.

### 7.2 RPO/RTO đề xuất **[đánh giá, không có nguồn chuẩn ngành chính thức]**

| Dữ liệu | RPO | RTO |
|---|---|---|
| CRM (giao dịch hằng ngày của nhân viên) | 24h. Nếu khách cần, tăng lên 2 lần/ngày | 2–4h |
| Metabase content | 24h (JSON), 7 ngày (H2 đầy đủ) | 1h sau khi stack chạy |
| Data lake / dashboard | 24h (dữ liệu nguồn Sapo/sàn có thể kéo lại) | ≤ 1 ngày làm việc, chủ yếu tốn thời gian `dbt build` |

### 7.3 Runbook dựng lại từ đầu trên máy mới (mục tiêu dưới 2h công, chưa tính dbt)

```
0. Chuẩn bị: Recovery Sheet + máy Linux (Ubuntu LTS) có Docker; DNS/Cloudflare quyền.
1. curl installer (tag = version ghi trên Recovery Sheet hoặc tag trong snapshot)  → cài docker, restic, rclone pin.
2. installer restore --tenant <id>:
     a. cấu hình rclone (SA JSON hoặc `rclone authorize` từ laptop) ; nhập restic key
     b. restic snapshots --tag tenant=<id> → chọn latest ; restic restore → /opt/fg/<tenant>
     c. đặt lại .env/.env.docker/secrets từ restore (0600) ; kiểm tra manifest
3. git checkout <tag git=sha trong snapshot> ; docker compose pull/build theo image digest đã pin
4. Khôi phục store: CRM db ← snapshot ; Metabase H2 ← latest.mv.db ; dagster_home ← staging
5. docker compose up -d ; chạy dbt build + serving (hoặc restore olap.duckdb nếu có, §7.4)
6. Cloudflare Tunnel: token trong .env → tunnel tự gắn lại máy mới ; Caddy TLS tự cấp lại
   (không backup caddy_data). Nếu khách dùng DNS nội bộ (*.lan.fwg.vn) → sửa bản ghi A.
7. Chạy restore-drill gates (T2) trên hệ thật → ký biên bản ; restic key remove key-host cũ ; key add key-host mới
8. Bật lại timers backup ; ping healthchecks.
```

Điều kiện tiên quyết **phải sửa** để runbook khả thi **[đánh giá dựa trên `docker-compose.yml`]**:
- Pin image: `caddy:alpine` và `cloudflare/cloudflared:latest` đang không pin. Metabase image cần pin digest.
- Mỗi snapshot phải ghi git sha và compose digest (tag restic).
- Installer khách mới và lệnh `restore` phải là **cùng một tool**. Cài mới là trường hợp "restore từ snapshot rỗng". Như vậy mỗi lần cài cho khách mới cũng chính là một lần test đường DR.

### 7.4 Có nên đưa DuckDB phái sinh off-site không?

- **Không (mặc định):** tiết kiệm dung lượng và upload. Restic dedup kém trên file DuckDB vì file bị ghi lại nhiều chỗ mỗi lần chạy dbt **[đánh giá]**. RTO phụ thuộc thời gian `dbt build` trên máy khách.
- **Có, hằng tuần:** khi `dbt build` đầy đủ mất vài giờ. Chụp `olap.duckdb` khi đang giữ `duckdb_lock`, sau `FORCE CHECKPOINT`, rồi copy và gắn tag `kind=accelerator`. Retention chỉ 2 bản.
- Cần đo thời gian full rebuild trên một máy khách thật để quyết định (xem câu hỏi mở).

---

## 8. Đề xuất cho sản phẩm

### 8.1 Stack mặc định (xếp hạng)

| Hạng | Stack | Khi nào dùng |
|---|---|---|
| **1** | **restic 0.19.x + rclone → Google Drive**: Shared Drive + service account nếu khách có Workspace, OAuth `drive.file` nếu khách dùng Gmail | Mặc định, khi khách chấp nhận lưu ở nước ngoài (đã cảnh báo về TIA) |
| 2 | restic → **S3 trong nước** (provider đã qua test tương thích) | Khách có ≥100k chủ thể dữ liệu, có dữ liệu nhạy cảm, hoặc muốn tránh vấn đề xuyên biên giới |
| 3 | restic → B2/R2 (S3 API, có Object Lock) | Đích thứ hai, append-only, do vendor quản lý, cho khách cần chống ransomware |
| 4 | restic → NAS Synology (SFTP/S3) | Khách đã có NAS. Chỉ tính là off-site nếu NAS đặt ở địa điểm khác |

Cả bốn dùng **cùng script**, chỉ khác `RESTIC_REPOSITORY` (DRY).

### 8.2 Sơ đồ

```
 Máy khách (Linux + Docker)                                       Off-site
 ┌───────────────────────────────────────────────────────┐
 │ data_platform ──01:04 backup.sh (local, 7 bản)        │
 │ crm ──02:00 backup_crm.py → crm_backups (gated)       │
 │ metabase ──Sun 00:30 cold copy + JSON export          │
 │                                                       │
 │ systemd timer 03:30 ─► [backup sidecar: restic+rclone]│   encrypted   ┌──────────────────┐
 │   reads :ro ─ raw parquet, seeds, input_source        │ ───packs────► │ Google Drive     │
 │            ─ crm_backups/latest, metabase latest      │  (AES-256)    │ (Shared Drive /  │
 │            ─ dagster_home (.backup→staging)           │               │  OAuth drive.file)│
 │            ─ .env*, secrets, compose files            │               │  hoặc S3 VN / B2 │
 │   forget (daily) · prune (Sun) · check subset n/28    │               └────────┬─────────┘
 │                                                       │                        │
 │ Sun 05:00 restore drill (drill_runner) ◄──────────────┼────── restore latest ──┘
 │   manifest · integrity_check · parquet counts         │
 │   · ephemeral Metabase /api/health · CRM drill        │
 │ monthly: rebuild drill (dbt) + tamper test            │
 └───────────┬───────────────────────────────────────────┘
             │ ping /start, /<exit>                 Keys: customer (sealed sheet)
             ▼                                            vendor (org vault)
      healthchecks.io (dead-man) ──► Telegram/email       host (0600, revocable)
      + Dagster failure sensor
```

### 8.3 Lịch và retention

| Job | Lịch | Ghi chú |
|---|---|---|
| Off-site backup | Hằng ngày 03:30 | `--pack-size 64`, `--compression auto` |
| forget | Mỗi lần backup | `--keep-daily 7 --keep-weekly 4 --keep-monthly 12`. Có thể thêm `--keep-yearly 3` cho dữ liệu tài chính **[đánh giá]** |
| prune | Chủ nhật 04:00 | `--max-unused 10%`, sau đó chạy `check` |
| check subset | Hằng ngày, sau backup | `n/28` |
| Restore drill T2 | Chủ nhật 05:00 | Restore từ off-site |
| Rebuild drill T3 | Ngày 1 hằng tháng | Có tamper test |
| Alert tuổi backup | Liên tục | Grace 6h trên healthchecks |

### 8.4 Các bước setup cho một khách (mục tiêu khoảng 30 phút)

1. `installer backup init --target gdrive|s3vn|b2|nas`.
2. Với Drive Workspace: khách tạo Shared Drive và thêm email service account của vendor (hoặc của khách) với quyền Content manager. Với Gmail: kỹ thuật viên chạy `rclone authorize "drive"` trên laptop rồi dán token.
3. Installer chạy `restic init`. Sinh 3 key, in Recovery Sheet ra PDF, đẩy key-vendor vào vault.
4. Installer cài timer/sidecar, tạo 3 check healthchecks, rồi chạy **backup đầu tiên và drill T2 ngay**. Biên bản bàn giao gồm snapshot id và kết quả drill.
5. Ghi nhận khách đã chọn đích lưu trữ và đã được giải thích về TIA.

### 8.5 Chi phí ước tính mỗi khách mỗi tháng (repo ~10–30 GB sau dedup) **[đánh giá]**

| Đích | Chi phí lưu trữ |
|---|---|
| Google Drive 100 GB | ~45k VND (thường khách đã có sẵn) |
| B2 | ~$0.07–0.2, có thể nằm gọn trong free 10 GB |
| R2 | 10 GB free, phần vượt ~$0.15–0.3 |
| S3 VN | ~10–30k VND |
| healthchecks | Free (20 check, đủ cho ~6 tenant với 3 check/tenant). Từ khoảng 7 tenant trở lên cần gói Business $20/tháng hoặc tự host |

Chi phí lớn nhất là **công của vendor**: phát triển một lần (sidecar, script, drill mở rộng, installer restore) cộng setup khoảng 30 phút/khách cộng xử lý alert.

### 8.6 Không làm (KISS)

- Không dùng Backrest UI.
- Không dùng ofelia.
- Không dùng `rclone sync` song song với restic.
- Không backup `caddy_data`.
- Không backup lịch sử run của Dagster.
- Không backup DuckDB hằng ngày.

---

## 9. Rủi ro áp dụng

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Google đổi chính sách OAuth/quota (đã từng xảy ra: SA quota, client_id rclone) | Trung bình | Abstraction là `RESTIC_REPOSITORY`. Đổi sang S3 không cần sửa code |
| Token OAuth bị thu hồi khi khách đổi mật khẩu | Trung bình | Dead-man alert; ưu tiên SA + Shared Drive |
| Pháp lý: TIA, vendor bị coi là "dịch vụ xử lý" | **Cao, chưa rõ** | Có lựa chọn đích trong nước; cần ý kiến luật sư |
| Mất key | Thấp nhưng hậu quả cực lớn | 3 key, 2 người giữ, Recovery Sheet; drill T2 dùng key-customer mỗi quý để chứng minh key còn dùng được |
| Ransomware trên host xóa repo | Thấp–trung bình | Đích phụ có Object Lock (hạng 3) |
| restic/rclone breaking change | Thấp (repo format v2 ổn định từ 0.14) | Pin version trong image, cập nhật có kiểm soát |

---

## 10. Giới hạn của nghiên cứu

- Chưa test thực nghiệm restic + rclone + Drive với dữ liệu thật (tốc độ, số file, hành vi `drive.file` khi restore trên máy mới).
- Chưa đọc văn bản gốc Luật 91/2025 và Decree 356. Mục §6.2 dựa trên Rajah & Tann, EY, VIR và Tilleke.
- Giá Google One tại VN và giá S3 trong nước lấy từ nguồn bán lẻ hoặc vendor blog, chưa kiểm tra trang chính thức.
- Chưa kiểm tra image `restic/restic` có kèm rclone hay không; chưa kiểm tra tên cờ verify của kopia.
- Chưa đo thời gian `dbt build` đầy đủ, nên RTO ở §7.2 là ước lượng.
- Không nghiên cứu chuyển Metabase H2 sang Postgres, dù docs Metabase khuyến nghị việc này. Nếu chuyển thì dùng `pg_dump` thay cho cold copy.

## 11. Nguồn (truy cập 2026-10-15)

- rclone Google Drive backend: https://rclone.org/drive/ (chính thức)
- rclone remote setup (headless): https://rclone.org/remote_setup/ (chính thức)
- Google Workspace storage and upload limits: https://knowledge.workspace.google.com/admin/drive/storage-and-upload-limits-for-google-workspace (chính thức)
- Google Drive API scopes: https://developers.google.com/workspace/drive/api/guides/api-specific-auth (chính thức)
- Fivetran: service accounts do not have storage quota: https://fivetran.com/docs/activations/destinations/available-destinations/google-drive/troubleshooting/service-accounts-storage-quota (thứ cấp)
- n8n community (SA tạo sau 04/2025 có quota 0): https://community.n8n.io/t/upload-file-google-drive-node-with-service-account-not-working/147750/15 (diễn đàn, độ tin cậy thấp)
- restic preparing repo (rclone/S3/B2): https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html (chính thức)
- restic check / read-data-subset: https://restic.readthedocs.io/en/stable/045_working_with_repos.html (chính thức)
- restic forget/prune: https://restic.readthedocs.io/en/stable/060_forget.html (chính thức)
- restic encryption / keys: https://restic.readthedocs.io/en/stable/070_encryption.html (chính thức)
- restic releases: https://github.com/restic/restic/releases (chính thức)
- restic 0.14 changelog pack-size: https://git.2li.ch/clitools/restic/src/commit/92df039e5d5bc43ee7924cda6d4ebcc2e9505d1e/changelog/0.14.0_2022-08-25/issue-2291 (mirror)
- restic forum: Google Drive: https://forum.restic.net/t/should-we-discourage-users-from-using-google-drive/1740/23 (diễn đàn)
- kopia repositories: https://kopia.io/docs/repositories/ ; releases: https://github.com/kopia/kopia/releases (chính thức)
- Borg 2.0 status: https://www.borgbackup.org/releases/borg-2.0.html ; https://en.wikipedia.org/wiki/Borg_(backup_software)
- Duplicati 2.2.0.0 release: https://forum.duplicati.com/t/release-2-2-0-0-stable-2025-10-23/21453/
- DuckDB EXPORT DATABASE: https://duckdb.org/docs/current/sql/statements/export.html ; concurrency: https://duckdb.org/docs/current/connect/concurrency.html ; CHECKPOINT: https://duckdb.org/docs/stable/sql/statements/checkpoint (chính thức)
- SQLite VACUUM INTO: https://www.sqlite.org/lang_vacuum.html (chính thức)
- Metabase backup: https://www.metabase.com/docs/latest/installation-and-operation/backing-up-metabase-application-data (chính thức)
- Backblaze B2 pricing: https://www.backblaze.com/cloud-storage/pricing ; Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/ (chính thức)
- GreenNode: so sánh object storage VN: https://greennode.ai/blog/object-storage-viet-nam-gia-do-tre (vendor blog)
- Google One VN price: https://cellphones.com.vn/sforum/google-one-la-gi-cac-goi-dich-vu-va-tinh-nang-co-gi-khac-so-voi-google-drive (bán lẻ); https://one.google.com/about/plans?hl=en_SG
- healthchecks.io docs/pricing: https://healthchecks.io/docs/ ; https://healthchecks.io/pricing/ (chính thức)
- supercronic: https://github.com/aptible/supercronic (chính thức)
- Rajah & Tann, Decree 356: https://www.rajahtannasia.com/viewpoints/new-decree-implementing-the-law-on-personal-data-protection-passed/ (thứ cấp)
- EY Vietnam legal alert 03/2026: https://www.ey.com/en_vn/technical/tax/tax-and-law-updates/legal-alert-march-2026-decree-no-356-2025-nd-cp-providing-detailed-guidance-for-implementation-of-personal-data-protection-law (thứ cấp)
- Tilleke, PDPL closer look: https://www.tilleke.com/insights/vietnams-new-personal-data-protection-law-a-closer-look/ (thứ cấp)
- VIR, data compliance: https://vir.com.vn/data-compliance-the-hidden-clause-in-cross-border-vietnam-deals-161633.html (báo chí)
- Repo: `scripts/backup/README.md`, `docs/operations/backup-restore-completeness-runbook.md`, `plans/260624-2010-warehouse-pipeline-dr-verified-restore/plan.md`, `docker-compose.yml`

## 12. Câu hỏi mở

1. **Pháp lý**: lưu backup đã mã hóa phía client trên Google Drive có phải "chuyển xuyên biên giới" cần TIA không? Vendor giữ key có bị coi là "dịch vụ xử lý dữ liệu cá nhân" (ngành nghề có điều kiện) không? Cần luật sư VN trả lời.
2. Khách điển hình dùng Gmail cá nhân hay Google Workspace? Câu trả lời quyết định đường mặc định là OAuth hay service account + Shared Drive.
3. Ai sở hữu GCP project, OAuth client và service account: vendor (một cho tất cả khách) hay từng khách? Có cần chạy verification cơ bản cho scope `drive.file` không?
4. Thời gian `dbt build` + serving đầy đủ trên máy khách thật là bao lâu? Con số này quyết định có đưa `olap.duckdb` off-site không (§7.4).
5. Vendor có muốn bán "managed backup" (giữ key-vendor, theo dõi tập trung) hay giao toàn quyền cho khách? Câu trả lời thay đổi cả DPA lẫn §6.1.
6. Có kế hoạch chuyển Metabase từ H2 sang Postgres không? Nếu có thì cold copy được thay bằng `pg_dump` online.
7. `dagster_home` là named volume: chạy `.backup` từ sidecar với mount `:ro` có ổn với WAL không, hay phải chạy trong `data_platform`? Cần test.
8. Ngưỡng 100.000 chủ thể dữ liệu: đã có khách nào vượt chưa (đếm khách hàng trong CRM/Sapo)?
