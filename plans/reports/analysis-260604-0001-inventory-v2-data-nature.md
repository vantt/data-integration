# Inventory Transaction v2 — Data Nature Analysis

**Date:** 2026-06-04 · **Source:** `sapo_raw/inventory_transaction_v2/*.parquet` · **Rows:** 32,984 raw → **32,957 deduped** (27 re-fetch dupes on `entity_id`) · **Span:** 2021-05-20 → 2026-06-03.

## 1. Event taxonomy
- `trans_type=301` sale_order_fulfillment = **24,725 (75%)** — dominant.
- Other types: stock_transfer (200), sales return, purchase receipt, stock adjustment, `501` catalog-init (mostly zero-qty), `600` pure cost adjustment (2 rows).
- 3 warehouse locations: **16 Trương Định (65%)**, Hậu Giang (26%), MM Market An Phú (9%).

## 2. Import vs export semantics
- **Mutually exclusive per row** — no row has both import_quantity>0 and export_quantity>0.
- → signed `quantity_delta = import_quantity − export_quantity` (+IN / −OUT), unambiguous.
- **Exception:** stock_transfer (200) action "received" fires at BOTH ends; derive direction from `import_quantity>0`, NOT the action name.

## 3. `onhand` running balance
- Verified: per-(variant_id, location_id) running balance ordered by `issued_at_utc`.
- `onhand[n] ≈ onhand[n-1] + import − export` holds **78.8%**; **12.2%** same-second ordering ambiguity (sub-second not available; onhand itself disambiguates order); **4.4% (1,449 rows / 5.6% of pairs)** genuine unexplained jumps (likely Sapo-side corrections w/o log).
- **`onhand` is authoritative — use as-is, never recompute.**

## 4. Cost semantics
- **`amount = onhand × mac` — perfect 100% identity** (28,387 rows w/ mac>0). `mac` = moving average cost AFTER txn; `amount` = current inventory value.
- `total_mac` always 0 → drop.

## 5. COGS
- **`export_amount` = COGS at PRE-txn MAC**, NOT `export_qty × mac` (mac reflects post-txn). **Use `export_amount` directly for COGS.**

## 6. Grain / natural key
- Business NK **`(log_root_id, variant_id, location_id, issued_at_utc, onhand)` → 32,957 distinct, 0 collisions.**
- `entity_id` (content hash) also perfectly unique → recommended surrogate `inventory_movement_id`.
- `log_root_id` = document/order id; up to 27 lines/doc, avg ~1.9.

## 7. Linkage
- `trans_object_code` (document_code): **SON… = Sapo order codes (41%)**, marketplace codes (33%), STN/PCN/SRN/IAN/PRN/PON operational docs.
- SON… → join `std_orders.order_code` (enables order-level COGS). variant_id/product_id → products.

## 8. Inventory interpolation feasibility — YES
- 572 variants, all have ≥1 movement. **58 (variant,location) pairs currently stock>0**; 7 negative (anomaly); no SKU nulls.
- Point-in-time stock = ASOF join on `onhand` ordered by issued_at_utc. Pre-2021-05 opening balance embedded in earliest row's onhand (acquisition history unrecoverable).

## std_ design recommendation
- **Model:** `std_inventory_movements` · `source_version='v2'`.
- **Surrogate PK:** `inventory_movement_id` ← `entity_id`.
- **Natural key:** `(log_root_id, variant_id, location_id, issued_at_utc, onhand)`.
- **Signed:** `quantity_delta = import_quantity − export_quantity`; `movement_direction` IN/OUT/ZERO (transfer dir via import_quantity>0).
- **Faithful cost:** keep `onhand`, `mac`, `amount` (=inventory_value), `export_amount` (=COGS), `import_amount`.
- `issued_date_key` = ICT DATE. **Drop** `total_mac`; denormalize names (product_name/variant_name/category) at mart, not std.
- **Dedup:** `QUALIFY ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY event_timestamp DESC)=1`.

## Marts opportunity (implemented)
- `fact_inventory_movements` — direct from std, filter `quantity_delta != 0`. 31,533 rows.
- `fact_inventory_onhand` — **sparse effective-dated balance ledger** (1 row per pair per movement-day = 17,616 rows), with `valid_from_date`/`valid_to_date` + `is_current`. Chosen over a dense daily date-spine snapshot, which would have been ~1.9M rows of which **99.1% were redundant no-movement carry-forward**. Current stock = `WHERE is_current`; stock on date X = `WHERE X BETWEEN valid_from_date AND valid_to_date`.
- Order-level COGS — join movements on `document_code = order_code` (future).

## Unresolved questions
1. **stock_transfer direction** — "received" action at both ends; std must encode direction from import_quantity>0 explicitly.
2. **`shipped_fulfillment_cancelled` (1,064 rows)** — 50/50 IN/OUT split; appear paired (export+import per cancel) but unconfirmed — do NOT blindly sum quantity_delta until pairing logic confirmed.
3. **1,449 onhand mismatches (5.6% pairs)** — unexplained, likely Sapo corrections; onhand still authoritative.
4. **7 negative-onhand pairs** — data anomaly to flag in a mart test.
5. Marketplace document_codes (33%) — which channel/table do they join to (Shopee?)?
