---
title: "P3 — Issuance writer: local /admin/refresh step → crm_hug_voucher"
status: pending
priority: P1
effort: 90m
---

## Context Links

- Plan overview: `plans/260620-1408-crm-hug-voucher-a2-golive/plan.md`
- `/admin/refresh` pipeline: `crm/src/adapters/inbound/http/admin_handler.py` (full file)
- Current refresh sequence (lines 140–179): `reverse_etl → hug_resolve → hug_customer_push → sync_parties → rebuild_search_index`
- Identity resolver pattern: `crm/src/hug/identity_resolver.py` + `crm/src/hug/identity_resolver_io.py`
- Campaign repository (offer_ref source): `crm/src/hug/campaign_repository.py`
- crm_hug_voucher migration: `crm/migrations/0025_hug_voucher_ledger.up.sql` (P1)
- mart_hug_optin (input — needs campaign_id col from P2): `transformation/models/marts/customer/mart_hug_optin.sql`
- crm_identity_link (resolved_customer_id source): `crm/migrations/0022_hug_identity_link.up.sql`
- Watermark pattern: `crm/src/hug/identity_resolver_io.py:55–102`

## Overview

**Priority:** P1 (prize-gate — no ledger = no redeem attribution)
**Status:** pending
**Depends on:** P1 (crm_hug_voucher table), P2 (campaign_id on mart_hug_optin)

For each opt-in event that:
- has a `campaign_id` (from P2)
- whose winning campaign has a non-null `offer_ref`
- whose token has been resolved to a `customer_id` (crm_identity_link.resolved_customer_id)

...write one row to `crm_hug_voucher`: `{code=offer_ref, customer_id, token, campaign_id, issued_at}`. Idempotent (`INSERT OR IGNORE` on PK `(code, customer_id)`).

Never write a NULL-customer_id row. If resolution is pending (crm_identity_link row absent or resolved_customer_id IS NULL), skip and rely on the watermark to retry on the next /admin/refresh cycle.

## Architecture

```
/admin/refresh sequence (admin_handler.py):
  reverse_etl          ← cache.db fresh (fact_orders, wh_customer_tier)
  hug_resolve          ← crm_identity_link populated for new opt-ins
  [NEW] hug_voucher_issue  ← read mart_hug_optin × crm_identity_link × crm_hug_campaign
                             → write crm_hug_voucher (INSERT OR IGNORE)
  hug_customer_push    ← push tier to edge
  sync_parties         ← party upsert
  rebuild_search_index

Data flow:
  olap.duckdb (read_only)
    mart_hug_optin [token, campaign_id, event_ts]
  crm.db (read-write)
    crm_identity_link  [token → resolved_customer_id]
    crm_hug_campaign   [campaign_id → offer_ref, min_order, sku_guard]
    crm_hug_voucher    ← INSERT OR IGNORE rows here
  watermark file: {CRM_DATA_DIR}/hug_voucher_watermark.json
```

## Requirements

- Idempotent: re-running the same refresh must not create duplicate ledger rows. PK `(code, customer_id)` + `INSERT OR IGNORE` guarantees this.
- Watermark: track `max(event_ts)` of processed opt-ins so each refresh only scans new rows (same pattern as `identity_resolver_io.py:55–102`).
- Skip opt-ins without `campaign_id` (pre-P2 events, or campaigns with no offer_ref).
- Skip opt-ins whose token is not yet resolved (crm_identity_link row absent or resolved_customer_id IS NULL). They will be retried when the next refresh runs after resolution.
- `offer_ref`, `min_order`, `sku_guard` are read from `crm_hug_campaign` (local, already pushed to edge separately). Do not re-fetch from edge D1.
- Module < 200 lines. Pure Python, no FastAPI dependency. Testable with in-memory SQLite + a fixture DuckDB.
- Best-effort in refresh: failure must not abort `sync_parties` (wrap in try/except like `hug_resolve`).

## Related Code Files

**Create:**
- `crm/src/hug/voucher_issuer.py` — issuance logic + watermark I/O
- `crm/src/tests/test_hug_voucher_issuer.py` — unit tests

**Modify:**
- `crm/src/adapters/inbound/http/admin_handler.py` — add `_hug_voucher_issue_run()` + wire into `_run_refresh` after `hug_resolve`

**No dbt/SQL files modified** (mart_hug_optin changes are in P2).

## Implementation Steps

### Step 1 — `crm/src/hug/voucher_issuer.py`

Key functions:

```python
def issue_vouchers(
    crm_conn: sqlite3.Connection,
    olap_path: str,
    watermark_path: str,
) -> int:
    """Read new opt-ins with resolved customer_id + offer_ref → insert crm_hug_voucher.

    Returns count of rows inserted (INSERT OR IGNORE — 0 if already exists).
    """
```

Internal logic:
1. Load watermark (`since_ts`) from `watermark_path` (JSON, same format as identity resolver).
2. Open `olap_path` with `duckdb.connect(read_only=True)`.
3. Query `mart_hug_optin` for rows where `campaign_id IS NOT NULL AND event_ts > since_ts`, ordered by `event_ts ASC`.
4. For each opt-in row:
   a. Look up `crm_identity_link` by token → `resolved_customer_id`. Skip if NULL.
   b. Look up `crm_hug_campaign` by `campaign_id` → `offer_ref`, `min_order`, `sku_guard`. Skip if no row or `offer_ref IS NULL`.
   c. `INSERT OR IGNORE INTO crm_hug_voucher (code, customer_id, token, campaign_id, min_order, sku_guard, issued_at) VALUES (?, ?, ?, ?, ?, ?, ?)` — use event_ts as issued_at for auditability, not wall-clock.
5. Advance watermark to `max(event_ts)` of processed rows (write even if 0 inserted — advances past unresolvable rows to avoid re-scanning forever).
6. Return total rows inserted.

Edge cases:
- `mart_hug_optin` table not yet in olap.duckdb (pre-deploy) → catch CatalogException, log, return 0.
- `crm_hug_campaign` row absent for a given `campaign_id` → log warning, skip.
- DuckDB connection must be closed in `finally` (read_only, but still holds file handle).

### Step 2 — `admin_handler.py`: add `_hug_voucher_issue_run()`

After the existing `_hug_resolve_run()` function (~line 92), add:

```python
def _hug_voucher_issue_run() -> None:
    """Issue vouchers for newly-resolved opt-ins that have a campaign offer_ref.

    Runs AFTER hug_resolve (so crm_identity_link is populated for this cycle).
    Config-gated: skips silently when olap.duckdb is absent (pre-deploy).
    """
    import os as _os
    import pathlib
    from crm.sync.config import olap_path
    from hug.voucher_issuer import issue_vouchers

    olap = olap_path()
    if not _os.path.exists(olap):
        log.info("hug_voucher_issue: olap.duckdb absent — skipping")
        return

    data_dir = _os.environ.get("CRM_DATA_DIR", "./data")
    crm_db_path = str(pathlib.Path(data_dir) / "crm.db")
    watermark = str(pathlib.Path(data_dir) / "hug_voucher_watermark.json")

    import sqlite3
    crm_conn = sqlite3.connect(crm_db_path)
    crm_conn.row_factory = sqlite3.Row
    try:
        n = issue_vouchers(crm_conn, olap, watermark)
        log.info("hug_voucher_issue: %d vouchers issued", n)
    finally:
        crm_conn.close()
```

### Step 3 — Wire into `_run_refresh` (admin_handler.py)

Insert after the `hug_resolve` block (currently ending ~line 156), before `hug_customer_push`:

```python
log.info("admin: hug_voucher_issue starting")
try:
    await asyncio.wait_for(
        loop.run_in_executor(None, _hug_voucher_issue_run),
        timeout=_REFRESH_TIMEOUT_S,
    )
except Exception as issue_exc:
    log.error("admin: hug_voucher_issue failed (non-critical): %s", issue_exc)
```

Refresh sequence becomes:
`reverse_etl → hug_resolve → hug_voucher_issue → hug_customer_push → sync_parties → rebuild_search_index`

### Step 4 — `crm/src/tests/test_hug_voucher_issuer.py`

Test matrix (in-memory SQLite + DuckDB tmp file):

| Test | Scenario |
|------|----------|
| `test_issues_voucher_when_resolved` | opt-in with campaign_id + offer_ref + resolved customer_id → 1 row inserted |
| `test_skips_unresolved_customer` | resolved_customer_id IS NULL → 0 rows |
| `test_skips_no_campaign_id` | opt-in has NULL campaign_id → 0 rows |
| `test_skips_no_offer_ref` | campaign row has offer_ref=NULL → 0 rows |
| `test_idempotent_double_run` | same opt-in processed twice → still 1 row (INSERT OR IGNORE) |
| `test_watermark_advances` | watermark file updated after run |
| `test_missing_olap_table` | mart_hug_optin absent → returns 0, no exception |

## Todo

- [ ] Create `crm/src/hug/voucher_issuer.py` with `issue_vouchers()` + watermark helpers
- [ ] Create `crm/src/tests/test_hug_voucher_issuer.py` (7 test cases)
- [ ] Add `_hug_voucher_issue_run()` to `admin_handler.py`
- [ ] Wire `hug_voucher_issue` into `_run_refresh` (after `hug_resolve`)
- [ ] `pytest crm/src/tests/test_hug_voucher_issuer.py` — all pass
- [ ] `pytest crm/src/tests/` — no regressions
- [ ] Manual smoke: trigger `/admin/refresh`, check `hug_voucher_watermark.json` updated

## Success Criteria

- After a /admin/refresh with at least one resolved opt-in whose campaign has `offer_ref`:
  - `SELECT * FROM crm_hug_voucher` returns at least 1 row with non-null `customer_id`, `code`, `campaign_id`, `issued_at`.
  - `redeemed_at` and `order_code` are NULL (set by P4 later).
- Running refresh twice on the same opt-in data → `crm_hug_voucher` row count unchanged (idempotent).
- Refresh without any resolved opt-ins → no error logged, watermark still advances.
- `hug_voucher_watermark.json` exists after first run.
- All 7 unit tests pass.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| mart_hug_optin lacks campaign_id col (P2 not deployed yet) | Medium | Medium | Voucher issuer catches CatalogException / missing col; logs + skips cleanly |
| DuckDB read_only file lock contention during long refresh | Low | Medium | read_only=True (no write lock); release in `finally`; same pattern as reverse_etl |
| Issuer hangs → blocks customer_push | Low | Medium | Wrapped in `asyncio.wait_for(_REFRESH_TIMEOUT_S)` — same cap as other steps |
| Watermark corruption (partial write) | Low | Low | Write atomically (write temp + rename) or accept small backward-rescan cost |
| resolved_customer_id populated after event_ts already advanced past watermark | Low | Low | At resolution time (hug_resolve), the opt-in event_ts is unchanged — watermark re-scans correctly because issuer's watermark is independent of resolver's |

## Security Considerations

- `voucher_issuer.py` only writes `crm_hug_voucher`; it never reads or writes PII columns (no phone, no name).
- `offer_ref` (coupon code) written to ledger — not PII, but is a commercial asset; stored only in local `crm.db`.
- DuckDB opened read-only (`duckdb.connect(read_only=True)`) per project convention (`feedback_duckdb_always_readonly.md`).

## Next Steps

- P4 (redeem matcher) runs after this phase; reads `crm_hug_voucher` rows where `redeemed_at IS NULL`.
- P5 uses `v_hug_voucher_attribution` view which queries `crm_hug_voucher` (available immediately after P1 migration).
