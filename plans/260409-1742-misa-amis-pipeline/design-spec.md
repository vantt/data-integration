# MISA AMIS Sales Ledger Pipeline — Design Specification

**Companion to:** `plan.md`
**Source doc:** `docs/misa-amis/data-source-description.md`
**Precedent:** `plans/260409-1710-shopee-pipeline/design-spec.md` (single-sheet variant of the same pattern)

## 1. Architectural placement

```
app_data/input_source/misa-amis/*.xlsx
                │
                ▼ (Dagster reactive sensor: file mtime change)
     ┌────────────────────────────────────┐
     │ ingestion/run_misa_sales_file_drop │  ← pandas + openpyxl, NO dlt SDK
     │   .py                              │    (mirrors gsheet_marketing_spend
     └────────────┬───────────────────────┘     + run_shopee_income_file_drop)
                  │ writes 1 parquet table
                  ▼
  data_lake/misa_raw/
    └── sales_lines/ingest_method=file_drop/year=*/month=*/*.parquet
                  │
                  ▼
  dbt src_ (view + dedup on (voucher_no, line_no))
    └── src_misa_sales_lines
                  │
                  ▼
  dbt stg_ (view, type casting, channel enrichment)
    └── stg_misa_sales_lines
                  │
                  ▼
  dbt fact_ (external parquet, rolling location)
    └── int_misa_sales_lines       ← margin, net revenue, channel joined
                  │
                  ▼
  data_lake/serving/olap.duckdb (Rolling Self-Refresh Views via
                                  generate_serving_db.py)
                  │
                  ▼
            Metabase queries (margin dashboards, cost analysis)
```

**Why Pattern C (file drop), not Pattern A (API):**

- MISA Open API exists (see `docs/misa-amis/README.md`) but requires paid-tier MISA plan + OAuth setup + explicit data-mapping effort; not in P0 scope.
- Excel export is human-triggered from MISA AMIS UI, cadence manual/weekly.
- Shopee pipeline already establishes the file-drop + reactive-sensor infrastructure; MISA reuses it verbatim.
- `dlt` has no verified source for local Excel.

**Why single-entity (no grain split) unlike Shopee:**

- Shopee's `Doanh thu` sheet mixes Order rows and Sku rows → needed a split on `row_grain`.
- MISA's `Sổ chi tiết bán hàng` is pre-flattened to one row per invoice line. No split required.

## 2. Ingestion layer

### 2.1 Entry point

**File:** `ingestion/run_misa_sales_file_drop.py`

```python
def run(argv=None, file_path: str | None = None):
    """
    Parse one MISA sales-ledger Excel file and emit 1 parquet table.
    If file_path is None, process every *.xlsx under INPUT_DIR
    (reactive sensor drives this).
    """
```

CLI args (for manual runs):
- `--file PATH` — process a single file (default: glob the drop zone)
- `--full-refresh-touched-months` — **explicit opt-in** flag for known-full-snapshot drops. Parser determines `(year, month)` partitions touched by the file, deletes ALL existing parquet files in those partitions, then writes the new ones. Use this only when the analyst confirms the drop is a complete snapshot for those months. Default: OFF (append-only). See § 2.7 for rationale.
- `--full-refresh` — drop & rebuild dlt state (rarely needed for file-drop sources)

### 2.2 Parser module

**File:** `ingestion/src/misa_amis/sales_ledger_parser.py`

Responsibilities:

1. **Discover files:** `glob("app_data/input_source/misa-amis/*.xlsx")` — exclude `_archive/` subdir (only fresh drops).
2. **No filename regex.** Rely on data-side truth via `posting_date`. Keep `source_file = os.path.basename(file_path)` as lineage metadata only. Even though the filename contains a `DD.MM.YYYY-DD.MM.YYYY` window, do NOT parse it — overlapping re-exports happen and the posting date is authoritative.
3. **Load workbook:**
   ```python
   import warnings; warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
   df = pd.read_excel(
       file_path,
       sheet_name=0,          # single sheet; name "SỔ CHI TIẾT BÁN HÀNG" is fixed
       header=3,              # rows 0-2 are banner/spacer
       engine="openpyxl",
   )
   df.columns = df.columns.str.strip()  # kills "Tên hàng trên chứng từ " trailing space
   ```
4. **Drop totals footer:**
   ```python
   df = df[df["Số chứng từ"].notna()].reset_index(drop=True)
   ```
   This removes the `"Tổng cộng"` row and any other blank separators. **Capture the totals BEFORE dropping** as a load-completeness checksum:
   ```python
   totals_row = df[df["Ngày hạch toán"].astype(str).str.strip().str.lower() == "tổng cộng"]
   cogs_total_claimed = int(totals_row["Giá vốn"].iloc[0]) if not totals_row.empty else None
   ```
   Log it and attach to the ingestion-asset metadata for Phase 6 reconciliation.
5. **Rename VN → snake_case** via a **static dict** held in the parser module (single source of truth for renames — see `data-source-description.md` § 8 for the full mapping).
6. **Synthesize `line_no`:**
   ```python
   df["line_no"] = df.groupby("voucher_no").cumcount() + 1
   ```
   Applied AFTER the totals-row filter and BEFORE any further dedup.
7. **Type coercion:**
   - Dates (`posting_date`, `voucher_date`, `invoice_date`) → `pd.to_datetime(..., errors="coerce").dt.date`
   - `invoice_no` (loaded as float like `1.0`) → `f"{int(x):08d}"` zero-padded string
   - Accounting codes (`debit_account`, `credit_account`, `discount_account`, `cogs_account`) → cast float → int → str: `str(int(x))` (preserves `"131"`, `"51111"`, allows nulls as `None`)
   - Money columns (`revenue_gross`, `discount_amount`, `total_payment`, `cogs_amount`) → `Int64` (nullable BIGINT)
   - `quantity` → `Int64`
   - `unit_price` → `float64` (DuckDB will cast to DECIMAL(18,4) downstream)
   - `is_promo_line`: `df["is_promo_line"] = df["is_promo_line"].notna()` (bool — `✓` → True, NaN → False)
8. **Inject ingestion metadata** on every row:
   - `ingest_method = "file_drop"`
   - `source_file = os.path.basename(file_path)`
   - `ingested_at = datetime.now(timezone.utc)` (TIMESTAMPTZ — see memory rule on TIMESTAMPTZ)
   - `year`, `month` (partition keys, derived from `posting_date`)
9. **Write 1 parquet table per (year, month) partition with UNIQUE filename per ingest** — append-only, never overwrite:
   ```
   {DBT_DATA_LAKE_PATH}/misa_raw/sales_lines/ingest_method=file_drop/year={YYYY}/month={MM}/misa_sales_{YYYY}-{MM}_{ingested_at_ts}.parquet
   ```
   where `ingested_at_ts = YYYYMMDDTHHMMSSZ` (UTC). Each ingest **adds** a new parquet file in the partition; existing files are **never rewritten**. Cross-month rows from the same drop land in separate files automatically.

   **Why unique filename, not fixed name:**
   - Parquet is immutable columnar storage — no in-place update.
   - If we used a fixed name (e.g. `misa_sales_2026-01.parquet`), every re-ingest would **overwrite** and destroy prior `ingested_at` lineage, breaking dbt src_ dedup (`ORDER BY ingested_at DESC` needs multiple versions to rank).
   - The `gsheet_marketing_spend` precedent uses a fixed name because a Google Sheet re-read IS a full snapshot of truth for that window. MISA drops are NOT — they may represent partial windows, corrected re-exports, or overlapping periods. Append-only preserves the audit trail.
   - Dedup happens at **read time** in dbt src_ (§ 3.2), not at write time.

### 2.3 Why partition by posting month, not filename window

A single file can span multiple accounting months (the sample covers Jan–Apr). Orders posted on `2026-01-31` and `2026-02-01` in the same drop must land in different `year=/month=` dirs so dbt's `union_by_name=true` external read pulls correct slices and future incremental pruning works.

### 2.4 Config (no secrets)

Add to `ingestion/.dlt/config.toml`:

```toml
[sources.misa_amis]
input_dir = "app_data/input_source/misa-amis"
file_pattern = "So_chi_tiet_ban_hang_*.xlsx"
```

Read via `dlt.config[...]` or plain `os.environ` — keep it simple, match `gsheet_marketing_spend` / Shopee style.

### 2.5 Post-ingest archive

On successful parquet write, **move** (not copy) the source `.xlsx` to:

```
app_data/input_source/misa-amis/_archive/{posting_month}/{ingested_at_ts}__{original_filename}
```

- `posting_month` = `YYYY-MM` derived from `MAX(posting_date)` in the file.
- `ingested_at_ts` = `YYYYMMDDHHMMSS` UTC.
- Atomic: `shutil.move`; if parquet write fails earlier, source stays in drop zone for retry.
- `_archive/` excluded from parser glob (§ 2.2 step 1).
- Rollback: manually move archived file back to drop zone → idempotent dedup in dbt handles re-ingest.

### 2.6 Idempotency & write semantics

- **Write-time**: parquet filename carries `ingested_at_ts` → every ingest writes a brand-new file. Existing files are untouched.
- **Read-time dedup** (dbt src_ view, § 3.2): `ROW_NUMBER() OVER (PARTITION BY voucher_no, line_no ORDER BY ingested_at DESC) = 1` picks the most recent version of every line across all parquet files in the partition.
- **Effective semantics**:
  - Row newly added in a later drop → appears in fact.
  - Row edited in a later drop (same `(voucher_no, line_no)`, different values) → newer `ingested_at` wins, older version silently shadowed.
  - Row physically deleted from MISA → **NOT reflected** — old row still lives in old parquet file and nothing in the new file tells dedup to drop it. See § 2.7 Deletion semantics.
- **Files auto-archived** (`.xlsx` moved to `_archive/`) on success → no accidental re-processing of the same input file.
- **Corrected re-export** (analyst drops a fix) → parser writes a new parquet with fresh `ingested_at`, dbt src_ picks it up on next build, idempotent.
- **Force re-process** (manual un-archive) → another parquet added; since business key is stable and dedup is by `ingested_at DESC`, no duplication at the fact layer.

### 2.7 Deletion semantics & drop-scope policy (LOCKED: discrete-drops mode)

**Drop scope assumption (confirmed by user 2026-04-09):** MISA exports are **discrete / non-overlapping windows** dropped ad-hoc, NOT periodic full snapshots from the start of the fiscal period. Examples:
- Drop A: Feb 1–28 (regular monthly export)
- Drop B: Feb 15–20 (a corrective re-export covering only the days that were fixed)
- Drop C: Jan 1 → today (occasional manual full refresh, rare)

This assumption **forces the design choice**: any "automatic full-refresh by partition" would silently destroy data. If Drop B (5 corrective rows) wiped Feb partition before writing, the 145 untouched February vouchers from Drop A would be lost. **Append-only is the only safe pattern.**

**Behavior under append-only with discrete drops:**

| Scenario | Pattern handles correctly? |
|---|---|
| Drop B re-ingests 5 voucher with newer values; Drop A's other 145 voucher untouched | ✅ Drop B's `ingested_at` is newer → 5 fixes win; 145 originals from Drop A still present in `src_` |
| Drop A and Drop C overlap on a row (different values) | ✅ Whichever has newer `ingested_at` wins; idempotent |
| Drop A and Drop C overlap on a row (same values) | ✅ Dedup keeps one copy; no fact duplication |
| MISA cancels a voucher between Drop A and Drop B; Drop B's window covers it but the row is absent | ❌ Parser cannot distinguish "row absent because deleted" from "row absent because outside this drop's effective scope" → row leaks into fact |

**Why deletion detection (tombstone) is impractical here:** to diff "what was deleted", parser would need to know each drop's **authoritative scope** — i.e. "this drop is the source of truth for date range X..Y, so any row in X..Y not in this drop is deleted". With discrete ad-hoc drops there is no reliable scope signal: filename window may overlap, undershoot, or overshoot the actual export. Tombstone logic would require either (a) trusting filename windows (banned by § 2.2 step 2) or (b) an explicit `--scope-start --scope-end` CLI flag the analyst must pass per drop (operational burden).

**P0 decision (LOCKED):**

1. **Append-only forever for normal drops.** Each `.xlsx` lands as a new parquet with unique `ingested_at_ts`. No automatic deletion.
2. **Manual escape hatch for known-full-refresh drops.** When the analyst intentionally exports a complete snapshot (e.g. `01.01.2026..hôm_nay`) and wants it to override everything, they invoke the parser with an explicit flag `--full-refresh-touched-months`. Parser then **deletes all parquet files in the touched `year=/month=` partitions before writing**. This is opt-in, never inferred from filename. **Frequency target: ≤ 1×/quarter.** Guardrail: parser **warns and requires `--force` confirmation** if the drop covers **< 7 calendar days** of `posting_date` range (likely a small corrective drop, not a full snapshot — running full-refresh with it would wipe the partition).
3. **Accept silent deletion drift** for all non-flagged drops. Document the limitation. If a stakeholder flags drift, run #2 as a one-shot fix.
4. **Reactive sensor always runs in append-only mode.** `--full-refresh-touched-months` is CLI-only, never triggered by sensor. This prevents a small file drop from accidentally wiping a partition via automation.
5. **Parquet GC by age.** Old parquet files are garbage-collected based on file age (mtime), not version count. Policy: files older than **30 days** are eligible for deletion, provided at least 1 newer file exists in the same partition. Implemented as a Dagster GC asset or ad-hoc script at P1; P0 is manual cleanup.

**Why TT200 makes this acceptable**: Vietnamese accounting convention treats posted vouchers as immutable. MISA users cancel via reversing vouchers (chứng từ điều chỉnh ngược dấu), not by physical deletion. The "row truly disappeared" event is extremely rare in this source. The escape hatch covers the edge cases without bloating the happy path.

## 3. dbt transformation layer

### 3.1 Source registration

Append to `transformation/models/sources.yml`:

```yaml
- name: misa_raw
  schema: main
  meta:
    external_location: "read_parquet('{{ env_var('DBT_DATA_LAKE_PATH') }}/misa_raw/{name}/ingest_method=*/**/*.parquet', hive_partitioning=1, union_by_name=true)"
  tables:
    - name: sales_lines
      description: "MISA AMIS Sổ chi tiết bán hàng — 1 row per invoice line, includes COGS (giá vốn)"
```

### 3.2 src_ model (view + dedup — NO 7-day lookback)

> **Design note (same as Shopee resolution D2):** File-drop sources use view materialization with full-scan dedup. The 7-day lookback pattern protects against late updates in API feeds and does not apply to accounting snapshots. MISA's ledger export is closed-period data.

**`src_misa_sales_lines.sql`** — materialize `view`
- Business key: `(voucher_no, line_no)`
- Dedup: `ROW_NUMBER() OVER (PARTITION BY voucher_no, line_no ORDER BY ingested_at DESC) = 1`
- No incremental config, no lookback.
- Tag: `['src', 'misa']`

```sql
{{ config(materialized='view', tags=['src','misa']) }}

WITH ranked AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY voucher_no, line_no
      ORDER BY ingested_at DESC
    ) AS rn
  FROM {{ source('misa_raw', 'sales_lines') }}
)
SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1
```

### 3.3 stg_ model (type cleanup + channel enrichment, view)

**`stg_misa_sales_lines.sql`** — view over `src_misa_sales_lines`

- Final casts: dates → `DATE`; money → `BIGINT`; `unit_price` → `DECIMAL(18,4)`.
- Coalesce null `channel_code` → `'UNKNOWN'`.
- Left join `seeds/ref_misa_channel_codes.csv` for friendly channel names.
- Derived columns:
  - `revenue_net_of_discount = revenue_gross - discount_amount`
  - `gross_profit = (revenue_gross - discount_amount) - cogs_amount`
  - `gross_margin_pct = CASE WHEN (revenue_gross - discount_amount) = 0 THEN NULL ELSE gross_profit / (revenue_gross - discount_amount) END`
  - `is_promo_line_int = CAST(is_promo_line AS INT)` (for SUM-based counts in BI)
  - `voucher_source_hint` = CASE-WHEN pattern match on `voucher_no`:
    - `voucher_no LIKE 'SON%'` → `'SAPO_DEALER'`
    - `voucher_no ~ '^2[0-9]{5}[A-Z0-9]{14}$'` → `'SHOPEE'`
    - `voucher_no ~ '^58[0-9]{11}$'` → `'AEON'`
    - else → `'OTHER'`
    (lightweight classification; can be validated by downstream joins later)

### 3.4 Seed: channel code map

**File:** `transformation/seeds/ref_misa_channel_codes.csv`

```csv
channel_code,channel_name,channel_group
DAILY,Đại lý,B2B_DEALER
ECOM,E-commerce,MARKETPLACE
CS,Chăm sóc khách hàng,DIRECT_B2C
KHAC,Khác,OTHER
UNKNOWN,Chưa phân loại,UNKNOWN
```

Values for `CS`/`KHAC` are tentative — see open question #2; update after accounting confirms.

Configure in `dbt_project.yml` under `seeds.transformation.ref_misa_channel_codes`:
```yaml
ref_misa_channel_codes:
  +column_types:
    channel_code: varchar
    channel_name: varchar
    channel_group: varchar
```

### 3.5 Intermediate model (enrichment layer — NOT primary fact)

> **Design note (locked 2026-04-10):** This model is `int_` (intermediate) because MISA COGS data is enrichment for Sapo orders, not a primary business event. All orders already exist in Sapo `fact_orders`. MISA adds cost-of-goods-sold per line. `int_` prefix signals this clearly. Rolling location is applied pragmatically so P0 Metabase queries work before the P1 unified `fact_order_economics` is built.

#### `int_misa_sales_lines.sql` (one row per invoice-line)

```sql
{{ config(
    tags=['int', 'misa'],
    materialized='table',
    location="{{ get_rolling_location() }}"
) }}

SELECT
    {{ dbt_utils.generate_surrogate_key(['voucher_no','line_no']) }} AS misa_sales_line_sk,

    -- business keys
    voucher_no,
    line_no,

    -- temporal
    posting_date,
    voucher_date,
    invoice_date,
    invoice_no,

    -- product
    product_code,
    product_name,
    product_name_on_document,
    unit_of_measure,
    is_promo_line,

    -- customer
    customer_code,
    customer_name,

    -- quantity & amounts
    quantity,
    unit_price,
    revenue_gross,
    discount_amount,
    total_payment,
    cogs_amount,
    revenue_net_of_discount,
    gross_profit,
    gross_margin_pct,

    -- accounting accounts
    debit_account,
    credit_account,
    discount_account,
    cogs_account,

    -- channel & salesperson
    channel_code,
    channel_name,
    channel_group,
    voucher_source_hint,
    salesperson_name,

    -- raw description (free text)
    description,

    -- lineage
    source_file,
    ingested_at
FROM {{ ref('stg_misa_sales_lines') }}
```

**No dim models in P0.** Products, customers, salespeople, channels can graduate to `dim_*` tables only when downstream analytics demand it.

### 3.6 Tests (schema.yml additions)

```yaml
- name: int_misa_sales_lines
  columns:
    - name: misa_sales_line_sk
      tests: [unique, not_null]
    - name: voucher_no
      tests: [not_null]
    - name: line_no
      tests: [not_null]
    - name: posting_date
      tests: [not_null]
    - name: cogs_amount
      tests: [not_null]
    - name: channel_code
      tests:
        - accepted_values:
            values: ['DAILY','ECOM','CS','KHAC','UNKNOWN']
  tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns: [voucher_no, line_no]
```

### 3.7 Pre-create rolling dir

Append `int_misa_sales_lines` to `scripts/ensure_dbt_directories.py` (same edit location as Shopee plan; coordinate to avoid merge conflicts).

## 4. Serving layer

No new code. `scripts/provisioning/generate_serving_db.py` auto-discovers any new `rolling/{model}/` folder. Verification only:

```bash
python scripts/provisioning/generate_serving_db.py
duckdb data_lake/serving/olap.duckdb -c "SELECT COUNT(*), SUM(cogs_amount), SUM(revenue_gross) FROM int_misa_sales_lines"
```

**Critical rule already covered:** `int_` model includes `location="{{ get_rolling_location() }}"` — pragmatic exception to the convention that only `dim_/fact_` use rolling. This ensures P0 Metabase access before P1 `fact_order_economics` exists.

## 5. Dagster orchestration

### 5.1 New module

**File:** `orchestration/assets/misa_amis_assets.py` (copy shape from `shopee_assets.py` / `sheets_assets.py`)

```python
@asset(
    group_name="misa_amis_ingestion",
    key_prefix=["misa_amis"],
    op_tags={"dagster/concurrency_key": "duckdb_lock"},
)
def misa_sales_file_drop_asset(context):
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        run_misa_sales_file_drop.run(argv=[])
    finally:
        os.chdir(cwd)
    return Output("OK", metadata={"status": "Success"})
```

### 5.2 Reactive sensor (mirror sheets / Shopee sensor)

Add `misa_sales_ledger_sensor` watching file mtime in `app_data/input_source/misa-amis/` (exclude `_archive/`). Pattern: `.skills/data-pipeline/templates/dagster-reactive-sensor-template.py` + existing sheets sensor (`48be670`).

Cascade: `misa_sales_file_drop_asset → dbt_assets (src_/stg_/fact_ selection) → serving_db_asset`

### 5.3 Job registration

Add to `orchestration/definitions.py`:
- Include `misa_amis_assets` in `load_assets_from_modules`.
- Inject upstream keys in `DagsterDbtTranslator.get_upstream_asset_keys()` so `src_misa_sales_lines` depends on `misa_sales_file_drop_asset` (critical rule #10 in SKILL.md).
- Add to `sapo_nightly_reconciliation_job` selection for nightly catchup of any file dropped outside business hours.

## 6. Verification plan (Phase 6)

1. **Unit parser:**
   ```bash
   python ingestion/run_misa_sales_file_drop.py \
     --file app_data/input_source/misa-amis/So_chi_tiet_ban_hang_01.01.2026-08.04.2026.xlsx
   ```
2. **Row-count audit:**
   - `SELECT COUNT(*) FROM int_misa_sales_lines` → **472**
   - `SELECT COUNT(DISTINCT voucher_no) FROM int_misa_sales_lines` → **344**
3. **Reconciliation vs audit baseline (data-source-description.md § 9):**
   - `SELECT SUM(revenue_gross) FROM int_misa_sales_lines WHERE is_promo_line = FALSE` → **5,176,752,390 VND**
   - `SELECT SUM(cogs_amount) FROM int_misa_sales_lines` → must match the captured `Tổng cộng` footer (logged by the parser).
   - `SELECT SUM(cogs_amount) FROM int_misa_sales_lines WHERE is_promo_line = TRUE` → **56,729,582 VND**
4. **Uniqueness:** `SELECT voucher_no, line_no, COUNT(*) FROM int_misa_sales_lines GROUP BY 1,2 HAVING COUNT(*) > 1` → **empty**
5. **Channel coverage:**
   ```sql
   SELECT channel_code, COUNT(*) FROM int_misa_sales_lines GROUP BY 1
   -- expect: ECOM 212, DAILY 186, CS 60, KHAC 6, UNKNOWN 8
   ```
6. **Voucher-pattern classification sanity:**
   ```sql
   SELECT voucher_source_hint, COUNT(*) FROM int_misa_sales_lines GROUP BY 1
   ```
   Expect a plausible breakdown (Sapo dealer + Shopee + AEON + other).
7. **Idempotency:** rerun ingestion; `SELECT COUNT(*)` unchanged, no new `ingested_at` timestamps leaking into the fact.
8. **Sensor trigger:** drop a fresh `.xlsx` (or copy a test file) into `misa-amis/`; confirm Dagster run kicks off within the sensor interval.
9. **Metabase probe:** ad-hoc question — top 10 products by gross profit over the window:
   ```sql
   SELECT product_code, product_name,
          SUM(revenue_net_of_discount) AS net_rev,
          SUM(cogs_amount) AS cogs,
          SUM(gross_profit) AS gp
   FROM int_misa_sales_lines
   WHERE is_promo_line = FALSE
   GROUP BY 1,2
   ORDER BY gp DESC
   LIMIT 10
   ```

## 7. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| MISA changes column order or renames headers | Parser produces wrong data silently | Assert `set(df.columns) >= REQUIRED_VN_HEADERS`; fail loud on mismatch; pin rename dict in parser as single source of truth |
| `line_no` instability across re-exports (if MISA reorders lines) | Dedup picks wrong row → margin drift | Dedup uses `ingested_at DESC` + `(voucher_no, line_no)` → re-export overwrites cleanly; cross-validate `SUM(cogs)` against totals footer every load |
| Promo lines filtered out by accident | Margin overstated by ~56M VND/period | Explicit not-filter in stg_ + test asserting `COUNT(*) WHERE is_promo_line = TRUE > 0` |
| `Tổng cộng` footer leaking into fact | Inflated totals, NaN contamination | Filter `WHERE voucher_no IS NOT NULL` in parser step 4; dbt test enforces `not_null(voucher_no)` |
| Cross-source join breaks if Shopee voucher format changes | Future `fact_order_margin` join fails | Preserve `voucher_no` verbatim — no normalization at source layer; defer normalization to join view in P1 |
| `unit_price` decimal precision loss (DECIMAL vs FLOAT) | Penny drift vs MISA | Store `unit_price` as DECIMAL(18,4); test `ABS(SUM(unit_price * quantity) - SUM(revenue_gross)) < 1 VND` (may legitimately fail on discounts — document the delta) |
| Service-UoM rows (`Giờ`, `Tháng`) distort unit-level metrics | Avg-price / qty-per-line misleading | Expose `unit_of_measure` in fact; downstream dashboards must segment by UoM |
| Multiple MISA tenants/companies in future | Source key `misa_raw` ambiguous | Add `company_code` partition layer before `sales_lines/` when 2nd tenant onboards |
| Windows path unicode in filename | File glob fails | Use `pathlib.Path(..., encoding='utf-8')`; tested on Windows native (per memory: deployment env) |
| Coordinate conflicts with Shopee plan | Both plans edit `sources.yml`, `ensure_dbt_directories.py`, `definitions.py` | Implement sequentially; second plan rebases on first; use distinct source blocks (`shopee_raw` vs `misa_raw`) so no line-level conflict in `sources.yml` |
| **Parquet accumulation without GC** | Each ingest appends a new file → partition dir grows unbounded → DuckDB scan slows, disk fills | **P0**: manual cleanup. **P1**: Dagster GC asset — delete files with mtime > 30 days (keeping ≥1 newer file per partition). See § 2.7 rule #5. |
| **MISA row deletions not propagated** | Old rows linger in fact after MISA deletes them | See § 2.7 — P0 accepts limitation; P1 promotes to "periodic full-refresh by posting_month" if drift observed |

## 8. Out of scope (deferred)

- **`fact_order_margin`** — join MISA COGS with Shopee/Sapo revenue on `voucher_no`. P1 deliverable.
- **`dim_misa_products`, `dim_misa_customers`, `dim_misa_salespeople`** — only when dashboards require drill-down by these entities.
- **MISA Open API integration** — replaces manual file drop with live pulls. Requires MISA paid plan + OAuth; `docs/misa-amis/README.md` has the reference URLs. Future phase.
- **VAT reconciliation** — source export does not include a VAT column; clarify with accounting before publishing any "revenue incl. VAT" metric.
- **Period-close audit trail** — currently ingests whatever is in the drop zone; no automatic "this period is closed, reject re-edits" gate.
- **Multi-tenant (multi-company) MISA** — current scope is single company.

## 9. Rename cheat sheet

Full list in `docs/misa-amis/data-source-description.md` § 8. Parser `sales_ledger_parser.py` owns the canonical rename dict; dbt models consume post-rename columns only.

## 10. File manifest (to be created)

```
ingestion/
├── run_misa_sales_file_drop.py                    NEW
├── src/misa_amis/
│   ├── __init__.py                                NEW
│   └── sales_ledger_parser.py                     NEW
└── requirements.txt                               EDIT (+openpyxl — may already be added by Shopee plan)

transformation/
├── models/
│   ├── sources.yml                                EDIT (+misa_raw block)
│   ├── staging/
│   │   ├── src_misa_sales_lines.sql               NEW
│   │   ├── stg_misa_sales_lines.sql               NEW
│   │   └── schema.yml                             EDIT (+tests)
│   └── intermediate/misa/
│       ├── int_misa_sales_lines.sql              NEW
│       └── schema.yml                             EDIT (+tests)
└── seeds/
    └── ref_misa_channel_codes.csv                 NEW

scripts/
└── ensure_dbt_directories.py                      EDIT (+1 rolling dir: int_misa_sales_lines)

orchestration/
├── assets/misa_amis_assets.py                     NEW
└── definitions.py                                 EDIT (+module, +sensor, +job sel, +upstream keys)

ingestion/.dlt/
└── config.toml                                    EDIT (+[sources.misa_amis])
```

## 11. Comparison with Shopee pipeline (shape reuse audit)

| Aspect | Shopee pipeline | MISA pipeline | Reuse? |
|---|---|---|---|
| Pattern | C — file drop | C — file drop | ✅ full |
| # sheets to parse | 2 (`Doanh thu`, `Service Fee Details`) | 1 (`SỔ CHI TIẾT BÁN HÀNG`) | ⚠ simpler |
| # output parquet tables | 3 (order_revenue, items, service_fees) | 1 (sales_lines) | ⚠ simpler |
| Grain split needed | Yes (Order vs Sku on `row_grain`) | No | ⚠ simpler |
| Natural key | `order_code` (+ `product_code` for items) | **synthesized** `(voucher_no, line_no)` | ❗ unique wrinkle |
| Totals/footer handling | N/A | Filter `"Tổng cộng"` row | ❗ unique wrinkle |
| Numeric cleanup (`"-"` sentinels) | Heavy (mixed string/int cols) | Light (MISA exports clean numerics) | ⚠ simpler |
| Seed file | None | `ref_misa_channel_codes.csv` | ❗ unique addition |
| Dagster sensor | New | Same template | ✅ full |
| `get_rolling_location()` on fact | ✅ | ✅ | ✅ full |
| Upstream injection in dbt translator | ✅ | ✅ | ✅ full |
| `gsheet_marketing_spend` as precedent | ✅ | ✅ | ✅ full |

**Net:** MISA is **simpler** in every dimension except the natural key (needs synthesis) and the totals-footer filter. Strongly recommend implementing **Shopee first, MISA second** — MISA can copy-paste from a battle-tested Shopee ingestion module.

## Unresolved questions

1. Should Phase 6 include a dbt test asserting `ABS(SUM(cogs_amount) - <totals footer>) < 10 VND`? The parser already logs the footer; promoting it to a test requires persisting it as a metric anchor (e.g. a tiny `ref_misa_load_checksums.csv` seed or a dbt variable). Recommendation: add in P1 after we see 3+ real drops.
2. Is `voucher_source_hint` worth computing in stg_, or should it wait until a real join with Shopee/Sapo facts validates the regex patterns? Cheap enough to ship at P0, but must be documented as heuristic-only.
3. Sensor interval for MISA — match Shopee (30s) or longer since MISA drops are less frequent than Shopee's weekly rhythm?
4. Should `is_promo_line = TRUE` rows appear in the **default** fact, or be segregated into `int_misa_sales_lines` (all) + `int_misa_sales_lines_sold` (excluding promos) views? Current recommendation: single fact with the flag, let BI do `WHERE is_promo_line = FALSE`. Revisit if analysts repeatedly forget the filter.
5. Does the `"CS"` channel code mean "Customer Service" (direct B2C returns/exchanges) or "Chuỗi Siêu thị" (supermarket chain)? Needs confirmation with accounting before the seed CSV goes to prod.
6. If MISA exports two drops with overlapping windows where a voucher was edited in between, does `(voucher_no, line_no)` still hold? Need a real scenario to confirm line_no stability; fallback is to include `unit_price` in the dedup partition.
