# Phase 3: Dual-Stream Supply Tracking — Implementation Report

**Date:** 2026-07-08
**Phase file:** `plans/260708-1501-gift-purchase-sku-action-scenario/phase-03-dual-stream-supply-tracking.md`
**Status:** DONE — all 4 regression checks clean, hard gate (check d) = 0

## Files Modified

- `transformation/models/marts/core/intermediate/int_customer_sku_supply_tracking.sql`
- `transformation/models/marts/core/intermediate/int_customer_sku_supply_tracking.yml`

## Changes (file:line refs, post-edit)

1. **`ever_purchased` CTE** (sql:51-72) — new CTE before `raw_purchases`. Direct branch (52-58, `fs.is_gift_line = FALSE`) UNION pack/alias branch (60-71, mirrors `raw_purchases` Branch 2's `dim_sku_alias` join + guards).
2. **`raw_purchases`** (sql:89-137) — `LEFT JOIN ever_purchased ep` (131-132), `CASE WHEN ep.customer_key IS NOT NULL THEN 'purchased' ELSE 'gift_only' END AS supply_stream` (95), `supply_stream` added to `GROUP BY` (133-136). Had to fully-qualify the outer `SELECT`/`GROUP BY` columns with `raw.` (they were previously bare identifiers over a single-source subquery; adding the `ep` join made `customer_key` ambiguous — DuckDB Binder Error, fixed by qualifying, not by changing logic).
3. **`purchases_numbered`** (sql:140-151) — `ROW_NUMBER() PARTITION BY customer_key, sku, supply_stream` (147).
4. **`supply_stack`** (sql:158-188) — `supply_stream` added to column list (159), anchor SELECT (165), recursive SELECT (177), and join key (183-187). Stacking formula itself (`GREATEST(p.purchase_date, s.depletion_date) + p.effective_supply_days`, line 180) untouched.
5. **`last_order_ctx`** (sql:215-320) — full rework per spec: both UNION branches (224-269, 271-319) independently `LEFT JOIN ever_purchased ep` and classify `supply_stream` inline; outer `ROW_NUMBER() OVER (PARTITION BY customer_key, sku, supply_stream ORDER BY ordered_at DESC)` (223).
6. **Final SELECT** (sql:322-346) — `s.supply_stream` added to output (326), `LEFT JOIN last_order_ctx` condition includes `s.supply_stream = loctx.supply_stream` (344), `QUALIFY` partitions by `(s.customer_key, s.sku, s.supply_stream)` (346).
7. **`.yml`** — grain doc updated (yml:6-31, incl. explicit "ever_purchased is static, not chronological" note per spec), new `supply_stream` column with `not_null` + `accepted_values` tests (yml:39-46), model-level uniqueness test grain changed to `[customer_key, sku, supply_stream]` (yml:68-70).

No deviation from the phase file's prescribed SQL — the only addition beyond the spec text was qualifying `raw.` in `raw_purchases`' outer SELECT/GROUP BY to resolve a DuckDB ambiguous-column error the spec's pseudocode didn't need to spell out (the spec's snippet used bare `customer_key` before the join was added; that's exactly where the ambiguity appeared).

## dbt Run Output

```
1 of 1 START sql table model main_marts.int_customer_sku_supply_tracking ....... [RUN]
1 of 1 OK created sql table model main_marts.int_customer_sku_supply_tracking .. [OK in 0.34s]
Done. PASS=1 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=1
```

`dbt test --select int_customer_sku_supply_tracking`: 5/5 PASS (`accepted_values` on `supply_stream`, `unique_combination_of_columns(customer_key, sku, supply_stream)`, `not_null` × 3).

`data_platform` was restarted before running dbt (manifest reload for the new column/test, per project convention).

## Snapshot / Regression Methodology

Pre-change snapshot exported via read-only DuckDB connection **before any SQL edits**:
`COPY (SELECT * FROM main_marts.int_customer_sku_supply_tracking) TO '.../old_snapshot_....parquet' (FORMAT PARQUET)` — 6570 rows (old grain `(customer_key, sku)`).

Post-change: `main_marts.int_customer_sku_supply_tracking` = 6570 rows total, split `purchased`=4253, `gift_only`=2317. Total row count identical to old snapshot — expected, since `supply_stream` is a per-`(customer_key, sku)` constant (every old pair maps 1:1 to exactly one new `(customer_key, sku, supply_stream)` row, never split or duplicated).

### Check (a) — zero-gift-history customers unchanged (purchased stream)
```sql
SELECT COUNT(*) FROM (
  SELECT old.customer_key, old.sku, old.estimated_depletion_date, new.estimated_depletion_date
  FROM old_snapshot old
  JOIN new_output new
    ON old.customer_key = new.customer_key AND old.sku = new.sku AND new.supply_stream = 'purchased'
  WHERE old.estimated_depletion_date != new.estimated_depletion_date
)
```
**Result: 0 rows.** PASS.

### Check (b) — row-count parity, no silent drops
```sql
SELECT COUNT(*) FROM (SELECT DISTINCT customer_key, sku FROM old_snapshot) old
LEFT JOIN (SELECT DISTINCT customer_key, sku FROM new_output) new
  ON old.customer_key = new.customer_key AND old.sku = new.sku
WHERE new.customer_key IS NULL
```
**Result: 0 rows.** PASS — every pre-change `(customer_key, sku)` pair still exists post-change.

### Check (c) — purchased-with-gift-history unchanged (the check (a) structurally misses)
```sql
SELECT COUNT(*) FROM (
  SELECT old.customer_key, old.sku, old.estimated_depletion_date, new.estimated_depletion_date
  FROM old_snapshot old
  JOIN new_output new
    ON old.customer_key = new.customer_key AND old.sku = new.sku AND new.supply_stream = 'purchased'
  JOIN (
    SELECT DISTINCT fs.customer_key, dp.sku
    FROM main_marts.fact_sales fs
    JOIN main_marts.dim_products dp ON fs.product_key = dp.product_key
    WHERE fs.is_gift_line
  ) g ON old.customer_key = g.customer_key AND old.sku = g.sku
  WHERE old.estimated_depletion_date != new.estimated_depletion_date
)
```
**Result: 0 rows.** PASS. Population size (purchased-stream customers who DO have gift-line history for that SKU): **699 pairs** — confirms this check is exercising a real, non-trivial population, not vacuously passing.

### Check (d) — HARD GATE: open/claimed CRM task overlap with gift_only reclassification
`wh_sku_action_queue` lives in `cache.db`, `crm_task` lives in a *separate* SQLite file `crm.db` (both in the same `crm_data` docker volume, mounted `/data` in the `crm` container — not a single file, so no in-process SQL join is possible; queried both read-only and joined the results in Python instead of via SQL ATTACH):

```python
# read-only, cache.db
SELECT action_id, customer_key, sku FROM wh_sku_action_queue
# → 3898 total rows; 1087 overlap the 2317 gift_only (customer_key, sku) pairs

# read-only, crm.db
SELECT source_ref FROM crm_task WHERE status IN ('open','doing') AND source_ref IS NOT NULL
# → 18 open/doing task source_refs total

# overlap of the two sets (action_id ∈ open_refs AND action's (customer_key,sku) ∈ gift_only)
```
**Result: 0.** Both connections opened strictly read-only (`file:...?mode=ro`, `uri=True`); no writes issued; scratch files (`gift_only_pairs.csv` in `/tmp` inside the `crm` container, and the DuckDB snapshot parquet in the host `app_data/data_lake`) were deleted after the check.

**Check (d) is a PASS (0), not a blocking finding.** Deploy is not blocked by this phase's regression gate.

## Success Criteria — Explicit Verification

- [x] Output grain is `(customer_key, sku, supply_stream)`, values ∈ {'purchased','gift_only'} — confirmed via `accepted_values` test + query above.
- [x] Check (a): 0 rows.
- [x] Check (b): 0 rows.
- [x] Check (c): 0 rows (699-pair population, not vacuous).
- [x] Check (d) — HARD GATE: 0. Reported per spec; not treated as a pass by default, verified explicitly via the count above.
- [x] New `gift_only` rows exist only where `ever_purchased` is false — true by construction (supply_stream is derived directly from the `ever_purchased` LEFT JOIN in `raw_purchases`/`last_order_ctx`; there is no code path that could set `gift_only` while `ever_purchased` matched). An additional empirical cross-check (joining gift_only pairs back against a fresh `is_gift_line=FALSE` purchase scan) was attempted but blocked by a transient DuckDB single-writer lock (another process — likely a Dagster daemon/sensor tick inside `data_platform` — held the write lock across ~8 retries over 30s). Not re-attempted further to avoid contending with production Dagster activity; not required by the phase's 4 mandatory checks, and the guarantee is structural (single `CASE WHEN ep.customer_key IS NOT NULL ...` expression, same `ever_purchased` CTE used everywhere), not empirically inferred.
- [x] `last_order_ctx`'s two UNION branches both join `ever_purchased` and emit `supply_stream`; final join uses 3-column key — verified by reading the edited file back (sql:215-320, 340-346).
- [x] Recursive CTE still terminates correctly, same `rn`-based traversal per stream — `dbt run` completed without recursion errors/timeouts; rn-partitioning logic unchanged except for the added `supply_stream` key.
- [x] `dbt run --select int_customer_sku_supply_tracking` succeeds — see output above.

## Deviations from Spec

None in the SQL logic. One necessary syntactic fix not spelled out in the phase file's pseudocode: qualifying `raw_purchases`' outer `SELECT`/`GROUP BY` columns with `raw.` after adding the `ever_purchased` join (DuckDB ambiguous-column Binder Error otherwise — `ep.customer_key` and `raw.customer_key` both in scope). This does not change any join, filter, or grouping semantics — purely a qualifier fix.

## Cleanup

- Deleted `old_snapshot_int_customer_sku_supply_tracking.parquet` and `gift_only_pairs.csv` from the host `app_data/data_lake` (bind-mounted into `data_platform`) after all checks completed.
- Deleted `/tmp/gift_only_pairs.csv` from inside the `crm` container.
- No writes were made to `cache.db` or `crm.db` — both opened strictly read-only for check (d).

## Not Touched (per constraints)

- No changes under `crm/` (Phase 5 scope).
- No changes to Dagster schedules/reverse-ETL crons.
- Recursive CTE stacking formula untouched.

## Unresolved Questions

None. Both the plan's own Deploy Sequencing (Phase 3+4 same deploy window, reverse-ETL paused until diff verified) and the Phase 5 CRM-side wiring remain out of scope for this phase, as specified.
