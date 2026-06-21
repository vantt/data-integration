---
title: "PLAN-004 - Dead-stock → Customer Targeting Engine"
description: "Engine ghép SKU ế/slow → khách từng mua (SKU past-purchase) → outreach 2 kênh (Hug voucher + Shopee-native), thiết kế cho scale + ngưỡng kích hoạt."
status: in-progress
priority: P2
effort: ~6-9 ngày data + tích hợp (P0 0.5d · P1 2-3d · P2 2-3d · P3 1-2d)
branch: main
tags: [retail-reactivation, deadstock, demand-match, hug, reverse-etl, inventory]
source: "OPP-005"
stage: 5
created: 2026-06-20
---

# PLAN-004 - Dead-stock → Customer Targeting Engine

**Registry:** [PLAN-004](../REGISTRY.md#plan-004)

> **Nguồn:** [OPP-005](../04-opportunities/OPP-005-deadstock-customer-targeting-engine.md) · [FIND-008](../02-understand/FIND-008-deadstock-customer-targeting-granularity.md) · [data-probe report](../../reports/data-probe-deadstock-customer-targeting-granularity-260620-1242-report.md)
> **Quyết định owner 2026-06-20:** BUILD FULL ENGINE cho scale + ngưỡng kích hoạt — KHÔNG cắt scope theo YAGNI (business call, xem OPP-005 Decision Note).
> **Cây cầu thiếu:** plan resell hiện thuần phía CẦU (trạng thái khách); engine này là phía CUNG (tồn kho ế) × past-purchase = mắt xích product→customer.

---

## Trạng thái deploy 2026-06-21

**Engine core LIVE & verified (P0/P1/P2 data path GREEN).** Activation outreach (Hug campaign + Shopee export) còn PENDING.

| Phase | Trạng thái | Bằng chứng live |
|---|---|---|
| P0 | ✅ DEPLOYED | `mart_product_action_queue.sql` filter live; CLEAR_DEADSTOCK **17→5 SKU / 5.5M** (verified) |
| P1 | ✅ DEPLOYED | `mart_deadstock_target_queue` live: **498 rows / 4 FJV SKU / 414 khách**; grain (product_key,customer_key) UNIQUE; **17 dbt test PASS**; Dagster run `8f8c0f1a` SUCCESS |
| P2 | ✅ DEPLOYED (data path) · activation PENDING | `wh_deadstock_target` (cache.db): **498 rows** (HUG=309, SHOPEE_NATIVE=189); reverse_etl sync OK; crm container rebuilt; serving view bootstrapped. Hug "deadstock-resell" SEEDED nhưng PAUSED; Shopee export script sẵn sàng |
| P3 | pending | đo + ngưỡng (chưa làm) |

**Đính chính số liệu vs spec (số live ĐÚNG, không phải bug):** thực tế **4 SKU / 83.1M capital** (KHÔNG phải ~20 SKU như spec). ~16 SKU "slow/dead" còn lại bị loại đúng vì tồn kho/vốn = 0 (không có gì để thanh lý) + điều kiện past-buyer. 4 SKU này GỒM 2 SKU vốn lớn `VTST23023L001` (41.5M) + `VCST21003L001` (35.2M).

**Verify Dagster — KHÔNG bug:** run scheduled post-deploy `f8bcc9ba` = CANCELED (KHÔNG phải lỗi code): health sensor auto-terminate khi treo 9 phút ở pha dbt test (DuckDB checkpoint stall — failure-mode đã biết, có sẵn DBT_TIMEOUT + stuck-run sensor). Run kế tiếp `e7407873` (hourly) = SUCCESS → tự hồi phục, KHÔNG kill-loop, KHÔNG stale lock. Deliverables intact post-cancel.

**Bonus fix lúc deploy:** `schema.yml` sửa deprecation dbt 1.11 (`combination_of_columns`→nest `arguments:`); thêm `LIVE_CORE` vào `crm/src/hug/targeting_catalog.py`.

**Follow-up còn mở (chưa làm):**
1. 4 SKU NULL-`brand_code` bị filter `brand_code='FJV'` bỏ sót (**6.85M**, chủ yếu `VCMC21010H001` Medicine 5.46M) — chờ owner: fix brand_code source HOẶC fallback `brand_name='Fine Japan Vietnam'` + redeploy.
2. Hug campaign activate: cần config voucher (min-order + SKU-guard margin) + destination URL.
3. Holdout hiện 23.5% (mục tiêu ~20%) — tune `% 20 < 4` nếu P3 cần.
4. Shopee: verify quota Chat Broadcast VN khi chạy đợt đầu.

---

## Bối cảnh data đã ground (probe live 2026-06-20, parquet rolling)

Probe này mở rộng FIND-008 (vốn chỉ đo 5 SKU dead-thật → audience 8). Khi lấy **toàn universe slow/dead bán-được** (`mart_product_health` DOG/QUESTION + dead-stock, loại noise category) × past-buyer (fact_sales COMPLETED) × tier eligible:

| Chỉ số | Giá trị | Nguồn probe |
|---|---:|---|
| SKU slow/dead bán-được (noise removed) | **12 SKU có match** | `mart_product_health` |
| Rows (SKU × khách) | **538** | engine join |
| Khách distinct match | **426** | engine join |
| Trong đó replenishment-due (DUE_SOON/OVERDUE) | **333 / 426** | `dim_customers.next_purchase_signal` |
| Có discount_sensitivity (gate được) | **426 / 426** (chỉ 7 FULL_PRICE) | `dim_customers.discount_sensitivity` |
| 2 SKU vốn lớn | `VCST21003L001` DOG 35.2M (250+ buyer), `VTST23023L001` QUESTION 41.5M (92 buyer) | — |

→ **Cơ hội thực lớn hơn FIND-008 narrow probe.** Engine khả thi NGAY ở quy mô hiện tại, không phải chỉ "build sẵn cho tương lai".

**Noise CLEAR_DEADSTOCK xác nhận:** `Vận Hành` 11 SKU/27.6M + `Uncategorized` 1 SKU/9.0M = 12 SKU/36.6M phải loại; còn lại 5 SKU/5.5M sellable (DS 4 + Medicine 1).

---

## Ràng buộc data thực tế (đọc trước khi build)

1. **Match key DUY NHẤT = SKU past-purchase** (`fact_sales.product_key` + `customer_key`, line-grain, FK đã có). KHÔNG dùng category (=blast, dead-cat ≈ toàn catalog FineJapan), brand (`product_affinity` chỉ 2 giá-trị = hỏng), affinity-col (`top_affinity_sku` 68% thưa).
2. **`mart_product_health` chỉ track 104 SKU** (101 có health_class). `health_class` chỉ populate cho ~42 SKU có MISA COGS; SKU không-COGS vẫn có velocity/inventory. **Cần verify** phủ này không bỏ sót SKU ế ngoài 104 (xem P1 verify step).
3. **2/5 dead-thật có 0 past-buyer** (failed-launch) → đẩy sang **merchandising fallback** (bundle/markdown/delist), KHÔNG vào engine nhắm khách.
4. **MASKED_REPEAT (433)** không DM trực tiếp được → route Shopee-native; **Shopee messaging/campaign API chưa xác minh** (open question).
5. **Track RIÊNG** khỏi NBA customer-state queue (`mart_customer_action_queue`): trigger inventory-driven ≠ customer-state-driven.
6. **PII:** worklist (tên/SĐT) KHÔNG commit git — đọc trực tiếp dashboard/cache; export ngoài repo nếu cần (xem Cảnh báo PII stage 05).
7. **DuckDB single-writer / read-only:** mọi probe parquet read-only; sync ghi cache.db tuân 1-writer rule (xem `crm/sync`).

---

## Tổng quan phase

| Phase | Tên | Thời hạn | Status | File |
|---|---|---|---|---|
| P0 | Dọn tín hiệu nguồn (prereq) | 0.5 ngày | ✅ DEPLOYED (2026-06-21) | (inline dưới) |
| P1 | Mart match warehouse (engine core) | 2-3 ngày | ✅ DEPLOYED (2026-06-21) | [phase-p1](./PLAN-004-phase-p1-deadstock-match-mart.md) |
| P2 | Serving + routing 2 kênh | 2-3 ngày | ✅ DEPLOYED data path · Hug/Shopee activation pending | [phase-p2](./PLAN-004-phase-p2-serving-routing.md) |
| P3 | Đo + ngưỡng kích hoạt | 1-2 ngày | pending | (inline dưới) |

**Phụ thuộc:**
```
P0 (dọn noise) ──→ P1 (mart match) ──→ P2 (serving+routing) ──→ P3 (đo+ngưỡng)
                                   └─(P3 trigger threshold gate quyết định P2 có chạy không)
```

---

## P0 — Dọn Tín Hiệu Nguồn (prereq, rẻ, làm trước)

**Priority:** cao (nền cho mọi phase). **Owner:** Data. **Effort:** 0.5 ngày.
**Status: ✅ DEPLOYED (2026-06-21).** Code viết + validate + deploy xong; filter live trên warehouse, CLEAR_DEADSTOCK 17→5 SKU/5.5M verified.

**Mục tiêu:** loại category không-bán-được (`Vận Hành`, `Uncategorized`, NULL→coalesce 'Uncategorized'→loại) khỏi trigger `CLEAR_DEADSTOCK` để mart action queue đáng tin — hiện ~70% (12/17 SKU, 36.6M/42.1M) là noise vận hành/nội bộ (UMBRELLA, demo VFJDEMOH001, mã VB23/VB24).

**Validate live parquet (2026-06-20):** CLEAR_DEADSTOCK **17 → 5 SKU / 5.5M**; loại 11 `Vận Hành` (27.6M) + 1 `Uncategorized` (9.0M). Filter đã thêm vào `mart_product_action_queue.sql` nhánh CLEAR_DEADSTOCK: `category NOT IN ('Vận Hành','Uncategorized')` (NULL coalesce 'Uncategorized' nên cũng bị loại).

**Dependencies:** không.

### Related code files
- **Modify:** `transformation/models/marts/core/mart_product_action_queue.sql` — thêm điều kiện loại noise category vào nhánh `CLEAR_DEADSTOCK` (và cân nhắc `DELIST`) của CTE `classified` (dòng 91-107).

### Data flow
`mart_product_health` (category, is_dead_stock, dead_stock_value_at_risk) → CTE `classified` gán `action_type` → **chèn guard category** → SELECT WHERE action_type IS NOT NULL.

### Implementation steps
1. Trong `classified` CTE, nhánh `CLEAR_DEADSTOCK` (dòng 94-96): thêm `AND category NOT IN ('Vận Hành','Uncategorized')`. Cùng guard cho nhánh `DELIST` (dòng 103-105) để hàng vận hành không lọt DELIST.
2. Comment SQL: giải thích **lý do nghiệp vụ** ("category nội bộ/vận hành không bán lẻ — không phải dead-stock thương mại"), KHÔNG reference finding-code/phase.
3. Cân nhắc dùng allow-list category bán-được thay vì deny-list nếu catalog mở rộng (deny-list 2 giá trị hiện đủ, KISS — chốt deny-list).
4. Build lại model: `dbt run --select mart_product_action_queue` trong container data_platform. Adding/đổi node → cần restart data_platform nếu thêm node mới (đây chỉ sửa SQL, không thêm node → run thường đủ).
5. Verify: CLEAR_DEADSTOCK chỉ còn 5 SKU sellable / ~5.5M (không còn `Vận Hành`/`Uncategorized`).

### Todo
- [x] Thêm guard `category NOT IN ('Vận Hành','Uncategorized')` vào nhánh CLEAR_DEADSTOCK (NULL→coalesce 'Uncategorized'→loại).
- [x] Comment nghiệp vụ (không phase/finding ref).
- [x] Validate live parquet: CLEAR_DEADSTOCK 17 → 5 SKU / 5.5M (loại 11 Vận Hành 27.6M + 1 Uncategorized 9.0M).
- [x] **Deploy (2026-06-21):** `dbt run --select mart_product_action_queue` + rebuild serving view. CLEAR_DEADSTOCK 17→5 SKU/5.5M verified live.

### Success criteria
- `mart_product_action_queue` WHERE action_type='CLEAR_DEADSTOCK' không còn category nội bộ; count + tổng vốn khớp probe (5 SKU / 5.5M).

### Risk
| Risk | L×I | Mitigation |
|---|---|---|
| Deny-list miss category nội bộ khác mới | thấp×TB | P1 verify-coverage step rà toàn category; mở rộng deny-list nếu lộ thêm |
| Sửa SQL làm vỡ nhánh khác | thấp×cao | Guard chỉ thêm AND vào 2 nhánh dead, không động RESTOCK/REVIEW/PROMOTE; verify count toàn action_type trước/sau |

### Security/PII
Không có PII (mart product-level).

---

## P1 — Mart Match (engine core)

→ **Chi tiết:** [PLAN-004-phase-p1-deadstock-match-mart.md](./PLAN-004-phase-p1-deadstock-match-mart.md)

Tóm tắt: mart mới `mart_deadstock_target_queue` (grain = SKU ế × khách) ghép universe slow/dead bán-được (từ `mart_product_health` đã dọn), **scope chốt own-brand Fine Japan Vietnam — filter `brand_code='FJV'`** (20 SKU/81.1M, ~97% vốn + ~342/426 buyer của universe rộng) × past-buyer (`fact_sales` COMPLETED) × gate tier eligible (LIVE_CORE/SECOND_ORDER/DORMANT_VALUABLE/LAPSED_VALUABLE/MASKED_REPEAT), enrich replenishment-due + discount-sensitivity, rank + reason fragments. **Owner:** Data. **Depends:** P0.

---

## P2 — Serving + Routing 2 Kênh

→ **Chi tiết:** [PLAN-004-phase-p2-serving-routing.md](./PLAN-004-phase-p2-serving-routing.md)

Tóm tắt: sync `mart_deadstock_target_queue` → cache.db (pattern `reverse_etl_warehouse_to_crm`), push subset contactable → Hug D1 campaign "deadstock-resell" (voucher engine, **leg tự động**), route MASKED_REPEAT → **export list → ops chạm thủ công Shopee Seller Center** (KHÔNG có API messaging — resolved bằng research, xem P2 + report). Track riêng. **Owner:** Data + CRM/Marketing. **Depends:** P1. Shopee leg KHÔNG còn blocked: manual workflow đã chốt.

---

## P3 — Đo + Ngưỡng Kích Hoạt

**Priority:** TB (gate quyết định engine "đáng chạy"). **Owner:** Data + Marketing. **Effort:** 1-2 ngày. **Dependencies:** P1 (mart) cho threshold compute; P2 cho holdout outreach.

**Mục tiêu:** (a) định nghĩa **trigger threshold** engine tự bật khi vốn-ế tích đủ; (b) holdout/measurement đo incremental.

### Trigger threshold — CHỐT khởi điểm (owner 2026-06-20)
Engine "đáng chạy" khi mart vượt **một trong**:
- **vốn-kẹt-bán-được ≥ 30M VND** (bằng cỡ 1 SKU lớn như VCST21003L001 35M), HOẶC
- **≥ 3 SKU mỗi cái có ≥ 20 past-buyer eligible**.

→ Compute từ mart P1: tổng `stock_value_at_mac`/`dead_stock_value_at_risk` của SKU có ≥20 buyer. Hiện tại (probe): 2 SKU lớn (35M+41.5M=76.7M) đều >20 buyer → **đã vượt cả 2 ngưỡng** → engine đáng chạy NGAY. Đây là ngưỡng khởi điểm; review lại sau 1 chu kỳ.

### Holdout / measurement
- Mỗi SKU-campaign giữ **10-20% past-buyer eligible làm holdout** (không outreach) → đo conversion incremental (tránh nhận công đơn tự đến — nguyên tắc PLAN-001 §Rủi ro).
- KPI: (1) conversion past-buyer được chạm vs holdout; (2) vốn-kẹt-bán-được giảm theo SKU (so `stock_value_at_mac` trước/sau); (3) voucher issue→redeem→đơn-lặp (qua Hug attribution, xem phase-hug §3).

### Implementation steps
1. SQL/notebook compute threshold metric từ mart P1 (tổng vốn của SKU ≥M buyer) → so ngưỡng → cờ `engine_should_run`.
2. Định nghĩa holdout: cột `is_holdout` (hash customer_key % bucket) trong mart P1 hoặc tại serving — **chốt ở P1 mart để deterministic & sync được** (xem phase-p1).
3. KPI card Metabase (engine health): #SKU active, vốn-kẹt-bán-được, #khách target, redeem rate, vốn giảm. Dùng skill `/deploy-metabase-blueprint` (không patch tay).
4. Review cadence: weekly trong [06 execution log](../06-execute/README.md).

### Todo
- [x] Owner chốt ngưỡng: ≥30M VND HOẶC ≥3 SKU×≥20 buyer (2026-06-20, khởi điểm).
- [ ] Compute `engine_should_run` flag từ mart P1.
- [ ] Holdout column quyết định (P1 mart) + đảm bảo sync giữ holdout.
- [ ] KPI blueprint engine-health (Metabase) qua skill.
- [ ] Wire weekly review vào 06 execution log.

### Success criteria
- Threshold rule có con số owner-chốt; flag compute được; holdout giữ 10-20%; KPI card live; đo được conversion incremental + vốn giảm.

### Risk
| Risk | L×I | Mitigation |
|---|---|---|
| Base nhỏ → holdout làm mẫu conversion không đủ power | cao×TB | Gộp đo cross-SKU; đọc directional không claim significance; owner biết trước |
| Threshold đặt sai → engine chạy lúc vốn quá nhỏ (phí effort) | TB×TB | Khởi điểm bảo thủ (≥30M); review sau 1 chu kỳ |

### Security/PII
KPI level aggregate (không PII). Holdout list = PII → giữ trong cache/dashboard, không export git.

---

## File ownership (không phase nào đụng file phase khác)

| Phase | Files sở hữu |
|---|---|
| P0 | `mart_product_action_queue.sql` |
| P1 | `mart_deadstock_target_queue.sql` (mới) + `schema.yml` entry + `sources`/ref |
| P2 | `crm/sync/duckdb_reader.py`, `sqlite_upsert.py`, `cache_schema.sql`, reverse_etl + Hug campaign config |
| P3 | Metabase blueprint + holdout col (chốt trong P1 mart, P3 chỉ tiêu thụ) |

---

## Rủi ro tổng thể & open questions

**Decisions chốt 2026-06-20 (đóng open Q #1-#3):**
1. ✅ **Ngưỡng kích hoạt — CHỐT:** ≥30M VND HOẶC ≥3 SKU mỗi cái ≥20 past-buyer eligible (khởi điểm). Probe đã vượt → chạy ngay.
2. ✅ **Shopee leg — RESOLVED bằng research** ([report](../../reports/researcher-260620-2217-shopee-seller-messaging-masked-buyers-re-engagement-report.md)): KHÔNG có API messaging Shopee → leg Shopee KHÔNG tự động hoá; engine chỉ **sinh danh sách** masked-repeat (433), ops chạm thủ công qua Seller Center (Chat Broadcast + Repeat Buyer Voucher auto + Follow Prize). Caveat: quota VN chưa verify.
3. ✅ **Scope sản phẩm P1 — CHỐT:** own-brand **Fine Japan Vietnam**, filter chính `brand_code='FJV'`. Giữ ~97% vốn + ~342/426 past-buyer của universe rộng.

**Open questions còn lại:**
4. **`product_affinity` 2-giá-trị** — có kế hoạch làm brand taxonomy thật? (ảnh hưởng brand-match tương lai, KHÔNG block engine hiện tại.)

**Follow-up post-deploy (2026-06-21, chưa làm):**
1. 4 SKU NULL-`brand_code` bị filter `brand_code='FJV'` bỏ sót (**6.85M**, chủ yếu `VCMC21010H001` Medicine 5.46M) — chờ owner: fix brand_code source HOẶC fallback `brand_name='Fine Japan Vietnam'` + redeploy.
2. Hug campaign "deadstock-resell" activate: config voucher (min-order + SKU-guard margin) + destination URL (hiện SEEDED+PAUSED).
3. Holdout hiện 23.5% (mục tiêu ~20%) — tune `% 20 < 4` nếu P3 cần.
4. Shopee: verify quota Chat Broadcast VN khi chạy đợt đầu.
