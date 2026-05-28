# Sapo Product Investigation — 4 Open Questions Answered

> **Created:** 2026-05-28 17:30 ICT
> **Investigated by:** Direct DuckDB queries on raw payload + MISA sales lines
> **Context:** Follow-up cho agent reports (af4df + ad776 + abbe51) tại commit 4d233a5

---

## Q1: `VCSP20002G001` Metabo Green Tea — discontinued hay khác SKU?

**Answer: Không discontinued. Đây là UoM (Unit of Measure) coding mismatch.**

### Evidence
**MISA `VCSP20002G001`** "Trà túi lọc Metabo Green Tea":
- 2,103 invoice lines từ 2022-01-06 → 2025-10-28
- 1.07B VND revenue, 818M VND COGS, 11,184 units
- Last sold cách đây 7 tháng → vẫn ongoing trong window

**Sapo catalog có 6 variants liên quan Metabo (all active + sellable):**
| Sapo SKU | Variant name | Status |
|----------|-------------|--------|
| `VCSP20002H030` | TPBVSK Fine Japan Metabo Green Tea - Hộp | active |
| `VCSP20002T900` | TPBVSK Fine Japan Metabo Green Tea - Thùng | active |
| `VTSP20002H030` | (*) TPBVSK ... Metabo Green Tea - hộp | active |
| `VTSP20002T900` | (*) TPBVSK ... Metabo Green Tea - thùng | active |
| `CB.3ME` | Combo 3 Metabo | active |
| `CB.7ME` | Combo 7 Metabo | active |

### Pattern (UoM convention difference)
- **MISA suffix `G001`** = Gói (bag/sachet, 1 unit) — granular accounting unit
- **Sapo suffix `H030`** = Hộp (Box of 30 bags) — retail pack unit
- **Sapo suffix `T900`** = Thùng (Case of 900 bags) — wholesale pack unit

Cùng 1 sản phẩm thật, 2 cách đếm khác nhau.

### Implications cho dim_products rebuild
- Direct SKU join `VCSP20002G001 = ?` sẽ FAIL (Sapo không có code này)
- Cần **UoM expansion mapping** (1 Sapo H030 = 30 MISA G001 units)
- Hoặc Sapo cần thêm "component SKU" field cho mỗi pack variant
- **Recommendation:** Phase 1 trong dbt plan nên handle 2 cases:
  - Direct match (181/201 codes ✅)
  - UoM mismatch (handle qua manual `dim_sku_alias` seed với conversion factor) — added scope cho Phase 1

### Business decision needed
- Confirm with finance: Có nên consolidate về 1 đơn vị (gói) trong reporting không?
- Procurement team: code G001 vs H030 sourcing có giống nhau không?

---

## Q2: `DV*`/`CPBH` MISA codes — filter or flag?

**Answer: Add `is_service_line` flag. KHÔNG filter (mất legitimate revenue).**

### Evidence (last 12 months)
| Type | Lines | Revenue | COGS |
|------|-------|---------|------|
| PRODUCT | 8,502 | 23.7B VND | 12.8B VND |
| **SERVICE** | **111** | **2.4B VND** | **0** |

Service codes detail:
| Code | Name | Last seen | Revenue | Status |
|------|------|-----------|---------|--------|
| `DVCCNS1` | Phí dịch vụ cung cấp nhân sự cho US (FGO) | 2026-03-31 | 1.30B | **ACTIVE** |
| `DVCCNS` | Phí dịch vụ cung cấp nhân sự cho US | 2026-03-10 | 1.12B | **ACTIVE** |
| `DVRENTAL`/`DVDIEN`/`DVGX`/`DVQL`/`DVNUOC`/`DVVS` | Office utilities/rent | 2022-12-07 | 788M total | DISCONTINUED |
| `DVDT1` | Thiết bị phóng cao áp | 2022-06-13 | 1.29B (one-off) | DISCONTINUED |
| `DVVC` | Dịch vụ vận chuyển | 2025-10-13 | 0.6M | LOW VOLUME |
| `CPBH` | Chi phí bán hàng khác (negative — refund adjustments) | 2025-01-23 | -58.5M | LOW VOLUME |

### Recommendation
- **Add column `is_service_line BOOLEAN` to `int_misa_sales_lines`** via regex match:
  ```sql
  product_code LIKE 'DV%' OR product_code LIKE 'CPBH%' AS is_service_line
  ```
- **Downstream usage:**
  - `mart_sku_economics_monthly`: filter OUT services (no Sapo SKU equivalent, no COGS — would skew margin)
  - `finance_pl` blueprint: surface services as separate revenue line ("Dịch vụ" vs "Hàng hóa")
  - Channel P&L: services likely don't have channel attribution → group as "Other" or exclude

### Business decision needed
- DVCCNS (US HR services) 2.4B/year — có cần dashboard riêng theo dõi không?
- Coding standard: future-proof bằng cách thêm `vat_pit_category_code` filter thay vì code prefix?

---

## Q3: Daily inventory snapshot mechanism — separate API hay repeat payload?

**Answer: Repeat product payload (đã có sẵn data, zero additional API cost).**

### Evidence
Inventory data ĐÃ NẰM trong product payload, KHÔNG cần API riêng:
- 2,046 inventory rows từ 558 products (679 SKUs × 3 locations average)
- Per row fields: `location_id`, `variant_id`, `on_hand`, `available`, `committed`, `incoming`, `onway`, `mac`, `bin_location`, `wait_to_pack`, `min_value`, `max_value`
- **3 distinct locations**: `452566`, `494912`, `624127` (đều có 682 rows mỗi loc — full coverage)
- `modified_on` ALWAYS NULL → no per-row history timestamp (snapshot only)

### Architecture recommendation
**Option chosen: re-extract from product batch** (KISS):
- Sapo `sapo_products_batch_asset` already runs nightly at 3am
- Daily snapshot date = batch run date (use `_dlt_load_id` or wrap in dbt with `current_date - INTERVAL 1 day`)
- New dbt mart: `fact_inventory_snapshot`
  - Grain: `(variant_id, location_id, snapshot_date)`
  - Source: latest `stg_sapo_variants` joined with extracted inventories
  - Materialization: incremental, partition by snapshot_date
- Storage: ~2,046 rows × 365 days = 750K rows/year — small

### Why NOT separate API
- Extra API call → 2x rate limit pressure, more failure modes
- Sapo's product endpoint already returns inventories (free data)
- Maintaining 2 ingestion paths = 2x complexity, dedup conflicts

### Phase 3 design impact
- Build `fact_inventory_snapshot` (NEW mart) tách từ raw products parquet
- Build `mart_inventory_health` (NEW): OOS rate (on_hand=0), slow-mover (no movement 30d), days-of-supply (on_hand / daily_velocity from mart_sku_economics_monthly)
- Unblocks `product_inventory` blueprint (currently DEFERRED)

### Caveats
- `modified_on` NULL → cannot detect *intra-day* changes; only snapshot freshness = nightly batch time
- Real-time inventory needs webhook handler — out of scope for Phase 3

---

## Q4: `packsize_root_sku` always NULL — Sapo API bug hay intentional?

**Answer: Intentional Sapo API behavior. Resolution = self-join in dbt.**

### Evidence
| Metric | Count | Pct |
|--------|-------|-----|
| Total variants | 682 | 100% |
| `packsize = true` | 120 | 17.6% |
| Has `packsize_root_id` (BIGINT) | 120 | 100% of packsize |
| Has `packsize_root_sku` | **0** | **0%** |
| Has `packsize_root_name` | **0** | **0%** |

Sapo API trả về `packsize_root_id` (BIGINT pointer) NHƯNG luôn omit denormalized `packsize_root_sku` + `packsize_root_name`. Đây là design choice (caller responsible for joining).

### Sample (from user-provided payload)
```json
{
  "id": 108946084,
  "sku": "VCSL19001H010",   // pack SKU
  "name": "...Hyaluron & Collagen Plus - Hộp",
  "packsize": true,
  "packsize_quantity": 10,
  "packsize_root_id": 72204389,    // <-- parent variant ID
  "packsize_root_sku": null,        // <-- intentionally null
  "packsize_root_name": null        // <-- intentionally null
}
```

Parent variant `72204389` exists IN SAME PRODUCT's variants array với `sku: "VCSL19001C001"` (single bottle = base unit).

### Resolution
**In `stg_sapo_variants`:** self-join để resolve:
```sql
SELECT
  v.variant_id, v.sku, v.packsize, v.packsize_quantity, v.packsize_root_id,
  root.sku   AS packsize_root_sku,
  root.name  AS packsize_root_name
FROM stg_sapo_variants v
LEFT JOIN stg_sapo_variants root
  ON v.packsize_root_id = root.variant_id
 AND v.product_id = root.product_id  -- root must be in SAME product
```

Note: cần `product_id` filter vì root_id chỉ unique trong scope của product.

### Use case unlock
Với pack resolution, có thể:
- **COGS per pack unit** = COGS per base unit × packsize_quantity
- **MISA UoM alignment** (xem Q1) — link Sapo H030 (pack of 30) → MISA G001 (base unit) × 30
- **Inventory expansion** — 1 box on shelf = N base units sellable

---

## Summary — 4 decisions

| Q | Decision | Effort | Where |
|---|----------|--------|-------|
| Q1 | Add `dim_sku_alias` seed với UoM conversion factor (handle Metabo case + others) | LOW | Phase 1 |
| Q2 | Add `is_service_line` flag to `int_misa_sales_lines`; surface separately in P&L blueprint | LOW | Quick win |
| Q3 | Build `fact_inventory_snapshot` từ product payload (no new API) | MED | Phase 3 (NEW phase to add) |
| Q4 | Self-join in `stg_sapo_variants` to resolve packsize_root_sku/name | LOW | Phase 1 (sub-task) |

## Updated dbt plan impact

Plan tại `plans/260528-1654-sapo-product-dbt-plan/` cần add:
- **Phase 1 (revised):** include packsize self-join + `dim_sku_alias` seed cho UoM cases
- **Phase 3 (NEW — was missing):** `fact_inventory_snapshot` + `mart_inventory_health` để unblock `product_inventory` dashboard
- **Quick win sub-task:** `is_service_line` flag in int_misa_sales_lines (1-line change, immediate value)

## Unresolved questions (require business owner)

1. Q1: Có cần consolidate Metabo about về 1 UoM (gói) trong reporting? Procurement team xác nhận G001 vs H030 sourcing chain.
2. Q1: Tổng số SKU có UoM mismatch (giống Metabo) — cần audit toàn bộ MISA codes không match Sapo direct.
3. Q2: DVCCNS (US HR services 2.4B/năm) có cần dedicated dashboard không?
4. Q3: 3 Sapo locations `452566`/`494912`/`624127` — tên cụ thể (warehouse Hà Nội / HCM / kho phụ)? Cần map vào `dim_locations`.
5. Q3: Inventory snapshot retention — giữ daily 12 tháng (4K rows) hay weekly only?
