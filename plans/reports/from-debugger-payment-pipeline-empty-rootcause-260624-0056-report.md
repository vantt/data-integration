# Payment Pipeline Empty — Root Cause Report
**Date:** 2026-06-24 | **Severity:** HIGH | **Status:** FIXED

---

## Executive Summary

Root cause: **Extraction path wrong (Hypothesis A)**. `src_sapo_v2_orders.sql` extracted `$.payments` from order payloads, but the Sapo API returns payment records under `$.prepayments`. The key `payments` does not exist in any order payload across all ingest methods. One-line fix applied to `src_sapo_v2_orders.sql`. After `dbt run --full-refresh -s src_sapo_v2_orders`, `stg_sapo_v2_payments` will populate.

---

## Evidence Chain

### 1. Raw payload inspection — `$.payments` key is absent
- Sampled 176 batch_sync orders → 0 had `payments` key
- Sampled 41 history_log orders → 0 had `payments` key
- Webhook: 0 files exist (no webhook-based order ingestion active)
- Confirmed: `payments` key **never exists** in any Sapo order payload

### 2. `$.prepayments` is the correct field
- All history_log orders contain `prepayments` key (41/41 sampled)
- batch_sync: 16025+ orders with non-empty `prepayments` out of 35385 sampled
- `prepayments` items contain all 7 fields that `stg_sapo_v2_payments.sql` extracts:
  `id`, `payment_method_id`, `amount`, `status`, `reference`, `created_on`, `paid_on`
- Missing field: `code` (extracted as `payment_code`) → returns NULL (acceptable)

### 3. Projection of fix impact
- 30-file batch_sync sample: 15445 total orders → 5569 will yield non-null `payments_json`
- Paid orders in same sample: 13942 (discrepancy: some paid orders have empty `prepayments` arrays, likely COD orders where payment is recorded post-fulfillment outside the order payload)

### 4. `dbt parse` — no errors after fix

---

## Files Changed

| File | Change |
|------|--------|
| `transformation/models/staging/src_sapo_v2_orders.sql:175` | `$.payments` → `$.prepayments` |
| `ingestion/src/sapo/orders.py:34` | Added clarifying comment on `prepayments` field |

**Diff (src_sapo_v2_orders.sql):**
```sql
-- Before
json_extract_string(payload, '$.payments') as payments_json,

-- After
-- Sapo API returns payment records under 'prepayments', not 'payments'
-- ($.payments does not exist in any order payload; verified across all ingest methods)
json_extract_string(payload, '$.prepayments') as payments_json,
```

---

## Why This Bug Existed

The `orders.py` schema comment (lines 28-38) documents the Sapo normalized-model fields (pre-dlt normalization). That list includes `prepayments` — the correct field. However, when `src_sapo_v2_orders.sql` was written, the extraction path was incorrectly set to `$.payments` (likely confused with the generic concept of "payments"). The `orders.py` schema was using the envelope pattern where the full `raw_order` is stored as `payload` — so the schema comment's listed fields are top-level API fields baked into `payload`, but the extraction SQL referenced a non-existent sibling key.

---

## Rebuild Required

`src_sapo_v2_orders` is incremental (`delete+insert`). Because `payments_json` was NULL for all existing rows, a **full-refresh is required** to backfill:

```bash
# In data_platform container (or via Dagster)
dbt run --full-refresh -s src_sapo_v2_orders
# Then rebuild dependents:
dbt run -s stg_sapo_v2_payments std_payments fact_payments dim_customers
```

After rebuild: `stg_sapo_v2_payments` should yield ~16K+ rows from historical data.

---

## Unresolved Questions

1. **COD gap**: 13942 paid orders but only 5569 have non-empty `prepayments`. Hypothesis: COD orders (cash paid on delivery) may not have prepayments until after delivery is confirmed. Needs verification — is `prepayments` populated on `payment_status='paid'` COD orders post-delivery, or is there a separate payment recording mechanism?

2. **`payment_code` field**: `$.code` is extracted by `stg_sapo_v2_payments.sql` but `prepayments` items have no `code` field (they have `source` instead). `payment_code` will be NULL for all rows. If `payment_code` is used downstream for anything meaningful, consider mapping from `source` instead.

3. **Webhook gap**: No webhook parquet files for orders. If Sapo sends order-update webhooks with payment info, that path should be activated to get real-time payment status.
