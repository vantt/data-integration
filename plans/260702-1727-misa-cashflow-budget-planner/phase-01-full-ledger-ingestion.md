# Phase 01 — Full-ledger ingestion + idempotency fix

**Status:** IN PROGRESS — parser + models DONE; downloader unblocked pending account-picker debug.

## What's ALREADY DONE (do not re-implement)

- **Parser** `ingestion/src/misa_amis/account-ledger-parser.py` — emits 3 new additive columns: `debit_balance` (col 8), `credit_balance` (col 9), `opening_balance` (signed, per "Số dư đầu kỳ" row). Regression: 642 June-2026 PASS (116 rows, total_debit=104,945,218, mismatches=[]).
- **Downloader** `ingestion/src/misa_amis/misa_account_ledger_web_downloader.py` — `--all-accounts` flag added (passed as empty string to `_select_account_prefix`); `_select_account_prefix` L88-130 already handles empty prefix.
- `sources.yml` `misa_raw` source already uses `union_by_name=true` (L137) → old 642-only parquet partitions get NULL for new balance columns; no schema breakage.

## Context links

| Item | Path |
|------|------|
| Runner (file-drop) | `ingestion/run-misa-account-ledger-file-drop.py` |
| Runner (download) | `ingestion/run-misa-account-ledger-download.py` |
| Parser | `ingestion/src/misa_amis/account-ledger-parser.py` |
| Downloader | `ingestion/src/misa_amis/misa_account_ledger_web_downloader.py` |
| File-drop utils | `ingestion/src/file-drop-utils.py` |
| Dagster assets | `orchestration/assets/misa_amis_assets.py` |
| Raw source | `transformation/models/sources.yml` L134-175 |
| Staging dedup | `transformation/models/staging/src_misa_account_ledger.sql` |
| Staging rollup | `transformation/models/staging/standard/std_misa_account_ledger.sql` |
| Overhead consumer | `transformation/models/intermediate/overhead/int_overhead_pool_monthly.sql` L45 (filters `account_group IN ('6421','6422')`) |

## Critical hazard — Dagster sensor + UPSERT-by-month

**What happened tonight (incident, 2026-07-02 ~21:57):**
File `So_chi_tiet__202606.xlsx` dropped in `app_data/input_source/misa-account-ledger/` was auto-ingested by the active sensor. `run-misa-account-ledger-file-drop.py` L125-127 builds `touched = set of (year, month)` from the file, then calls `full_refresh_partitions(base_path, "account_ledger", touched)` which deletes ALL parquet in `year=2026/month=6/` — wiping the 642 overhead data. Recovery: re-ingest from `_archive/`.

**Root cause:** UPSERT key = (year, month) ≡ "all accounts in that month". A partial export (cash-only 11x) clears the entire month before re-writing, losing 642 overhead.

**Rule going forward:** NEVER drop a partial-account export file in the sensor input dir while the sensor is running unless the full-ledger export problem is resolved.

---

## Blocked item — Full-ledger export from MISA

`_select_account_prefix(page, "")` (empty prefix) currently returns the SAME account set as the previous run because MISA caches report params server-side. The `.row-check-all` checkbox selects all currently-listed accounts, which reflect the stale filter.

**User action pending:** debug in headed mode to force-clear account picker selection before clicking "Chọn tất cả".

### Branch A — Full-ledger export works

Condition: headed debug confirms that clearing the search field (Ctrl+A + Delete) then clicking `.row-check-all` reliably selects ALL chart-of-accounts entries.

**Result:** each monthly export contains ALL accounts (incl 642). UPSERT-by-(year,month) remains valid. Overhead 642 is preserved because it's in the same file.

Implementation steps:
1. In headed mode, inspect if `inp.press("Control+A"); inp.press("Delete")` resets the MISA server-side filter or if an explicit UI "clear" button must be clicked first.
2. If a clear button exists, add a `page.locator("[class*='clear']").first.click()` step before `inp.fill(account)` in `_select_account_prefix` (L100-106 of `misa_account_ledger_web_downloader.py`).
3. Validate: run headless with `account=""`, inspect downloaded file — must contain accounts from multiple classes (1xx, 3xx, 5xx, 6xx).
4. Update `run-misa-account-ledger-download.py` to pass `--account ""` when `--all-accounts` flag is set (already wired per tonight's work, verify CLI plumbing).
5. Update Dagster config: change `MisaAccountLedgerDownloadConfig.account` default from `"642"` to `""` when scheduling full-ledger pulls; OR add a separate asset `misa_full_ledger_download_asset` with `account=""` to preserve the existing 642 monthly schedule without risk.
6. First full-ledger ingest: verify raw parquet contains account_codes across classes; run regression check (see Tests section).

No code change to file-drop-utils or UPSERT logic needed.

### Branch B — Full-ledger export stays broken (recommended mitigation: b1, narrow key)

Condition: headed debug cannot reliably force MISA to return the full chart. Multiple separate exports required per period (e.g. one for 11x, one for 642, one for 3xx, etc.).

**Option b1 (RECOMMENDED) — narrow idempotency key to (account_group_prefix, year, month)**

This allows coexisting exports for different account ranges within the same month.

#### Tradeoff vs b2

| | b1 narrow key | b2 separate table |
|--|--------------|------------------|
| Code change | Medium — file-drop runner + utils | Medium — new runner + new source |
| dbt change | None (same parquet path) | New source + new model |
| Dagster change | New config/asset param | New asset + sensor |
| Risk to overhead | Low if key narrowed correctly | None (separate file) |
| Complexity | Moderate | Moderate |
| Preferred? | **YES** — same physical table, simpler | Acceptable fallback |

#### b1 — Exact implementation steps

**Files to modify:**

1. **`ingestion/run-misa-account-ledger-file-drop.py`** — narrow the UPSERT key.

   Current (L125-127):
   ```python
   touched = set(df[["year", "month"]].drop_duplicates().itertuples(index=False, name=None))
   utils.full_refresh_partitions(base_path, "account_ledger", touched)
   ```

   Change to: partition per `(account_group_prefix, year, month)` where `account_group_prefix` = first 3 chars of account code (e.g. "111", "112", "642").

   Implementation: extract prefix set from `df["account"].str[:3].unique()`, then for each `(prefix, year, month)` delete only parquet rows matching that prefix within the partition dir. Since parquet files are per `(year, month)` dir (not further sub-partitioned), we can't selectively delete by prefix within a single parquet file using the existing `full_refresh_partitions` helper.

   **Practical approach:** Instead of deleting whole partition dirs, write into separate sub-paths per account group prefix:
   - Change `write_partitioned_parquet` call to add `account_prefix=prefix` as an extra hive level, OR
   - Use a separate parquet filename prefix that encodes the account range, and on re-ingest delete only files matching `{account_prefix}*.parquet` within the partition dir.

   **Recommended:** add a 4th hive partition level `account_prefix=XXX` alongside `year/month`:

   In `run-misa-account-ledger-file-drop.py`, before writing:
   ```python
   # Group by account_prefix (first 3 digits) to allow partial-account coexistence
   df["account_prefix"] = df["account"].str[:3]
   ```

   Then write per `(account_prefix, year, month)` using a modified helper call — or modify `write_partitioned_parquet` to accept an extra partition column list.

   Path becomes: `misa_raw/account_ledger/ingest_method=file_drop/account_prefix=642/year=2026/month=6/`

   UPSERT key becomes `(account_prefix, year, month)` — clearing only the `account_prefix=642/year=2026/month=6/` dir on re-ingest.

2. **`ingestion/src/file-drop-utils.py`** — add optional `extra_partition_cols` param to `write_partitioned_parquet` and `full_refresh_partitions` (or a new helper).

   Signature change:
   ```python
   def write_partitioned_parquet(df, base_path, entity_name, source_prefix, date_col,
                                  extra_partition_cols=None):
   ```
   Where `extra_partition_cols=["account_prefix"]` is passed from the account-ledger runner.

3. **`transformation/models/sources.yml`** — `misa_raw.account_ledger` external_location already uses `hive_partitioning=1` + `union_by_name=true`. A new `account_prefix` hive key is automatically read by DuckDB's hive partition reader. **No change needed** — DuckDB ignores unknown hive keys or adds them as columns; `union_by_name=true` handles mixed partition presence.

   Verify: after first partial-prefix write, run:
   ```sql
   SELECT account_prefix, COUNT(*) FROM read_parquet(
     '{DATA_LAKE_PATH}/misa_raw/account_ledger/ingest_method=file_drop/**/*.parquet',
     hive_partitioning=1, union_by_name=true
   ) GROUP BY account_prefix;
   ```

4. **UPSERT touchset** in runner — replace `touched` build:
   ```python
   touched = set(
       df[["account_prefix", "year", "month"]]
       .drop_duplicates()
       .itertuples(index=False, name=None)
   )
   utils.full_refresh_partitions_with_prefix(base_path, "account_ledger", touched)
   ```
   Where `full_refresh_partitions_with_prefix` deletes `account_prefix={p}/year={y}/month={m}` dirs.

5. **Existing 642 parquet** (no `account_prefix` hive dir) — old files at `year=YYYY/month=M/*.parquet` remain readable (DuckDB `union_by_name=true` tolerates missing hive keys, yields NULL for `account_prefix`). On first Branch-B re-ingest for 642, files write into `account_prefix=642/year=.../month=.../` and old flat partition dirs remain alongside. This is safe — dedup in `src_misa_account_ledger` (ROW_NUMBER on business key) prevents duplicates.

   **Migration sweep (optional but recommended):** after confirming Branch B works for 1 full month, move old flat parquet files into `account_prefix=642/` dirs via one-time script. Not urgent.

6. **Dagster asset** (`orchestration/assets/misa_amis_assets.py` `misa_account_ledger_download_asset` L164-200) — no change to asset config. The file-drop sensor processes any `.xlsx` dropped in the input dir regardless; the narrowed UPSERT key is entirely in the file-drop runner.

---

## Regression gate — 642 overhead MUST be unchanged

Run after ANY ingestion change:

```bash
# From project root (PowerShell or Bash)
python - <<'EOF'
import duckdb, os
lake = os.environ["DBT_DATA_LAKE_PATH"]
conn = duckdb.connect(read_only=False)
res = conn.execute(f"""
  SELECT
    SUM(debit) AS total_debit,
    COUNT(*) AS rows
  FROM read_parquet(
    '{lake}/misa_raw/account_ledger/ingest_method=file_drop/**/*.parquet',
    hive_partitioning=1, union_by_name=true
  )
  WHERE account LIKE '642%'
    AND year = 2026 AND month = 6
""").fetchone()
print(f"642 June-2026: total_debit={res[0]:,}, rows={res[1]}")
assert res[0] == 104_945_218, f"REGRESSION: expected 104,945,218 got {res[0]}"
print("PASS")
EOF
```

Expected: `total_debit=104,945,218` (116 rows). If mismatch: re-ingest from `_archive/2026-06/` before any further changes.

---

## Sources.yml update needed

Add the 3 new parser columns to `transformation/models/sources.yml` under `misa_raw.account_ledger.columns` (L148-174):

```yaml
- name: debit_balance
  description: "Dư Nợ — running debit balance after this line (col 8 in Excel)"
- name: credit_balance
  description: "Dư Có — running credit balance after this line (col 9 in Excel)"
- name: opening_balance
  description: "Signed opening balance for this account in this period (debit_balance − credit_balance from 'Số dư đầu kỳ' row)"
```

Also update description to reflect all-account scope (not just 642).

---

## Dagster asset update (when Branch A confirmed or Branch B implemented)

File: `orchestration/assets/misa_amis_assets.py`

When Branch A works, add a scheduled asset for full-ledger download:
```python
class MisaFullLedgerDownloadConfig(Config):
    account: str = ""  # empty = all accounts

@asset(group_name="misa_amis_ingestion", key_prefix=["misa_amis"])
def misa_full_ledger_download_asset(context, config: MisaFullLedgerDownloadConfig):
    """Download full chart-of-accounts ledger monthly."""
    ...
```
Keep the existing `misa_account_ledger_download_asset` (account="642") until full-ledger is verified for 3 consecutive months.

---

## Safety rules — MANDATORY

1. **Never drop test/partial files into `app_data/input_source/misa-account-ledger/`** while sensor is running. Use `--file` CLI flag to test: `python ingestion/run-misa-account-ledger-file-drop.py --file path/to/file.xlsx` (sensor does not watch CLI invocations).
2. **Always verify 642 regression** before and after any ingestion change (query above).
3. **Backup partition before any UPSERT change**: `cp -r {DATA_LAKE_PATH}/misa_raw/account_ledger/ingest_method=file_drop/year=2026/month=6/ /tmp/backup_642_202606/`

---

## Tests / validation

| Test | Command / Check |
|------|----------------|
| Parser regression (642) | `python ingestion/src/misa_amis/account-ledger-parser.py` on any 642 xlsx; assert 104,945,218 |
| New columns present | `df.columns` includes `debit_balance`, `credit_balance`, `opening_balance` |
| Full-ledger file accounts | After new ingest: `SELECT DISTINCT LEFT(account,1) FROM src_misa_account_ledger` → must include classes 1,3,5,6 |
| Overhead allocation unchanged | `dbt build --select int_overhead_pool_monthly+` → compare pool_net per (pool_id, period_month) with pre-change snapshot |
| Old partition NULL-safe | `SELECT COUNT(*) FROM src_misa_account_ledger WHERE opening_balance IS NULL` — OK (old 642 partitions) |
| UPSERT idempotent | Drop same file twice → row count same, no duplicates in `src_misa_account_ledger` |

---

## Rollback

- Ingestion vỡ: `full_refresh_partitions` on touched months → re-ingest from `_archive/`.
- UPSERT key change vỡ overhead: revert `run-misa-account-ledger-file-drop.py` to commit before b1 change; re-ingest from `_archive/`.
- Branch A causes partial export: keep Branch B (b1) as fallback; both approaches are compatible.
- `dbt` model downstream: no change to `std_misa_account_ledger` or `int_overhead_pool_monthly` needed (they already filter by account_group IN ('6421','6422') at L45 of `int_overhead_pool_monthly.sql`).

---

## Unresolved questions

1. **Account-picker headed debug**: does Ctrl+A+Delete on the search input clear MISA's server-side cached filter, or is a UI "clear" / "reset" button required? (blocking Branch A).
2. **Account count**: how many distinct accounts in the full chart? If >200, MISA may paginate the picker; `.row-check-all` must still select all non-visible pages.
3. **File size**: will a full-ledger monthly export (all accounts) be significantly larger than current 642-only (116 rows)? Estimate row count to flag potential Playwright timeout risk.
4. **Branch B migration sweep**: after 3 months, move flat `year=X/month=Y/*.parquet` → `account_prefix=642/year=X/month=Y/` to clean up mixed-structure parquet. Assign to maintenance ticket.
