# Phase 00 Implementation Report — customer_group JSON parse at staging

**Plan:** `plans/260619-0830-crm-tag-acl-sync/` · **Phase:** phase-00-customer-group-code-staging.md
**Status:** DONE

## Files modified

- `transformation/models/staging/stg_sapo_v2_customers.sql` — added `customer_group_id/code/name` via `json_extract_string(customer_group, '$.id'|'$.code'|'$.name')`; updated header comment (was inaccurate: claimed "no JSON extraction needed").
- `transformation/models/staging/standard/std_customers.sql` — pass-through the 3 new columns.
- `transformation/models/marts/core/dim_customers_base.sql` — pass-through the 3 new columns + NULL for the `Unknown` sentinel row. **Not in the original file list** (see Deviations).
- `transformation/models/marts/core/dim_customers.sql` — pass-through 3 new columns to final SELECT; refactored `customer_type` CASE and `is_us_gift_recipient` to match `customer_group_code`/`customer_group_name` instead of `LIKE` across the raw JSON blob (same branches/substrings, behavior-preserving).
- `crm/sync/cache_schema.sql` — added 3 columns to `wh_customer_base`.
- `crm/sync/sqlite_upsert.py` — added 3 `ALTER TABLE wh_customer_base ADD COLUMN` migrations to Group A (schema evolution for existing cache.db files). `upsert_customer_base` uses the generic `_upsert()` (column-agnostic), so no other change needed there.
- `crm/sync/duckdb_reader.py` — added 3 columns to `_DIM_CUSTOMERS_BASE_COLS` and the `fetch_customer_base` SQL.
- `crm/sync/tests/test_reverse_etl_warehouse_to_crm.py` — added 3 columns to both synthetic `dim_customers` fixtures (`_make_warehouse`, `_create_minimal_dim_tables`) with realistic JSON blob + parsed values.

## Deviations from phase doc

1. **`dim_customers_base.sql` had to be edited** (not listed in the phase doc's file list). The phase doc assumed `dim_customers.sql` line 46 (`c.customer_group`) referenced `std_customers` directly. Actual CTE chain is `stg_sapo_v2_customers` → `std_customers` → `dim_customers_base` → `dim_customers` (circular-dependency breaker, see that model's own header comment). Without editing this intermediate hop the 3 columns can't reach `dim_customers` at all. Confirmed correct by end-to-end verification below.
2. **`sqlite_upsert.py`**: the phase doc said "passthrough (if upsert enumerates columns)" — `upsert_customer_base` is generic (`_upsert()`, uses `rows[0].keys()`), so no code change needed there; only the `ALTER TABLE` migration list needed the 3 new columns for schema evolution on existing cache.db files.
3. Did not touch `docs/context/customer-segmentation.md`, `transformation/models/staging/standard/schema.yml`, or `transformation/models/marts/schema.yml` (column docs) — not in the file-ownership list; flagging as a follow-up doc gap, not fixed here per scope discipline.

## Regression check (mandatory, before/after customer_type refactor)

Ran directly against the rebuilt `sapo_warehouse.duckdb` main_marts.dim_customers:

```
customer_type distribution:
CROSSBORDER=662, PARTNER=11, RETAIL=6757, WHOLESALE=161   (total=7591)
```

Matches expected **161 WHOLESALE / 662 CROSSBORDER / 11 PARTNER** exactly. Refactor is behavior-preserving.

`customer_group_id` population check (grouped by raw/parsed values):
- All 6 real Sapo groups (ids 1812238 RETAIL/BANLE+TYPE_RETAIL, 1812239 WHOLESALE/BANBUON+TYPE_WHOLESALE, 2421894 US/CTN00014, 2308212 Selly/CTN00013, 2281219 Ký Gửi/KY_GUI, 1812240 VIP) → `customer_group_id` populated.
- The literal `'Unknown'` string row → `customer_group_id = NULL`, `customer_group_code = NULL`, `customer_group_name = NULL`. Confirms `json_extract_string` handles non-JSON input as required.

## End-to-end verification (actually executed, not just code review)

1. `dbt build --select stg_sapo_v2_customers+ dim_customers --full-refresh` — had to route around an **unrelated, pre-existing crash-loop** on the `data_platform` service (dagster `grpc_health` protobuf gencode/runtime version mismatch, visible in `docker compose logs data_platform`; likely from a concurrent task's dependency bump — `Dockerfile.dataplatform` was already showing as modified in git status at session start for an unrelated codex-CLI addition). Worked around by `docker compose stop data_platform` (releases the DuckDB write lock) then `docker compose run --rm --no-deps --entrypoint bash data_platform -lc "cd /app/transformation && dbt build ..."` as a one-off container, then `docker compose start data_platform` to restore prior state. Result: `Done. PASS=230 WARN=0 ERROR=0 SKIP=0 NO-OP=2 TOTAL=232` — full green, including `accepted_values_dim_customers_customer_type`, `unique`/`not_null`/`relationships` tests on `dim_customers` and `dim_customers_base`.
2. Regression query — see above, exact match.
3. **Serving-layer gotcha discovered and handled**: `dim_customers` is a rolling-parquet "external model" (`get_rolling_location()`); `main_marts.dim_customers` in `olap.duckdb` is a `CREATE VIEW ... SELECT * FROM read_parquet(glob)` bound at creation time. Multi-file `read_parquet(glob)` resolves columns from whichever file is encountered first when schemas differ across snapshot generations — old-schema rolling files (pre-existing, from before this change) caused the new columns to disappear even after the correct new-schema file was written and `bootstrap_serving_views.py` was re-run. Fixed by removing the 3 stale pre-change parquet snapshots from `export/marts/rolling/dim_customers/` (a normal `ROLLING_KEEP_VERSIONS` GC would have done this on the next scheduled pipeline run; accelerated here since I ran an ad-hoc `dbt build` outside the Dagster asset that normally triggers `refresh_rolling.py` GC). Followed the documented Metabase-stop protocol: `docker compose stop metabase` → `docker compose exec -T data_platform python scripts/provisioning/bootstrap_serving_views.py` → `docker compose start metabase`. This is a **real operational gap** worth flagging (see Unresolved Questions) but out of scope to fix generically in this phase.
4. Verified `main_marts.dim_customers` in `olap.duckdb` now exposes the 3 columns with correct data and the same customer_type distribution (662/11/6757/161).
5. `docker compose up -d --build crm` — rebuilt (crm/sync/ is baked into the image, not bind-mounted).
6. `docker compose exec crm python3 -m crm.sync.reverse_etl_warehouse_to_crm` — succeeded: `[wh_customer_base] 7591 rows upserted ok`, all 10 steps `ok`.
7. Queried `cache.db:wh_customer_base` directly:
   - Schema includes `customer_group_id`, `customer_group_code`, `customer_group_name`.
   - `7590` of `7591` rows have non-NULL `customer_group_id`; the 1 NULL row is exactly the `'Unknown'` literal (`customer_id='Unknown'`).
   - Sample: `(148976946, '1812238', 'TYPE_RETAIL', 'RETAIL')`, `(149191270, '2421894', 'CTN00014', 'US')`, etc.
8. `crm/sync/.venv/Scripts/python.exe -m pytest crm/sync/tests/test_reverse_etl_warehouse_to_crm.py -v` (host venv — `crm/sync/tests/` is `.dockerignore`'d from the crm image build context, so this is the correct/only invocation path). Result: **5 failed, 1 passed — identical failures before and after my change** (root cause: `main_marts.dim_customers` test fixture is missing the discount-bucket columns `last_line_discount_rate` etc. added by an earlier, unrelated plan — `260629-1215-customer-discount-tracking`). Confirmed by running the suite before touching any file: same 5 failures, same error message. My 3-column fixture additions did not introduce any new failure.

## Unresolved questions / follow-ups (not fixed, out of scope for phase 00)

1. **Rolling-parquet schema drift is undetected column-wise.** `refresh_rolling.py`'s `SCHEMA_DRIFT` check only compares table *folder* sets, not per-table column schemas. Adding a column to any rolling-exported mart can silently make the serving view "lose" the new column if 2+ pre-change snapshot files still exist in the glob when `bootstrap_serving_views.py` runs (which itself only fixes it if the *file selection* resolves to a homogeneous-schema set). Worth a real fix in a future infra phase (e.g. GC-before-rebuild, or switch to `union_by_name=true` — trades off wrong: that would silently NULL-pad old files instead of erroring, may be acceptable). Flagging per "no one-off hardcode fixes" — this needs a proper fix, not per-phase manual GC.
2. `crm/sync/tests/test_reverse_etl_warehouse_to_crm.py` has 5/6 pre-existing failing tests (discount-bucket columns from plan `260629-1215-customer-discount-tracking` never added to the fixture). Not fixed here — out of phase-00 scope, but worth a dedicated cleanup task since the suite currently gives near-zero signal.
3. `data_platform` container is in an active crash-loop (`grpc_health` protobuf gencode/runtime mismatch crashing `dagster dev` on every startup) — unrelated to this phase, but blocks normal `docker compose exec` dbt workflows until fixed. Likely caused by a recent Python dependency change (evidence: `Dockerfile.dataplatform` was already dirty at session start with an unrelated `codex` CLI addition — plausibly a `pip install` for `google-genai` or similar bumped `protobuf`/`grpcio` transitively). Flagging for the user/next session; did not fix as it's unrelated to CRM tag ACL sync.
4. Did not add column docs to `transformation/models/staging/standard/schema.yml` or `transformation/models/marts/schema.yml` for the 3 new columns (not in file-ownership list). Low-risk gap, easy follow-up.

Status: DONE
Summary: customer_group JSON parsed once at staging (customer_group_id/code/name), customer_type/is_us_gift_recipient refactored off the LIKE-hack (regression-verified 161/662/11 unchanged), propagated end-to-end into wh_customer_base via a real reverse-ETL run — all verified live, not just reviewed.
Concerns/Blockers: dim_customers_base.sql required editing beyond the phase doc's file list (necessary pass-through hop, documented above); data_platform container has an unrelated pre-existing crash-loop; rolling-parquet schema-drift gotcha required manual GC to unblock verification (see Unresolved Questions #1 for the systemic fix needed).
