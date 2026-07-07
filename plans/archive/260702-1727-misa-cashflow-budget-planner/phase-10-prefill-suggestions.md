# Phase 10 — Pre-fill "Gợi ý" vào Sheet (P2)

**Status: CODE DONE, NOT LIVE** (2026-07-05) — user chose to build this now rather than wait for the T7→T8 loop to run smoothly first (overriding this doc's own YAGNI gate below). Option (b) implemented: `--write-suggestions` mode in `gsheet_budget_sync/suggestions.py` + `sheet_writeback.py`, `budget_suggestion_writeback_asset`/`_job`/`_schedule` (day 1, 08:00 ICT). 31 tests pass (mocked, no real API calls), Dagster imports clean with zero credentials configured (lazy `gspread` import). **Hard blocker: no Google service-account credential exists yet** — setup moved to its own plan `plans/260707-1201-google-sheets-service-account` (Phase 1 = create SA + share Editor on this sheet, Phase 3 = activate this write-back). Until that plan's Phase 1+3 land, the schedule fails loud every tick by design. Full code details: `plans/reports/impl-260705-2010-phase5-prefill-suggestions-report.md`.

## Mục tiêu

Cột `Gợi ý Tx` trong sheet matrix hiện finance phải tự ước — thiết kế gốc (`phase-04-budget-hybrid.md`) là script auto-fill để giảm nhập liệu còn ~15'/tháng. Chiều ghi ngược: pipeline → sheet.

## Phụ thuộc

Phase-06 (đã có kết nối sheet + hiểu layout). **Chỉ làm sau khi vòng nhập T7→T8 chạy trơn** — YAGNI: nếu finance thấy không cần gợi ý, drop phase này.

## Logic gợi ý (theo thiết kế gốc `plans/260702-1727-misa-cashflow-budget-planner/phase-04-budget-hybrid.md`)

| item_type | Gợi ý |
|---|---|
| recurring | rolling avg 3 tháng actual từ `fact_cash_movement` (per cashflow_line + direction) |
| reserve (target + deadline) | `gap_còn_lại / months_until_target` (từ `mart_cashflow_reserve_status`) |
| reserve (target only / open-ended) | không tính — hiện "X/target" hoặc để trống |
| one_off | 0 trừ tháng target_month |

## Cách ghi vào sheet — 2 options, chốt khi làm

- **(a) Apps Script kéo từ pipeline**: cần expose endpoint đọc rolling avg → phức tạp, chưa có HTTP serving layer phù hợp. Không khuyến nghị.
- **(b) Python script ghi qua Sheets API** (khuyến nghị): mở rộng `gsheet_budget_sync.py` thêm mode `--write-suggestions`; cần service account + share sheet quyền edit (khác phase-06 chỉ cần link-share đọc). Chạy trong Dagster asset riêng, schedule ngày 1 hàng tháng 08:00 (sau ingest 07:00).

## Steps (option b)

1. Tạo service account / dùng creds gsheet hiện có nếu đã có ghi (kiểm tra `ingestion/.dlt/config.toml` + các `gsheet_*` khác).
2. Query rolling avg 3 tháng từ parquet `fact_cash_movement` (read-only, host path hoặc trong container).
3. Ghi CHỈ cột `Gợi ý Tx` của tháng tiếp theo; không đụng cột Budget.
4. Idempotent: chạy lại cùng tháng = cùng giá trị.

## Verify

- Gợi ý T8 = avg(actual T5,T6,T7) per line — hand-check 2 line.
- Cột Budget không bị ghi đè; validator `.gs` không báo lỗi sau khi script chạy.

## Risks

- Ghi nhầm cột Budget → mất số finance đã nhập: mitigation — resolve cột theo header "Gợi ý" exact match, dry-run in ra diff trước lần chạy đầu.
- Quyền edit sheet cho service account = bề mặt rủi ro mới — scope đúng 1 sheet.
