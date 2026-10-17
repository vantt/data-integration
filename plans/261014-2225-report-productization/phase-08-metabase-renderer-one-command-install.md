---
phase: 8
title: "Renderer Metabase (spec v2 → IR), tra field theo schema.bảng.cột, cài một lệnh, chứng minh 3 thước đo trên Metabase tạm"
status: pending
priority: P1
effort: "3d"
dependencies: [2, 7]
---

# Phase 08: Renderer Metabase và lệnh cài

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi seam Python → IR JSON → Node vào `analytics/README.md` và `.skills/metabase-automation/STRATEGY.md`. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `analytics/README.md` (lệnh `install`, `render metabase`); `.skills/metabase-automation/SKILL.md`, `STRATEGY.md` (bảng `field_id` cứng ở `STRATEGY.md:133-138` đánh dấu legacy; đường mới tra field lúc deploy); `.skills/metabase-automation/METABASE_VIZ_CATALOG.md` (bảng viz term → JSON mà renderer đọc); `docs/architecture/modules.md`; `.claude/commands/` thêm wrapper `install-reports.md`.

## Mục tiêu

Hoàn tất đường spec v2 → Metabase và đo ba thước đo của thiết kế §1 trên Metabase tạm: (1) cài một lệnh, không sửa tay; (2) chạy lại không đổi gì; (3) report riêng đi qua cùng đường.

## Thiết kế

- `analytics/renderers/metabase_ir.py`: spec + registry + hồ sơ → IR JSON đúng dạng `markdown_parser` trả về, cộng `spec_key`. SQL card do compiler sinh (dùng chung với Evidence; khác nhau chỉ ở bảng ánh xạ relation và `as_of`: Metabase dùng `current_date` lúc truy vấn vì report tương tác), viz lấy từ bảng viz term → JSON (chuyển các template JSON trong `METABASE_VIZ_CATALOG.md` §5 thành dữ liệu `analytics/renderers/metabase_viz.yml`). Tham số khách chỉ đi vào SQL dưới dạng literal đã escape; định danh bảng/cột phải thuộc danh sách lấy từ registry (không nối chuỗi tự do).
- **Tra field (hàng rào 6):** bộ lọc khai báo `field_ref: {schema, table, column}`; lúc deploy gọi một lần `GET /api/database/:id/metadata`, lập map `(schema, table, column) → field_id`; thiếu thì `POST /api/database/:id/sync_schema`, đợi, thử lại một lần, rồi **lỗi cứng** ghi rõ cột thiếu (không lặng lẽ rơi về biến `text`). Không dùng `Table.find` (`lib/resources/Table.js`, tìm toàn instance theo cả `display_name`). Schema đúng mà Metabase thấy cho view serving kiểm trên Metabase tạm (dự kiến `main`; `main_marts` là alias).
- **Lệnh cài:** `python -m analytics install --tenant <t> --target metabase [--plan|--apply]`: validate → render IR cho mọi report `engine: metabase` của khách (catalog chuẩn đã bật + report riêng trong `tenants/<t>/analytics/reports/`) → gọi `node .skills/metabase-automation/scripts/deploy_report.js` với IR và hồ sơ. Một lệnh, exit ≠ 0 khi bất kỳ bước nào lỗi.

## Các bước

1. Renderer + bảng viz; test golden IR cho spec Weekly Pulse (render hai lần ra cùng byte).
2. Tra field trong `lib/field-resolver.js`; test trên Metabase tạm, gồm trường hợp cột mới chưa sync.
3. **So số dạng Metabase:** render Weekly Pulse sang IR Metabase (spec không phụ thuộc engine), chạy SQL từng card bằng DuckDB trên bản chụp và so SQL blueprint theo phương pháp phase 05 (cùng harness, thêm `--engine metabase`). Kỳ vọng 30/30 khớp.
4. **Thước đo 1:** dựng Metabase tạm mới, `install --apply` cho tenant thử (`tenants/_test/analytics/`, catalog bật Weekly Pulse bản Metabase), không thao tác tay; mọi card `POST /api/card/:id/query` không lỗi.
5. **Thước đo 2:** chạy lại: `--plan` toàn `noop`, `--apply` 0 request ghi, `updated_at` không đổi.
6. **Thước đo 3:** thêm một report riêng mẫu (L2, chỉ dùng chỉ tiêu có sẵn) vào `tenants/_test/analytics/reports/`, chạy đúng lệnh ở bước 4: report mới được tạo, report cũ `noop`.

## Files

- Tạo: `analytics/renderers/metabase_ir.py`, `analytics/renderers/metabase_viz.yml`, `.skills/metabase-automation/lib/field-resolver.js`, `analytics/install.py` (lệnh `install`), `tenants/_test/analytics/{profile.yml,overlay.yml,reports/sample_custom_report.yml}`, test tương ứng, `.claude/commands/install-reports.md`.
- Sửa: `.skills/metabase-automation/lib/deploy-core.js` (bộ lọc dùng field resolver), `analytics/compare/harness.py` (`--engine metabase`), tài liệu ở đầu file.

## Verification

- Bước 3: 30/30 card khớp.
- Bước 4–6: ba thước đo đạt, log lưu trong báo cáo phase.
- `pytest analytics/tests`, `node --test` xanh; validator xanh.
- Metabase tạm đã dừng.

## Đổi số?

Không. Chỉ Metabase tạm.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Định dạng API 0.62 khác giả định (metadata, sync, MBQL) | Kiểm trên Metabase tạm cùng phiên bản trước khi viết phần phụ thuộc |
| Tenant thử lẫn vào cấu hình thật | `tenants/_test/` bị validator đánh dấu, `environment: temp`, deployer từ chối URL prod với tenant thử |

## Rollback

Revert commit.
