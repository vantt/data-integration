# Phase 03 — Cashflow report vận hành (Metabase)

**Status:** BLOCKED on cash data ingestion (Phase 01) + `fact_account_balance_monthly` (Phase 02).
**Scope:** deploy báo cáo dòng tiền vận hành (thu/chi + số dư quỹ). KHÔNG phải BC lưu chuyển tiền tệ TT200 3 mục.

## Nguồn sự thật — 4 tài liệu handbook (WHAT sống ở đây, KHÔNG lặp lại trong phase file)

Thiết kế báo cáo (metrics, viz, layout) là các tài liệu analytics-handbook chuẩn — phase file này chỉ điều phối THỰC THI:

| Lớp | Tài liệu | Nội dung |
|---|---|---|
| Domain (semantic) | `docs/analytics-handbook/domains/finance.md` § Cashflow | Metrics CF1-CF4, dimensions, grain, sources, recon anchor |
| Playbook | `docs/analytics-handbook/playbooks/finance_cashflow.md` | Audience, câu hỏi nghiệp vụ, filters, action triggers, reading flow |
| Design spec | `docs/analytics-handbook/designs/finance_cashflow.md` | Bộ viz: scorecard · waterfall · pivot table · line+forecast · combo · horizontal bar; tokens, composition, anti-patterns |
| Blueprint (deploy) | `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` | SQL per card + metabase-viz JSON + metabase-pos; deployable qua deploy_from_markdown.js |

Metric canonical (khớp cả 4 tài liệu): `cash_balance` (số dư quỹ), `cash_inflow` (thu), `cash_outflow` (chi), `net_cash_flow` (ròng). **RULE: mọi metric thu/chi luôn `WHERE NOT is_internal_transfer`.**

## Dependencies (phải xong trước)
1. **Phase 01** — cash data (111/112) ingested vào production account_ledger (đang blocked: full-ledger export). Không có data thì mart rỗng.
2. **Phase 02** — `fact_account_balance_monthly` materialized (số dư quỹ chính xác incl TK 0-phát-sinh). Fallback: blueprint có sẵn SQL comment dùng `MAX(running_balance)` từ `fact_cash_movement` nếu chưa có.
3. `fact_cash_movement` + `dim_gl_account` — DONE (Phase 02).

## Thực thi (HOW)
1. Đảm bảo marts materialized ra parquet rolling location (`dbt build --select fact_cash_movement dim_gl_account fact_account_balance_monthly`). Node mới → restart `data_platform` (manifest pre-parsed).
2. **Bootstrap serving views** — `scripts/provisioning/bootstrap_serving_views.py` với **Metabase STOPPED trước** (memory: PID 0 lock storm nếu không). Verify view `main_marts.fact_cash_movement` tồn tại.
3. **Field_id**: blueprint để placeholder `field_id: 9999` cho filter `period_month` — thay bằng field_id thật lấy từ `/api/table/:id/query_metadata` SAU khi sync schema (memory: verify field_id, đừng copy). Metabase v0.60.2.
4. **Deploy**: `node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow.md`. CHỈ deploy qua skill này (memory: không patch tay).
5. **Recon gate**: số liệu dashboard T6/2026 phải khớp: thu 464.4M, chi 434.0M, ròng +30.4M, chuyển nội bộ 299M đã loại, số dư cuối kỳ 164.5M.

## Điểm cần verify khi deploy (từ blueprint agent)
- Metabase có hỗ trợ `waterfall` type trên v0.60.2 không (METABASE_VIZ_CATALOG) — nếu không, fallback diverging horizontal bar (blueprint đã note).
- `pivot_table.column_split` key đúng trên v0.60.2 — nếu sai, pivot render thành bảng thường, chỉnh tay.
- `signed_amount` dấu: + cho inflow, − cho outflow (verify trước khi deploy waterfall; sai thì negate trong movements CTE).
- Metabase serving TZ = ICT — KHÔNG cộng offset thủ công trong WHERE (TIMESTAMPTZ auto-convert).

## Rủi ro / rollback
- Rollback = xóa dashboard qua `/manage-metabase-resources`; marts giữ nguyên.
- Metabase phải stop trước bootstrap (memory) — không thì lock.

## Câu hỏi chưa chốt
1. `cashflow_line` taxonomy cần finance sign-off (hiện prefix-derived, provisional) — trước khi coi là báo cáo quản trị chính thức.
2. Tách 111 vs 112 trên scorecard theo ý CFO? (chưa xác nhận)
3. Budget columns (pivot) + forecast dashed line = Phase 04 extension trên CÙNG dashboard (cần `fact_cashflow_budget`) — blueprint đã tách "Phase-04 extensions" non-deployable.
