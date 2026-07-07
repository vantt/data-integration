# Phase 09 — Ledger Re-pull ngày 10 + Default Filter (P1)

**Status: DONE** (2026-07-05) — `ingest_monthly_repull_schedule` (cron `0 7 10 * *` ICT) added, reuses `ingest_monthly_job`. Default filter token: **`past1months`**, NOT `previousmonth` (empirically confirmed `previousmonth` 500s on Metabase v0.60.2 via live `/api/dataset` test). `finance_cashflow.md` (dashboard 113) already used `past6months`, not `thismonth` — left untouched. Confirmed via `misa_amis_assets.py` docstring: account-ledger ingest is idempotent, full-replaces (year, month) partition.

## Vấn đề

1. **Actuals đông cứng trước khi sổ chốt**: `ingest_monthly_schedule` chạy ngày 1 lúc 07:00 ICT (`orchestration/definitions.py` L462-471), downloader default kéo **tháng trước** — nhưng sổ MISA thường chốt ngày 5–10 (guide §4). Kéo ngày 1 = thiếu bút toán, không re-pull → variance sai âm thầm.
2. **Landing view trống**: dashboard 114 filter `period_month` default `thismonth` (blueprint L60) — giữa tháng actuals hiện tại chưa có/mới một phần → mở dashboard thấy gần 0 → mất niềm tin.

## Thay đổi

### 4a. Re-pull schedule ngày 10

**File:** `orchestration/definitions.py`

- Thêm schedule thứ hai trên cùng `ingest_monthly_job`: cron `0 7 10 * *` (ngày 10, 07:00 ICT). Downloader default = tháng trước → ngày 10 kéo lại đúng tháng vừa chốt sổ.
- An toàn idempotent: UPSERT-by-(year,month) — re-pull đè trọn partition tháng, không trộn (đã là cơ chế hiện tại).
- Guard `_has_active_run` như các schedule khác.
- Tên: `ingest_monthly_repull_schedule`, comment nêu lý do (sổ MISA chốt ngày 5–10).

Restart `data_platform` sau khi thêm (definitions reload).

### 4b. Default filter dashboard

**File:** `docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md` (filter `period_month`, L56-63)

- Đổi `"default": "thismonth"` → token "tháng trước" (`"previousmonth"` / `"past1months"` — **verify token hợp lệ** trên Metabase v0.60.2 qua 1 filter thử trước khi sửa blueprint; ghi lại token đúng vào blueprint).
- Cân nhắc cùng token cho dashboard 113 (finance_cashflow.md) nếu đang `thismonth` — kiểm tra và đồng bộ.
- Redeploy qua `/deploy-metabase-blueprint`.

## Verify

- Dagster UI: schedule mới xuất hiện, tick preview đúng ngày 10.
- (Sau ngày 10 gần nhất hoặc trigger tay) job chạy → partition tháng trước refresh; `fact_order_costs` regression không đổi ngoài chênh do sổ chốt muộn (user duyệt nếu lệch).
- Mở dashboard 114 không chọn gì → thấy tháng trước với actuals đầy đủ + plan.

## Risks

- Re-pull ngày 10 làm 642 lịch sử dịch theo sổ mới (đã từng chấp nhận khi backfill — plan 260702 ghi "user duyệt") — ghi chú vào morning digest/changelog tháng đầu áp dụng.
- Download nặng chạy thêm 1 lần/tháng — chấp nhận được.
