# Open Questions — Shopee Pipeline

> User fills in answers below. Each answer unlocks a locked-in decision in `design-spec.md`.

## From data source analysis

### Q1. Full fee coverage
Does `Doanh thu.Phí Dịch Vụ` + `Service Fee Details.Phí Hạ Tầng` + `Service Fee Details.Voucher Xtra` exhaust all Shopee-charged fees, or are there more hidden in `Adjustment` / `Summary`?

**Impact:** determines if P0 `net_settlement` can reconcile with Shopee "Tổng phát hành" or needs `Adjustment` sheet parsing.

**Answer:**
```
(pending)
```

---

### Q2. Multi-SKU orders
Sample has 1 SKU per order. Real data may have N>1. Confirm: can an order have multiple Sku rows in `Doanh thu`?

**Impact:** validates `(order_code, product_code)` composite key for `fact_shopee_order_items`.

**Answer:**
```
(pending)
```

---

### Q3. Shop identity
File carries `seller_tax_code = 0317341714` but no `shop_id`/`shop_name`. Will we onboard multiple Shopee shops?

**Impact:** if yes → add `shop_code` partition in folder path `input_source/shopee/{shop_code}/*.xlsx` and column in fact tables.

**Answer:**
```
(pending)
```

---

### Q4. Overlapping drops
If two drops cover overlapping date ranges, which wins? Dedup key proposed: `(order_code, payout_released_at)` with `ingested_at` tiebreaker.

**Impact:** confirms dedup strategy in `src_shopee_order_revenue`.

**Answer:**
```
(pending)
```

---

### Q5. Adjustment sheet semantics
Does `Adjustment` sheet add/subtract from `order_code`-level totals, or is it standalone (chargebacks, manual compensations)?

**Impact:** decides if `Adjustment` needs to be joined to `fact_shopee_orders` (modifying net_settlement) or becomes its own `fact_shopee_adjustments`.

**Answer:**
```
(pending)
```

---

### Q6. Summary sheet usage
Pivot/report for humans, or useful reconciliation anchor?

**Impact:** if reconciliation anchor → parse into a small `shopee_income_summary_checksums` table for automated test; else skip entirely.

**Answer:**
```
(pending)
```

---

## From design spec

### Q7. Omnichannel join timing
Should `fact_shopee_orders` join to Sapo `fact_orders` for omnichannel reconciliation in P0, or stay an island until P1?

**Impact:** if P0 → add `sapo_order_sk` FK lookup in `fact_shopee_orders`; if P1 → defer.

**Answer (2026-04-09):** **Defer to P1.** Sapo đã ingest Shopee orders qua connector (xác nhận qua `ref_order_sources.csv` có 8 shop con Shopee), nhưng Sapo `order_code` = mã nội bộ Sapo (`SOxxx`) ≠ Shopee order SN (`260404V8SJUXBX`). Join key mapping chưa verify: cần scan payload JSON Sapo xem có field `reference_number` / `external_code` lưu Shopee SN không. Nếu có → P1 task build join. Nếu không → P1 task điều tra connector config. P0 giữ Shopee là standalone island — analyst vẫn được giá trị mới (fee trend + net settlement per order) mà Sapo không cung cấp.

---

### Q8. `piship_service_fee` type
Source stores as STR (`"-1620"`, `"-"`). Always integer-parseable, or can contain decimals / thousand-separator strings?

**Impact:** decides `to_int_vnd()` vs `to_decimal()` parser. If decimal possible → switch dtype to `DECIMAL(18,2)`.

**Answer:**
```
(pending)
```

---

### Q9. Archive policy
Keep all `.xlsx` drops forever under `input_source/shopee/`, or GC to `_archive/{YYYY-MM}/` after ingest success?

**Impact:** affects parser glob scope (fresh only vs full history) and disk cost.

**Answer (2026-04-09):** **Move to archive after successful ingest.** Target: `app_data/input_source/shopee/_archive/{YYYY-MM}/{ingested_at_ts}_{original_filename}`. Move (not copy) để parser glob chỉ thấy file chưa xử lý. Nếu ingest fail → file giữ nguyên tại drop zone, retry next run. `_archive/` excluded khỏi parser glob pattern.

---

### Q10. Sensor interval
Match sheets sensor (30s polling) or longer (5–15 min) since file drops are manual/rare?

**Impact:** Dagster scheduler load.

**Answer:**
```
(pending)
```

---

### Q11. Summary reconciliation dbt test
Need a dbt test asserting `ABS(SUM(net_settlement) - <summary sheet total>) < 10 VND`? Requires parsing `Summary` sheet.

**Impact:** pulls `Summary` sheet back into P0 scope (was deferred).

**Answer:**
```
(pending)
```

---

---

## Design clarifications (resolved 2026-04-09)

These were raised by user after reading `design-spec.md`; answers now locked in.

### D1. Purpose of `window_start` / `window_end` from filename
**Concern:** employees export files with overlapping date ranges → filename unreliable.

**Resolution:** **Drop filename window parsing entirely.** Keep only `source_file` (basename) + `ingested_at` as lineage metadata. Actual coverage window derivable from data: `SELECT MIN/MAX(payout_released_at) GROUP BY source_file`. Filename-derived fields bring zero reliable value when filenames can lie.

### D2. `7-day lookback` semantics and applicability to Shopee
**Concern:** does 7-day lookback break when orders ship >7 days or customers pay 30 days late?

**Resolution:**
- 7-day lookback protects against late **UPDATES arriving in source**, NOT against long business timelines. For Sapo (API source with `updated_at` cursor), late payment → Sapo sets fresh `updated_at` → record lands in 7-day window of next sync. Long shipping OK too. 7-day is a compromise buffer for clock skew + short sync gaps.
- Sapo keeps 7-day lookback as-is (correct design).
- **Shopee file-drop has different semantics:** no per-row `updated_at`, each file is atomic snapshot, files may overlap. → **Shopee `src_` models do NOT use 7-day lookback.** Instead: materialize as `view`, read full parquet history, dedup via `ROW_NUMBER() OVER (PARTITION BY order_code ORDER BY ingested_at DESC) = 1`. Data volume small (~100 rows/file) so full scan is cheap and more robust against overlapping drops.

### D3. Omnichannel join benefit
**Concern:** what does joining `fact_shopee_orders` ↔ Sapo `fact_orders` in P0 actually unlock?

**Resolution (same as Q7):** Benefit is real (true net margin per order, cash flow reconciliation, per-shop omnichannel P&L), but key mapping unverified (Sapo `order_code` ≠ Shopee order SN). Defer to P1 task that first verifies whether Sapo payload stores Shopee SN in a reference field.

---

## Status tracking

| # | Question | Status |
|---|---|---|
| Q1 | Full fee coverage | pending |
| Q2 | Multi-SKU orders | pending |
| Q3 | Shop identity | pending |
| Q4 | Overlapping drops | pending |
| Q5 | Adjustment sheet semantics | pending |
| Q6 | Summary sheet usage | pending |
| Q7 | Omnichannel join timing | **answered** → defer to P1 (key mapping unverified) |
| Q8 | `piship_service_fee` type | pending |
| Q9 | Archive policy | **answered** → move to `_archive/{YYYY-MM}/` on success |
| Q10 | Sensor interval | pending |
| Q11 | Summary reconciliation test | pending |
