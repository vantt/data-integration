# Project Changelog

> Record of significant changes, features, and fixes

## [2026-08-05] CRM — Suggestion Settings panel (P07)

**Summary:** NV thường nhầm "Bỏ qua 1 thẻ" với "tắt hẳn loại gợi ý cho khách này" — không có nơi
tường minh để tắt/mở từng loại cơ hội (`action_type`) riêng cho 1 khách, có ngày hết hạn tự chọn.
Thêm tab "Cài đặt gợi ý" (P07) trên Customer 360, đọc/viết `crm_action_dismissal` trực tiếp — không
cần action đang active (pre-emptive suppression).

**⚠️ Behaviour change (D4):** `crm_action_dismissal` giờ khoá theo `(party_id, action_type,
source_mart)` thay vì `(party_id, action_type)` — dismiss nhanh 1 thẻ SKU-level `REORDER_NUDGE`
**không còn** tự động ẩn luôn `REORDER_NUDGE` customer-level của khách đó (và ngược lại). Trước đây 2
tầng này bị gộp chung do thiếu discriminator; giờ tách độc lập — đúng ý nhưng là thay đổi hành vi
thật, cần báo CS/Sales trước khi deploy.

**3 cơ chế suppression hiện có, không cái nào bị đổi ý nghĩa:**
- "Bỏ qua" trên thẻ (`crm_action_state`, episode-scoped) — vẫn dùng chung bảng `crm_action_dismissal`
  làm cross-episode memory, giờ chỉ đổi ở việc ghi thêm `source_mart`.
- "🚫 Đừng gọi nữa" (`crm_activity_log.outcome_reason='do_not_contact'`) — hoàn toàn không đụng tới.
- Cờ tắt toàn hệ thống (`seed_action_scenario_registry.enabled`) — không đụng tới, panel chỉ đọc.

**Files (7 phase, xem `plans/260805-1216-crm-worklist-suppression-settings-panel/`):**
- `transformation/models/marts/customer/dim_action_scenario_registry.sql` — passthrough mart mới,
  cho phép reverse-ETL đọc dbt seed (seed không tự sinh rolling folder).
- `crm/sync/{cache_schema,duckdb_reader,sqlite_upsert,reverse_etl_warehouse_to_crm}.py` —
  sync `wh_action_scenario_registry` (13 dòng, 7 customer/6 sku).
- `crm/migrations/0046_action_dismissal_source_mart.{up,down}.sql` — thêm `source_mart`, PK 3 cột,
  backfill row-expansion (1 dòng cũ → 2 dòng, 1/mart — giữ nguyên ngữ nghĩa "tắt everywhere" cũ).
- `crm/src/adapters/outbound/sqlite/action_state_repository.py` — `suppress()`/`unsuppress()`/
  `list_dismissals_for_party()` mới; `_resolve_party_and_action_type()` trả 3-tuple.
- `crm/src/application/suggestion_settings_service.py` — mới, validate catalog + convert ICT date → UTC.
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_suggestion_settings.py` +
  `fragments/c360_suggestion_settings_panel.html` — panel P07 mới.
- `crm/docs/ui-spec/panels/P07-suggestion-settings-panel.md` — spec, `ui-spec validate` xanh.

**Tests:** 1196/1197 CRM suite pass (1 skip, pre-existing) — bao gồm E1/E2 (per-mart suppression
độc lập, assertion quan trọng nhất của cả feature), R1-R9 (route level), U1-U12 (repository/service).

**Deploy order:** dbt (Phase 01) → reverse-ETL (Phase 02) → CRM app (03+04+05+06 cùng lúc — 05 một
mình trên schema cũ sẽ làm worklist trống âm thầm, không phải crash).

---

## [2026-05-27] Discount Nature Classification

**Summary:** Chuẩn hóa dữ liệu discount để report retail metrics không bị contaminate bởi hidden wholesale orders. Thêm `discount_nature` và `discount_rate` vào pipeline thay vì reclassify customer.

**Vấn đề:** `discount_manual` = 74.5% volume (~100 tỷ), 93% empty reason. `discount_rate` có trong staging nhưng bị drop trước mart — không có signal phân biệt "giảm 5%" vs "giảm 70%". Khách sĩ ẩn (được sales confirm là Retail) đang làm lệch avg discount, ARPU của kênh retail.

**Giải pháp:** Classify mỗi discount item theo `discount_nature` (reason text + rate) thay vì reclassify customer.

**Taxonomy (10 loại):** `voucher_promotional`, `bundle`, `sampling_gift`, `wholesale_explicit`, `overseas`, `campaign`, `employee_internal`, `negotiated_micro`, `negotiated_standard`, `negotiated_deep`

**Distribution thực tế:**
| discount_nature | Orders | disc_M |
|---|---|---|
| negotiated_deep (≥40% rate, no reason) | 2,016 | 31.1 tỷ |
| negotiated_standard | 1,852 | 10.4 tỷ |
| voucher_promotional | 1,648 | 1.5 tỷ |

**Files:**
- `transformation/models/marts/sales/fact_order_costs.sql` — thêm `discount_rate`, `discount_nature`
- `transformation/models/marts/sales/fact_orders.sql` — thêm `max_discount_rate`, `primary_discount_nature`
- `transformation/models/marts/schema.yml` — docs + `accepted_values` tests
- `docs/architecture/order-pl/discount-classification.md` — taxonomy, logic, report examples

**Tests:** 22/22 PASS (bao gồm 2 `accepted_values` tests mới)

**Status:** Production — deployed via `dbt build` trong Docker, Dagster reloaded

---

## [2026-04-19] fact_order_economics — Validation Complete

**Summary:** Unified per-order P&L model validation finished. Phase 6 (voucher coverage) and Phase 7 (E2E verification) completed.

**Validation Results:**

| Metric | Value |
|--------|-------|
| MISA→Sapo voucher match | 92.7% (319/344) |
| COGS timing lag | avg 3.7 days |
| Gross margin (orders with COGS) | 55.4% |
| Row count match | 2,813 = fact_orders |

**Schema Updates:**
- Added `not_null` test for `net_revenue`
- Documented 5 missing columns: `status`, `shopee_infra_fee`, `shopee_voucher_xtra_fee`, `shopee_taxes`, `has_shopee_fees`

**Files:**
- `transformation/models/marts/schema.yml` — tests + docs
- `plans/260411-fact-order-economics/plan.md` — complete plan
- `plans/reports/verify-260419-fact-order-economics.md` — E2E report

**Status:** Production-ready

---

## [2026-04-17] Team Configuration — Google Sheets Integration

**Summary:** New team management system via Google Sheets for sales team definitions and member assignments with SCD2 history tracking.

**Components:**

| Layer | File | Purpose |
|-------|------|---------|
| Ingestion | `ingestion/src/gsheet_team_config.py` | XLSX download, validation, parquet output |
| Dagster | `orchestration/assets/sheets_assets.py` | `sheets_team_config_asset` |
| dbt Staging | `transformation/models/staging/stg_teams.sql` | Team definitions with surrogate key |
| dbt Staging | `transformation/models/staging/stg_team_members.sql` | Member assignments with SCD2 |
| Source | `transformation/models/sources.yml` | `teams_raw`, `team_members_raw` |

**Google Sheet Structure:**

- **teams tab:** `team_code`, `team_name`, `revenue_type` (member/platform/channel_name), `revenue_filter`, `leader_email`, `description`
- **team_members tab:** `staff_email`, `team_code`, `effective_from`, `effective_to` (SCD2)

**Revenue Attribution Models:**

| `revenue_type` | `revenue_filter` | Logic |
|----------------|------------------|-------|
| `member` | (empty) | Sum revenue of team members' orders |
| `platform` | `Shopee,Lazada` | Sum revenue from specified platforms |
| `channel_name` | `SOC,WEB` | Sum revenue from specified channels |

**Jobs Updated:**
- `ingest_sheets_sync_job` — includes team_config asset
- `pipeline_batch_nightly_job` — includes team_config asset

**Env Var:** `SOURCES__SPREADSHEET_URL__TEAM_CONFIG`

**Docs:** `docs/context/team-management.md`

---

## [2026-04-16] Ingestion Health Monitor — Dashboard Fix

**Summary:** Dashboard 40 showed blank values for most cards due to 3 cascading bugs.

**Root Causes & Fixes:**

| Bug | Impact | Fix |
|-----|--------|-----|
| Missing `return` in 5 batch runners | `LoadInfo` always `None` → health logger recorded all runs as "skipped" instead of "success" | Added `return` before `run_pipeline()` in `run_orders_batch.py`, `run_customers_batch.py`, `run_products_batch.py`, `run_history_log.py`, `run_accounts_batch.py` |
| Wrong `asset_key` in drift cards | Blueprint used `recon/recon_*` prefix but code uses `recon/*` | Fixed 4 drift card queries in `ingestion_health.md` blueprint |
| SQL cross-join returns empty on no-data | CTE cross-join produces 0 rows when asset never ran | Rewrote to scalar subqueries + COALESCE fallback (9999h freshness, 999 drift) |

**Deploy infra fix:** Blueprint parser now reads `> **Database:** \`Name\`` from markdown header, overriding `METABASE_DB_NAME` env var. Prevents deploying cards to wrong database when `.env.local` has a different default.

**Files:** `ingestion/run_*_batch.py` (5), `docs/analytics-handbook/blueprints/ingestion_health.md`, `.skills/metabase-automation/lib/markdown_parser.js`, `.skills/metabase-automation/scripts/deploy_from_markdown.js`

**Commit:** `b0f6678`

---

## [2026-04-16] Docker Volume Restructure

**Summary:** Reorganized Docker volume mounts from flat `/app/` to grouped `/app/var/` for data directories.

**Changes:**

| Before | After | Type |
|--------|-------|------|
| `/app/data_lake` | `/app/var/data_lake` | Data dir |
| `/app/.dagster_home` | `/app/var/dagster_home` | Data dir |
| `/app/logs` | `/app/var/logs` | Data dir |
| `/app/backups` | `/app/var/backups` | Data dir |
| (not mounted) | `/app/var/input_source` | Data dir (NEW) |
| `/app/transformation`, `/app/ingestion`, `/app/orchestration`, `/app/scripts` | (unchanged) | Code dirs |

**Local Host Bind:**
```
app_data/data_lake       →  /app/var/data_lake
app_data/dagster_home    →  /app/var/dagster_home
app_data/logs            →  /app/var/logs
app_data/backups         →  /app/var/backups
app_data/input_source    →  /app/var/input_source
```

**Env Var Updates:**

```bash
# .env.docker now uses:
DBT_DATA_LAKE_PATH=/app/var/data_lake
DBT_EXPORT_PATH=/app/var/data_lake/export/marts
DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/var/data_lake
BACKUP_ROOT=/app/var/backups
DAGSTER_HOME=/app/var/dagster_home
SHOPEE_INPUT_DIR=/app/var/input_source/shopee
```

**Critical Impact:**

- **Serving views bake absolute paths** — After mount changes, must regenerate:
  ```bash
  docker compose down
  docker compose up -d data_platform
  docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
  docker compose up -d metabase
  ```

**Benefits:**

1. Clear separation: code at `/app/`, data at `/app/var/`
2. Simpler volume management in docker-compose.yml
3. Easier to identify data vs code directories at glance
4. File drop input_source now mounted (enables auto-trigger sensors)

**Documentation Updated:**

- `docs/architecture/overview.md` — Docker deployment topology
- `docs/operations/deployment.md` — Volume mount references + serving views regeneration
- `.skills/data-pipeline/SKILL.md` — Docker volume convention + critical serving views note

---

## Future Changelog Entries

Add new entries in reverse chronological order (newest first) using this template:

```markdown
## [YYYY-MM-DD] Feature/Fix Title

**Summary:** One-line description

**Changes:**
- List of changes
- Document any breaking changes

**Impact:**
- Documentation files updated
- Code files modified
```
