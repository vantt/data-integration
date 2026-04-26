# Shopee Pipeline — Design Specification

**Companion to:** `plan.md`
**Source doc:** `docs/shopee-integration/data-source-description.md`

## 1. Architectural placement

```
app_data/input_source/shopee/*.xlsx
                │
                ▼ (Dagster reactive sensor: file mtime change)
     ┌─────────────────────────────┐
     │ ingestion/run_shopee_income │  ← pandas + openpyxl, NO dlt SDK
     │   .py                       │    (mirrors gsheet_marketing_spend)
     └────────────┬────────────────┘
                  │ writes 3 parquet tables
                  ▼
  data_lake/shopee_raw/
    ├── order_revenue/ingest_method=file_drop/year=*/month=*/*.parquet
    ├── order_revenue_items/ingest_method=file_drop/year=*/month=*/*.parquet
    └── order_service_fees/ingest_method=file_drop/year=*/month=*/*.parquet
                  │
                  ▼
  dbt src_ (incremental + dedup, 7-day lookback on payout_released_at)
    ├── src_shopee_order_revenue
    ├── src_shopee_order_revenue_items
    └── src_shopee_order_service_fees
                  │
                  ▼
  dbt stg_ (view, type casting, numeric cleanup, "-"→0)
    ├── stg_shopee_order_revenue
    ├── stg_shopee_order_revenue_items
    └── stg_shopee_order_service_fees
                  │
                  ▼
  dbt fact_ (external parquet, rolling location)
    ├── int_shopee_order_fees         ← revenue LEFT JOIN service_fees
    └── int_shopee_order_items    ← items INNER JOIN orders
                  │
                  ▼
  data_lake/serving/olap.duckdb (Rolling Self-Refresh Views via
                                  generate_serving_db.py)
                  │
                  ▼
            Metabase queries
```

**Why Pattern C (file drop), not Pattern A (API):**
- No Shopee Open Platform API access in scope.
- Excel is human-exported from Seller Center; cadence is manual/weekly.
- `dlt` has no verified source for local Excel.
- We already have a working file-drop pattern for Google Sheets (`gsheet_marketing_spend.py`) — copy its shape, swap CSV-from-URL for Excel-from-disk.

## 2. Ingestion layer

### 2.1 Entry point

**File:** `ingestion/run_shopee_income_file_drop.py`

```python
def run(argv=None, file_path: str | None = None):
    """
    Parse one Shopee income Excel file and emit 3 parquet tables.
    If file_path is None, process every *.xlsx under INPUT_DIR (file_drop sensor drives this).
    """
```

CLI args (for manual runs):
- `--file PATH` — process a single file (default: glob the drop zone)
- `--full-refresh-touched-months` — **explicit opt-in** flag for known-full-snapshot drops. Parser determines `(year, month)` partitions touched by the file (per `payout_released_at`), deletes ALL existing parquet files in those partitions across all 3 entities, then writes the new ones. Use this only when the analyst confirms the drop is a complete snapshot for those months. Default: OFF (append-only). See § 2.7 for rationale.
- `--full-refresh` — drop & rebuild dlt state (rarely needed for file-drop sources)

### 2.2 Parser module

**File:** `ingestion/src/shopee/income_parser.py`

Responsibilities:

1. Discover files: `glob("app_data/input_source/shopee/*.xlsx")` — **exclude `_archive/` subdir** (only fresh drops).
2. **No filename regex parsing.** Filenames are human-exported and may have overlapping date windows / wrong naming. Rely on data-side truth via `payout_released_at`. Keep only `source_file = os.path.basename(file_path)` as lineage metadata — nothing else is extracted from the filename.
3. Load workbook with `openpyxl` (`data_only=True`), `warnings.filterwarnings("ignore")`.
4. **Sheet: `Doanh thu`** → `pd.read_excel(..., sheet_name="Doanh thu", header=2)` (skip 2 banner rows).
   - Trim trailing all-NaN columns.
   - Rename VN headers → snake_case using a **static dict** in `income_parser.py` (mapping table = canonical renames from data description § 4.3).
   - Split on `row_grain`:
     - `df_order = df[df.row_grain == "Order"]` → `order_revenue`
     - `df_sku   = df[df.row_grain == "Sku"]`   → `order_revenue_items`
5. **Sheet: `Service Fee Details`** → `pd.read_excel(..., sheet_name="Service Fee Details", header=1)`.
   - Rename 4 columns to `row_seq, order_code, infrastructure_fee, voucher_xtra_fee`.
6. **Numeric cleanup** (shared helper):
   ```python
   def to_int_vnd(series):
       return (series.astype(str)
                     .str.replace(r"[^\d\-]", "", regex=True)
                     .replace({"": "0", "-": "0"})
                     .astype("Int64"))
   ```
   Apply to: cols 31, 39–53 of Doanh thu + all fee cols of SFD.
7. **Type coercion:**
   - Dates (`order_placed_at`, `payout_released_at`) → `pd.to_datetime(..., errors="coerce").dt.date`
   - Money → `Int64`
   - `transaction_fee_rate_pct` → `Decimal` / `float64`
8. **Inject ingestion metadata** on every row:
   - `ingest_method = "file_drop"`
   - `source_file = os.path.basename(file_path)` — lineage only
   - `ingested_at = datetime.now(timezone.utc)` (TIMESTAMPTZ per memory rule)
   - `year`, `month` (partition keys, derived from `payout_released_at`)
   - (No `window_start`/`window_end` — dropped; see resolution D1 in `open-questions.md`)
9. **Drop `row_seq`** before write.
10. **Write 3 parquet tables per (year, month) partition with UNIQUE filename per ingest** — append-only, never overwrite:
    ```
    {DBT_DATA_LAKE_PATH}/shopee_raw/{entity}/ingest_method=file_drop/year={YYYY}/month={MM}/shopee_income_{YYYY}-{MM}_{ingested_at_ts}.parquet
    ```
    where `ingested_at_ts = YYYYMMDDTHHMMSSZ` (UTC). Each ingest **adds** a new parquet file per entity per partition; existing files are **never rewritten**.

    **Why unique filename, not fixed name (or window-based name):**
    - Parquet is immutable columnar storage — "overwrite" means full-file rewrite + loss of prior `ingested_at` lineage → breaks dbt src_ dedup (`ORDER BY ingested_at DESC` needs multiple versions to rank).
    - Filename-embedded window (`{window_start}_{window_end}`) is fragile: re-exports of the same period would either (a) collide on filename → overwrite, or (b) differ only if window parses correctly — both relying on filename metadata that § 2.2 explicitly banned from business logic.
    - Timestamp-suffixed names preserve full audit trail on the lake; dedup happens at **read time** in dbt src_ (§ 3.2).
    - The `gsheet_marketing_spend` precedent uses a fixed name because a Google Sheet re-read IS a full snapshot of truth; Shopee drops are NOT — they may overlap, be corrected, or be partial.

### 2.3 Why partition by payout month, not filename month

The filename window may span multiple months; orders released on 2026-03-30 and 2026-04-02 in the same file should land in different `year=/month=` dirs so dbt's `union_by_name=true` external read pulls correct slices.

### 2.4 Config (no secrets)

Add to `ingestion/.dlt/config.toml`:

```toml
[sources.shopee]
input_dir = "app_data/input_source/shopee"
file_pattern = "Income.*.xlsx"
```

Read via `dlt.config["sources.shopee.input_dir"]` or plain `os.environ` — keep it simple, match gsheet_marketing_spend style.

### 2.5 Post-ingest archive

On successful write of all 3 parquet tables for a given file, **move** (not copy) the source `.xlsx` to:

```
app_data/input_source/shopee/_archive/{payout_month}/{ingested_at_ts}__{original_filename}
```

- `payout_month` = `YYYY-MM` derived from `MAX(payout_released_at)` in the file (fall back to ingest month if empty).
- `ingested_at_ts` = `YYYYMMDDHHMMSS` UTC.
- Move is atomic (`shutil.move`); if any parquet write fails beforehand, the source file stays in drop zone for retry.
- `_archive/` subdir excluded from parser glob (step 1 of § 2.2).
- Rollback: if ingest logically succeeded but downstream dbt finds the data bad, manually move the archived file back to drop zone — idempotent dedup in dbt handles the rest.

### 2.6 Idempotency & write semantics

- **Write-time**: parquet filename carries `ingested_at_ts` → every ingest writes a brand-new file per entity per partition. Existing files are untouched.
- **Read-time dedup** (dbt src_ view, § 3.2): `ROW_NUMBER() OVER (PARTITION BY <business_key> ORDER BY ingested_at DESC) = 1` picks the most recent version of every row across all parquet files in the partition. Business keys: `order_code` for order_revenue + order_service_fees, `(order_code, product_code)` for order_revenue_items.
- **Effective semantics**:
  - Row newly added in a later drop → appears in fact.
  - Row edited in a later drop (same business key, different values) → newer `ingested_at` wins, older version silently shadowed.
  - Row physically disappearing from Shopee's report → **NOT reflected** — old row still lives in old parquet file. Shopee released-income rows are effectively immutable once a payout is released, so this is a low-risk limitation in practice.
- **Files auto-archived** (`.xlsx` moved to `_archive/`) on success → no accidental re-processing of the same input file.
- **Corrected re-export** (analyst drops a fix) → parser writes a new parquet with fresh `ingested_at`, dbt src_ picks it up on next build, idempotent at the fact layer.
- **Force re-process** (manual un-archive) → another parquet added; dedup by `ingested_at DESC` guarantees no duplication downstream.

### 2.7 Drop-scope policy & deletion semantics (LOCKED: discrete-drops mode)

**Drop scope assumption (confirmed by user 2026-04-09, applies to BOTH Shopee and MISA pipelines):** file drops are **discrete / non-overlapping windows** dropped ad-hoc, NOT periodic full snapshots from a fixed start date. Examples for Shopee:
- Drop A: `Income.đã phát hành.vn.20260201_20260228.xlsx` (regular monthly)
- Drop B: `Income.đã phát hành.vn.20260215_20260220.xlsx` (corrective re-export covering only the days that needed re-issuing — e.g. an adjustment was processed late)
- Drop C: full quarter export, occasional manual catch-up

This assumption **forces the design choice**: any "automatic full-refresh by partition" would silently destroy data. If Drop B (5 corrective rows) wiped the Feb partition before writing, the 85 untouched February orders from Drop A would be lost. **Append-only is the only safe pattern.**

**Behavior under append-only with discrete drops:**

| Scenario | Pattern handles correctly? |
|---|---|
| Drop B re-ingests 5 orders with newer values; Drop A's other 85 orders untouched | ✅ Drop B's `ingested_at` is newer → 5 fixes win; 85 originals from Drop A still present in `src_` |
| Drop A and Drop C overlap on a row (different values, e.g. fee adjustment) | ✅ Whichever has newer `ingested_at` wins; idempotent |
| Drop A and Drop C overlap on a row (same values) | ✅ Dedup keeps one copy; no fact duplication |
| Shopee removes a row between Drop A and Drop B; Drop B's window covers it but the row is absent | ❌ Parser cannot distinguish "row absent because removed" from "row absent because outside this drop's effective scope" → row leaks into fact (but see § Why Shopee makes this acceptable below) |

**Why deletion detection (tombstone) is impractical:** to diff "what was removed", parser would need to know each drop's **authoritative scope** — i.e. "this drop is the source of truth for date range X..Y, so any row in X..Y not in this drop is removed". With discrete ad-hoc drops there is no reliable scope signal: filename window may overlap, undershoot, or overshoot the actual export. Tombstone logic would require either (a) trusting filename windows (banned by § 2.2 step 2) or (b) an explicit `--scope-start --scope-end` CLI flag the analyst must pass per drop (operational burden).

**P0 decision (LOCKED):**

1. **Append-only forever for normal drops.** Each `.xlsx` lands as a new parquet (per entity) with unique `ingested_at_ts`. No automatic deletion.
2. **Manual escape hatch for known-full-refresh drops.** When the analyst intentionally exports a complete snapshot for a known scope and wants it to override everything, they invoke the parser with explicit `--full-refresh-touched-months`. Parser then **deletes all parquet files in the touched `year=/month=` partitions across all 3 entities (`order_revenue`, `order_revenue_items`, `order_service_fees`) before writing**. Opt-in only, never inferred from filename. **Frequency target: ≤ 1×/quarter.** Guardrail: parser **warns and requires `--force` confirmation** if the drop covers **< 7 calendar days** of `payout_released_at` range (likely a small corrective drop, not a full snapshot — running full-refresh with it would wipe the partition).
3. **Accept silent removal drift** for non-flagged drops. Document the limitation.
4. **Reactive sensor always runs in append-only mode.** `--full-refresh-touched-months` is CLI-only, never triggered by sensor. This prevents a small file drop from accidentally wiping a partition via automation.
5. **Parquet GC by age.** Old parquet files are garbage-collected based on file age (mtime), not version count. Policy: files older than **30 days** are eligible for deletion, provided at least 1 newer file exists in the same partition. Implemented as a Dagster GC asset or ad-hoc script at P1; P0 is manual cleanup.

**Why Shopee makes this acceptable**: a Shopee released-income row represents a payout that has already been credited to the seller wallet. By Shopee Seller Center semantics, **released payouts are immutable** — they cannot be retroactively unpaid; corrections come as **separate adjustment rows** (not row deletions), which is exactly what the `Adjustment` sheet is for (deferred to P1). The "row physically disappeared from a re-export" event is therefore extremely rare in this source — much rarer than for batch order data where Shopee can update an order status.

## 3. dbt transformation layer

### 3.1 Source registration

Append to `transformation/models/sources.yml`:

```yaml
- name: shopee_raw
  schema: main
  meta:
    external_location: "read_parquet('{{ env_var('DBT_DATA_LAKE_PATH') }}/shopee_raw/{name}/ingest_method=*/**/*.parquet', hive_partitioning=1, union_by_name=true)"
  tables:
    - name: order_revenue
      description: "Shopee order-level revenue & fees (Doanh thu sheet, Order rows)"
    - name: order_revenue_items
      description: "Shopee order × product line items (Doanh thu sheet, Sku rows)"
    - name: order_service_fees
      description: "Shopee extra service fees: infrastructure + Xtra voucher (Service Fee Details sheet)"
```

### 3.2 src_ models (view + dedup — NO 7-day lookback)

> **Design note (resolution D2):** Unlike Sapo's API-sourced `src_` models which use 7-day lookback on `updated_at` cursor, Shopee file-drop sources use **view materialization with full-scan dedup**. Rationale: file drops have no per-row `updated_at`; files may overlap; data volume is small (~100 rows/file); a full parquet scan each `dbt build` is cheap and inherently robust against overlapping re-exports. The 7-day lookback pattern (protecting against late updates arriving in source) does not apply here.

**`src_shopee_order_revenue.sql`** — materialize `view`
- Business key: `order_code`
- Dedup: `ROW_NUMBER() OVER (PARTITION BY order_code ORDER BY ingested_at DESC) = 1`
- No incremental config, no lookback
- Tag: `['src', 'shopee']`

**`src_shopee_order_revenue_items.sql`** — materialize `view`
- Business key: `(order_code, product_code)`
- Dedup: `ROW_NUMBER() OVER (PARTITION BY order_code, product_code ORDER BY ingested_at DESC) = 1`

**`src_shopee_order_service_fees.sql`** — materialize `view`
- Business key: `order_code`
- Dedup: `ROW_NUMBER() OVER (PARTITION BY order_code ORDER BY ingested_at DESC) = 1`

### 3.3 stg_ models (type cleanup, view)

**`stg_shopee_order_revenue.sql`** — view over `src_shopee_order_revenue`
- Final cast: all `STR→INT` cols → `BIGINT`
- `CAST(order_placed_at AS DATE)`, `CAST(payout_released_at AS DATE)`
- Drop rarely-used diagnostic columns (`buyer_payment_method_detail`, `installment_plan`) if empty in audit
- Compute convenience fields:
  - `gross_revenue = total_paid_amount + refund_amount`
  - `total_shipping_net = shipping_fee_paid_by_buyer + shipping_fee_actual + shipping_subsidy_from_shopee + shipping_fee_return_refund + shipping_refund_by_piship + shipping_fee_failed_delivery`
  - `total_discounts = seller_voucher_discount + seller_cofunded_voucher_discount + seller_coin_cashback + seller_cofunded_coin_cashback + product_subsidy_from_shopee`
  - `total_platform_fees = fixed_fee + service_fee + payment_fee + affiliate_commission_fee + piship_service_fee + auto_topup_amount`
  - `total_taxes = vat_tax + personal_income_tax`

**`stg_shopee_order_revenue_items.sql`** — thin view, just casts + `order_code`, `product_code`, `product_name` (money columns dropped since they are parent-derived).

**`stg_shopee_order_service_fees.sql`** — thin view, casts `infrastructure_fee`, `voucher_xtra_fee` → BIGINT.

### 3.4 Intermediate models (enrichment layer — NOT primary facts)

> **Design note (locked 2026-04-10):** These models are `int_` (intermediate) because Shopee fee data is enrichment for Sapo orders, not a primary business event. All orders already exist in Sapo `fact_orders`. Shopee adds fee breakdowns (platform fees, shipping, vouchers). `int_` prefix signals this clearly. Rolling location is applied pragmatically so P0 Metabase queries work before the P1 unified `fact_order_economics` is built.

#### `int_shopee_order_fees.sql` (one row per order)

```sql
{{ config(
    tags=['int', 'shopee'],
    materialized='table',
    location="{{ get_rolling_location() }}"
) }}

WITH rev AS (
    SELECT * FROM {{ ref('stg_shopee_order_revenue') }}
),
fees AS (
    SELECT * FROM {{ ref('stg_shopee_order_service_fees') }}
)
SELECT
    {{ dbt_utils.generate_surrogate_key(['rev.order_code']) }} AS shopee_order_sk,
    rev.order_code,
    rev.order_placed_at,
    rev.payout_released_at,
    rev.order_type,
    rev.payment_method,
    rev.buyer_username,
    -- revenue
    rev.total_paid_amount,
    rev.product_list_price,
    rev.refund_amount,
    rev.gross_revenue,
    -- shipping
    rev.total_shipping_net,
    rev.shipping_fee_paid_by_buyer,
    rev.shipping_fee_actual,
    rev.shipping_subsidy_from_shopee,
    -- discounts / subsidies
    rev.total_discounts,
    -- platform fees (from Doanh thu)
    rev.total_platform_fees,
    rev.service_fee,
    rev.payment_fee,
    rev.fixed_fee,
    -- extra service fees (from Service Fee Details sheet)
    COALESCE(fees.infrastructure_fee, 0)  AS infrastructure_fee,
    COALESCE(fees.voucher_xtra_fee, 0)    AS voucher_xtra_fee,
    -- taxes
    rev.total_taxes,
    rev.vat_tax,
    rev.personal_income_tax,
    -- derived net settlement (matches Shopee "Tổng phát hành")
    (rev.total_paid_amount
        + rev.total_shipping_net
        + rev.total_discounts
        + rev.total_platform_fees
        + rev.total_taxes
        + COALESCE(fees.infrastructure_fee, 0)
        + COALESCE(fees.voucher_xtra_fee, 0)
    ) AS net_settlement,
    -- lineage
    rev.source_file,
    rev.ingested_at
FROM rev
LEFT JOIN fees USING (order_code)
```

#### `int_shopee_order_items.sql` (one row per order × product)

```sql
{{ config(
    tags=['int', 'shopee'],
    materialized='table',
    location="{{ get_rolling_location() }}"
) }}

SELECT
    {{ dbt_utils.generate_surrogate_key(['items.order_code','items.product_code']) }} AS shopee_order_item_sk,
    items.order_code,
    items.product_code,
    items.product_name,
    orders.payout_released_at,
    orders.order_placed_at,
    orders.net_settlement,         -- allocatable at item level later
    orders.source_file,
    orders.ingested_at
FROM {{ ref('stg_shopee_order_revenue_items') }} items
INNER JOIN {{ ref('int_shopee_order_fees') }} orders USING (order_code)
```

**No `dim_shopee_*`** tables in P0 — buyers, vouchers, carriers can become dims later if analyst demand materializes.

### 3.5 Tests (schema.yml additions)

```yaml
- name: int_shopee_order_fees
  columns:
    - name: shopee_order_sk
      tests: [unique, not_null]
    - name: order_code
      tests: [unique, not_null]
    - name: payout_released_at
      tests: [not_null]
    - name: net_settlement
      tests: [not_null]

- name: int_shopee_order_items
  columns:
    - name: shopee_order_item_sk
      tests: [unique, not_null]
    - name: order_code
      tests:
        - not_null
        - relationships:
            to: ref('int_shopee_order_fees')
            field: order_code
```

### 3.6 Pre-create rolling dirs

Append `int_shopee_order_fees` and `int_shopee_order_items` to `scripts/ensure_dbt_directories.py`.

## 4. Serving layer

No new code. `scripts/provisioning/generate_serving_db.py` already auto-discovers any new `rolling/{model}/` folder. Verification only:

```bash
python scripts/provisioning/generate_serving_db.py
duckdb data_lake/serving/olap.duckdb -c "SELECT COUNT(*), SUM(net_settlement) FROM int_shopee_order_fees"
```

**Critical rule already covered:** both `int_` models include `location="{{ get_rolling_location() }}"` — pragmatic exception to the convention that only `dim_/fact_` use rolling. This ensures P0 Metabase access before P1 `fact_order_economics` exists.

## 5. Dagster orchestration

### 5.1 New module

**File:** `orchestration/assets/shopee_assets.py` (copy shape from `sheets_assets.py`)

```python
@asset(group_name="shopee_ingestion", key_prefix=["shopee"],
       op_tags={"dagster/concurrency_key": "duckdb_lock"})
def shopee_income_file_drop_asset(context):
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        run_shopee_income_file_drop.run(argv=[])
    finally:
        os.chdir(cwd)
    return Output("OK", metadata={"status": "Success"})
```

### 5.2 Reactive sensor (mirror sheets sensor)

Add `shopee_income_sensor` watching file mtime in `app_data/input_source/shopee/`. Pattern: per skill `.skills/data-pipeline/templates/dagster-reactive-sensor-template.py` + existing sheets sensor (`48be670 feat(orchestration): sheets reactive sensor + downstream cascade`).

Cascade: `shopee_income_file_drop_asset → dbt_assets (selection) → serving_db_asset`

### 5.3 Job registration

Add to `orchestration/definitions.py`:
- Include `shopee_assets` in `load_assets_from_modules`.
- Inject upstream keys in `DagsterDbtTranslator.get_upstream_asset_keys()` so `src_shopee_*` dbt models depend on `shopee_income_file_drop_asset` (critical rule #10).
- Add to `sapo_nightly_reconciliation_job` selection so the nightly job also picks up any file dropped outside business hours.

## 6. Verification plan (Phase 6)

1. **Unit:** `python ingestion/run_shopee_income_file_drop.py --file app_data/input_source/shopee/Income.đã*.xlsx`
2. **Data audit:**
   - `SELECT COUNT(*) FROM int_shopee_order_fees` = 90 (expected from sample)
   - `SELECT COUNT(*) FROM int_shopee_order_items` ≥ 90
   - `SELECT COUNT(*) FROM int_shopee_order_fees WHERE infrastructure_fee IS NULL OR infrastructure_fee = 0` = 4 (orders with no SFD record)
3. **Reconciliation vs human report:** sum `net_settlement` must match the `Summary` sheet's "Tổng phát hành" total.
4. **Idempotency:** rerun ingestion; `SELECT COUNT(DISTINCT order_code) FROM int_shopee_order_fees` unchanged.
5. **Sensor trigger:** `touch` the xlsx file, confirm Dagster run kicks off within the sensor interval.
6. **Metabase probe:** new question `SELECT order_code, net_settlement FROM int_shopee_order_fees ORDER BY payout_released_at DESC LIMIT 20`.

## 7. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Excel header drift when Shopee updates export format | Parser crashes / silently wrong cols | Assert `set(df.columns) >= REQUIRED_COLS`; fail loud; pin canonical rename dict in parser |
| Multi-SKU orders violate current 1:1 assumption | `int_shopee_order_items` unique test fails | Use `(order_code, product_code)` SK from day one (already in spec) |
| `"-"` sentinels in new columns we didn't audit | Bad cast to int | Numeric cleanup helper is applied generically; anything unmapped goes to `Int64` nullable |
| File with same filename but different content (re-export) | Overwrite loses audit trail | Archive originals to `app_data/input_source/shopee/_archive/{ingested_at}/` before reprocess |
| Adjustment/Summary sheets ignored → incomplete P&L | Net settlement drifts from Shopee's number | P0 reconciles to Summary total; if gap >1 VND, escalate to P1 adjustment sheet support |
| Windows path / unicode filename (`đã phát hành`) | Open/glob fails on some tools | Use `pathlib.Path`, `encoding='utf-8'`, test on Windows native (per memory: deployment env) |
| **Parquet accumulation without GC** | Each ingest appends new files → partition dir grows unbounded → DuckDB scan slows, disk fills | **P0**: manual cleanup. **P1**: Dagster GC asset — delete files with mtime > 30 days (keeping ≥1 newer file per partition per entity). See § 2.7 rule #5. |
| **Orders disappearing from Shopee report** | Old rows linger in fact after Shopee removes them | Accepted limitation — Shopee released-income rows are effectively immutable once payout is credited. Revisit only if Phase 6 reconciliation shows drift. |

## 8. Out of scope (deferred)

- `Summary` sheet (human report, use only as checksum)
- `Adjustment` sheet (chargebacks/compensation) — P1
- `dim_shopee_buyers`, `dim_shopee_vouchers` — only if analysts request
- Multi-shop support — currently single `seller_tax_code`; add `shop_code` partition when a 2nd shop onboards
- Shopee Open Platform API (real-time) — remains manual file drop

## 9. Rename cheat sheet

Full list in `docs/shopee-integration/data-source-description.md` § 4.3 and § 6. Parser `income_parser.py` owns the canonical mapping dict; dbt models consume post-rename columns only.

## 10. File manifest (to be created)

```
ingestion/
├── run_shopee_income_file_drop.py              NEW
├── src/shopee/
│   ├── __init__.py                             NEW
│   └── income_parser.py                        NEW
└── requirements.txt                            EDIT (+openpyxl)

transformation/models/
├── sources.yml                                 EDIT (+shopee_raw block)
├── staging/
│   ├── src_shopee_order_revenue.sql            NEW
│   ├── src_shopee_order_revenue_items.sql      NEW
│   ├── src_shopee_order_service_fees.sql       NEW
│   ├── stg_shopee_order_revenue.sql            NEW
│   ├── stg_shopee_order_revenue_items.sql      NEW
│   ├── stg_shopee_order_service_fees.sql       NEW
│   └── schema.yml                              EDIT (+tests)
└── intermediate/shopee/
    ├── int_shopee_order_fees.sql               NEW
    ├── int_shopee_order_items.sql              NEW
    └── schema.yml                              EDIT (+tests)

scripts/
└── ensure_dbt_directories.py                   EDIT (+2 rolling dirs)

orchestration/
├── assets/shopee_assets.py                     NEW
└── definitions.py                              EDIT (+module, +sensor, +job sel, +upstream keys)

ingestion/.dlt/
└── config.toml                                 EDIT (+[sources.shopee])
```

## Unresolved questions

1. ~~Should `int_shopee_order_fees` also join to Sapo `fact_orders` for omnichannel reconciliation, or keep Shopee as its own island until P1?~~ **RESOLVED (2026-04-10):** Keep as standalone `int_` at P0; join into `fact_order_economics` at P1.
2. `piship_service_fee` is stored as STR in source — confirm if it's always integer-parseable or can contain decimal strings.
3. Archive policy: keep all `.xlsx` drops forever, or GC after ingest success?
4. Sensor interval: match sheets sensor (30s) or longer since file drops are manual/rare?
5. Do we need a dbt test asserting `ABS(SUM(net_settlement) - <summary sheet total>) < 10 VND`? Requires parsing the Summary sheet too.
