# MISA ↔ Sapo SKU Alignment Diagnostic

> **Created:** 2026-05-28 16:08 ICT
> **Trigger:** Deployment validation phát hiện `mart_sku_economics_monthly` chỉ có 32% rows với gross_margin_pct populated. User clarification: MISA quản lý nhiều SKU hơn Sapo → cần đảo hướng kiểm tra (Sapo SKUs missing in MISA).

---

## TL;DR

- **82/105 Sapo SKUs (78%) thiếu MISA invoice match** = ~71 tỷ VND doanh thu không có COGS attribution
- Vấn đề **không phải MISA thiếu data** — là **2 hệ thống dùng coding system riêng biệt** + naming conventions khác
- **Fix khả thi**: fuzzy name normalization có thể nâng coverage **22% → 47%** ngay lập tức (zero manual data); thêm seed alias cho top-20 missing nâng tiếp lên **~80%**

---

## 1. SKU Universe Diagnostic

| Metric | Value |
|--------|-------|
| Sapo total SKUs (dim_products) | 105 |
| Sapo SKUs với sales (fact_sales) | 105 (100% — all sold) |
| MISA distinct product_codes | 201 |
| **Direct SKU code match** | **23 (22%)** |
| Sapo SKUs MISSING MISA | **82 (78%)** |
| Revenue from missing SKUs | **~71B VND** |

User hypothesis verified: ✅ MISA có nhiều SKU hơn (201 vs 105) — vì MISA cũng track raw materials, services (DVCCNS — "Phí dịch vụ cung cấp nhân sự"), bundle components, và variants không phải master SKU bán retail.

## 2. Naming pattern analysis

**Sapo coding systems** (mixed):
- Short legacy codes: `SHA1`, `COR1`, `FU1`, `NAT1`, `ME1`, `REI1`, `COL1`, `COR2`, `CORP.H`, `COLY.H`
- Long structured codes: `VFJHCORLIQ2102H010`, `VNFJCOLLIQ1901H0010`, `VTSC20001L001`, `VTSL24001H010`
- Combo SKUs: `PVN146`, `PVN147`, `PVN150`, `CB.3NAT`, `VB23007`

**MISA coding system** (consistent structured):
- Pattern: `VCS[XPC][YY][NNN][L|H|C|G][NNN]`
- Examples: `VCSC20001L001`, `VCSL21002C001`, `VCST21004L001`

**Same product, different codes** (typical mismatches):

| Product | Sapo code | MISA code |
|---------|-----------|-----------|
| Shark Cartilage (18B VND!) | `SHA1` | `VCST21004L001` |
| Cordyceps | `COR1` | `VCSC20001L001` |
| Cordyceps Plus | `VFJHCORLIQ2102H010`, `VSL21002C001`, `VTSL24009H010` | `VCSL21002C001` |
| Hyaluron & Collagen Plus | `VNFJCOLLIQ1901H0010`, `COL1`, `VB24018` | `VCSL19001C001` |
| Royal Reishi | `REI1` | `VCSC21006L001` |

## 3. Product name alignment

| Method | Match count | Hit rate |
|--------|------------|---------|
| Exact name (lowercased + trimmed) | 25 / 105 | 24% |
| + Strip "Thực phẩm bảo vệ sức khỏe" / "TPBVSK" / "(*)" prefix | 49 / 105 | **47%** |

MISA names systematically add regulatory prefix "Thực phẩm bảo vệ sức khỏe" (TPBVSK = abbreviation). Sapo names vary: some have prefix `(*)` marker, some have full prefix, some just product name.

**Fuzzy match recovers 26 additional SKUs** không cần manual data — gần gấp đôi coverage hiện tại.

## 4. Still missing after fuzzy match (top by revenue)

| Sapo SKU | Product | Revenue (M VND) | Pattern |
|----------|---------|----------------|---------|
| SHA1 | Shark Cartilage | **17,965** | Name: "Shark Cartilage" vs MISA "...Shark Cartilage Extract" (suffix differs) |
| CORP.H | Đông trùng hạ thảo nước | 9,006 | Vietnamese name, no MISA equivalent in name |
| COLY.H | Collagen Yến | 6,530 | Vietnamese name |
| FU1 | Fine Fucoidan Nhật Bản | 3,834 | Brand "Fine" prefix in Sapo |
| VTST23023L001 | (*) ...Fine Japan Shark Cartilage Extract | 988 | Different structured code |
| VTSL24009H010 | (*) TPBVSK Fine Japan Cordyceps Plus | 828 | Different structured code |
| PVN146, PVN147, PVN150, CB.3NAT, VB23007 | Combo bundles | ~200 mỗi | **Bundle SKUs** — MISA track components, not bundles |

Total still-missing revenue after fuzzy: ~38B VND (top 15 = 95% of still-missing volume).

## 5. Recommendations

### Level 1 — Fuzzy name normalization (recommended START)
**Effort:** ~1 hour | **Coverage gain:** 22% → 47% | **Manual data:** zero

Implementation:
1. Add normalized name CTEs trong `mart_sku_economics_monthly`:
   - Strip `(*) `, `Thực phẩm bảo vệ sức khỏe `, `TPBVSK ` prefixes
   - Lowercase + trim
2. Join logic: `LEFT JOIN MISA ON sapo_sku = misa_code FALLBACK normalized_name match`
3. Rebuild mart + verify hit rate

Pros: ngay lập tức nâng coverage gấp đôi, không cần business input, fully automated
Cons: vẫn còn ~50% missing; có rủi ro false positive (2 SKU khác nhau có cùng normalized name)

### Level 2 — Manual alias seed (recommended FOLLOWUP)
**Effort:** ~2-3 hours (1h dev + 1-2h business owner validate) | **Coverage gain:** 47% → ~80% | **Manual data:** ~20 alias entries

Implementation:
1. Create `transformation/seeds/seed_sku_alias.csv` với schema:
   ```
   sapo_sku, misa_product_code, confidence, notes
   SHA1, VCST21004L001, verified, "Shark Cartilage = Shark Cartilage Extract"
   CORP.H, ???, pending, "Need business owner mapping"
   ...
   ```
2. Build `dim_sku_alias.sql` mart từ seed
3. Update `mart_sku_economics_monthly` join: `direct → fuzzy → alias` (3-tier fallback)
4. Business owner review session để fill in pending entries

Pros: 80% coverage là điểm mục tiêu thực tế; có audit trail; future-proof
Cons: yêu cầu business owner time

### Level 3 — Bundle component expansion (DEFER)
**Effort:** High | **Coverage gain:** +5-10% | **Complexity:** New mart for bundle decomposition

Combo SKUs (PVN*, CB.*, VB23007) cần expand thành component SKUs để rollup COGS. Cần `dim_bundle_components` table. **Defer** — chỉ ~200M VND/combo, không phải priority.

### Decisions NOT to make
- ❌ **Không bắt MISA và Sapo dùng cùng coding system** — cả 2 hệ thống đều có lý do riêng (Sapo focus sales UX, MISA focus accounting compliance). Forcing alignment sẽ break existing workflows.
- ❌ **Không tự động generate alias bằng ML/LLM** — risk false positive với regulated products quá cao; manual review là chuẩn.

## 6. Implementation plan (nếu approve)

**Phase A (immediate, 1h):**
1. Modify `mart_sku_economics_monthly.sql` thêm fuzzy normalization CTE
2. Rebuild mart
3. Verify coverage jumps to ~47%
4. Commit

**Phase B (next, 2-3h):**
1. Create seed_sku_alias.csv + dim_sku_alias.sql model
2. Pre-fill top 20 highest-revenue missing SKUs với best-guess (mark as `pending`)
3. Update mart join logic to 3-tier
4. Send to business owner for verification → flip `pending` → `verified`
5. Rebuild + commit

## Unresolved questions

1. **Bundles (PVN146, CB.3NAT etc.)** — có existing data nào ở Sapo về bundle composition không? Hoặc business owner có maintain Excel mapping?
2. **MISA "VCST21004L001 Shark Cartilage Extract" vs Sapo "SHA1 Shark Cartilage"** — đây có cùng 1 sản phẩm không? Hay 2 variants khác (Extract concentration vs base)? Cần business validate.
3. **Services trong MISA (DVCCNS - "Phí dịch vụ cung cấp nhân sự")** — có nên loại khỏi mart_sku_economics_monthly không? Hiện tại int_misa_sales_lines bao gồm tất cả lines, có thể inflate cogs hoặc miscategorize.
4. **Sapo SKU multiple cho cùng product** ("Cordyceps Plus" có 3 SKU: VFJHCORLIQ2102H010, VSL21002C001, VTSL24009H010) — có nên consolidate trong dim_products không, hay là intentional (size/variant)?
5. **Coverage target** — 47% (fuzzy only) đủ cho production reporting, hay phải đạt 80%+ trước khi publish dashboards với confidence?
