---
title: "Backup, khôi phục và tái dựng hệ thống"
description: "Đưa mọi thành phần có trạng thái ra ngoài máy (restic + rclone, mã hoá, khách giữ khoá), có restore.sh cho Linux, diễn tập khôi phục hằng tuần và dựng lại hằng tháng tự động, cảnh báo hai kênh, và một lần dựng lại từ con số 0 cho Fine Japan trong RTO."
status: in-progress
priority: P1
effort: 9d
branch: feat/backup-offsite-dr
tags: [operations, backup, disaster-recovery, security]
supersedes: [260624-2010-warehouse-pipeline-dr-verified-restore]
blockedBy: []
blocks: []
created: 2026-10-15
---

# Backup, khôi phục và tái dựng hệ thống

## Overview

Hôm nay mọi bản backup nằm cùng ổ với dữ liệu gốc, không mã hoá, không có secret, và chưa có lần khôi phục thử nào cho warehouse, Metabase H2 hay Dagster ([đánh giá](../reports/assessment-261015-1045-backup-restore-current-state.md)). Plan này thêm một chặng ngoài máy vào gate chain đã chứng minh với CRM, viết công cụ khôi phục cho Linux, tự động hoá việc chứng minh bản backup khôi phục được, và diễn tập dựng lại cả hệ thống trên máy khác cho Fine Japan.

Thiết kế và các quyết định (D1–D12): **[design.md](design.md)**. Plan này thay thế stub `plans/260624-2010-warehouse-pipeline-dr-verified-restore/` (design §13); coordinator đánh dấu stub là `cancelled`, superseded by plan này.

## Yêu cầu thiết kế và tài liệu hoá (bắt buộc)

**Làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó** (yêu cầu của user 13/10/2026, ghi ở đầu mọi phase). Bản sống là tài liệu mới `docs/operations/backup-and-recovery.md` (phase 0 tạo khung); mỗi phase cập nhật mục của mình **cùng commit** với code. ADR `docs/decisions/019-offsite-backup-and-recovery.md` viết ở phase 0 (quyết định) và chốt ở phase 8.

## Yêu cầu vận hành liên tục (bắt buộc)

1. Không làm việc trên checkout prod `/home/vantt/app/fg-dataware-house`. Làm trên worktree nhánh `feat/backup-offsite-dr`; thử trên dữ liệu shadow hoặc bản sao trong thư mục scratch, không bao giờ trên `app_data` của prod.
2. Prod chỉ đổi qua runbook "Refactor deploys (shadow-verified)" trong `docs/operations/deployment.md`, **sau khi user duyệt giờ**. Không làm việc nặng trong 02:30–04:00, trừ chính job off-site sau khi đã cài.
3. Không ghi vào Metabase prod. Mọi bước dừng Metabase (chép nguội) đi qua `scripts/backup/metabase_cold_backup.sh`.
4. Không đọc nội dung `.env*` hay secret khi phát triển; script chỉ chuyển file, không in giá trị.
5. Không đổi số liệu dashboard; không đổi schedule hiện có (chỉ thêm).

## Phases

| # | Phase | File | Effort | Phụ thuộc | Đụng prod | Cần giờ user duyệt |
|---|---|---|---|---|---|---|
| 0 | Chốt các ẩn số + khung tài liệu, ADR | [phase-00](phase-00-resolve-unknowns.md) | 0.5d | — | Chỉ đọc | Không (tránh 02:30–04:00) |
| 1 | Chụp nhất quán cục bộ: dagster_home, DuckDB export, manifest Metabase, file trạng thái, bỏ đường dẫn cứng | [phase-01](phase-01-consistent-local-capture.md) | 0.75d | 0 | Có (deploy D1) | **Có** |
| 2 | Sidecar `backup` + off-site (restic/rclone, nhiều backend, khoá, Recovery Sheet) | [phase-02](phase-02-offsite-backup-sidecar.md) | 1.5d | 1 | Không | Không |
| 3 | Công cụ khôi phục `restore.sh` (extract, verify, apply, full, drill mode) | [phase-03](phase-03-restore-tooling.md) | 1.25d | 2 | Không | Không |
| 4 | Xác minh tự động (T2 tuần, T3 tháng, tamper) + cảnh báo Lark/dead-man + check tuổi backup | [phase-04](phase-04-verification-and-alerting.md) | 1.5d | 3 | Không (deploy ở phase 5) | Không |
| 5 | Triển khai Fine Japan: SA + Shared Drive, nghi thức khoá, cài timer, backup đầu, T2 chứng kiến, 14 ngày quan sát | [phase-05](phase-05-fine-japan-rollout.md) | 0.75d + 14 ngày | 4 | Có (deploy D2) | **Có** |
| 6 | Ghim image + dựng lại từ con số 0 (bootstrap host, runbook) + diễn tập Fine Japan trên máy khác | [phase-06](phase-06-rebuild-from-zero.md) | 1.5d + 1 ngày diễn tập | 5 (cần repo thật) | Có (ghim image, deploy D3); diễn tập trên máy khác | **Có** |
| 7 | Đường Gmail OAuth (`drive.file`, app FG publish) + hướng dẫn cài cho khách | [phase-07](phase-07-gmail-oauth-path.md) | 0.75d | 2 | Không | Không |
| 8 | Sửa tài liệu lỗi thời, `restore.ps1`, ADR, đóng plan | [phase-08](phase-08-docs-cleanup-close.md) | 0.5d | 1–7 | Không | Không |

**Tổng ~9 ngày công**, cộng 14 ngày quan sát (phase 5) và một ngày diễn tập (phase 6). Phase 7 chạy song song với 3–6 được vì chỉ đụng file của riêng nó (bảng sở hữu file bên dưới).

**Điểm deploy:** D1 sau phase 1 (sửa `backup.sh`, `metabase_cold_backup.sh`, unit sinh từ template); D2 ở phase 5 (service `backup` trong compose với profile `ops`, timer mới, check `backup_freshness`); D3 ở phase 6 (ghim image trong compose/Dockerfile). Mỗi điểm deploy theo runbook, user chọn giờ.

## Phụ thuộc

```text
0 ẩn số ─► 1 chụp cục bộ ─(D1)─► 2 sidecar off-site ─┬─► 3 restore.sh ─► 4 xác minh + cảnh báo ─► 5 rollout FJ (D2, 14 ngày) ─► 6 dựng lại từ 0 (D3 + diễn tập) ─► 8 đóng
                                                     └─► 7 Gmail OAuth ─────────────────────────────────────────────────────────────────────┘
```

Phụ thuộc ngoài: phase 5 cần admin Workspace của Fine Japan tạo Shared Drive và service account; phase 6 cần một máy (hoặc VM) khác prod; phase 7 cần FG tạo GCP project và publish OAuth app. Không chặn bởi Đợt 2, nhưng xem design §13 về việc Đợt 2 đổi volume.

## Sở hữu file (không hai phase song song đụng cùng file)

| Phase | File chính |
|---|---|
| 1 | `scripts/backup/backup.sh`, `scripts/backup/metabase_cold_backup.sh`, `scripts/backup/duckdb_snapshot.py`, `scripts/backup/sqlite_snapshot.py`, `scripts/backup/systemd/*.in`, `scripts/backup/install-units.sh`, `orchestration/packs/crm/jobs.py` (`execution_timezone`) |
| 2 | `Dockerfile.backup`, `docker-compose.yml` (service `backup`, volume `backup_staging`, `restic_cache`), `scripts/backup/offsite.sh`, `scripts/backup/sidecar/*`, `scripts/backup/offsite-include.txt`, `scripts/backup/backends/{local,s3,sftp,gdrive-sa}.md`, `scripts/checks/check_backup_scope.py`, `scripts/checks/run-all.sh` (thêm bước) |
| 3 | `scripts/backup/restore.sh`, `scripts/backup/sidecar/restore_*.py`, `crm/ops/restore_verify_crm.py` (thêm `--backups-dir`) |
| 4 | `scripts/backup/restore-drill.sh`, `scripts/backup/sidecar/drill_gates.py`, `orchestration/asset_checks/backup_freshness_checks.py`, `orchestration/definitions.py` (đăng ký asset spec + check), `scripts/backup/systemd/fg-restore-drill-*.in`; ping healthchecks thêm vào `scripts/backup/backup.sh`, `scripts/backup/metabase_cold_backup.sh` (sau phase 1, tuần tự) và `orchestration/packs/crm/crm_sync.py` |
| 5 | Không có code mới; chỉ `docs/operations/backup-and-recovery.md` §Triển khai và nhật ký |
| 6 | `docker-compose.yml` (dòng `image:` của `fileserver`), `Dockerfile.metabase` và các `Dockerfile.*` (dòng `FROM`), `caddy-global/Dockerfile.caddy` (dòng `FROM`), file constraints dependency Python, `scripts/host/bootstrap-host.sh`, `scripts/backup/restore.sh` (nhánh `full --mode real`, build image từ git) |
| 7 | `scripts/backup/backends/gdrive-oauth.md`, `scripts/backup/sidecar/backend_gdrive_oauth.sh` |
| 8 | `docs/operations/operations.md`, `scripts/backup/README.md`, `scripts/backup/*.ps1`, `docs/operations/backup-restore-completeness-runbook.md`, `crm/docs/backup-restore-runbook.md`, ADR 019 |

`docker-compose.yml` bị phase 2 và phase 6 đụng; `restore.sh` bị phase 3 và 6 đụng; `install-units.sh` bị phase 1, 2, 4 đụng; `backup.sh`, `metabase_cold_backup.sh` bị phase 1 và 4 đụng. Các cặp này đều tuần tự trên cùng nhánh nên không xung đột. Phase 7 là phase duy nhất chạy song song và chỉ đụng file của riêng nó.

## Acceptance Criteria

1. **Off-site xanh 14 ngày liên tiếp** cho Fine Japan: 14 file `status/offsite.json` liên tiếp `ok=true`, healthchecks không có lần "down", mỗi ngày có một snapshot mới trong `restic snapshots --tag tenant=fine_japan`.
2. **T1:** 14/14 lần `check --read-data-subset` PASS trong khoảng quan sát; sau 28 ngày, mọi phần 1..28 đã đọc ít nhất một lần (ghi trong `status/check.json`).
3. **T2:** hai lần diễn tập tuần liên tiếp PASS từ bản ngoài máy (gate a–f), trong đó một lần mở repo bằng `key-customer` có khách chứng kiến (biên bản bàn giao). Bốn kiểu tamper (xoá partition parquet, sửa một ô CRM, cắt cụt H2, sửa một dòng manifest) đều làm T2 FAIL.
4. **T3:** một lần dựng lại hằng tháng PASS: lake rỗng + dữ liệu giải nén từ off-site build xanh, số dòng các bảng trong `scripts/checks/public_models.yaml` nằm trong ngưỡng so với prod cho dữ liệu tới ngày snapshot; tamper xoá một partition làm T3 FAIL.
5. **Dựng lại từ con số 0:** một lần diễn tập cho Fine Japan trên máy khác prod, từ Recovery Sheet tới khi dashboard Metabase mở được với 43/888/23 (collection/card/dashboard, hoặc số trong manifest hiện hành), CRM health xanh, một nightly ở chế độ drill xanh, **trong ≤ 8 giờ làm việc**, có nhật ký thời gian từng bước; prod không bị đụng (dấu vân tay và tunnel không có connector lạ).
6. **Cảnh báo:** gây lỗi có chủ đích (sai mật khẩu repo trên worktree, tắt timer trên máy thử) tạo tin Lark trong 15 phút và healthchecks báo down sau grace; check `backup_freshness` đỏ khi một file trạng thái quá hạn và xanh lại khi có bản mới.
7. **Secret:** không có file `.env*` hay key service account dạng rõ trong `app_data/backups/` và thư mục scratch sau mọi lần chạy (lệnh `find` theo danh sách tên ở phase 2 trả 0 dòng); secret khôi phục được từ repo và khớp sha256 trong manifest.
8. **Đổi backend không sửa code:** cùng script chạy chu trình backup → restore → verify PASS với thư mục local, MinIO S3 và SFTP.
9. **Không đường dẫn cứng:** `grep -rn "/home/vantt" scripts/backup scripts/host` trả 0 dòng (ngoại trừ ví dụ trong tài liệu nếu có, ghi rõ).
10. **Tài liệu:** `docs/operations/backup-and-recovery.md` đủ các mục; bảng backup lỗi thời ở `docs/operations/operations.md:296-376` được thay bằng liên kết; `restore.ps1` xử lý theo quyết định của user; ADR 019 chốt; roadmap (coordinator) đóng hai dòng liên quan.

## Risks chính

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| ~~Phase 0 phát hiện nhiều dữ liệu tích luỹ không dựng lại được~~ **Đã đóng ở phase 0:** chỉ một bảng (`monitor_taxonomy_parity_log`); snapshot giá/tồn không có lịch sử (plan riêng) | — | `duckdb_snapshot.py --tables` (phase 1); không cần đưa `sapo_warehouse.duckdb` lên off-site |
| Diễn tập dựng lại gây tác dụng ra ngoài (tunnel nhận traffic thật, HUG, email Metabase) | Trung bình × Cao | `--mode drill` (design §8.2), danh sách đầy đủ từ phase 0, kiểm env trước khi start; T2/T3 `--network none` |
| T2/T3 làm cạn RAM host (swap đã đầy) và ảnh hưởng dashboard | Trung bình × Trung bình | Giới hạn RAM container, preflight `MemAvailable`, chạy sáng Chủ nhật, bỏ qua có cảnh báo |
| Google đổi chính sách (quota SA, OAuth) | Trung bình × Trung bình | Backend chỉ là cấu hình; đã chứng minh S3/SFTP ở phase 2; FJ dùng SA + Shared Drive |
| Mất khoá | Thấp × Rất cao | 3 khoá, 2 người phía khách; T2 hằng quý mở bằng khoá khách; biên bản |
| Đợt 2 đổi volume làm sidecar đọc thư mục rỗng mà vẫn "xanh" | Trung bình × Cao | Preflight đường dẫn không rỗng; ghi chú vào plan 260705 (coordinator) |
| Đọc raw parquet đúng lúc dlt đang ghi (dlt ghi thẳng tên cuối, không có file tạm để loại) | Thấp × Thấp | Off-site 03:30: giờ 3 không có writer parquet thường, chỉ realtime ghi Delta; T2 đọc mọi file và mở mọi bảng Delta; state dlt ghi sau dữ liệu nên khôi phục chỉ có thể ghi trùng (staging khử trùng) |
| Build lại image trên máy mới ra phiên bản dependency khác (không lưu image, D12 đã bỏ; dlt đang chạy 1.29.1, không ghim) | Trung bình × Cao | Phase 6 ghim base image theo digest và ghim phiên bản dependency đang chạy (lấy từ `pip freeze` trong image hiện tại); diễn tập phase 6 build lại thật trên máy khác; phần còn lại là Đợt 2 |
| Upload lần đầu lâu hoặc chạm giới hạn Drive | Thấp × Thấp | ~2–3 GB, dưới 750 GB/ngày; `--drive-stop-on-upload-limit`; chạy lần đầu trong giờ user duyệt |

## Rollback

Mỗi phase có mục Rollback riêng. Tổng quát: phase 1 revert bằng `git revert` theo runbook (backup.sh quay về chép như cũ); phase 2–5 tắt bằng `systemctl --user disable --now fg-offsite-backup.timer fg-restore-drill-*.timer` và gỡ service `backup` (profile `ops`, không chạy thường trực nên gỡ không ảnh hưởng stack); check `backup_freshness` revert như mọi asset check. Repo off-site không bị xoá khi rollback (là dữ liệu của khách). Phase 6 revert dòng ghim image; image cũ vẫn trong cache Docker.

## Ngoài phạm vi

Chuyển Metabase sang Postgres; đích phụ Object Lock; giám sát tập trung nhiều khách (Đợt 8); CLI `init/doctor/upgrade` (Đợt 5); ý kiến luật sư (user hoãn); backup lịch sử run Dagster; backup `caddy_data`.

## Nguồn

[design.md](design.md); [đánh giá](../reports/assessment-261015-1045-backup-restore-current-state.md); [nghiên cứu](../reports/research-261015-1040-offsite-backup-restore-dr.md); [roadmap](../261013-1751-modularize-data-platform-suite/roadmap.md) mục "Backup, khôi phục và tái dựng hệ thống"; `docs/operations/backup-restore-completeness-runbook.md`; `crm/docs/backup-restore-runbook.md`; `docs/operations/deployment.md` mục "Refactor deploys" và "Metabase: backup and restore".

## Đã chốt (user, 15/10/2026 ~17:00)

- **Máy diễn tập dựng lại (phase 6):** `vantt@fg-server2`. Trước diễn tập phải kiểm (chỉ đọc) máy đủ yêu cầu (Ubuntu LTS, ≥ 16 GB RAM, ≥ 60 GB trống) và **không** nằm trong DNS/tunnel của prod (chạy `--mode drill`, không `cloudflared`). Ngày diễn tập: chọn khi tới phase 6.
- **Script Windows cũ** (`backup.ps1`, `restore.ps1`, `setup-task-scheduler.ps1`): chuyển vào `scripts/backup/legacy-windows/` (không xoá).
- **Chép nguội Metabase H2: mỗi đêm 00:30** (gián đoạn ~18 giây, RPO 24 giờ) cho giai đoạn này, vì phần lớn trong 888 câu hỏi đã lưu chỉ tồn tại trong H2. Khi report chuẩn thành code (plan report), cân nhắc quay về hằng tuần.
- **KHÔNG lưu image Docker** (user đổi ý 15/10 ~17:15 sau ước tính mới 5–7 GB nén): khi khôi phục build lại image từ git; D12 bỏ. Giảm rủi ro build lỗi bằng ghim phiên bản/digest (phase 6) và Đợt 2.

**Quyết định sau phase 0 (user, 15/10 ~17:15):**
- `crm_backup_job`: thêm `execution_timezone`, chạy **02:00 giờ VN** (đang chạy 09:00 do lịch tính theo UTC).
- Lịch sử giá/tồn kho theo ngày: **cần** → plan riêng (sửa model để tích luỹ, đưa vào off-site) — ghi trong roadmap.
- `data_lake/backup` (ảnh chụp tay Sapo 13/04, 21 MB): **giữ, đưa vào backup**.
- `.env.local` (dev cũ, có thông tin đăng nhập Sapo): **giữ nguyên**, không đưa vào backup.
- Credentials Cloudflare tunnel: **đưa vào kho backup mã hoá**; không dùng khi diễn tập (chế độ drill không chạy `cloudflared`).
- File key Google (0644) và credentials tunnel (0444): **đổi 0600** qua runbook, kiểm container vẫn đọc được trước khi áp.
- `monitor_taxonomy_parity_log` (bảng duy nhất không dựng lại được) đưa vào off-site; `monitoring_db` chép bằng SQLite backup API; `app_data/analysis` (sổ MISA nhập tay) đưa vào backup.
- Phần còn lại của phase 0 (cập nhật design/plan, ADR 019): làm tiếp.
- **Cảnh báo "không nhận được tín hiệu":** healthchecks.io gói miễn phí, tài khoản Gmail cá nhân của user (user tự đăng ký). Mỗi check có một ping URL riêng: user tạo check và điền URL vào `.env` (coi như secret, không dán vào chat/commit). Kênh báo: email + webhook vào nhóm Lark nhận cảnh báo. Check dự kiến: backup đêm, đẩy off-site, chép nguội Metabase, backup CRM, kiểm tra khôi phục hằng tuần.

## Ghi nhận từ phase 0

Bằng chứng: [reports/phase-00-findings.md](reports/phase-00-findings.md). Thay đổi so với bản đầu (design đã sửa theo):

- **Monitoring là SQLite** (`ingestion_health.db`, WAL), không phải DuckDB: chụp bằng `sqlite_snapshot.py` (SQLite backup API), bỏ ý định `EXPORT DATABASE`. Bản đêm hiện đã có nó nhưng là `cp -a` nóng.
- **Chỉ một bảng không dựng lại được:** `main.monitor_taxonomy_parity_log` trong `sapo_warehouse.duckdb`; `duckdb_snapshot.py` chỉ cần `COPY` bảng đó. Snapshot giá/tồn không có lịch sử (GC rolling giữ 3 lần build): plan riêng.
- **`dagster_home`:** chỉ chụp `schedules/schedules.db` (321 MB); bỏ `storage/` và `history/` (10,1 GB, gồm event log `index.db` 5,1 GB).
- **CRM backup thực chạy 09:00** (thiếu `execution_timezone`); phase 1 sửa về 02:00 (thêm `orchestration/packs/crm/jobs.py` vào sở hữu file của phase 1, deploy cùng D1).
- **dlt không ghi qua file tạm** và ghi state sau dữ liệu: bỏ `--exclude-file` cho file tạm; T2 thêm kiểm bảng Delta. Không có cơ chế lùi cursor theo giờ: design §8.3 chọn "chạy tiếp từ cursor trong snapshot", cờ `--rewind-hours` chỉ làm nếu diễn tập cho thấy cần.
- **Đường ra ngoài thêm** cho `--mode drill`: ack webhook Sapo/HUG (xoá hàng đợi Worker), budget sync ghi Google Sheet, `caddy-global` ghi DNS qua Cloudflare API.
- **Thành phần mới vào off-site:** `app_data/analysis`, `data_lake/backup`, credentials Cloudflare tunnel (`${FG_CLOUDFLARED_DIR}`, ngoài repo). `.env.local` không đưa.
- **Lịch:** nightly kết thúc p95 ~03:14 (77 đêm, số liệu thay thế vì lịch sử run Dagster chỉ còn ~1,4 ngày): giữ off-site 03:30.
- **Phát hiện phụ:** `Dockerfile.dataplatform:33-37` ghi dlt 1.25.0 trong khi image chạy 1.29.1 (phase 6 ghim); file secret 0644/0444 (runbook đổi quyền, theo quyết định user, đi cùng deploy D1 ở phase 1; xem câu hỏi mở 6 về cloudflared); healthchecks.io đứng tên user, trong khi D11 ghi "tài khoản thuộc khách" (câu hỏi mở 2).

## Câu hỏi mở cho user

Đã trả lời (xem "Đã chốt" ở trên): máy diễn tập (`fg-server2`), Metabase hằng đêm, không lưu image, script Windows chuyển `legacy-windows/`, dữ liệu tích luỹ (chỉ parity log; giá/tồn là plan riêng), giờ CRM, `data_lake/backup`, `.env.local`, credentials tunnel, quyền 0600. Còn mở:

1. **Phía Fine Japan:** ai là admin Workspace tạo Shared Drive "FG Backup – fine_japan" và service account (đề xuất: tạo SA mới riêng cho backup trong GCP project FJ đang dùng cho Google Sheet, không dùng lại SA của Sheet)? Ai giữ `key-customer` và `key-customer-2`, và ai ký biên bản? (Cần trước phase 5.)
2. **Tài khoản healthchecks.io:** hiện là tài khoản của anh (Gmail cá nhân). D5 và D11 ghi tài khoản thuộc **khách** (FG không vận hành backup thay khách). Giữ tài khoản này cho giai đoạn đầu rồi chuyển sang Fine Japan khi bàn giao, hay sửa D11? FG có ở trong nhóm Lark nhận cảnh báo không?
3. **Chu kỳ dựng lại từ con số 0 sau lần đầu:** đề xuất mỗi năm một lần cho mỗi khách, và mỗi lần cài khách mới (cài mới dùng chính đường này).
4. **Giữ bản năm:** thêm `--keep-yearly 3` cho dữ liệu tài chính không? Chi phí dung lượng nhỏ.
5. **Thời điểm off-site:** phase 0 đo nightly kết thúc p95 ~03:14, nên đề xuất chốt 03:30. Đồng ý?
6. **Quyền credentials tunnel:** container `cloudflared` chạy với uid `65532` (`docker inspect`), còn file thuộc `vantt` (uid 1000). `chmod 0600` giữ chủ `vantt` sẽ làm `cloudflared` **không đọc được ở lần khởi động lại sau** (tunnel đang chạy vẫn sống nên lỗi không lộ ngay). Chọn: (a) `chown 65532:65532` + `0400` (đề xuất; `vantt` đọc lại bằng `sudo` khi backup, hoặc sidecar chạy root đọc được); hay (b) thêm `user: "1000:1000"` vào `/home/vantt/cloudflared-tunnel/docker-compose.yml` rồi `0600`. Key Google dùng trong `data_platform` (chạy root) nên `0600` an toàn.

## Đã chốt sau phase 0 (user, 15/10/2026 ~17:30)

- Credentials Cloudflare tunnel: **chủ uid 65532, quyền 0400** (để `cloudflared` vẫn đọc được khi khởi động lại); key Google: 0600 (data_platform chạy root).
- Healthchecks.io Gmail cá nhân của user là **tài khoản của user**: dùng tạm cho FJ, **bàn giao** sang tài khoản FJ khi có email FJ (chuyển project). D5/D11 giữ nguyên nguyên tắc "tài khoản thuộc khách".
- Diễn tập dựng lại từ con số 0: **mỗi năm một lần + mỗi lần cài khách mới**.
- Giữ bản: 7 ngày / 4 tuần / 12 tháng **+ 3 bản năm**; đẩy off-site lúc **03:30**.
- Còn mở: phía FJ ai tạo Shared Drive + service account, ai giữ 2 khoá (trước phase 5).
- **User trả lời 15/10/2026 ~23:00:** user là admin Workspace của FJ (tạo Shared Drive + service account). Người giữ khoá (16/10/2026): **user giữ một mình**, trước mắt cả `key-customer` và `key-customer-2` (hai bản in, cất hai nơi); thêm người thứ hai sau bằng `key add`. User xác nhận 16/10/2026: **giữ tạm**, sau đó **giao cho người của FJ** (thêm khoá mới cho người FJ bằng `key add`, rồi `key remove` khoá của user sau khi người FJ mở thử được). Nguyên tắc "khách giữ khoá" (D5/D11) giữ nguyên; người nhận phía FJ và thời điểm bàn giao: chưa có.

## Ghi chú hoàn tác quyền credentials Cloudflare tunnel (user, 15/10/2026 ~18:05)

Trạng thái trước khi đổi (thư mục `/home/vantt/cloudflared-tunnel/config`):

| File | Chủ | Quyền |
|---|---|---|
| `<tunnel-id>.json` | `vantt:vantt` | `444` |
| `cert.pem` | `vantt:vantt` | `644` |
| `config.yml` | `vantt:vantt` | `644` |

Hoàn tác:

```bash
TUN=/home/vantt/cloudflared-tunnel/config
sudo chown vantt:vantt "$TUN"/*.json "$TUN"/cert.pem "$TUN"/config.yml
sudo chmod 0444 "$TUN"/*.json
sudo chmod 0644 "$TUN"/cert.pem "$TUN"/config.yml
docker restart cloudflared
```

- **Đã áp 15/10/2026 ~18:05** (user chạy bằng sudo): 3 file thành chủ `65532:65532` (host hiện `UNKNOWN` vì uid không có trong /etc/passwd), quyền `400`; `cloudflared` khởi động lại, `bi.fwg.vn/api/health` và `crm.fwg.vn` trả 302 (Cloudflare Access) → tunnel chạy bình thường.
