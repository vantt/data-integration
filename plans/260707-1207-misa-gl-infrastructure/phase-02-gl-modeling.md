# Phase 02 — GL modeling (dim / fact)

**Status:** DONE (2026-07-03) — `dim_gl_account` (281 accounts, 14 cashflow_line), `fact_cash_movement`, and `fact_account_balance_monthly` all built and validated on real data (6 months live). Per parent plan's "Tiến độ 2026-07-03" log (now `plans/260707-1207-misa-gl-infrastructure/plan.md`).

**Depends on:** Phase 01 (full-ledger parquet with `opening_balance` column).

---

## What's ALREADY DONE (do not re-implement)

### `transformation/models/marts/core/dim_gl_account.sql` — DONE

Self-populating from `src_misa_account_ledger` (account ∪ offset_account union). Enriched via seed `ref_gl_accounts.csv`.

Final schema:

| Column | Type | Notes |
|--------|------|-------|
| `account_code` | VARCHAR | PK — distinct from both posting + counterpart accounts |
| `account_name` | VARCHAR | From seed; falls back to `'TK ' \|\| account_code` |
| `account_class` | VARCHAR(1) | `LEFT(account_code, 1)` — 1=asset, 3=liability, 5=revenue, 6=expense |
| `is_cash` | BOOLEAN | `account_code LIKE '111%' OR '112%'` |
| `cashflow_line` | VARCHAR | Counterpart grouping for operational cashflow budgeting (prefix CASE) |
| `source_system` | VARCHAR | `'misa'` |

Materialization: table (via `get_rolling_location()`), tags: `['mart','dim','misa']`.

Note: `cashflow_line` is on the **counterpart** account, not the cash account. Finance must confirm taxonomy (open-q #3 in plan.md).

### `transformation/models/marts/finance/fact_cash_movement.sql` — DONE

Grain: 1 row per journal line hitting a cash/bank account (`111%` or `112%`).

Final schema:

| Column | Type | Notes |
|--------|------|-------|
| `posting_date` | DATE | |
| `period_month` | DATE | `DATE_TRUNC('month', posting_date)` |
| `cash_account` | VARCHAR | Account code (111x/112x) |
| `cash_account_name` | VARCHAR | From dim_gl_account |
| `offset_account` | VARCHAR | TK đối ứng |
| `offset_account_name` | VARCHAR | From dim_gl_account |
| `cashflow_line` | VARCHAR | From dim_gl_account on offset_account |
| `direction` | VARCHAR | `'inflow'` (debit>0) / `'outflow'` (credit>0) |
| `is_internal_transfer` | BOOLEAN | offset ∈ 111%/112% → net zero, exclude from true thu/chi |
| `amount` | BIGINT | Absolute VND (debit or credit whichever > 0) |
| `signed_amount` | BIGINT | `+inflow / −outflow` |
| `running_balance` | BIGINT | `debit_balance − credit_balance` from parser (authoritative, don't recompute) |
| `opening_balance` | BIGINT | Period opening per account from parser |
| `voucher_no` | VARCHAR | |
| `description` | VARCHAR | |
| `source_system` | VARCHAR | `'misa'` |

Materialization: table (`get_rolling_location()`), tags: `['mart','fact','misa','finance']`.

**Validated June-2026:** thu 464.4M, chi 434.0M, net +30.4M (recon with MISA sổ quỹ OK).
Key fact: `WHERE NOT is_internal_transfer` needed in all external cashflow queries (11221↔11212 internal transfer = 149.5M, nets to 0).

### `transformation/seeds/ref_gl_accounts.csv` — DONE

Covers: 111, 1111, 112, 1121, 11212, 11219, 1122, 11221, 131, 133, 1331, 136, 1368, 13681, 138, 141, 156, 331, 333 + more. Registered in `transformation/seeds/properties.yml`.

---

## Still to build — `fact_account_balance_monthly`

### Why this model is needed

`fact_cash_movement` only contains accounts with journal activity (`debit>0 OR credit>0`). Account `11219` (Tiền gửi ngân hàng - khác) has a standing balance of 71,511 VND but zero movement in June-2026 → **invisible in fact_cash_movement** → số dư quỹ aggregate is understated.

`fact_account_balance_monthly` fixes this by anchoring every account's opening balance and carrying it forward even across zero-movement months.

### Grain

`(account_code, period_month)` — one row per account per month, covering ALL accounts with any parquet data (not just cash). This model is the foundation for balance-sheet and P&L reporting in later phases.

### Source of truth for balances

- **Opening balance** = `opening_balance` column emitted by the parser for "Số dư đầu kỳ" rows. Available in `src_misa_account_ledger` (NULL for old 642 partitions that predate the parser enhancement).
- **Period movements** = `SUM(debit)` / `SUM(credit)` per (account, period_month) from `src_misa_account_ledger`.
- **Closing balance** = `opening_balance + Σdebit − Σcredit` for debit-normal accounts (1x, 6x); `opening_balance + Σcredit − Σdebit` for credit-normal accounts (3x, 4x, 5x). Simpler: use `running_balance` of the **last line** per (account, period_month) from the parser — it's authoritative and avoids direction confusion.
- **Zero-movement accounts**: opening carries forward as closing with no period movement rows. Must be handled via a separate CTE (see implementation below).

### File to create

`transformation/models/marts/finance/fact_account_balance_monthly.sql`

### Implementation (exact SQL structure)

```sql
{{ config(
    tags=['mart', 'fact', 'misa', 'finance'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: ACCOUNT BALANCE MONTHLY
-- =================================================================================================
-- Grain: (account_code, period_month) — 1 row per account × calendar month
-- Purpose: opening + Σdebit + Σcredit + closing for ALL accounts in the ledger.
--   Includes zero-movement accounts (those with an opening_balance but no lines in a period).
--   Closing = running_balance of the LAST line in period (authoritative from parser, col 8−9).
--   For zero-movement months: closing = opening (no journal lines → balance unchanged).
--
-- Note: old 642-only parquet partitions have opening_balance=NULL (pre-parser-enhancement).
--   Filter `WHERE opening_balance IS NOT NULL` if you only want post-full-ledger data.
-- =================================================================================================

WITH raw AS (
    SELECT
        account,
        DATE_TRUNC('month', posting_date::DATE)  AS period_month,
        debit,
        credit,
        debit_balance,
        credit_balance,
        opening_balance,
        (debit_balance - credit_balance)         AS running_balance,
        -- Row ordering within account×month to find last line
        ROW_NUMBER() OVER (
            PARTITION BY account, DATE_TRUNC('month', posting_date::DATE)
            ORDER BY posting_date DESC, voucher_no DESC
        )                                        AS rn_last
    FROM {{ ref('src_misa_account_ledger') }}
    WHERE posting_date IS NOT NULL
),

-- Sum movements per (account, month)
movements AS (
    SELECT
        account                         AS account_code,
        period_month,
        SUM(debit)                      AS period_debit,
        SUM(credit)                     AS period_credit,
        COUNT(*)                        AS line_count
    FROM raw
    GROUP BY account, period_month
),

-- Opening balance anchor: one row per (account, month) from "Số dư đầu kỳ" rows.
-- opening_balance is forward-filled to all detail rows by the parser,
-- so MAX() is safe (all rows in same account×month have same opening_balance).
opening AS (
    SELECT
        account                         AS account_code,
        period_month,
        MAX(opening_balance)            AS opening_balance
    FROM raw
    WHERE opening_balance IS NOT NULL
    GROUP BY account, period_month
),

-- Closing balance: running_balance of the last journal line in the period.
-- Authoritative — taken directly from col 8−9 (Dư Nợ − Dư Có) in Excel.
closing AS (
    SELECT
        account                         AS account_code,
        period_month,
        (debit_balance - credit_balance) AS closing_balance
    FROM raw
    WHERE rn_last = 1
)

SELECT
    m.account_code,
    m.period_month,
    COALESCE(o.opening_balance, 0)      AS opening_balance,
    COALESCE(m.period_debit, 0)         AS period_debit,
    COALESCE(m.period_credit, 0)        AS period_credit,
    -- closing: prefer parser running_balance; fallback = opening + net movement
    COALESCE(
        c.closing_balance,
        COALESCE(o.opening_balance, 0) + COALESCE(m.period_debit, 0) - COALESCE(m.period_credit, 0)
    )                                   AS closing_balance,
    m.line_count,
    'misa'                              AS source_system
FROM movements m
LEFT JOIN opening o
    ON  o.account_code = m.account_code
    AND o.period_month  = m.period_month
LEFT JOIN closing c
    ON  c.account_code = m.account_code
    AND c.period_month  = m.period_month
```

**Zero-movement account handling:** accounts with `opening_balance` but no journal lines in a given period will have no row in `movements` — they won't appear in this model for that period. This is acceptable for now because:
- The parser only emits `opening_balance` for periods where a file was exported.
- If account 11219 has a standing 71,511 balance and no activity in July, no July export will contain it, so we can't synthesize a balance-carry-forward row without a source.
- **Mitigation in reporting layer:** when summing số dư quỹ for a period, use the last available `closing_balance` per account (LAG/LAST_VALUE in the Metabase query or mart view), not just the current period.
- Full fix (Phase 4 / later): implement a "balance carry-forward" CTE using a date spine. Out of scope for Phase 02.

### Serving step (MANDATORY after building this model)

Per memory: new dbt mart consumed by Metabase requires bootstrap serving views with Metabase stopped.

```bash
# 1. Stop Metabase
docker compose stop metabase

# 2. Run bootstrap
python transformation/scripts/bootstrap_serving_views.py

# 3. Restart Metabase
docker compose start metabase
```

Also restart `data_platform` to reload dbt manifest (new node):
```bash
docker compose restart data_platform
```

---

## dbt build steps (ordered)

```bash
# 1. Seed (already done; re-run if ref_gl_accounts.csv changed)
dbt seed --select ref_gl_accounts --profiles-dir transformation --project-dir transformation

# 2. Build dim (already built; re-run if dim_gl_account.sql changed)
dbt build --select dim_gl_account --profiles-dir transformation --project-dir transformation

# 3. Build fact_cash_movement (already built; re-run after any source change)
dbt build --select fact_cash_movement --profiles-dir transformation --project-dir transformation

# 4. Build fact_account_balance_monthly (NEW)
dbt build --select fact_account_balance_monthly --profiles-dir transformation --project-dir transformation

# 5. Regression: overhead unchanged
dbt build --select int_overhead_pool_monthly+ --profiles-dir transformation --project-dir transformation

# Full finance layer rebuild
dbt build --select tag:finance --profiles-dir transformation --project-dir transformation
```

If adding new mart columns to dim_gl_account later (e.g. `normal_side`), run with `--full-refresh`:
```bash
dbt build --select dim_gl_account --full-refresh --profiles-dir transformation --project-dir transformation
```

---

## Validation queries

### 1. Số dư quỹ recon (June-2026, cash accounts)

```sql
-- Run directly against serving DuckDB or via dbt test
SELECT
    account_code,
    opening_balance,
    period_debit,
    period_credit,
    closing_balance,
    -- Expected: closing = opening + debit - credit (cash = debit-normal)
    (opening_balance + period_debit - period_credit) AS computed_closing,
    ABS(closing_balance - (opening_balance + period_debit - period_credit)) AS discrepancy
FROM fact_account_balance_monthly
WHERE period_month = '2026-06-01'
  AND account_code LIKE '11%'
ORDER BY account_code;
-- Discrepancy should be 0 for all cash accounts; non-zero means parser running_balance mismatch
```

Expected for June-2026:
- Aggregate `SUM(period_debit)` for 111%/112% ≈ 464.4M
- Aggregate `SUM(period_credit)` ≈ 434.0M
- Net movement ≈ +30.4M

### 2. fact_cash_movement recon

```sql
SELECT
    direction,
    is_internal_transfer,
    SUM(amount) AS total_amount,
    COUNT(*) AS lines
FROM fact_cash_movement
WHERE period_month = '2026-06-01'
GROUP BY direction, is_internal_transfer
ORDER BY direction, is_internal_transfer;
-- External inflow (is_internal_transfer=false) ≈ 464.4M
-- External outflow (is_internal_transfer=false) ≈ 434.0M
```

### 3. Overhead 642 regression (MUST PASS before and after any change)

```python
# Run from project root; requires DBT_DATA_LAKE_PATH in env
import duckdb, os
lake = os.environ["DBT_DATA_LAKE_PATH"]
conn = duckdb.connect(read_only=False)
res = conn.execute(f"""
    SELECT SUM(debit) AS total_debit, COUNT(*) AS rows
    FROM read_parquet(
        '{lake}/misa_raw/account_ledger/ingest_method=file_drop/**/*.parquet',
        hive_partitioning=1, union_by_name=true
    )
    WHERE account LIKE '642%' AND year = 2026 AND month = 6
""").fetchone()
assert res[0] == 104_945_218, f"REGRESSION: expected 104,945,218 got {res[0]}"
print(f"PASS: 642 June-2026 total_debit={res[0]:,}, rows={res[1]}")
```

### 4. dbt data tests to add in schema yml

Add to `transformation/models/marts/finance/schema.yml` (create if missing):

```yaml
models:
  - name: fact_account_balance_monthly
    description: "Opening + movements + closing per (account, period_month). All accounts in ledger."
    columns:
      - name: account_code
        tests: [not_null]
      - name: period_month
        tests: [not_null]
      - name: closing_balance
        tests: [not_null]
    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns: [account_code, period_month]

  - name: fact_cash_movement
    description: "1 row per journal line on cash/bank account (111x/112x)."
    columns:
      - name: posting_date
        tests: [not_null]
      - name: cash_account
        tests: [not_null]
      - name: direction
        tests:
          - accepted_values:
              values: ['inflow', 'outflow']
      - name: amount
        tests: [not_null]

  - name: dim_gl_account
    columns:
      - name: account_code
        tests: [not_null, unique]
```

---

## File ownership

| File | Action |
|------|--------|
| `transformation/models/marts/finance/fact_account_balance_monthly.sql` | CREATE (new) |
| `transformation/models/marts/finance/schema.yml` | CREATE (new) or UPDATE |
| `transformation/models/marts/core/dim_gl_account.sql` | DONE — no change needed |
| `transformation/models/marts/finance/fact_cash_movement.sql` | DONE — no change needed |
| `transformation/seeds/ref_gl_accounts.csv` | DONE — may extend with more account codes |
| `transformation/seeds/properties.yml` | DONE — no change needed |
| `transformation/models/staging/src_misa_account_ledger.sql` | DONE — no change needed |
| `transformation/models/staging/standard/std_misa_account_ledger.sql` | DONE — no change needed |
| `transformation/models/intermediate/overhead/int_overhead_pool_monthly.sql` | DONE — no change needed (filter at L45 is self-sufficient) |

---

## Risks and rollback

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `opening_balance` NULL for old partitions → balance model incomplete | High (old 642 files) | Low (only June-2026 full export has balance columns) | Filter `WHERE opening_balance IS NOT NULL` in reporting; note in model comment |
| `closing_balance` discrepancy vs MISA (rounding, transfer exclusion) | Low | Medium | Use MISA running_balance directly (not recomputed); recon query #1 above must show discrepancy=0 |
| `dim_gl_account` misses new counterpart account → NULL cashflow_line | Low | Low | Self-populating from ledger; add to ref_gl_accounts.csv if name needed |
| dbt manifest stale → new node not found | Certain (first run) | Low | `docker compose restart data_platform` before `dbt build` |
| Metabase DuckDB binder error after new mart | Certain if skipped | High | Run `bootstrap_serving_views.py` with Metabase stopped (see serving step above) |
| fact_account_balance_monthly zero-movement gap | Medium | Medium | Documented above; mitigate in reporting with LAST_VALUE; full fix = date spine in Phase 3/4 |

**Rollback:** new models (`fact_account_balance_monthly`, `schema.yml`) can be deleted without affecting any existing pipeline. `dim_gl_account` + `fact_cash_movement` are new-to-prod and also safe to drop. Overhead pipeline (`int_overhead_pool_monthly+`) has no dependency on these finance marts.

---

## Unresolved questions

1. **cashflow_line taxonomy**: current CASE in `dim_gl_account.sql` is a technical first pass. Finance team must confirm groupings match their budget line names (e.g., `'Chi lương'` vs `'Lương & BHXH'`). Schema is easily changed — affects only Phase 03 dashboard labels and Phase 04 budget join key.
2. **Zero-movement carry-forward**: should Phase 02 include a date-spine CTE to synthesize balance rows for months with no activity? Adds complexity. Defer to Phase 03 if Metabase report needs it.
3. **`normal_side` column** on `dim_gl_account`: not yet added (was in original Phase 02 spec). Required for automated sign-flip in `fact_account_balance_monthly`. Currently handled by COALESCE fallback formula. Add if P&L / balance-sheet work begins in Phase 3+.
4. **`std_misa_gl_ledger`** (original Phase 02 spec item 2): original plan called for a canonical full-ledger staging model. Currently `src_misa_account_ledger` (dedup view) serves this role directly. Skip unless a downstream model needs a different grain or aggregation not served by `src_misa_account_ledger`.
