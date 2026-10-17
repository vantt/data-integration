# Phase 04 — báo cáo worker

**Trạng thái:** code + test xong trên worktree `/home/vantt/app/fg-dw-report` (nhánh `feat/report-productization`, gốc HEAD `34019ca2`), chưa commit, chưa deploy. Không đụng container prod, không ghi Metabase, không gửi tin Lark thật.

## Thiết kế đã làm (theo quyết định 14/10 và tin nhắn coordinator)

- **Builder** (`evidence`, giữ `mem_limit: 4g`): `evidence/scripts/build-areas.sh` thay CMD cũ; không phục vụ HTTP, bỏ nhãn Caddy và mạng `caddy_net`. Build tuần tự từng khu vực (`evidence/areas/*` + `legacy` = `evidence/pages` cũ, không basePath) trong project tạm, timeout 1200 s/khu vực, vá theme dark, chuyển vào `app_data/report_site/<area>/builds/<id>/`, đổi symlink `current` nguyên tử, giữ 3 bản, ghi `app_data/data_lake/report_build/status.json`. Khởi động: chỉ build khu vực chưa có `current`; restart **không** build lại. Mỗi `request_id` build một lần; `flock` chống chạy chồng; healthcheck bằng heartbeat (Dockerfile không đổi).
- **Đăng nhập** (`report_site`, `caddy:alpine`, `caddy_net`, nhãn `caddy: evidence.lan.fwg.vn`, **không cổng host**): `evidence/site/Caddyfile` sinh từ `access.areas` (`python3 -m analytics render site`); mỗi khu vực một đường dẫn `/<area>/` với `basic_auth` riêng `import /etc/caddy/users/<area>.caddy`; `legacy` ở đường dẫn gốc. **Mỗi người một tài khoản** (một dòng `<user> <bcrypt>` trong file khu vực, ngoài git: `app_data/secrets/report_site/`). Log JSON ghi `user_id` mỗi request. Fail-closed: thiếu file → Caddy không khởi động (caddy-global trả 502); file rỗng → 401 cho mọi người (đã kiểm). Biến `EVIDENCE_BASIC_AUTH_USER/HASH` (một tài khoản chung) không còn dùng; bỏ khỏi compose và `.env.compose.example`.
- **Quản lý tài khoản:** `evidence/site/report-users.sh add|remove|list|reload`. Mật khẩu đọc bằng `read -s` hai lần (≥ 12 ký tự), băm bằng `caddy hash-password` qua stdin (`docker run --rm -i --network none caddy:alpine`), chỉ lưu hash, file 600, thư mục 700; không in mật khẩu hay hash.
- **Dagster** `orchestration/reports/` (module kernel, đăng ký trong `definitions.py`): `report_site_build_after_nightly_sensor` (nightly SUCCESS → `report_site_build_job` ghi `request.json`; job này cũng là "build ngay" bằng tay); `report_site_build_status_sensor` (5 phút: khu vực lỗi → thẻ Lark kênh cảnh báo; quá 2 giờ chưa có kết quả → cảnh báo; build ok + dữ liệu đến hết hôm qua + tin đến hạn → `report_summary_message_job`). Cả hai sensor `default_status RUNNING`.
- **Tin tóm tắt:** `analytics/renderers/message.py` dựng thẻ từ `kpi_tiles` (as_of của bản build), link `access.site_url/<area>/<report>/`. Kênh và lịch trong hồ sơ: `message.channels[] {id, title?, env_webhook, env_secret, can_view_cost}`, `message.reports[] {report, channels, weekdays, not_before}`. FJ: kênh `lanh_dao` (`LARK_REPORT_LEADERSHIP_WEBHOOK` / `LARK_REPORT_LEADERSHIP_SECRET`, `can_view_cost: true`, **không có tên nhóm**), Weekly Pulse thứ Hai từ 07:00. **Mặc định dry-run** (`REPORT_MESSAGE_DRY_RUN` khác `0` thì chỉ ghi log); kênh thiếu biến webhook bị bỏ qua, **không bao giờ rơi về webhook cảnh báo**; lỗi dựng/gửi chỉ ghi log.
- `data_platform` mount thêm `./analytics` và `./tenants` (`:ro`); `scripts/shadow/run-shadow.sh` mount tương ứng để `run-all.sh` phản ánh compose (sửa nhỏ ở script dùng chung; không dùng thư mục shadow).

## File (worktree)

Mới: `evidence/scripts/build-areas.sh`, `evidence/site/Caddyfile` (sinh ra), `evidence/site/report-users.sh`, `evidence/tests/{test_build_areas,test_report_users}.py`, `analytics/renderers/{site,message}.py`, `analytics/tests/test_site_and_message.py`, `orchestration/reports/{__init__,build_request,build_status,summary_message}.py`, `orchestration/reports/README.md`, `orchestration/reports/__tests__/test_report_site.py`.

Sửa: `docker-compose.yml` (`evidence`, `report_site` mới, `data_platform` volume), `.env.compose.example`, `orchestration/definitions.py`, `analytics/__main__.py` (`render site`), `analytics/compiler/spec_validate.py` (kpi_tile phải là card một giá trị; kiểm `message`), `analytics/schema/tenant-profile.schema.json` (`access.site_url`, `message`), `tenants/fine_japan/analytics/profile.yml`, `scripts/checks/run-all.sh` + `README.md` (bước 6 chạy thêm `evidence/tests`), `scripts/shadow/run-shadow.sh`, `evidence/areas/dieu-hanh/**` (chỉ đổi hash đầu vào trong banner vì hồ sơ đổi). Tài liệu: `evidence/README.md`, `docs/operations/deployment.md` (mục "Report site (Evidence)"), `docs/architecture/modules.md` (§11, §12, §13), `orchestration/README.md`, `analytics/README.md`, `CLAUDE.md`, `.claude/commands/deploy-evidence-page.md`, `.skills/evidence-automation/SKILL.md`, `docs/analytics-handbook/blueprints/evidence/{README,finance_cashflow}.md`. `AGENTS.md` không có dòng deploy Evidence nên không sửa. `Dockerfile.evidence` không sửa.

## Kiểm chứng

- `scripts/checks/run-all.sh` (SHADOW_ROOT trong scratchpad): `RUN-ALL: PASS` (pytest 416, analytics + evidence 137).
- `dagster_inventory.py diff` (HEAD vs worktree): 0 khác biệt; chỉ thêm `report_site_build_job`, `report_summary_message_job`, `report_site_build_after_nightly_sensor`, `report_site_build_status_sensor`.
- `docker compose config` (biến giả, bản sao trong scratchpad): `evidence` không cổng/nhãn, `report_site` không cổng, `data_platform` có `/app/analytics`, `/app/tenants`.
- **Thử trong container cô lập** (17:00 ICT; `evidence-spike` builder, 4g, bridge, data_lake `:ro`; `evidence-spike-site` Caddy trên 127.0.0.1:3106; không `caddy_net`; tài khoản thử với mật khẩu dùng một lần, đã xoá):
  - Lần đầu build cả hai khu vực (dieu-hanh 56 s, legacy 55 s), `status.json` ok; restart → log "current exists for every area … waiting", không build; ghi `request.json` mới → build lại đúng một lần, `current` đổi sang bản mới.
  - Caddy: `/dieu-hanh/ceo_weekly_pulse` và một file trích parquet: 401 không đăng nhập, 401 với tài khoản `legacy`, 401 sai mật khẩu, 200 với tài khoản `dieu-hanh`; `/`, `/ceo-weekly-pulse`, `/finance-cashflow`: 200 chỉ với tài khoản `legacy`; xoá tài khoản cuối + reload → 401 với mọi người; thêm lại → 200; access log ghi `user_id`.
  - Chromium headless có đăng nhập: trang Weekly Pulse (3 tab) và trang legacy `/ceo-weekly-pulse` không lỗi console, không HTTP lỗi.
  - Tin tóm tắt dry-run trên bản chụp chỉ đọc (as_of 14/10): thẻ đủ 6 ô gồm Lãi ròng kênh, Biên lãi gộp, link `https://evidence.lan.fwg.vn/dieu-hanh/ceo_weekly_pulse/`; không gửi.
  - Dọn: hai container đã xoá, cổng 3106 trống, thư mục build/tài khoản thử đã xoá.
- Không kiểm trên bản build thật khu vực không quyền chi phí (`ban-hang`); test renderer bảo đảm SQL và trang của khu vực đó không chứa id metric chi phí, và file trích chỉ sinh từ SQL đó.

## Lệnh user phải tự chạy (mật khẩu, trên server, từ gốc checkout prod sau khi code đã vào)

Chạy trong terminal (lệnh hỏi mật khẩu hai lần, không hiện chữ; nếu `!` trong Claude Code không cho nhập ẩn thì dùng terminal thường). Mỗi người một tài khoản; người xem cả hai khu vực thì chạy cho cả hai:

```bash
! evidence/site/report-users.sh add dieu-hanh <tên-đăng-nhập>
! evidence/site/report-users.sh add legacy <tên-đăng-nhập>
! evidence/site/report-users.sh list
! evidence/site/report-users.sh reload        # chỉ sau khi report_site đã chạy
! evidence/site/report-users.sh remove dieu-hanh <tên-đăng-nhập>   # thu hồi
```

Webhook nhóm Lark (khi đã biết nhóm), thêm vào `.env.docker` không hiện giá trị:

```bash
! read -rs -p 'Lark webhook: ' W; echo; read -rs -p 'Lark secret: ' S; echo; sed -i '/^LARK_REPORT_LEADERSHIP_/d' .env.docker; printf 'LARK_REPORT_LEADERSHIP_WEBHOOK=%s\nLARK_REPORT_LEADERSHIP_SECRET=%s\n' "$W" "$S" >> .env.docker; unset W S
```

Chỉ khi muốn gửi thật: thêm `REPORT_MESSAGE_DRY_RUN=0` vào `.env.docker` rồi recreate `data_platform`.

## Các bước deploy cho coordinator (giờ user duyệt, ngoài 02:30–04:00 và sáng thứ Hai)

1. Trên nhánh: `run-all.sh` PASS; `python3 -m analytics render evidence --check` và `render site --check` exit 0.
2. Trên server: `mkdir -p app_data/report_site app_data/data_lake/report_build app_data/secrets/report_site && chmod 2775 app_data/report_site app_data/data_lake/report_build && chmod 700 app_data/secrets/report_site` (builder chạy uid 1001 gid 1000; user vantt gid 1000).
3. User tạo tài khoản cho **cả** `dieu-hanh` và `legacy` (lệnh trên). Thiếu file thì `report_site` không chạy (đúng thiết kế, nhưng trang sẽ 502).
4. Deploy code `data_platform` theo runbook "Refactor deploys" (stop → ff → start → instigator diff: chỉ thêm 2 job, 2 sensor; hai sensor mặc định RUNNING).
5. `docker compose up -d evidence report_site` (recreate, không build image). Lần đầu builder build mọi khu vực (~2 phút). Lưu ý: image `evidence` hiện tại vẫn dùng được (builder không cần gói `serve`).
6. Kiểm theo `docs/operations/deployment.md` "Report site (Evidence)" bước 6; sau nightly kế tiếp: `status.json` có `request_id` của run nightly, ok.
7. Báo trước cho người đang dùng trang Evidence: đường dẫn cũ giữ nguyên nhưng đăng nhập bằng tài khoản riêng mới.

Rollback: `deployment.md` mục "Rollback" (dừng `report_site`, revert, compose cũ cần lại `EVIDENCE_BASIC_AUTH_*` trong `.env`).

## Câu hỏi mở

1. **Tên nhóm Lark ban lãnh đạo** nhận Weekly Pulse (hay tạo nhóm mới)? Khi có: điền `title` của kênh `lanh_dao` trong hồ sơ, đặt webhook/secret, rồi tắt dry-run.
2. **Danh sách người và khu vực:** ai được tài khoản `dieu-hanh`, ai `legacy` (trang legacy chứa dữ liệu cả bảng, gồm tên khách và tài chính: đề xuất chỉ điều hành/tài chính).
3. Truy cập qua Tailscale: `evidence.lan.fwg.vn` phải phân giải được trên máy Tailscale (DNS nội bộ / subnet route) — ngoài phạm vi code, cần kiểm khi deploy.
4. Hai card Forecast / Run-rate (từ phase 02) vẫn `draft`.

## Lo ngại

- `scripts/shadow/run-shadow.sh` là script dùng chung với worker shadow: chỉ thêm mount `:ro` cho `analytics/`, `tenants/` (bắt buộc để `dagster definitions validate` và pytest nạp được `orchestration/reports`). Coordinator nên báo worker kia.
- Hash đầu vào trong banner của `evidence/areas/dieu-hanh/**` đổi mỗi khi hồ sơ khách đổi (kể cả mục `message`), nên diff có 25 file chỉ đổi một dòng.
- Hai sensor bật mặc định: sau deploy, sensor build chạy sau mỗi nightly; tin chỉ ghi log cho tới khi tắt dry-run.

## Sáng 16/10 (kiểm 09:23, chỉ đọc): đạt

- Sau nightly `3af400cf` (SUCCESS 03:01), builder nhận request `6621ccb1` lúc 03:06:47 và build xong
  03:08:52, `as_of` 15/10: `dieu-hanh` ok (60 giây), `legacy` ok (65 giây).
- Link `current` của cả hai khu đã đổi sang bản build `20261016T030647`.
- `https://evidence.lan.fwg.vn/` trả 401 khi không đăng nhập.
- Tin Weekly Pulse thật đầu tiên: thứ Hai 19/10 07:00 (tin thử đã gửi 15/10 ~18:15, nhóm Lark alert).
