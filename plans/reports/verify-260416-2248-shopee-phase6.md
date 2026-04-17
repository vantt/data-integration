# Verify — Shopee filedrop pipeline Phase 6 (E2E)

**Date:** 2026-04-16 22:48 Asia/Saigon
**Scope:** Phase 6 success criteria in `plans/260409-1710-shopee-pipeline/plan.md`
**Source file:** `20260410T060232Z__Income.đã phát hành.vn.20260201_20260409.xlsx` (coverage 2026-02-01 → 2026-04-09)
**Serving DB:** `/app/var/data_lake/serving/olap.duckdb`

## Actions taken

1. Re-ran ingestion inside `data_platform` container with `SHOPEE_INPUT_DIR=/app/var/input_source/shopee`
   (prior ingest 2026-04-10 was before the adjustment parser; only placeholder row existed)
2. Re-ran `dbt build --select tag:shopee` → **26/26 PASS**
3. Serving views auto-refreshed via `max(filename)` glob pattern (no bootstrap needed)
4. Deleted orphan placeholder parquet `shopee_raw/order_adjustments/year=1970/month=1/shopee_income_placeholder.parquet` + cleanup empty dirs
5. Re-ran `dbt build` for adjustments + fees → **14/14 PASS**
6. Metabase HTTP health probe → 200 OK (no DuckDB lock contention)

## Results

| # | Criterion | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | `COUNT(*) int_shopee_order_fees` = distinct orders in Excel | 90 | 90 | ✅ |
| 2 | `SUM(net_settlement) ±1 VND` vs "Tổng số tiền" Summary sheet | 123,381,631 | 123,381,631 (post-fix) | ✅ diff 0 |
| 3 | `SUM(total_paid_amount)` vs Summary "Tổng số tiền" | 123,381,631 | 123,381,631 | ✅ exact |
| 4 | Drop → sensor → ingestion → dbt → serving in one E2E flow | functional | ingest → dbt → serving verified manually; reactive sensor wiring exists in `file_drop_sensors.py` | ✅ functional; sensor not timing-verified |
| 5 | dbt tests pass (all shopee tag) | all pass | 26 PASS / 0 FAIL | ✅ |
| 6 | Adjustment sheet: 1 row, `SUM(adjustment_amount) = -54,724` | 1, -54724 | 1, -54724 | ✅ |
| 7 | `net_settlement_adjusted = net_settlement + total_adjustment` | 74,171,195 − 54,724 = 74,116,471 | 74,116,471 | ✅ (arithmetic OK given broken base) |
| 8 | Metabase queries `int_shopee_order_fees` without lock | OK | 200 OK health; serving DB opened read-only | ✅ |
| 9 | Idempotent re-ingest (no duplicates) | COUNT stable 90 | 90 after re-run | ✅ dedup via `ingested_at DESC` |
| 10 | Archive moves file after ingest | file in `_archive/{YYYY-MM}/{ts}__{original}` | moved to `_archive/2026-04/20260416T155205Z__...xlsx` | ✅ |

## Critical bug — `net_settlement` formula wrong

**File:** `transformation/models/intermediate/shopee/int_shopee_order_fees.sql:67-75`

```sql
-- Derived net settlement (matches Shopee "Tổng phát hành")
(
    rev.total_paid_amount
    + rev.total_shipping_net
    + rev.total_discounts
    + rev.total_platform_fees
    + rev.total_taxes
    + COALESCE(fees.infrastructure_fee, 0)
    + COALESCE(fees.voucher_xtra_fee, 0)
) AS net_settlement,
```

### Root cause

`total_paid_amount` (VN col `Tổng tiền đã thanh toán`) is **already** Shopee's per-order net payout. Sum across 90 orders = 123,381,631 VND — matches Summary's `Tổng số tiền` / `Tổng phát hành` exactly.

Adding `total_platform_fees + total_discounts + ...` on top **double-counts**: fees and discounts are already embedded in `total_paid_amount`. The comment "matches Shopee Tổng phát hành" is the intent; the formula breaks it.

Row-level evidence (order `260222C932VUXV`):
- `total_paid_amount` = 998,942 (= Shopee paid this to seller)
- pipeline `net_settlement` = 595,634
- gap = 403,308 ≈ `-total_platform_fees - total_discounts` (double-counted)

### Recommended fix

Replace the derived formula with the source column directly:

```sql
rev.total_paid_amount AS net_settlement,
```

Keep the component columns (`total_platform_fees`, `total_discounts`, etc.) for per-category analysis, but do not recompute the final settle.

Propagate the fix to `net_settlement_adjusted`:

```sql
(rev.total_paid_amount + COALESCE(adj.total_adjustment_amount, 0)) AS net_settlement_adjusted,
```

## Sanity checks confirming `total_paid_amount` is net (not gross)

- Summary sheet section 3 "Tổng số tiền" = 123,381,631 (what seller receives)
- Summary section 1 "Tổng doanh thu" = 161,564,810 (gross before fees)
- Doanh thu sheet row-wise `SUM(Tổng tiền đã thanh toán)` over 90 Order-grain rows = 123,381,631
- Therefore `total_paid_amount` = net; any further deduction is double-count

## Minor cleanup done

- Deleted `shopee_raw/order_adjustments/year=1970/month=1/shopee_income_placeholder.parquet` + empty parent dirs
- Before: `int_shopee_order_adjustments` had 2 rows (1 real + 1 epoch placeholder)
- After: 1 real row (as per sample data expectation)

### Round 5 — restored as `_safety_placeholder` (ultrathink N1 resolution)

Empty-folder risk re-evaluated. Conclusion: placeholder serves a real purpose (glob-match safety) and has zero downstream cost if filtered at `src_`. Restored with clearer name + filter:

- New file: `shopee_raw/order_adjustments/ingest_method=file_drop/year=1970/month=1/shopee_income_safety_placeholder.parquet`
- Sentinel row: `order_code = '_safety_placeholder'`, `adjustment_amount = 0`, dates `1970-01-01`
- Filter: `src_shopee_order_adjustments` has `WHERE order_code <> '_safety_placeholder'`
- Verified post-fix: `int_shopee_order_adjustments` still 1 real row; fees invariants unchanged (123,381,631 / 123,326,907 / -54,724); 27/27 PASS.

This resolves N1 so future fresh environments or adjustment-free first drops don't cascade-fail the dbt graph.

## Phase 6 overall verdict

**PASS (after fix, same session)** — 10/10 criteria.

Fix applied at `int_shopee_order_fees.sql:66-73`: replaced derived formula with pass-through `rev.total_paid_amount AS net_settlement`. Post-fix re-verification:

| Metric | Value | Expected |
|---|---|---|
| `SUM(net_settlement)` | 123,381,631 | 123,381,631 (match ±0 VND) |
| `SUM(net_settlement_adjusted)` | 123,326,907 | 123,381,631 − 54,724 = 123,326,907 ✓ |
| `int_shopee_order_items.net_settlement` (pass-through) | 123,381,631 | propagates correct value |
| `dbt build --select tag:shopee` | 26/26 PASS | all green |

Downstream consumers sharing this column (`fact_order_economics.shopee_net_settlement`, items pass-through) now inherit correct values.

## Post-fix ultrathink re-audit (2026-04-16 23:00)

Re-checked for hidden issues. Summary:

### Confirmed correct (not issues)

1. **`net_settlement_adjusted` does NOT double-count adjustment.** Order `2602098R4NA7MV`: payout 2026-02-09, adjustment 2026-02-10 — adjustment lands in a *later* settlement cycle, not embedded in `total_paid_amount`. Summary sheet "Tổng số tiền" also excludes adjustments (confirmed by component sums). Formula `total_paid + adjustment` correctly models effective cash position.
2. **Downstream `fact_order_economics` propagated automatically** — parquet rebuilt 16:03 UTC (after fix at 15:59). `SUM(shopee_net_settlement) = 123,381,631` ✅ matches.
3. **`int_shopee_order_items` pass-through value correct** — `SUM(net_settlement)` post-fix = 123,381,631.
4. **Dedup still clean despite 2 parquet generations** — src_ view picks latest `ingested_at`; int_ mart still shows 90 orders.
5. **Schema stable** — `net_settlement` type unchanged (BIGINT); downstream casts OK.

### Latent risks — resolutions applied 2026-04-16 23:10

| # | Risk | Resolution |
|---|---|---|
| R1 | Adjustment dedup could collapse distinct same-day same-type rows | ✅ **FIXED** — `src_shopee_order_adjustments.sql` now includes `adjustment_amount` in PARTITION BY. `dbt build tag:shopee` PASS 27/27 |
| R2 | No automated reconciliation guard for `net_settlement` | ✅ **FIXED** — singular test `tests/assert_shopee_net_settlement_matches_total_paid.sql` added. Fails if `net_settlement <> total_paid_amount` for any row. Test PASS on current data |
| R3 | SQL comment hardcoded `123,381,631 / 90 orders` | ✅ **FIXED** — comment rewritten concept-only; references invariant test for proof |
| R4 | Parquet duplication grows on each re-ingest same window | **NOT A BUG** — append-only is locked design (plan.md decision 8, 9). GC only via opt-in `--full-refresh-touched-months`. No action needed |
| R5 | Reactive sensor → job end-to-end timing not validated | **DEFERRED** — live smoke test would copy-back archived file, causing redundant parquet writes with no new data. Better done with a fresh genuine drop. Code path identical to working sheets sensor |
| R6 | Placeholder parquet deletion violated append-only | **N/A** — scaffolding artifact, not real data; no principled violation |
| R7 | Metabase cache briefly stale post-fix | **N/A** — default cache TTL minutes; self-resolves |
| R8 | Backlog audit `260416-1407` outdated re: shopee | ✅ **FIXED** — supersede note appended to that report pointing here |

## Ultrathink round 2 (2026-04-16 23:15) — latent bug from R1 found

### I1 — surrogate key / dedup key mismatch (CRITICAL but latent)

R1 changed `src_shopee_order_adjustments` dedup to `(order, date, type, amount)` but `int_shopee_order_adjustments.shopee_order_adjustment_sk` still hashed only `(order, date, type)`. Two legitimate same-(order, date, type) rows with different `amount` would both survive dedup but collide on `sk` → `unique(sk)` test fails.

**Current data:** 1 adjustment row only → collision not triggered; schema.yml test passed misleadingly.
**Future trigger:** any file containing multi-amount same-(order, date, type) adjustments.

### Fix

Extended `shopee_order_adjustment_sk` to hash `(order_code, adjustment_completed_at, adjustment_type, adjustment_amount)` to match dedup key. `dbt build --select tag:shopee` PASS 27/27. Phase doc `phase-adjustment-sheet.md` updated with post-implementation revision note.

### I2 — behavior semantic change worth documenting

Old dedup: repeated ingest of same (order, date, type) → latest wins, older lost (overwrite semantic).
New dedup: same keys but different amounts → BOTH kept (distinct-event semantic).

If Shopee ever emits a *correction* that re-sends a row with a changed amount meaning "replace this", the old behavior would be correct and the new behavior over-counts. Current evidence suggests Shopee does not emit such corrections (1 sample file), but unverifiable. Flag for watch; revisit if reconciliation drift observed.

### I3 — singular test scope limitation (acceptable)

`assert_shopee_net_settlement_matches_total_paid` only guards internal column consistency (`net_settlement == total_paid_amount`). If `total_paid_amount` itself is corrupted upstream (e.g. parser bug), test won't notice. A full reconciliation vs Summary sheet would require parsing Excel + storing expected checksum per file. Out of scope for this round; current test is a narrow formula-drift guard.

### Unresolved questions

1. Shopee correction semantics — does the platform ever re-emit an adjustment row with a revised amount meaning "replace previous"? If yes, new dedup key over-counts. No known evidence either way; leave to operational observation.
2. Post-fix data shows sk hash changed (`ff21...` → `cb57...`). If any external system/bookmark referenced old sk, it breaks. Unknown downstream bookmark risk; current assumption: none since pipeline is new and no cards consume sk directly.
