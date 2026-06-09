# Phase 0 — Probe Findings (Sapo Inventory Transactions v2)

Date: 2026-06-03. Endpoint: `GET /admin/reports/inventories/transaction.json`. Run in `data_platform` container via existing Sapo client (cached cookies).

## Auth / permission
- Account `0355514031` initially **missing `read_inventory_report`** → 403. User granted permission → 200 OK (server-side check, cached cookie still valid).
- Successful request included headers `X-Requested-With: XMLHttpRequest`, `Referer: {base}/reports/inventories/transaction`, `Accept: application/json,...`. **Keep these headers in production source** (harmless; may be required).

## Response shape
- Top-level keys: `metadata`, `items`, `summary`.
- `metadata`: `{total, page, limit}`.
- `items[]`: 1 row per (document × product line). Keys: issued_at_utc, log_root_id, log_type, log_type_name, trans_type, trans_type_name, trans_object_id, trans_object_code, action, product_id, product_name, product_category, variant_id, variant_name, sku, barcode, unit, location_id, location_label, import_quantity, import_amount, export_quantity, export_amount, onhand, amount, mac, total_mac, source.
- `summary`: report aggregate — **ignore** for line ingestion.
- Sort: **newest-first** by `issued_at_utc` (DESC) — confirmed.

## Pagination
- `limit` caps at **250** (requested 500 → `metadata.limit=250`). Use `limit=250`.
- Page to exhaustion using `metadata.total`: `pages = ceil(total/limit)`; stop when page > pages or items empty.

## Earliest data (backfill boundary)
- Yearly totals (ICT-day windows): 2019=0, 2020=0, **2021=1854**, 2022=7975, 2023=9001, 2024=8928, 2025=3848, 2026=1351 (to date).
- 2021 months: Jan–Apr=0, **May=48** (first), Jun=192, … Dec=580.
- **Backfill start = 2021-05-01 (ICT).** Total all-time ≈ **32,957 lines** — tiny.

## Design parameters locked
- `limit = 250`; window filter via `start_date`/`end_date` UTC (computed from ICT).
- Backfill chunk = **monthly** (each month ≤ ~580 recs ≤ 3 pages); ~61 months from 2021-05.
- Hourly = current+prev hour (ICT); Nightly = full current ICT day.
- entity_id = md5(`log_root_id|trans_type|product_id|variant_id|location_id|issued_at_utc`); payload_hash = md5(sorted item).

## Unresolved
- Negative `trans_object_id` (e.g. -1965053459) — sign meaning unknown; defer to Phase 5 analysis.
- `onhand`/`mac`/`amount` semantics (running balance vs snapshot) — defer to Phase 5.
