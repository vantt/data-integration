# Sapo Followup — User Answers + Deeper Investigation

> **Created:** 2026-05-28 17:58 ICT
> **Context:** User answered 4/5 questions tại commit a61778d → deeper investigation cho Q1+Q2 systematic, Q3 dashboard, Q4 detail, Q5 rephrase

---

## User answers summary

| # | User answer | Action implication |
|---|-------------|-------------------|
| Q1 Metabo | Đơn vị nên là **hộp** | Báo cáo standardize ở hộp (not gói); UoM expansion: Sapo hộp = 30 MISA gói |
| Q2 UoM pattern | **Nhiều**: collagen nước, cordyceps nước — hộp chứa nhiều gói/chai | **Cần systematic UoM solution**, không phải one-off seeds |
| Q3 DVCCNS dashboard | **Làm luôn** | Build services revenue blueprint (2.4B/năm) |
| Q4 Locations | Không rõ — list chi tiết để xác nhận | Đã ID được 3 locations từ dim_branch_location |
| Q5 Inventory retention | Chưa hiểu câu hỏi | Rephrase below |

---

## Q4 — 3 locations resolved từ `dim_branch_location`

| location_id | Tên | Code | Inventory state | Phân loại đề xuất |
|-------------|------|------|----------------|-----|
| `452566` | **16 Trương Định** | VVT | 118,699 on_hand, 114 variants in stock, 17 bin patterns (B3-A11-A1, B3-A12-A1...) | **Kho chính** (warehouse main) |
| `494912` | **Hậu Giang** | HG | 100,843 on_hand, **chỉ 7 variants** in stock, 1 bin (B1234) | Có thể là **kho phụ / tỉnh xa** |
| `624127` | **MM Market An Phú** | MMA | **NEGATIVE -18 on_hand**, 4 variants, 2 bins | **Consignment** to MM Market partner (committed > on_hand → đã ship hết) |

Plus 3 locations khác trong `dim_branch_location` nhưng KHÔNG có inventory data trong product payload:
- `639290` = TheHealthyUs (HUS)
- `657377` = ShowroomVVT (ST)
- `NULL` = Unknown (UNK)

**Cần business owner verify:**
- "16 Trương Định" = địa chỉ kho chính (Hà Nội?)
- "Hậu Giang" = tỉnh hay tên kho riêng?
- TheHealthyUs / ShowroomVVT có physical inventory không? Nếu có, sao Sapo payload không show?

---

## Q1 + Q2 — Systematic UoM solution (NOT one-off seeds)

### Confirmed: 120 packsize variants / 86 products có pattern hộp-chứa-gói

Examples từ raw data:
| Product | Variants (sku + unit) |
|---------|----------------------|
| Cordyceps | `VCSC20001L001`(Lọ) + `VCSC20001T024`(Thùng 120 viên x24) + `VCSC23166L001`(Lọ) + `VCSC23166T024`(Thùng 30 viên x24) + `VCSC23166L002`(Combo 2 lọ × 2) |
| Luna Sakura Collagen | `VTSL21001C001`(Chai) + `VTSL21001H010`(Hộp × 10) + `VTSL21001H020`(Combo 2 Hộp × 20) + `VTSL21001H030`(Combo 3 Hộp × 30) |
| Hyaluron & Collagen Plus | `VCSL19001C001`(Chai) + `VCSL19001H010`(Hộp × 10) + `VCSL19001T050`(Thùng × 50) + `VSL19001C003`(3 chai) + `VSL19001C004`(4 chai) + `VB24018`(Combo 1+1) |

### Pattern observation

Sapo SKU structure: `<base_code><uom_suffix><multiplier>`
- `VCSL19001` = base code (product family)
- `C` / `H` / `T` = UoM suffix (Chai / Hộp / Thùng)
- `001` / `010` / `050` = multiplier (per Hộp/Thùng quantity)

MISA SKU structure: cùng `<base_code><uom_suffix><multiplier>` NHƯNG:
- Thường chọn 1 UoM cố định per product (e.g., MISA dùng `G001` cho Metabo = gói)
- Coding suffix có thể khác (C vs L cho cùng "Chai/Lọ")

### Systematic solution — leverage `packsize_root_id`

Sapo API ALREADY cho biết relationship giữa pack variants. Sử dụng:

```sql
-- Pseudo-logic cho dim_sku_alias mart (auto-generated, không manual)
WITH variants AS (
  SELECT variant_id, sku, product_id, packsize, packsize_root_id, packsize_quantity, unit
  FROM stg_sapo_variants
),
roots AS (
  -- Base variants (no packsize, or packsize_root_id = self)
  SELECT variant_id AS root_variant_id, sku AS root_sku, product_id
  FROM variants WHERE packsize IS NOT TRUE
)
SELECT
  v.sku                                    AS sapo_pack_sku,
  v.unit                                   AS sapo_pack_unit,
  v.packsize_quantity                      AS units_per_pack,
  r.root_sku                               AS sapo_base_sku,
  r.root_sku                               AS misa_join_key,  -- assume MISA matches base SKU
  v.packsize_quantity                      AS misa_qty_multiplier
FROM variants v
LEFT JOIN roots r
  ON v.packsize_root_id = r.root_variant_id
 AND v.product_id = r.product_id
```

**Kết quả:** dim_sku_alias mart auto-generated từ Sapo's own packsize metadata. Không cần manual maintenance cho 120 variants. Future-proof: Sapo thêm pack mới → tự động pick up.

### Special cases (Metabo, etc.) cần manual seed nhỏ

Cases mà MISA code KHÔNG match Sapo base SKU (Metabo: MISA = `VCSP20002G001` "Gói", Sapo base = `VCSP20002H030` "Hộp 30"):
- Cần seed `dim_sku_alias_manual.csv` (chỉ vài chục entries) cho cases MISA code = component không phải SKU base
- Conversion factor: MISA gói × 30 = Sapo hộp
- Per user: REPORTING dùng đơn vị hộp → seed map MISA-gói → Sapo-hộp với divider 30

### Combined approach

```
Stage 1 (AUTO): dim_sku_alias_auto from Sapo packsize_root_id
Stage 2 (MANUAL): dim_sku_alias_manual.csv for MISA<>Sapo base mismatches (Metabo etc.)
Stage 3: dim_sku_alias_final = UNION + dedupe (manual wins if conflict)
```

**Effort estimate:**
- AUTO part: 1 dbt model, ~50 lines SQL (LOW effort, covers 120 variants free)
- MANUAL part: 1 CSV với ~20-30 rows (LOW effort, audit-once)
- Maintenance: AUTO part = zero; MANUAL part = update only when business changes coding

---

## Q3 — DVCCNS Services Dashboard plan

### Scope
Audience: **CFO**, có thể CEO secondary
Cadence: **Monthly review**
Stakes: 2.4B VND/năm ongoing revenue (DVCCNS + DVCCNS1 US HR services)

### Proposed blueprint: `finance_services_revenue.md`

| Tab | Widgets (5-8 cards each) |
|-----|--------------------------|
| **Tab 1 — Overview** | Total services rev MTD/YTD scalar + MoM/YoY combo, services as % of total rev gauge, breakdown by service type (DVCCNS/DVCCNS1/DVRENTAL/etc.) pie |
| **Tab 2 — US HR Services Deep Dive** | DVCCNS + DVCCNS1 monthly trend 12M, by customer (if available), forecasted MTD vs target |
| **Tab 3 — Other Services Audit** | Historical services no longer active (rental/utilities 2022 only), CPBH refund adjustments trend, low-volume services list |

### Key metrics (Domain entry trong finance.md)
- **Services Revenue** = SUM(revenue_net_of_discount) WHERE `is_service_line = true`
- **Services as % of Total Rev** = Services / (Services + Products)
- **Service Type Breakdown** = grouped by service_code prefix

### Data requirements
- `is_service_line` flag in `int_misa_sales_lines` (1-line addition)
- Optionally: `dim_service_categories` seed nếu cần grouping (US_HR / Office / Shipping / Other)

### Effort: LOW (~3-4 hours total)
- 1 line change in int_misa_sales_lines
- 1 new blueprint (8-15 widgets)
- Optional dim_service_categories seed

---

## Q5 — Rephrase: Inventory retention policy

### Context
Khi build `fact_inventory_snapshot`:
- Mỗi nightly batch (3am) tạo snapshot mới cho ALL variants × ALL locations
- ~2,046 rows × 365 ngày = **~750K rows/năm**
- Sau 3 năm = 2.2M rows (vẫn nhỏ cho DuckDB, ~50MB)

### Câu hỏi rephrase

**"Inventory historical data — giữ tới bao xa, granularity nào?"**

Options:
| Option | Storage | Use case unlock | Cost |
|--------|---------|----------------|------|
| **A. Daily forever** | 750K rows/năm, ~50MB/năm | YoY inventory trend, "tháng 12 năm ngoái stock có thấp hơn không?" | Storage cheap, query OK |
| **B. Daily last 90d + Weekly last 12 tháng** | ~250K rows total | Recent detail + medium-term trend | Compromise |
| **C. Daily last 30d only** | ~60K rows | Recent state only, no trend | Smallest, no historical analysis |
| **D. Daily last 12 tháng, weekly after** | ~800K rows total | Best of both, complex maintenance | Most flexible |

### Decision impact
- Option A là default cho most ecom (storage cheap)
- Option C nếu chỉ cần "tình trạng hiện tại" + không quan tâm trend (operational only)
- Option B/D nếu muốn vừa detail vừa lịch sử

**Recommend Option A (Daily forever, 12 tháng trước khi review).** Lý do: storage rẻ; trend analysis là big use case (slow-mover detection, seasonal stock planning, dead-stock cost).

---

## Updated decision matrix — ready to implement

| Item | Decision | Owner | Effort | Priority |
|------|----------|-------|--------|----------|
| 1. dim_sku_alias AUTO (from Sapo packsize_root_id) | BUILD | Data | LOW | P0 (foundation) |
| 2. dim_sku_alias_manual seed (Metabo cases) | BUILD scaffold | Data + Business | LOW | P0 (after #1) |
| 3. is_service_line flag in int_misa_sales_lines | BUILD | Data | TRIVIAL (1 line) | P0 (quick win) |
| 4. finance_services_revenue dashboard | BUILD | Data | LOW (~4h) | P1 (CFO request) |
| 5. fact_inventory_snapshot mart (daily forever) | BUILD | Data | MED | P2 (unblock dashboard) |
| 6. mart_inventory_health (OOS/slow/days-of-supply) | BUILD | Data | MED | P2 |
| 7. product_inventory dashboard (unblock from DEFERRED) | BUILD | Data | MED | P2 (after #5,#6) |
| 8. Verify "16 Trương Định" address + Hậu Giang nature | INVESTIGATE | Business | LOW | Q-back |
| 9. Audit all MISA codes vs Sapo base SKU mismatches | INVESTIGATE | Data | LOW | After #1 done |
| 10. TheHealthyUs / ShowroomVVT inventory tracking | INVESTIGATE | Business | LOW | Q-back |

## Next steps proposal

Pipeline 1 — **P0 quick wins (1-2 days)**:
1. Add `is_service_line` flag (1-line, can do in seconds)
2. Build `dim_sku_alias_auto` mart từ Sapo packsize (LOW SQL effort)
3. Bootstrap `dim_sku_alias_manual.csv` với top 10 cases (audit-driven)
4. Update `dim_products` to consume Sapo catalog + apply alias mapping
5. Rebuild `mart_sku_economics_monthly` — expected COGS coverage **32% → 85%+**

Pipeline 2 — **P1 + P2 marts + dashboards (3-5 days)**:
6. Build `finance_services_revenue.md` blueprint
7. Build `fact_inventory_snapshot` mart
8. Build `mart_inventory_health` mart
9. Unblock `product_inventory` blueprint with real data

Pipeline 3 — **Business validation (parallel)**:
10. Send back 3 questions: location addresses + TheHealthyUs/Showroom physical inventory + Metabo unit decision impact downstream

## Unresolved (need business owner)

1. Location addresses + nature (Q4 deep dive)
2. TheHealthyUs / ShowroomVVT physical inventory status (Q4)
3. Inventory retention policy (Q5 — recommend Option A but confirm)
4. Services categorization for dashboard grouping (US_HR vs Office vs Other) — Q3
5. Anti-counterfeit (*) prefix variants vs non-(*) (e.g. "Cordyceps" vs "(*) Cordyceps") — same product duplicate listing trong Sapo? Cần audit + consolidate or document.
