# Open Questions — Shopee Pipeline

> User fills in answers below. Each answer unlocks a locked-in decision in `design-spec.md`.

---

## Pending questions

*Tất cả câu hỏi đã được trả lời (2026-04-16).*

---

---

## Answered questions

### Q1. Phí Shopee đã đủ chưa?

**Answered (2026-04-16):** Tất cả phí Shopee trong file Income đã đầy đủ → `net_settlement` chính xác. Tuy nhiên chưa có: (1) chi phí quảng cáo Shopee (Shopee Ads — nguồn dữ liệu riêng, không nằm trong file Income), (2) giá vốn / COGS (nguồn từ MISA). Hai khoản này thuộc P1 `fact_order_economics`, không ảnh hưởng P0.

---

### Q2. Nhiều SKU / đơn?

**Answered (2026-04-16):** Có. Một đơn hàng có thể có nhiều SKU (cũng có đơn chỉ 1 SKU). Thiết kế hiện tại composite key `(order_code, product_code)` cho `int_shopee_order_items` đã đúng — không cần thay đổi.

---

### Q3. Có bán trên nhiều shop Shopee không?

**Answered (2026-04-16):** Có bán nhiều shop. **Không cần thay đổi pipeline.** `order_code` unique across shops → khi P1 join vào `fact_orders`, shop identity tự có qua `channel_key` → `dim_channels`.

---

### Q4. Hai file trùng khoảng thời gian thì xử lý sao?

**Answered (2026-04-16):** Có thể xảy ra (nhân viên cẩu thả / export lại). Pipeline đã xử lý đúng: append-only + dedup `ingested_at DESC` → file mới nhất thắng. Thiết kế hiện tại đã đủ robust, không cần thay đổi.

---

### Q5. Sheet `Adjustment` chứa gì?

**Answered (2026-04-16):** Cần parse sheet này. Sheet có 2 phần: (1) liên quan đến đơn hàng — **parse phần này**, (2) liên quan đến shop — bỏ qua. Nâng từ "P1 defer" lên **P0 scope** — thêm entity `order_adjustments` vào ingestion + dbt models.

---

### Q6. Sheet `Summary` có cần dùng không?

**Answered (2026-04-16):** Bỏ qua. Không parse, không dùng làm checksum.

---

### Q8. Số tiền có phải luôn là số nguyên không?

**Answered (2026-04-16):** Luôn là số nguyên (VND, không có đồng lẻ). Parser `to_int_vnd()` → `Int64` là đúng.

---

### Q11. Có cần tự động đối chiếu với Summary không?

**Answered (2026-04-16):** Không. Bỏ qua Summary hoàn toàn (đi kèm Q6).

---

### Q7. Omnichannel join timing

**Answered (2026-04-09):** **Defer to P1.** Sapo đã ingest Shopee orders qua connector (xác nhận qua `ref_order_sources.csv` có 8 shop con Shopee), nhưng Sapo `order_code` = mã nội bộ Sapo (`SOxxx`) ≠ Shopee order SN (`260404V8SJUXBX`). Join key mapping chưa verify: cần scan payload JSON Sapo xem có field `reference_number` / `external_code` lưu Shopee SN không. Nếu có → P1 task build join. Nếu không → P1 task điều tra connector config. P0 giữ Shopee là standalone island — analyst vẫn được giá trị mới (fee trend + net settlement per order) mà Sapo không cung cấp.

---

### Q9. Archive policy

**Answered (2026-04-09):** **Move to archive after successful ingest.** Target: `app_data/input_source/shopee/_archive/{YYYY-MM}/{ingested_at_ts}_{original_filename}`. Move (not copy) để parser glob chỉ thấy file chưa xử lý. Nếu ingest fail → file giữ nguyên tại drop zone, retry next run. `_archive/` excluded khỏi parser glob pattern.

---

### Q10. Sensor interval

**Answered (implicitly — implemented):** Sensor đặt 300s (5 phút). File drop manual/weekly nên không cần poll nhanh hơn. Đã deploy trong `file_drop_sensors.py`.

---

## Status tracking

| # | Question | Status |
|---|---|---|
| Q1 | Phí Shopee đã đủ chưa? | **answered** → đủ phí Shopee; thiếu Ads + COGS (P1 scope) |
| Q2 | Nhiều SKU / đơn? | **answered** → có multi-SKU, design đã đúng |
| Q3 | Nhiều shop Shopee? | **answered** → không cần thay đổi, order_code match qua dim_channels |
| Q4 | File trùng khoảng thời gian | **answered** → dedup đã xử lý, không cần thay đổi |
| Q5 | Adjustment sheet | **answered** → parse phần đơn hàng, bỏ phần shop → **thêm vào P0 scope** |
| Q6 | Summary sheet usage | **answered** → bỏ qua |
| Q7 | Omnichannel join timing | **answered** → defer to P1 |
| Q8 | piship_service_fee type | **answered** → luôn số nguyên, parser đúng |
| Q9 | Archive policy | **answered** → move to `_archive/` |
| Q10 | Sensor interval | **answered** → 300s (5 min) |
| Q11 | Auto-check với Summary? | **answered** → không cần |

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
