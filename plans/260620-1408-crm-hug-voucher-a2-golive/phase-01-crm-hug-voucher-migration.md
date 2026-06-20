---
title: "P1 — crm.db migration: crm_hug_voucher + attribution view"
status: pending
priority: P1
effort: 45m
---

## Context Links

- Plan overview: `plans/260620-1408-crm-hug-voucher-a2-golive/plan.md`
- Migration pattern: `crm/migrations/0024_hug_campaign_authoring.up.sql` (most recent, follow numbering)
- CRMDatabase.apply_migrations: `crm/src/adapters/outbound/sqlite/connection.py:94`
- Edge D1 `hug_voucher` schema (reference): `webhook_receiver/cloudflareD1/schema_hug.sql:74–89`
- Existing migration runner: `crm/src/adapters/outbound/sqlite/migrations/`

## Overview

**Priority:** P1 (blocks P3 issuance writer + P4 redeem matcher)
**Status:** pending

Create `crm_hug_voucher` table in `crm.db` as the local issuance ledger — the authoritative record of "code X issued to customer Y from campaign Z". Also creates a simple attribution/ROI view used by P5 readout screen.

The local table is the master; the edge D1 `hug_voucher` table (already in `schema_hug.sql:74`) is a deferred projection (P6).

## Requirements

- Table schema must match edge D1 `hug_voucher` columns exactly (PK, nullable fields) so a future push/mirror requires no transform.
- PK = `(code, customer_id)` — one voucher row per (campaign-code × customer). Idempotent INSERT OR IGNORE at issuance time.
- `redeemed_at` and `order_code` are NULL at issuance; set by redeem matcher (P4).
- Attribution view: count issued vs redeemed per campaign, simple ratio.
- Migration must be additive (no DROP, no ALTER of existing tables).
- Down migration: DROP TABLE only (safe — no FK dependents).

## Architecture

```
crm.db (crm/data/crm.db)
  └── crm_hug_voucher          ← new table (this phase)
        PK(code, customer_id)
        token, campaign_id, min_order, sku_guard
        issued_at, redeemed_at, order_code

  └── v_hug_voucher_attribution  ← new view (this phase)
        campaign_id, code, issued, redeemed, redeem_rate
```

CRMDatabase.apply_migrations() auto-runs all `*.up.sql` in `crm/migrations/` ordered by filename — adding `0025_hug_voucher_ledger.up.sql` is sufficient.

## Related Code Files

**Create:**
- `crm/migrations/0025_hug_voucher_ledger.up.sql`
- `crm/migrations/0025_hug_voucher_ledger.down.sql`

**No files modified** (migration runner auto-discovers by filename).

## Implementation Steps

1. Check last migration number: `crm/migrations/0024_hug_campaign_authoring.up.sql` → next = `0025`.
2. Create `crm/migrations/0025_hug_voucher_ledger.up.sql`:
   ```sql
   -- crm_hug_voucher: local issuance ledger (master; edge D1 is deferred projection)
   -- Schema mirrors edge hug_voucher (schema_hug.sql:74) column-for-column.
   -- PK(code, customer_id): one row per campaign-code × customer pair.
   CREATE TABLE IF NOT EXISTS crm_hug_voucher (
       code         TEXT NOT NULL,
       customer_id  TEXT NOT NULL,
       token        TEXT,              -- hug_token that triggered issuance (nullable: some flows may not have token)
       campaign_id  TEXT NOT NULL,
       min_order    INTEGER,           -- informational; from campaign offer at issuance time
       sku_guard    TEXT,              -- JSON list of excluded SKUs (informational)
       issued_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
       redeemed_at  TEXT,              -- set by redeem matcher when order_coupon_code matches
       order_code   TEXT,              -- Sapo order_code of the redeeming order
       PRIMARY KEY (code, customer_id)
   );
   CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_campaign
       ON crm_hug_voucher (campaign_id);
   CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_customer
       ON crm_hug_voucher (customer_id);
   CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_token
       ON crm_hug_voucher (token);
   -- Redeem matcher needs fast lookup of unmatched rows
   CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_unmatched
       ON crm_hug_voucher (code, customer_id) WHERE redeemed_at IS NULL;

   -- Attribution view: issued vs redeemed per campaign
   CREATE VIEW IF NOT EXISTS v_hug_voucher_attribution AS
   SELECT
       campaign_id,
       code,
       COUNT(*) AS issued,
       COUNT(redeemed_at) AS redeemed,
       ROUND(
           CAST(COUNT(redeemed_at) AS REAL) / NULLIF(COUNT(*), 0) * 100, 1
       ) AS redeem_rate_pct
   FROM crm_hug_voucher
   GROUP BY campaign_id, code;
   ```
3. Create `crm/migrations/0025_hug_voucher_ledger.down.sql`:
   ```sql
   DROP VIEW  IF EXISTS v_hug_voucher_attribution;
   DROP TABLE IF EXISTS crm_hug_voucher;
   ```
4. Verify migration runner picks up the file: check `crm/src/adapters/outbound/sqlite/migrations/__init__.py` (or equivalent) for glob pattern.
5. Run migration locally: start CRM server (or trigger `db.apply_migrations()` in a test) and confirm `crm_hug_voucher` table exists.

## Todo

- [ ] Create `crm/migrations/0025_hug_voucher_ledger.up.sql`
- [ ] Create `crm/migrations/0025_hug_voucher_ledger.down.sql`
- [ ] Verify migration auto-discovered (check migrations runner glob)
- [ ] Run migration + confirm table + view exist via `sqlite3 crm.db .schema`
- [ ] Write unit test: migration idempotent (run twice → no error)

## Success Criteria

- `crm_hug_voucher` table present in `crm.db` after `apply_migrations()`.
- `v_hug_voucher_attribution` view present and queryable.
- `INSERT OR IGNORE INTO crm_hug_voucher ...` with same PK twice → 1 row (idempotent).
- `down.sql` rolls back cleanly (DROP both).
- Existing CRM tests still pass (`pytest crm/src/tests/` — no regressions).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Migration number collision (another migration added concurrently) | Low | Low | Check actual last number at write time |
| Migration runner doesn't auto-discover 0025 | Low | Medium | Inspect runner glob before shipping; add explicit test |
| Schema drift vs edge D1 `hug_voucher` | Low | Medium | Column-by-column diff against `schema_hug.sql:74–89` during review |

## Security Considerations

- `crm_hug_voucher` contains `customer_id` + voucher codes — no plaintext PII (no phone, no name). Low sensitivity.
- `crm.db` is local-only (not network-accessible). No additional ACL needed.

## Next Steps

- P3 (issuance writer) and P4 (redeem matcher) both depend on this migration.
- P5 readout uses `v_hug_voucher_attribution` directly.
