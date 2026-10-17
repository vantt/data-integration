---
phase: 3
title: "Spike tương lai Evidence + renderer Evidence (mỗi khu vực quyền một bản build, source chỉ chứa kết quả card)"
status: pending
priority: P1
effort: "3d"
dependencies: [2]
---

# Phase 03: Spike Evidence và renderer Evidence

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi kết quả spike và thiết kế renderer vào `evidence/README.md` và mục Analytics của `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `evidence/README.md` (khu vực, trang sinh ra, không sửa tay, kết quả spike); `.skills/evidence-automation/SKILL.md` (trang report sản phẩm do renderer sinh; quy trình viết tay chỉ còn cho trang legacy; bỏ hostname/scope cứng khỏi hướng dẫn chung); `analytics/README.md` (renderer Evidence); `docs/architecture/modules.md`.

## Mục tiêu

Biết chắc Evidence legacy đã ghim (40.1.8) làm được ba việc mà lớp đăng nhập và build theo lịch cần, ghi quyết định ở lại hay đổi kiến trúc, rồi viết renderer sinh trang Weekly Pulse từ spec v2.

## Hiện trạng đã kiểm

- Container chạy `cp olap.duckdb → sources && npm run sources && npm run build && … && npm run preview` mỗi lần khởi động (`Dockerfile.evidence:42`), tức build lại mỗi lần restart.
- Source `evidence/sources/datalake/fact_orders.sql` chọn **toàn bộ** `main_marts.fact_orders` (mọi đơn, kể cả `order_code`), và dữ liệu source được đóng vào bản build để trình duyệt tải về (thiết kế §4 ⑤ điều kiện 4). Trang `ceo-weekly-pulse/index.md` có 11 khối SQL chạy trên dữ liệu đó trong trình duyệt.
- Cổng `3006:3000` mở trên mọi interface của host (`docker-compose.yml:117-118`), đi vòng qua Caddy.

## Spike (0.5–1 ngày, chỉ trong container thử)

Chạy theo đúng cách thử ở `evidence/README.md` "Upgrading deliberately" bước 3: image hiện tại dưới tên container khác, không cổng prod, không mạng `caddy_net`, mount bản sao `pages/`, `sources/`, mount `app_data/data_lake` chỉ đọc. Cổng cố định 3106, dừng trong `finally`.

| # | Câu hỏi | Cách kiểm | Kết quả quyết định |
|---|---|---|---|
| S1 | Evidence 40.1.8 có build được dưới đường dẫn con (`basePath`) không | Thử cấu hình `deployment.basePath` trong `evidence.config.yaml` [UNVERIFIED tên khoá], build, phục vụ dưới `/dieu-hanh/` bằng `caddy file_server` thử | Có: mỗi khu vực một đường dẫn con dưới `evidence.lan.fwg.vn`. Không: mỗi khu vực một hostname riêng (`<area>.evidence.lan.fwg.vn`, cần DNS nội bộ, hỏi user) |
| S2 | File dữ liệu trích nằm ở đâu trong bản build, có ra ngoài thư mục khu vực không | Liệt kê bản build, grep tên source | Mọi file phải nằm dưới gốc của khu vực, để quyền theo đường dẫn che được cả dữ liệu |
| S3 | Build một project từ thư mục khác dùng chung `node_modules` của image | Tạo `/tmp/work/<area>` có `pages/`, `sources/`, `evidence.config.yaml`, symlink `node_modules`; chạy `npm run sources && npm run build` | Có: builder dựng project tạm cho từng khu vực. Không: mỗi khu vực một thư mục con có `package.json` riêng dùng chung lockfile |
| S4 | Thời gian và bộ nhớ build 2 khu vực (legacy + dieu-hanh) trong giới hạn `mem_limit: 2g` | Đo | Đặt timeout builder |
| S5 | Tương lai Evidence: ngày bản legacy cuối, Evidence mới có đọc DuckDB file cục bộ không | Đọc changelog/npm registry và tài liệu chính thức (WebFetch), ghi nguồn | Ghi quyết định: ở lại 40.1.8 đã ghim cho tới khi có lý do đổi; spec v2 không phụ thuộc engine nên đổi engine chỉ cần renderer mới |

Kết quả spike ghi vào `evidence/README.md` và báo cáo phase. Nếu S1 và S3 cùng thất bại, dừng phase và đưa user hai phương án (hostname theo khu vực, hoặc một build chỉ chứa các report cùng quyền).

## Thiết kế renderer

- **Khu vực (area)** là đơn vị quyền: tối đa 7 khu vực chức năng (`dieu-hanh`, `ban-hang`, `marketing`, `tai-chinh`, `hang-hoa`, `giao-van`, `khach-hang`), cộng khu vực trang chủ theo persona (phase 13) và khu vực `legacy` cho trang viết tay hiện có. Khai báo trong hồ sơ khách: `access.areas[] {id, functions, can_view_cost}`.
- `python -m analytics render evidence --tenant fine_japan` ghi cho mỗi report `engine: evidence` thuộc khu vực:
  - `evidence/areas/<area>/sources/datalake/<report_id>__<card_id>.sql`: **SQL đã biên dịch của từng card**, chạy lúc build trên DuckDB native, với `as_of` dạng biểu thức lúc build (`current_date - INTERVAL 1 DAY`). File dữ liệu trích chỉ chứa kết quả card (vài dòng), trừ card bảng chi tiết bị giới hạn theo cửa sổ của card. Không còn source "cả bảng".
  - `evidence/areas/<area>/pages/<report_id>/index.md`: trang dùng `select * from datalake.<report_id>__<card_id>`, component theo viz, dải "Dữ liệu đến hết ngày …", chân trang quy ước doanh thu, tooltip từ registry.
  - `evidence/areas/<area>/evidence.config.yaml` (theo kết quả S1).
- **Cờ chi phí:** card dùng metric `cost_sensitive` chỉ được render vào khu vực có `can_view_cost: true`. Ở khu vực khác, card bị bỏ và thay bằng một dòng "Cần quyền xem chi phí". Validator chặn report có `area` không có quyền mà lại đánh dấu card chi phí là bắt buộc.
- **Tất định:** render hai lần ra byte giống hệt; mọi file có banner "generated, đừng sửa tay" và hash của spec + registry + hồ sơ.
- **Trang legacy** (`evidence/pages/{index,ceo-weekly-pulse,finance-cashflow,theme-mvp}`) không đổi nội dung ở phase này; phase 04 đưa chúng vào khu vực `legacy` sau lớp đăng nhập.

## Files

- Tạo: `analytics/renderers/evidence.py`, `analytics/tests/test_render_evidence.py`, `analytics/schema/tenant-profile.schema.json` (thêm `access.areas`).
- Sinh (commit): `evidence/areas/dieu-hanh/{evidence.config.yaml,pages/ceo_weekly_pulse/index.md,sources/datalake/*.sql}`.
- Sửa: `tenants/fine_japan/analytics/profile.yml` (khu vực `dieu-hanh` có `can_view_cost: true`, khu vực `legacy`), `evidence/README.md`, `.skills/evidence-automation/SKILL.md`, `analytics/README.md`, `docs/architecture/modules.md`.
- Không sửa `docker-compose.yml`, `Dockerfile.evidence` ở phase này.

## Verification

- Spike S1–S5 có kết quả và nguồn.
- Build khu vực `dieu-hanh` trong container thử thành công; mở trang qua `caddy file_server` thử, 30 card hiển thị, không lỗi console.
- Kích thước thư mục dữ liệu trích của khu vực nhỏ hơn rõ rệt so với build legacy (ghi số); không file nào chứa cột ngoài danh sách `outputs` của card.
- Render lại không có diff; `pytest analytics/tests` xanh; validator xanh.
- Container thử đã dừng và xoá; cổng 3106 trống.

## Đổi số?

Không. Chưa chạm container prod.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| `basePath` không có ở 40.1.8 | Phương án hostname theo khu vực (S1) |
| Một card cần tương tác trong trình duyệt (bộ lọc) | Weekly Pulse "zero-interaction" (hội đồng tooling §2.3); report định kỳ sau này dùng bộ lọc tĩnh hoặc ở lại Metabase |
| Build lâu vượt khung sau nightly | Đo ở S4; builder chạy tuần tự từng khu vực, có timeout |

## Rollback

Revert commit. Container thử không để lại gì.
