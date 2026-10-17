---
phase: 4
title: "Build Evidence theo lịch sau nightly, lớp đăng nhập theo khu vực, tin tóm tắt kèm link (kênh thử)"
status: pending
priority: P1
effort: "3d"
dependencies: [3]
---

# Phase 04: Build theo lịch, đăng nhập, tin tóm tắt

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: vẽ luồng build/phục vụ/đăng nhập vào `docs/architecture/modules.md` (mục Analytics) và mục §11 Serving (Evidence không còn tự build khi khởi động). Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/deployment.md` (mục mới "Report site (Evidence)": build theo yêu cầu, xem trạng thái, build tay, thêm/thu hồi tài khoản, rollback bản build); `evidence/README.md`; `orchestration/reports/README.md` (mới); `orchestration/README.md`; `docs/architecture/modules.md` (§11 Serving, §12 Ranh giới container, mục Analytics); `CLAUDE.md` và `AGENTS.md` dòng "Deploy: `docker compose restart evidence`" đổi thành quy trình mới; `.claude/commands/deploy-evidence-page.md`.

## Mục tiêu

1. Evidence build **một lần sau nightly** do Dagster yêu cầu, không build lại khi restart container (thiết kế §4 ⑤ điều kiện 3).
2. Trang tĩnh nằm sau **lớp đăng nhập ở reverse proxy, phân quyền theo đường dẫn khu vực**; report có cờ chi phí chỉ build vào khu vực có quyền; dữ liệu trích giới hạn đúng mức card cần (điều kiện 4).
3. **Tin tóm tắt kèm link** dựng từ `kpi_tiles`, gửi qua notifier Lark sẵn có (điều kiện 5, quyết định 6), trong phase này chỉ gửi vào kênh thử.

## Thiết kế

### Luồng

```
03:00 pipeline_batch_nightly_job (orchestration/definitions.py:97-101, lịch 161-169)
  └─ thành công → run_status_sensor (orchestration/reports) ghi app_data/data_lake/report_build/request.json {request_id, requested_at, areas}
evidence (builder, không phục vụ HTTP)
  └─ thấy request mới → với từng khu vực: dựng project tạm, cp olap.duckdb, npm run sources && npm run build
     → ghi vào app_data/report_site/<area>/builds/<request_id>/ → đổi symlink current nguyên tử → giữ 3 bản
     → ghi app_data/data_lake/report_build/status.json {request_id, area, ok, as_of, duration_s, error}
report_site (caddy:alpine, cùng mẫu với data_fileserver)
  └─ evidence.lan.fwg.vn: /<area>/* → basic_auth theo khu vực → file_server root /srv/<area>/current
orchestration/reports sensor đọc status.json
  ├─ lỗi → thẻ Lark cảnh báo (kênh cảnh báo hiện có), trang giữ bản trước
  └─ thành công + report có lịch tin → job report_summary_message
```

### Builder (container `evidence`)

- `evidence/scripts/build-areas.sh`: vòng lặp đọc `request.json` mỗi 60 s; xử lý một request một lần; khoá file để không chạy chồng; timeout mỗi khu vực theo đo ở phase 03 (S4). Khi khởi động: chỉ build nếu khu vực chưa có `current` (container mới), **không build lại khi restart**.
- `docker-compose.yml` dịch vụ `evidence`: thêm `command: ["sh", "/app/scripts/build-areas.sh"]`; **bỏ** `ports: 3006:3000` và nhãn `caddy` (dời sang `report_site`); thêm volume `./evidence/areas:/app/areas:ro`, `./app_data/report_site:/app/site` (ghi), `./app_data/data_lake/report_build:/app/var/report_build` (ghi, mount lồng dưới `data_lake` chỉ đọc; kiểm hành vi mount lồng trong container thử trước). Giữ nguyên image: **không build lại image**, chỉ recreate container.
- Bước vá theme `sed "s/?? 'system'/?? 'dark'/g"` trong CMD cũ (`Dockerfile.evidence:42`) chuyển vào builder, áp cho từng bản build.

### Lớp đăng nhập (`report_site`)

- Dịch vụ mới `report_site` (`caddy:alpine`), theo đúng mẫu `data_fileserver` (`caddy/Caddyfile:1-9`, basic_auth với hash bcrypt từ ngoài git): volume `./app_data/report_site:/srv:ro`, `./evidence/site/Caddyfile:/etc/caddy/Caddyfile:ro`, `./app_data/secrets/report_site:/etc/caddy/users:ro`; mạng `caddy_net`; nhãn `caddy: evidence.lan.fwg.vn` (giữ hostname để link cũ không gãy); **không mở cổng host** (nếu cần kiểm cục bộ: chỉ `127.0.0.1:3006`).
- `evidence/site/Caddyfile` **sinh ra** từ `access.areas` trong hồ sơ khách (`python -m analytics render site`): mỗi khu vực một `handle /<area>/*` có `basic_auth { import /etc/caddy/users/<area>.caddy }`; khu vực `legacy` phục vụ các đường dẫn cũ (`/ceo-weekly-pulse/`, `/finance-cashflow/`, `/`) cùng dữ liệu của chúng; mặc định `respond 404`. File người dùng `app_data/secrets/report_site/<area>.caddy` (tên đăng nhập + hash bcrypt) do người vận hành tạo bằng `caddy hash-password`, không vào git; README ghi cách thêm và thu hồi.
- Trang legacy chứa dữ liệu cả bảng (source cũ) nên khu vực `legacy` chỉ cấp cho nhóm điều hành/tài chính (người dùng hiện tại của hai trang đó; hỏi user danh sách).

### Dagster (`orchestration/reports/`)

- `build_request.py`: `run_status_sensor` trên `pipeline_batch_nightly_job` SUCCESS → ghi `request.json`; job tay `report_site_build_job` (build ngoài lịch, ví dụ sau khi sửa trang).
- `build_status.py`: sensor đọc `status.json`; lỗi → `send_lark_card` (`orchestration/notifications/lark_client.py:45`) kênh cảnh báo; quá 2 giờ sau nightly chưa có kết quả → cảnh báo.
- `summary_message.py`: job `report_summary_message_job`, chạy khi build của khu vực thành công và report có `message.schedule` đến hạn (Weekly Pulse: sáng thứ Hai). Biên dịch SQL `kpi_tiles` bằng gói `analytics`, chạy chỉ đọc trên bản sao catalog `olap.duckdb`, dựng thẻ Lark có link `https://evidence.lan.fwg.vn/<area>/<report>/`. Webhook riêng `LARK_REPORT_WEBHOOK` / `LARK_REPORT_SECRET` (không dùng kênh cảnh báo); kênh khai báo trong hồ sơ `message.channels[] {id, env_webhook, can_view_cost}`; thẻ `cost_sensitive` không vào kênh `can_view_cost: false`. `REPORT_MESSAGE_DRY_RUN=1` chỉ ghi log (cùng cách `DIGEST_DRY_RUN` của `orchestration/ops/morning_digest.py`). Lỗi gửi không làm hỏng run. Zalo/Telegram là Đợt 8 (notifier nhiều backend); phase này chỉ Lark.
- `data_platform` cần đọc gói `analytics` và hồ sơ khách: thêm volume `./analytics:/app/analytics:ro`, `./tenants:/app/tenants:ro`. Đăng ký module trong `modules.yaml`/`definitions.py` theo quy ước Đợt 1; cập nhật `check_boundaries.py` nếu cần (orchestration được import `analytics`, không ngược lại).

## Các bước

1. Kiểm mount lồng và builder trong container thử (không tên/cổng prod).
2. Viết builder, renderer site, Dagster module, test (`orchestration/reports/__tests__/`: sensor ghi request đúng; status lỗi → gọi notifier stub; tin không có thẻ chi phí cho kênh không quyền).
3. Gate: `scripts/checks/run-all.sh`; `dagster_inventory.py` chỉ thêm asset/job/sensor mới, không đổi cái cũ; pytest.
4. User tạo tài khoản và file hash (session thực thi đưa lệnh, không thấy mật khẩu).
5. **Deploy (giờ user duyệt, ngoài 02:30–04:00 và sáng thứ Hai):** theo runbook "Refactor deploys" cho `data_platform` (stop → ff → start → instigator diff), rồi `docker compose up -d report_site evidence` (recreate, không build image). Lần đầu builder build mọi khu vực vì chưa có `current`.
6. Kiểm sau deploy (Verification), rồi theo dõi nightly kế tiếp: request ghi đúng, build thành công, tin gửi vào kênh thử.

## Files

- Tạo: `evidence/scripts/build-areas.sh`, `evidence/site/Caddyfile` (sinh ra), `analytics/renderers/site.py`, `orchestration/reports/{__init__,build_request,build_status,summary_message}.py`, `orchestration/reports/README.md`, `orchestration/reports/__tests__/*`, `analytics/renderers/message.py`.
- Sửa: `docker-compose.yml` (dịch vụ `evidence`, `data_platform` volume, dịch vụ mới `report_site`), `orchestration/definitions.py` hoặc `modules.yaml` (đăng ký), `scripts/checks/check_boundaries.py`, `.gitignore` (`app_data/report_site/`), `tenants/fine_japan/analytics/profile.yml` (`access`, `message`), tài liệu ở đầu file.
- Không sửa `Dockerfile.evidence`.

## Verification

- `curl -s -o /dev/null -w '%{http_code}' https://evidence.lan.fwg.vn/dieu-hanh/ceo_weekly_pulse/` trả 401 khi không đăng nhập, 401 với tài khoản khu vực khác, 200 với tài khoản đúng; cùng kiểm cho một file dữ liệu trích của khu vực (đường dẫn lấy từ S2).
- `ss -ltnp | grep 3006` không còn cổng mở trên mọi interface (chỉ 127.0.0.1 nếu giữ).
- Grep bản build khu vực không có quyền chi phí (tạo một khu vực thử `ban-hang` không quyền chi phí): không có id metric `cost_sensitive`.
- `docker compose restart evidence` không chạy build (log builder "current exists, waiting").
- Nightly kế tiếp: `status.json` ok cho mọi khu vực trước 05:30; tin thử đến kênh thử với link mở được (trong LAN).
- Trang legacy `/ceo-weekly-pulse/`, `/finance-cashflow/` vẫn mở được (sau đăng nhập).
- Instigator diff trước/sau deploy: chỉ thêm sensor/job mới, trạng thái cũ giữ nguyên.

## Đổi số?

Không. Số trang legacy giữ nguyên; trang Weekly Pulse mới chưa được giới thiệu cho người dùng.

## Rủi ro

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| Người dùng đang mở Evidence bị yêu cầu đăng nhập bất ngờ | Cao × Thấp | Báo trước, gửi tài khoản trước giờ deploy |
| Mount lồng ghi được trong `data_lake` chỉ đọc gây nhầm quyền | Thấp × Trung bình | Chỉ thư mục `report_build`; kiểm ở bước 1 |
| Build chạy cùng lúc lịch `*/3` ghi parquet | Trung bình × Thấp | Giống hôm nay (container cũ cũng đọc lúc khởi động); view serving tự chọn parquet mới nhất |
| Nightly đỏ → không build → trang cũ | Trung bình × Thấp | Dải "dữ liệu đến hết ngày …" và cảnh báo quá hạn |

## Rollback

1. `git revert` các commit; theo runbook cho `data_platform` (stop → revert → start).
2. `docker compose stop report_site && docker compose rm -f report_site`, rồi `docker compose up -d evidence` với compose cũ (container trở lại build lúc khởi động, cổng 3006, nhãn Caddy cũ).
3. Bản build cũ trong `app_data/report_site/` giữ lại để so; xoá sau khi ổn.
