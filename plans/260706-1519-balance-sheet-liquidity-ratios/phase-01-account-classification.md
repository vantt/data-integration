# Phase 1 — Chart-of-Account Classification

**Depends on:** none
**Blocks:** phase-02

## Context

`dim_gl_account.sql` (`transformation/models/marts/core/dim_gl_account.sql`) already has `account_class = LEFT(account_code, 1)` and `is_cash`. This phase adds the flags needed to compute a balance sheet: which accounts are current vs non-current assets/liabilities, which is equity, which is inventory, which is the trade-receivable account for DSO, and which side (debit/credit) is each account's normal balance — needed in phase-02 to fix the sign-inversion bug described in `plan.md`.

## Verified real account universe (2026-07-06, `olap.duckdb`, accounts with real posting activity in `fact_account_balance_monthly`)

```
class 1 (assets, current):     1111, 11212, 11219, 11221, 131, 1331, 13681, 1386, 13888, 141, 156, 157
class 2 (assets, non-current): 2421, 2422
class 3 (liabilities):         331, 33311, 3335, 3341, 3348, 33682, 3383, 3384, 3385, 33881
class 4 (equity):              4111, 4211, 4212
class 5 (revenue):             51111, 51113, 5113, 5153
class 6 (expense):             6321, 6323, 6351, 64211, 64212, 642121-642124, 64213, 64214, 64217, 642172-642288 (many sub-codes)
class 7 (other income):        7118
class 8 (other expense):       8112, 8118
```

No `class 3` account in this list is a long-term liability (no `34x`/`343` loans/bonds seen) — every class-3 account observed is a **current** liability (AP, tax, payroll, insurance payable). Design the classification generically by VAS sub-code rule anyway (see below), not by hardcoding "class 3 = current", so a future `341`/`343` account classifies correctly without a code change.

## Implementation

Edit `transformation/models/marts/core/dim_gl_account.sql`. Add these columns to the final `SELECT`:

```sql
-- Defensive: dim's account_universe unions `account` + `offset_account`; offset_account parsing
-- can leak garbage numeric "codes" (7-10 digit amounts) for unparseable multi-line entries.
-- Real VAS account codes are never longer than 6 digits. Flag, don't silently drop (other
-- consumers of dim_gl_account may rely on full row count).
(LENGTH(a.account_code) <= 6)                        AS is_valid_vas_code,

-- Normal balance side — needed to sign-correct closing_balance in fact_balance_sheet_monthly
-- (closing_balance = debit_balance - credit_balance is only "positive-normal" for classes 1/2/6/8;
-- classes 3/4/5/7 are credit-normal and will show negative closing_balance for a normal position).
CASE
    WHEN LEFT(a.account_code, 1) IN ('1', '2', '6', '8') THEN 'debit'
    WHEN LEFT(a.account_code, 1) IN ('3', '4', '5', '7') THEN 'credit'
    ELSE NULL
END                                                    AS normal_balance_side,

-- Current vs non-current asset (class 1 = current by VAS structure; class 2 = non-current)
(LEFT(a.account_code, 1) = '1')                       AS is_current_asset,
(LEFT(a.account_code, 1) = '2')                       AS is_non_current_asset,

-- Current vs non-current liability — class 3, split by 2-digit sub-code.
-- 34x = long-term borrowings/bonds (vay & nợ thuê tài chính, trái phiếu) → non-current.
-- Everything else in class 3 (331 AP, 333x tax, 334x payroll, 335/336/338x other payable) → current.
(LEFT(a.account_code, 1) = '3' AND LEFT(a.account_code, 2) NOT IN ('34')) AS is_current_liability,
(LEFT(a.account_code, 1) = '3' AND LEFT(a.account_code, 2) IN ('34'))     AS is_non_current_liability,

(LEFT(a.account_code, 1) = '4')                       AS is_equity,

-- Inventory (Hàng tồn kho, VAS class-1 sub-range 150-159)
(LEFT(a.account_code, 2) = '15')                      AS is_inventory,

-- Trade receivable from customers — 131 only (NOT 136/138 "other receivable", which are not
-- part of the standard DSO formula's Accounts_Receivable).
(a.account_code = '131' OR LEFT(a.account_code, 3) = '131') AS is_trade_receivable,
```

Keep all existing columns (`account_class`, `is_cash`, `cashflow_line`) unchanged — additive only, same pattern as the phase-02 changes in `plans/archive/260707-1207-misa-gl-infrastructure/phase-02-gl-modeling.md`.

## Validation

1. `dbt build --select dim_gl_account` — confirm no error.
2. Query: every account_code present in `fact_account_balance_monthly` must resolve to exactly one of `is_current_asset / is_non_current_asset / is_current_liability / is_non_current_liability / is_equity` OR be revenue/expense (class 5/6/7/8, expected — excluded from balance sheet, not an error). No account with real posting activity should end up with `normal_balance_side IS NULL`.
3. Spot-check against the verified list above: `131` → `is_trade_receivable=true, is_current_asset=true, normal_balance_side='debit'`. `331` → `is_current_liability=true, normal_balance_side='credit'`. `156`/`157` → `is_inventory=true`.
4. Add a dbt schema test (`not_null` + `accepted_values` where sensible) on the new columns for accounts joined from `fact_account_balance_monthly` — do not enforce on the full dim universe (garbage offset-only codes are expected to fail cleanly, e.g. `is_valid_vas_code=false`, and that's fine).

## Files touched

- `transformation/models/marts/core/dim_gl_account.sql` (edit)
- `transformation/models/marts/core/schema.yml` (add column tests, if this pattern exists for the dim already — check first)
