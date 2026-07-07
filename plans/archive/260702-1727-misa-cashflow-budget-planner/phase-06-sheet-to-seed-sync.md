# Phase 06 — Sheet→Seed Sync Script (P0)

**Status: DONE** (2026-07-05) — `ingestion/src/gsheet_budget_sync/` package (9 files, refactored from initial 1013-LOC single file per code review), `budget_sheet_sync_asset` + `budget_sheet_sync_schedule` (02:30 ICT) in Dagster, mart WHERE fix. 31 unit tests + dbt compile + Dagster import all verified. Open question 3 (auto-commit) resolved NO — asset writes seed files only. **Blocking on live sheet:** open question 5 (missing `remainder` row in ALLOCATION_POLICY tab) still unresolved in the actual Google Sheet — sync will reject until finance/kỹ thuật adds it.

## Mục tiêu

Cầu nối đang thiếu: đọc Google Sheet matrix (BUDGET_ITEMS + ALLOCATION_POLICY) → transform → ghi 2 seed CSV long-format → dbt build pick up. Finance chỉ edit sheet.

## Sheet (đã verify truy cập 2026-07-05)

- **URL:** `https://docs.google.com/spreadsheets/d/15hba6bzrTRXUDXBeUg5_DhefrETX9kLGG8SnPJZzTfA/edit` (user cung cấp 2026-07-03, link-shared — CSV export hoạt động, không cần creds)
- **Tabs:** `BUDGET_ITEMS` gid=0 · `ALLOCATION_POLICY` gid=1662021004 · `__REF` gid=2061002942
- **Endpoint dùng:** `.../export?format=csv&gid=<gid>` per tab (gviz-by-name gộp header sai — không dùng)
- **Phát hiện từ data thật:**
  - BUDGET_ITEMS có section rows (`THU` / `CHI THƯỜNG XUYÊN` / `CHI ĐẶC BIỆT / DỰ PHÒNG` ở cột Chiều, cột A trống) — parser phải skip.
  - Đã có rows thật ngoài placeholder: reserve `Quỹ Phúc Lợi Nhân Viên`, one_off `Mua SSD/RAM/Laptop 1/Laptop 2` (Tổng Cần 6M/10M/30M/30M, chưa có Tháng Cần).
  - Cột tháng hiện chỉ có T7–T9 2026 (3 cặp `Gợi Ý|Budget`); cell Budget còn trống (budget bắt đầu T7).
  - Giá trị tiền có format `6,000,000 ₫` → phải strip currency (tái dùng pattern `_parse_target_value` của `gsheet_targets.py`).
  - ALLOCATION_POLICY header tiếng Việt (`Ưu Tiên|Bucket|Rule Type|Value|Effective From|Effective To`) — map theo vị trí `AP_COL`. Policy đã có data thật (Chi Lương, Chi BHXH, Để dành mua SSD/RAM Server...).

## Context

- Sheet layout (source of truth): `scripts/budget/validate-budget-sheet.gs`
  - BUDGET_ITEMS: row1 = header tháng, row2 = tên cột, data từ row 3.
    Cột A–F: `Dòng Tiền | Chiều (Thu|Chi) | Type (recurring|one_off|reserve) | Tháng Cần | Tuần TT (1|2|3|4|spread) | Tổng Cần`. Từ G: cặp `[Gợi ý Tx][Budget Tx]` per tháng.
  - ALLOCATION_POLICY: `priority | bucket | rule_type | value | effective_from | effective_to`, 2 hàng header.
  - `__REF` (hidden): A = Chiều (Thu/Chi), B = cashflow_line (khớp `dim_gl_account`).
- Seed đích: `transformation/seeds/seed_cashflow_budget.csv` (long: `cashflow_line,period_month,direction,planned_amount,payment_week,item_type,item_label,item_target,target_month,notes`) + `seed_cash_allocation_policy.csv`.
- Pattern tham chiếu: `ingestion/src/gsheet_targets.py` — export CSV qua URL `.../export?format=csv&gid=<gid>` (sheet link-shared, không cần API creds), pandas parse, validate, fail loud.
- Nightly dbt build (03:00 ICT, `orchestration/assets/dbt.py` — `dbt build` gồm seeds) tự pick up seed mới.

## Files

- **Create** `ingestion/src/gsheet_budget_sync.py` — pull + transform + validate + write seeds. Module hóa: parse matrix / transform budget / transform policy / validators tách hàm rõ ràng (~dưới 200 LOC mỗi concern, tách file nếu vượt).
- **Create** Dagster asset `budget_sheet_sync_asset` trong `orchestration/assets/` (nhóm `sheets`, theo pattern `sheets_targets_asset`) + schedule daily 02:30 ICT trong `orchestration/definitions.py` (trước nightly build 03:00).
- **Modify** `.env.docker.example` / `.env.local`: thêm `SOURCES__SPREADSHEET_URL__BUDGET` (+ gid 2 tab).
- Seed CSVs: script ghi đè (đường dẫn container `/app/transformation/seeds/` — verify mount writable trước).

## Transform rules

1. Chỉ đọc cột `Budget Tx` (bỏ `Gợi ý Tx`); tháng lấy từ header row 1 → `period_month = YYYY-MM-01`.
2. `Thu → inflow`, `Chi → outflow`.
3. `item_type=recurring`: `cashflow_line` = col A (phải khớp `__REF`), `item_label` = null. **Trim whitespace** trước khi so khớp (__REF thực tế có dòng trailing space — sẽ vỡ exact join nếu không trim).
4. `item_type=one_off|reserve`: **KHÔNG khớp MISA** (user chốt 2026-07-05: "để dành, khi nào đủ thì dùng" — plan-side only). `item_label` = col A; `cashflow_line` = item_label. Các dòng này **loại khỏi BvA variance** (chỉ recurring tham gia so kế-hoạch-vs-thực-tế); vẫn tính vào forecast outflow (tiền để dành là dòng ra thật) + Tab B reserve tracking. Khi mua thật, khoản chi hiện trong actuals dưới line MISA tương ứng (vd NCC) — variance dương line đó là hành vi đúng.
5. Dòng không có tên (col A trống) hoặc section row (`THU`/`CHI THƯỜNG XUYÊN`/`CHI ĐẶC BIỆT` ở col B) → skip; dòng có Type nhưng thiếu tên → skip + warning (sheet thật có dòng template rác dạng `,Thu,recurring`).
6. Cell trống/0 → không sinh row (không ghi planned_amount=0).
7. Merge historical: giữ nguyên rows của các tháng đã đóng (period_month < tháng hiện tại) từ seed hiện có; chỉ replace tháng hiện tại + tương lai. Tránh sheet xóa cột tháng cũ làm mất lịch sử budget.
8. ALLOCATION_POLICY: map theo vị trí cột (header tiếng Việt), strip currency ở Value, validate rồi ghi (append-only semantics đã nằm trong sheet).
9. **BvA mart hệ quả (đổi ở `mart_cashflow_budget_vs_actual.sql`)**: budget CTE thêm `WHERE item_type = 'recurring'` — one_off/reserve không tham gia variance (rule 4). Forecast mart giữ nguyên (tính mọi item_type).

## Validation (mirror `.gs`, fail = không ghi seed, exit non-zero, log rõ dòng lỗi)

- recurring `cashflow_line` ∈ `__REF` tab (đọc cùng lần pull) — và cross-check ∈ distinct `dim_gl_account.cashflow_line` nếu chạy trong container.
- `direction` ∈ {Thu, Chi}; `item_type` ∈ {recurring, one_off, reserve}; `payment_week` ∈ {1,2,3,4,spread}.
- `target_month` có mà `item_target` null → reject.
- Policy: `rule_type` hợp lệ; `value` bắt buộc với fill_to_target/fixed/pct_remaining; `remainder` phải priority cuối; không gap/overlap effective dates per bucket.
- Sheet đọc về rỗng / thiếu tab / thiếu header kỳ vọng → **abort, không đè seed cũ**.

## Steps

1. Verify mount: `docker exec data_platform ls -la /app/transformation/seeds/` writable.
2. ~~Lấy gid 3 tabs~~ — done, xem § Sheet.
3. Viết script + unit test transform (fixture CSV matrix nhỏ, chạy pytest host).
4. Chạy tay lần đầu: so output với seed placeholder hiện tại (5 lines × 6 tháng) — phải khớp giá trị.
5. Wire Dagster asset + schedule; restart `data_platform` (manifest/definitions reload).
6. E2E: sửa 1 số trên sheet → chạy asset → `dbt build --select seed_cashflow_budget+` → verify dashboard 114 đổi số.

## Tests / verify

- Unit: matrix→long với đủ 3 item_type, cell trống, Thu/Chi map, merge historical.
- Reject cases: line sai, policy overlap, sheet rỗng.
- Regression: `dbt build` xanh; dashboard 113 không đổi.

## Risks & rollback

- Script bug ghi seed hỏng → nightly build fail hoặc số sai. Mitigation: validation abort-on-error + seed cũ giữ trong git (revert = `git checkout -- transformation/seeds/`... chỉ khi file đã commit — commit seed sau mỗi sync đúng).
- Sheet đổi cấu trúc cột → parser đọc header row 2 theo tên (không hardcode index ngoài block config, giống `BI_COL` trong `.gs`).
- Rollback: tắt schedule, seed revert từ git, dashboard không cần đụng.

## Open questions

1. ~~one_off/reserve mapping~~ — **RESOLVED 2026-07-05 (user)**: không khớp MISA, option (c) — plan-side only, xem transform rule 4+9.
2. ~~Sheet URL + gid~~ — RESOLVED 2026-07-05, xem § Sheet ở trên.
3. Sync ghi seed trong container: seed thay đổi có cần commit git tự động không, hay chấp nhận drift working-tree? Đề xuất: asset chỉ ghi file, user commit theo nhịp tháng.
4. ~~ALLOCATION_POLICY bucket ý định~~ — **RESOLVED 2026-07-05 (user fix sheet)**: Chi Lương/Chi BHXH đổi sang `from_plan` (để dành lương+BHXH tháng sau từ thặng dư), các quỹ mua sắm `fixed` 6M/tháng. Đúng semantics waterfall.
5. **Sheet còn thiếu dòng `remainder`** trong ALLOCATION_POLICY (validator `.gs` + sync đều require remainder cuối cùng) — user cần thêm: priority 9, bucket "Tiền mặt tự do", rule_type `remainder`, value trống. Nếu không, sync reject policy tab.
