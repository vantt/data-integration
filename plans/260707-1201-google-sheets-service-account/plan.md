# Google Sheets Service Account — Centralized Read/Write

**Status:** ALL 3 PHASES DONE (2026-07-07). Phase 3: `sheet_writeback.py` + `fetch.py` (budget read path) migrated to shared SA credential — the budget sheet's public CSV export also broke when link-sharing was turned off, so this fix was required (not just the write side, as originally scoped). First real, non-dry-run write succeeded for 2026-08 (8 cells), re-run confirmed idempotent, Budget column untouched (verified by reading the live sheet). 42/42 tests pass.
**Created:** 2026-07-07
**Context:** Split out of `plans/260705-1459-budget-cashflow-workable-loop` Phase 5 (pre-fill suggestions write-back), which needs Editor-level Sheets API credentials — that plan has since been merged into `plans/260702-1727-misa-cashflow-budget-planner` as Phase 10 (2026-07-07). Merges with a previously deferred security item — `plans/archive/260624-1958-pipeline-hardening-followups/phase-01-gsheets-service-account.md` — that already wanted a service account for 5 read-only sheets (public-link exposure). One credential, one auth helper, covers both needs instead of solving them twice.

## Vấn đề hiện tại

- **5 sheet đọc public-link** (no creds, "Anyone with link"): `gsheet_marketing_spend.py`, `gsheet_targets.py`, `gsheet_overhead_classification.py`, `gsheet_team_config.py`, `gsheet_us_shipment_prices.py`. Data (chi phí marketing, target, team config, giá ship) world-readable với ai có link. Sheet ID/URL cũng track trong `ingestion/.dlt/config.toml` (committed).
- **1 sheet cần ghi** (budget suggestions write-back, `gsheet_budget_sync/sheet_writeback.py`): code xong, hard-blocked vì chưa có service account nào — cần Editor quyền, cao hơn hẳn 5 sheet kia (Viewer).
- Cả 2 nhu cầu bị chặn bởi cùng 1 bước: tạo GCP service account. Làm 1 lần, dùng chung.

## Thiết kế

Một service account, share khác quyền theo sheet:
- Budget sheet (`ALLOCATION_POLICY`/`BUDGET_ITEMS`): share **Editor** (cần ghi cột "Gợi ý").
- 5 sheet còn lại: share **Viewer**, tắt "Anyone with link" sau khi xác nhận đọc qua API hoạt động.

Centralize auth trong 1 helper module (DRY) — mỗi reader hiện tại tự parse CSV/xlsx theo layout riêng; helper chỉ đổi **cách lấy data** (authenticated `gspread` thay vì public export URL), giữ nguyên parsing/normalization logic của từng reader để tránh vỡ contract downstream.

## Phases

| # | Phase | File | Ưu tiên | Ra được gì |
|---|-------|------|---------|-----------|
| 1 | GCP service account + centralized auth helper | `phase-01-service-account-setup.md` | P0 | 1 SA key, share đúng quyền từng sheet, `ingestion/src/gsheet_auth.py` helper |
| 2 | Migrate 5 read-only reader sang SA auth | `phase-02-migrate-readonly-sheets.md` | P1 | Không còn public-link exposure; config.toml không track sheet ID |
| 3 | Kích hoạt budget write-back (Phase 10 của `misa-cashflow-budget-planner`) | `phase-03-activate-budget-writeback.md` | P1 (phụ thuộc P1) | `budget_suggestion_writeback_schedule` chạy thật, không còn fail-loud |

Phase 2 và 3 độc lập sau khi Phase 1 xong — làm song song được (không đụng chung file).

## Acceptance criteria

- [x] 1 SA key tồn tại, không commit vào git, đường dẫn qua env var (không hardcode).
- [x] Budget sheet share Editor cho SA; 5 sheet còn lại share Viewer cho SA; tất cả tắt "Anyone with link".
- [x] 5 reader đọc qua SA auth, row count + columns giống hệt trước khi đổi (test từng reader trước/sau).
- [x] `config.toml` không còn sheet URL/ID thật (chuyển ra secrets/env).
- [x] `budget_suggestion_writeback_schedule` chạy thành công 1 lần thật (không phải dry-run) — verify cột "Gợi ý" ghi đúng, cột Budget không bị đụng.
- [x] Container (Windows-native + Docker) đều đọc được key path. (Docker verified live; Windows-native path set in .env.local, not run-tested since Docker is primary env)

## Rủi ro chính

- Mỗi reader hiện parse 1 format cụ thể (csv vs xlsx, gid cụ thể) — Sheets API trả values khác format hơn CSV/xlsx export → phải test từng reader giữ nguyên column names/dtypes.
- Ghi nhầm cột Budget khi activate Phase 3 → mất số finance đã nhập — mitigation đã có trong `sheet_writeback.py` (resolve cột theo header "Gợi ý" exact match) + dry-run diff trước lần chạy thật đầu tiên.
- Quyền Editor cho SA trên budget sheet là bề mặt rủi ro mới — scope đúng 1 sheet, không share Editor lên 5 sheet kia.

## Liên quan

- Thay thế: `plans/archive/260624-1958-pipeline-hardening-followups/phase-01-gsheets-service-account.md` (deferred item, nay gộp vào đây).
- Phụ thuộc bởi: `plans/260702-1727-misa-cashflow-budget-planner` Open item #2 (Phase 10 activation, tên cũ "Phase 5" trước khi merge 2026-07-07) — plan đó trỏ sang đây thay vì tự làm phần service-account.
