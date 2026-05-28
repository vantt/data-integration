# Project Changelog

> Record of significant changes, features, and fixes

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
- `docs/architecture/discount-classification.md` — taxonomy, logic, report examples

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
- `transform_batch_nightly_job` — includes team_config asset

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
