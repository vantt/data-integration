---
phase: 2
title: "Spec v2 (schema + template) và spec Weekly Pulse theo blueprint đang chạy; catalog tối thiểu"
status: pending
priority: P1
effort: "1.5d"
dependencies: [1]
---

# Phase 02: Spec v2 cho Weekly Pulse

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: viết định dạng spec v2 vào `.skills/analytics-design/` (skill sở hữu định dạng, quyết định D8) và cập nhật mục Analytics trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `.skills/analytics-design/SKILL.md` (sửa mâu thuẫn "Workflow C" ở dòng 12: spec v2 là lớp bắt buộc cho report sản phẩm; Phase 4–5 chọn metric id từ registry thay vì viết SQL); `.skills/analytics-design/templates/report_spec_v2_template.yml` (mới); `.skills/metabase-automation/STRATEGY.md` dòng 6 (bỏ "Forthcoming `deploy_from_design_spec.js`", trỏ tới plan này); `analytics/README.md` (mục spec v2, catalog); `docs/architecture/modules.md`.

## Mục tiêu

Một định dạng spec không phụ thuộc engine (kế thừa D1, D2, D4, D7, D8 của plan 260528) và spec `ceo_weekly_pulse` viết theo **dashboard đang chạy**, không theo design spec đã lệch (thiết kế §7; hội đồng tooling §1).

## Thiết kế spec v2

File YAML `analytics/specs/<report_id>.yml`, schema `analytics/schema/report-spec.schema.json`:

- `spec_id`, `spec_version: 2`, `title {vi}`, `question`, `cadence ∈ {daily, weekly, monthly}`, `period_mode` (`to_date` hoặc `closed`), `as_of` (mặc định "hết hôm qua").
- `tabs[]` → `blocks[]`; mỗi block có `time_axis` (ngày đơn / ngày hoàn / ngày đối soát) và tiêu đề hiện trục đó.
- `cards[]`, mỗi card: `card_id` (slug ASCII, duy nhất trong report, là khoá danh tính ở mọi engine), `kind ∈ {kpi_compare, trend, breakdown, breakdown_compare, derived, table, inline_sql, meta_period, meta_freshness, text}`, `metric_ref` (một hoặc nhiều id registry), `dimensions` (chiều khai báo trong lớp ngữ nghĩa), `window`, `comparison ∈ {prev_week_full, prev_wtd_same_span, prev_month, same_period_last_year, target}`, `viz` (term của `VISUALIZATION_VOCABULARY.md`), `size`, `position`.
- `inline_sql` (D2, bậc đệm): bắt buộc `outputs[] {name, type}`, được đánh dấu "không chuẩn" ở mọi renderer, đếm vào tỉ lệ card không chuẩn.
- `tenant_params`: tham số lấy từ hồ sơ khách, không ghi cứng: `monthly_target_goal` (thay `goal = 600,000,000` trong viz "MTD GMV vs Target"), `detailview_url_template` (thay link cứng `detailview.lan.fwg.vn` trong card danh sách đơn).
- Chú thích tự sinh cho từng thẻ (tooltip) và chân trang "doanh thu được tính thế nào" sinh từ hồ sơ khách (preset, VAT, trục ghi nhận) và registry (công thức bằng lời, độ phủ).
- `portability` (D6, ưu tiên thấp): renderer báo `native | fallback | unsupported` cho từng viz.

Catalog tối thiểu `analytics/catalog/catalog.yml` có đúng một mục: `ceo_weekly_pulse`, `cell: EXE-W`, `primary_cell: EXE-W`, `engine: evidence`, `area: dieu-hanh`, `metrics` (suy ra từ spec, không gõ tay), `kpi_tiles` (thẻ dùng cho tin tóm tắt và trang chủ), `status: pilot`. Schema `analytics/schema/catalog.schema.json`.

## Các bước

1. **Capture-first (D3):** chạy `node .skills/metabase-automation/scripts/capture_dashboard.js <id dashboard Weekly Pulse> <file tạm>` ở chế độ chỉ đọc với API key hiện có, rồi so SQL từng card với `docs/analytics-handbook/blueprints/metabase/ceo_weekly_pulse.md`. Nếu lệch: mốc so số là bản đang chạy trên Metabase, ghi rõ vào spec header và báo user. Script chỉ gọi GET (kiểm lại trong code trước khi chạy).
2. Viết schema spec v2 và catalog, template trong skill.
3. Viết `analytics/specs/ceo_weekly_pulse.yml`: 3 tab, 30 card, đúng thứ tự và tên card của blueprint. Card dữ liệu dùng `metric_ref`; dự kiến chỉ "Đơn hàng tuần này" (bảng chi tiết) và "Loss-Making Channel Count" (aggregate lồng) là `inline_sql`.
4. Validator (mở rộng từ phase 01) kiểm: schema; mọi `metric_ref` tồn tại và `active`; chiều có trong lớp ngữ nghĩa; `card_id` duy nhất; `inline_sql` có `outputs`; tỉ lệ card `inline_sql` trên card dữ liệu (cảnh báo khi > 30%); `metrics` của catalog bằng hợp `metric_ref` của spec; `cost_sensitive` của report suy ra từ metric.
5. Ghi vào `tenants/fine_japan/analytics/profile.yml`: `monthly_target_goal`, `detailview_url_template` đúng giá trị đang chạy.

## Files

- Tạo: `analytics/schema/report-spec.schema.json`, `analytics/schema/catalog.schema.json`, `analytics/catalog/catalog.yml`, `analytics/specs/ceo_weekly_pulse.yml`, `.skills/analytics-design/templates/report_spec_v2_template.yml`.
- Sửa: `analytics/compiler/validate.py`, `tenants/fine_japan/analytics/profile.yml`, `.skills/analytics-design/SKILL.md`, `.skills/metabase-automation/STRATEGY.md`, `analytics/README.md`, `docs/architecture/modules.md`.
- Tạo test: `analytics/tests/test_spec_validate.py` (spec thật pass; fixture hỏng fail).

## Verification

- Validator xanh; số card dữ liệu `inline_sql` ≤ 2/24 (8%).
- Bảng ánh xạ card blueprint → `card_id` đủ 30 dòng, ghi trong `analytics/specs/ceo_weekly_pulse.yml` (trường `baseline_name` của từng card) để harness so số tìm được cặp.
- Kết quả bước 1 (blueprint khớp bản đang chạy hay không) ghi trong báo cáo phase.

## Đổi số?

Không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Blueprint lệch bản đang chạy | Bước 1 capture chỉ đọc; mốc là bản đang chạy |
| Spec phình thêm trường "phòng khi cần" | Chỉ thêm trường Weekly Pulse dùng hoặc thiết kế §4 ③ nêu rõ |

## Rollback

Revert commit. Không có gì chạy trên prod; bước 1 chỉ đọc.
