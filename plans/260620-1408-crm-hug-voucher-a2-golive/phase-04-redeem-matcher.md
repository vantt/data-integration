---
title: "P4 — Redeem matcher: fact_orders × crm_hug_voucher → redeemed_at/order_code"
status: pending
priority: P1
effort: 60m
---

## Context Links

- Plan overview: `plans/260620-1408-crm-hug-voucher-a2-golive/plan.md`
- `/admin/refresh` pipeline: `crm/src/adapters/inbound/http/admin_handler.py`
- Refresh sequence after P3: `reverse_etl → hug_resolve → hug_voucher_issue → [NEW] hug_voucher_redeem → hug_customer_push → sync_parties → rebuild_search_index`
- `fact_orders.order_coupon_code` extraction: `transformation/models/staging/src_sapo_v2_orders.sql:157` (nested: `$.order_coupon_code.coupon_code`)
- `fact_orders.customer_id`: already present in mart
- crm_hug_voucher schema: `crm/migrations/0025_hug_voucher_ledger.up.sql` (P1) — PK `(code, customer_id)`, `redeemed_at TEXT`, `order_code TEXT`
- Watermark pattern: `crm/src/hug/identity_resolver_io.py:55–102`, `crm/src/hug/voucher_issuer.py` (P3)
- DuckDB read-only rule: `feedback_duckdb_always_readonly.md` — always `read_only=True`
- reverse_etl `wh_order_hdr` (cache.db, incremental): `crm/sync/reverse_etl_warehouse_to_crm.py:167`

## Overview

**Priority:** P1 (closes the redeem loop — without this, B4 never fires)
**Status:** pending
**Depends on:** P1 (crm_hug_voucher table exists)

After a customer uses coupon code HUG50, Sapo records it on the order. The ingest pipeline extracts `order_coupon_code` into `fact_orders`. This phase adds a local job that:

1. Reads `fact_orders` from `olap.duckdb` (read-only) for orders with non-null `order_coupon_code`.
2. Joins with `crm_hug_voucher` on `(customer_id, order_coupon_code = code)` where `redeemed_at IS NULL`.
3. For each match, sets `redeemed_at = order_date` and `order_code = order.order_code` on the ledger row.
4. Uses an `ordered_at`-based watermark to scan only new orders (same high-water mark pattern as other refresh steps).

Idempotent: if the row already has `redeemed_at` set, the UPDATE is a no-op (WHERE clause filters it out).

## Architecture

```
/admin/refresh (after P3 hug_voucher_issue):
  hug_voucher_redeem_run()
    │
    ├─ olap.duckdb (read_only)
    │    fact_orders: customer_id, order_coupon_code, order_code, ordered_at
    │    WHERE order_coupon_code IS NOT NULL AND ordered_at > watermark
    │
    └─ crm.db (read-write)
         crm_hug_voucher: SELECT unmatched rows (redeemed_at IS NULL)
         UPDATE crm_hug_voucher SET redeemed_at=?, order_code=?
         WHERE code=? AND customer_id=? AND redeemed_at IS NULL
```

Match key: `(fact_orders.customer_id, fact_orders.order_coupon_code)` = `(crm_hug_voucher.customer_id, crm_hug_voucher.code)`.

One customer can only redeem a given code once (`once_per_customer` enforced by Sapo at checkout). If somehow two orders arrive with the same `(customer_id, coupon_code)` combo, the first match wins (WHERE redeemed_at IS NULL means only the first UPDATE fires).

## Requirements

- Read `fact_orders` from olap.duckdb with `read_only=True`.
- Watermark on `fact_orders.ordered_at` (TIMESTAMPTZ): only scan orders newer than last processed. Persist watermark to `{CRM_DATA_DIR}/hug_redeem_watermark.json`.
- Update `crm_hug_voucher` in-place (no new rows). Only touch rows where `redeemed_at IS NULL`.
- Best-effort: failure must not abort `hug_customer_push` (wrap in try/except in admin_handler).
- Module < 200 lines. Pure Python, testable with in-memory SQLite + tmp DuckDB.
- `fact_orders.customer_id` may be NULL for guest orders — skip those (no match possible).

## Related Code Files

**Create:**
- `crm/src/hug/voucher_redeem_matcher.py` — match logic + watermark I/O
- `crm/src/tests/test_hug_voucher_redeem_matcher.py` — unit tests

**Modify:**
- `crm/src/adapters/inbound/http/admin_handler.py` — add `_hug_voucher_redeem_run()` + wire into `_run_refresh` after `hug_voucher_issue`

## Implementation Steps

### Step 1 — `crm/src/hug/voucher_redeem_matcher.py`

```python
def match_redeemed_vouchers(
    crm_conn: sqlite3.Connection,
    olap_path: str,
    watermark_path: str,
) -> int:
    """Scan new fact_orders for coupon codes matching issued crm_hug_voucher rows.

    Returns count of rows updated (redeemed_at set).
    """
```

Internal logic:
1. Load watermark `since_ts` (ISO-8601 UTC string, default `'1970-01-01T00:00:00Z'`).
2. Open `olap_path` with `duckdb.connect(read_only=True)`.
3. Query:
   ```sql
   SELECT customer_id, order_coupon_code AS code, order_code,
          ordered_at::TEXT AS ordered_at
   FROM main_marts.fact_orders
   WHERE order_coupon_code IS NOT NULL
     AND customer_id IS NOT NULL
     AND ordered_at > TIMESTAMPTZ '{since_ts}'
   ORDER BY ordered_at ASC
   ```
   (Use schema-qualified `main_marts.fact_orders` per `feedback_metabase_duckdb_schema_field_filter.md` convention — consistent with serving layer access.)
4. Close DuckDB connection (in `finally`).
5. For each row, execute against `crm_conn`:
   ```sql
   UPDATE crm_hug_voucher
   SET redeemed_at = ?, order_code = ?
   WHERE code = ? AND customer_id = ? AND redeemed_at IS NULL
   ```
   Accumulate `rowcount` sum.
6. `crm_conn.commit()` after all updates.
7. Advance watermark to `max(ordered_at)` of scanned rows. Save watermark.
8. Return total rows updated.

Edge cases:
- `fact_orders` table / `order_coupon_code` column absent (pre-extract-coupon) → catch DuckDB exception, log, return 0.
- Empty result set → commit no-op, advance watermark to `since_ts` (no change).
- `crm_hug_voucher` empty (P3 not yet run) → UPDATE matches nothing; harmless.

### Step 2 — `admin_handler.py`: add `_hug_voucher_redeem_run()`

After `_hug_voucher_issue_run()` function:

```python
def _hug_voucher_redeem_run() -> None:
    """Match redeemed coupon codes in fact_orders → set crm_hug_voucher.redeemed_at.

    Runs AFTER hug_voucher_issue so freshly-issued rows can be matched in the same cycle
    if the customer already placed the order before the refresh ran.
    Skips silently when olap.duckdb is absent (pre-deploy).
    """
    import os as _os
    import pathlib
    from crm.sync.config import olap_path
    from hug.voucher_redeem_matcher import match_redeemed_vouchers

    olap = olap_path()
    if not _os.path.exists(olap):
        log.info("hug_voucher_redeem: olap.duckdb absent — skipping")
        return

    data_dir = _os.environ.get("CRM_DATA_DIR", "./data")
    crm_db_path = str(pathlib.Path(data_dir) / "crm.db")
    watermark = str(pathlib.Path(data_dir) / "hug_redeem_watermark.json")

    import sqlite3
    crm_conn = sqlite3.connect(crm_db_path)
    crm_conn.row_factory = sqlite3.Row
    try:
        n = match_redeemed_vouchers(crm_conn, olap, watermark)
        log.info("hug_voucher_redeem: %d vouchers matched", n)
    finally:
        crm_conn.close()
```

### Step 3 — Wire into `_run_refresh`

Insert after the `hug_voucher_issue` block:

```python
log.info("admin: hug_voucher_redeem starting")
try:
    await asyncio.wait_for(
        loop.run_in_executor(None, _hug_voucher_redeem_run),
        timeout=_REFRESH_TIMEOUT_S,
    )
except Exception as redeem_exc:
    log.error("admin: hug_voucher_redeem failed (non-critical): %s", redeem_exc)
```

### Step 4 — `crm/src/tests/test_hug_voucher_redeem_matcher.py`

Test matrix:

| Test | Scenario |
|------|----------|
| `test_matches_and_sets_redeemed_at` | order with matching (customer_id, coupon_code) → `redeemed_at` set, `order_code` set |
| `test_no_match_when_code_differs` | order coupon_code ≠ ledger code → 0 updates |
| `test_no_match_when_customer_differs` | customer_id ≠ ledger customer_id → 0 updates |
| `test_idempotent_already_redeemed` | `redeemed_at` already set → not overwritten (WHERE redeemed_at IS NULL) |
| `test_skips_null_customer_id` | order with NULL customer_id → 0 updates |
| `test_watermark_advances` | watermark JSON updated after run |
| `test_missing_fact_orders_table` | DuckDB has no fact_orders → returns 0, no exception |

## Todo

- [ ] Create `crm/src/hug/voucher_redeem_matcher.py`
- [ ] Create `crm/src/tests/test_hug_voucher_redeem_matcher.py` (7 test cases)
- [ ] Add `_hug_voucher_redeem_run()` to `admin_handler.py`
- [ ] Wire `hug_voucher_redeem` into `_run_refresh` (after `hug_voucher_issue`)
- [ ] `pytest crm/src/tests/test_hug_voucher_redeem_matcher.py` — all pass
- [ ] `pytest crm/src/tests/` — no regressions
- [ ] Manual smoke: place a test order with a coupon code, trigger `/admin/refresh`, check `crm_hug_voucher.redeemed_at`

## Success Criteria

- A `crm_hug_voucher` row with `code='HUG50'` and `customer_id='X'` where `redeemed_at IS NULL`, paired with a `fact_orders` row `{customer_id='X', order_coupon_code='HUG50'}` → after refresh, `redeemed_at` and `order_code` are populated.
- Re-running refresh → `redeemed_at` not overwritten (idempotent).
- `v_hug_voucher_attribution` shows `redeemed > 0` and `redeem_rate_pct` is non-zero.
- No error in refresh logs when `crm_hug_voucher` is empty.
- All 7 unit tests pass.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `fact_orders.order_coupon_code` is still a JSON object instead of scalar | Low | High | Verify column type post-extract-coupon deploy; build-order.md confirms scalar extraction is done (`$.order_coupon_code.coupon_code`) |
| Customer places order before issuance written (B3 before B2 in same refresh cycle) | Medium | Low | Issuer runs before matcher in refresh; same-cycle match possible. If not matched this cycle, watermark re-scans next cycle |
| `fact_orders.customer_id` NULL for Shopee masked orders | Medium | Low | WHERE clause already filters `customer_id IS NOT NULL`; masked orders skip cleanly |
| Long fact_orders scan on first run (no watermark) | Low | Medium | First run scans all orders with coupon_code — typically small set; watermark then advances |

## Security Considerations

- Reads `fact_orders` read-only from olap.duckdb — no warehouse mutation.
- Writes only `redeemed_at` + `order_code` to `crm_hug_voucher` — no PII columns touched.
- `order_code` is a Sapo order reference (internal, non-sensitive).

## Next Steps

- P5 reads `v_hug_voucher_attribution` (depends on both P3 and P4 having run).
- Optional P6: push `redeemed_at` to edge D1 `hug_voucher` for edge-visible redeem status (deferred).
