# Phase 03 — báo cáo worker

**Trạng thái:** xong. Spike S1–S5 có kết quả; renderer Evidence sinh khu vực `dieu-hanh`; build trong container thử thành công, trang mở qua Caddy `file_server`, không lỗi console. Có một rủi ro prod cần coordinator biết (bộ nhớ build Evidence, mục "Lo ngại").

## File của phase này (worktree `/home/vantt/app/fg-dw-report`)

Mới:
- `analytics/compiler/cards.py` (biên dịch card spec → SQL, câu meta)
- `analytics/renderers/evidence.py`, `analytics/tests/test_render_evidence.py`
- Sinh (commit): `evidence/areas/dieu-hanh/{evidence.config.yaml, pages/index.md, pages/ceo_weekly_pulse/index.md, sources/datalake/connection.yaml, sources/datalake/ceo_weekly_pulse__*.sql (24 card + meta)}`

Sửa (chỉ phase này):
- `.skills/evidence-automation/SKILL.md` (report sản phẩm do renderer sinh; quy trình viết tay chỉ cho legacy; scope FJ ghi là ví dụ legacy; bảng giới hạn cập nhật Tabs/đăng nhập), `evidence/README.md` (khu vực, file sinh ra, kết quả spike)

Sửa tiếp các file đã đụng ở phase 01/02 (so với snapshot `scratchpad/rp/worktree-end-phase02.tgz`):
- `analytics/compiler/sql.py` (`grouped`, `grouped_compare`, `last_event`, `bounds`), `analytics/compiler/spec_validate.py` (`card_cost_sensitive`, kiểm khu vực/cờ chi phí, derived không được nhóm), `analytics/__main__.py` (`render evidence [--check]`)
- `analytics/schema/tenant-profile.schema.json` (`access.areas`), `analytics/schema/report-spec.schema.json` (`inline_sql.cost_sensitive` bắt buộc, card `required`)
- `analytics/specs/ceo_weekly_pulse.yml`, `.skills/analytics-design/templates/report_spec_v2_template.yml` (`cost_sensitive` của `inline_sql`), `analytics/tests/test_spec_validate.py` (fixture)
- `tenants/fine_japan/analytics/profile.yml` (`access.areas`: `dieu-hanh` có `can_view_cost: true`, `legacy`)
- `analytics/README.md` (mục Renderer Evidence), `docs/architecture/modules.md` (§13)

Không sửa `docker-compose.yml`, `Dockerfile.evidence`, `evidence/pages`, `evidence/sources`. Container prod `evidence` không mount `evidence/areas/`, nên không có gì chạy trên prod.

## Spike (container `evidence-spike`, image `fg-dataware-house-evidence` hiện có, cổng 127.0.0.1:3106, mạng bridge mặc định, bản sao pages/sources, `data_lake` `:ro`; 00:00 ICT, ngoài khung 02:30–04:00)

| # | Kết quả |
|---|---|
| S1 | ✅ `deployment.basePath` có ở 40.1.8 (`paths.base` của SvelteKit). Build với `/dieu-hanh`: HTML, `_app`, link và fetch `/data`, `/api` lúc chạy đều có tiền tố. Caddy (`try_files {path} {path}.html {path}/index.html` + `file_server`): `/dieu-hanh/`, `/dieu-hanh/ceo_weekly_pulse`, `/dieu-hanh/data/manifest.json` → 200. Quyết định: mỗi khu vực một đường dẫn con dưới `evidence.lan.fwg.vn`, không cần DNS mới |
| S2 | Dữ liệu trích nằm trong gốc build của khu vực (`data/datalake/<query>/<hash>/*.parquet`, `api/prerendered_queries/*.arrow`); không file nào ra ngoài |
| S3 | ✅ Project ở thư mục khác với `package.json` chép và symlink `node_modules → /app/node_modules`, `npx evidence sources && npx evidence build` |
| S4 | Khu vực `dieu-hanh`: sources 9 s, build 44 s; 25 file trích tổng **12.617 byte** (legacy: 9 file cả bảng ≈ 1,1 MB). Bộ nhớ đỉnh `evidence build` ≈ 3,5–3,7 GiB cho cả legacy lẫn khu vực nhỏ; ở `--memory 2g` không swap bị OOM-kill (legacy 2/2, khu vực 1/1); ở 4g thành công |
| S5 | npm `@evidence-dev/evidence` latest = 40.1.8 (06/02/2026), chưa có bản nào sau; `@evidence-dev/duckdb` 2.0.1 cùng ngày. Không xác minh được "Evidence mới" có đọc DuckDB file cục bộ. Quyết định: ở lại 40.1.8 đã ghim |

Nguồn S5: https://registry.npmjs.org/@evidence-dev/evidence , https://registry.npmjs.org/@evidence-dev/duckdb , https://docs.evidence.dev/core-concepts/data-sources/duckdb

## Kiểm chứng

- Trang `/dieu-hanh/ceo_weekly_pulse` mở bằng Chromium headless (image `data_platform`, mạng của container thử): 0 lỗi console, 0 HTTP ≥ 400; 3 tab hiển thị đủ thẻ (tab 1: 8 số liệu + 2 biểu đồ/bảng, tab 2: biểu đồ + bảng, tab 3: 9 số liệu + biểu đồ); 6 card meta hiển thị chu kỳ/độ tươi. Có vài request `.arrow` bị trình duyệt huỷ giữa chừng (requestfailed, không phải 404) khi đổi tab.
- Cột của mọi file trích khớp đầu ra khai báo (card `inline_sql` khớp `outputs`), 0 lệch.
- Render lại không có diff (`render evidence --check` exit 0, test); khu vực không có quyền chi phí không chứa id chỉ tiêu chi phí nào và không có SQL của card chi phí (test).
- `pytest analytics/tests`: 113 passed; `run-all.sh`: `RUN-ALL: PASS`.
- Dọn: container `evidence-spike`, `evidence-spike-caddy` đã xoá, cổng 3106 trống; bản sao pages/sources, bản build, ảnh chụp màn hình (có tên khách) đã xoá. Không build image mới.

## Lo ngại

1. **Rủi ro prod:** swap của host đã đầy (8189/8191 MB), container `evidence` prod có `mem_limit 2g` (+2g swap). Build Evidence cần ≈ 3,5 GiB; nếu restart/recreate `evidence` bây giờ, build có thể bị OOM-kill và trang không lên. Không đụng prod; cần user/coordinator biết trước khi restart Evidence và khi đặt giới hạn bộ nhớ cho builder phase 04 (đề xuất ≥ 4 GiB, build tuần tự từng khu vực, có timeout).
2. Container prod chạy `npx serve` (không có trong lockfile, tải lúc khởi động); phase 04 nên phục vụ bằng Caddy `file_server`.
3. Card bảng đơn hàng vẫn chứa tên khách (như legacy) — chỉ đúng khi có lớp đăng nhập theo khu vực (phase 04).
4. Viz chưa có component tương ứng được thay: gauge → số + nhãn mức, donut → cột ngang, progress → số + % mục tiêu (D6 "fallback").
5. Ảnh `alpine:latest` dùng để xoá thư mục tạm (có sẵn hoặc vừa được kéo về; không đụng gì khác).
