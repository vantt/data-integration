---
title: "PLAN-004 P2 - Serving + Routing 2 Kênh"
status: deployed
priority: P2
parent: "PLAN-004"
stage: 5
created: 2026-06-20
---

# PLAN-004 P2 — Serving + Routing 2 Kênh

**Parent:** [PLAN-004](./PLAN-004-deadstock-customer-targeting-engine.md) · **Depends:** P1 (mart). Shopee leg **RESOLVED** (open Q #2 đóng — KHÔNG có API messaging, chốt manual workflow).

> Đưa `mart_deadstock_target_queue` ra ngoài: sync → cache.db (pattern reverse_etl), push subset contactable → Hug D1 campaign voucher, route MASKED_REPEAT → Shopee-native. Track RIÊNG khỏi NBA customer-state queue.

> **2 leg tách bạch (chốt 2026-06-20):**
> - **Leg Hug — TỰ ĐỘNG:** subset contactable (real contact) → Hug D1 campaign "deadstock-resell", voucher engine self-funding, route lúc scan.
> - **Leg Shopee — THỦ CÔNG (KHÔNG có API):** masked-repeat (433) → engine chỉ **sinh danh sách export**; ops chạm tay qua Seller Center. [Research report](../../reports/researcher-260620-2217-shopee-seller-messaging-masked-buyers-re-engagement-report.md): KHÔNG có API messaging Shopee → cách phủ in-channel = **Chat Broadcast** (2 msg/buyer/tuần, ~280–350/433) + **Repeat Buyer Voucher** (auto, passive) + Follow Prize. ~25 phút/đợt, $0, ~99% phủ qua 2 tuần. **Caveat:** nguồn hub MY/SG/PH, **quota VN chưa verify** → cần xác minh khi chạy.

---

## Overview
- **Priority:** TB-cao. **Owner:** Data (sync) + CRM/Marketing (Hug campaign) + Ops (Shopee Seller Center thủ công). **Effort:** 2-3 ngày (Shopee leg = export list + ops chạm tay ~25 phút/đợt, không dev).
- **Status:** ✅ DEPLOYED (data path) 2026-06-21 · Hug/Shopee **activation PENDING**.

> **Deploy 2026-06-21 (data path GREEN):** `wh_deadstock_target` (cache.db `/data/cache.db`) = **498 rows** (route HUG=309, SHOPEE_NATIVE=189); reverse_etl sync OK; crm container rebuilt (`--build`); serving view bootstrapped (stop/start Metabase).
> **Activation còn PENDING:** Hug campaign "deadstock-resell" **SEEDED nhưng PAUSED** (Hug infra có sẵn) — cần config voucher (min-order + SKU-guard margin) + destination URL trước khi bật. Shopee export script **sẵn sàng** (CSV ngoài git) — verify quota Chat Broadcast VN khi chạy đợt đầu.
> **Bonus fix:** thêm `LIVE_CORE` vào `crm/src/hug/targeting_catalog.py`.

## Key insights (ground)
- Pattern reverse-ETL đã chuẩn hóa: `_<MART>_COLS` pinned contract → `fetch_*` (read-only DuckDB, `duckdb_reader.py`) → `upsert_*` (ON CONFLICT, `sqlite_upsert.py`) → `CREATE TABLE IF NOT EXISTS` (`cache_schema.sql`) → wire trong `reverse_etl_warehouse_to_crm.run()`. 1-writer rule: Python ghi CHỈ cache.db.
- Hug = dynamic touchpoint platform: campaign là DATA (D1 row), voucher engine self-funding (min-order + loại SKU lỗ), route lúc scan. Deadstock-resell = thêm 1 campaign trên Hug, KHÔNG build kênh mới (xem [phase-hug](../../260619-1030-crm-nba-resell-engine/phase-hug-dynamic-touchpoint-platform.md)).
- MASKED_REPEAT (433) không DM trực tiếp → Shopee-native. **KHÔNG có API messaging Shopee** (research-confirmed) → engine chỉ export list, ops chạm tay Seller Center (Chat Broadcast + Repeat Buyer Voucher auto + Follow Prize).

## Architecture / data flow

```
WAREHOUSE                          CACHE (cache.db, SQLite WAL)            OUTREACH
mart_deadstock_target_queue ──┐
  (parquet rolling)           │ fetch_deadstock_targets (read_only)
                              ▼
                       wh_deadstock_target ──┬─ route_channel='HUG' ──────► Hug D1 campaign (TỰ ĐỘNG)
                       (CREATE IF NOT EXISTS)│   (contactable subset)        "deadstock-resell"
                                             │                               voucher engine
                                             └─ route_channel='SHOPEE_NATIVE'► export list → ops THỦ CÔNG
                                                 (MASKED_REPEAT)              Seller Center*
```
\* KHÔNG có API messaging Shopee (research-confirmed). Engine chỉ export CSV (ngoài git, PII). Ops chạm tay: Chat Broadcast (2 msg/buyer/tuần) + Repeat Buyer Voucher (auto) + Follow Prize. Caveat: quota VN chưa verify.

## Requirements
**Functional**
- Sync mart → bảng cache `wh_deadstock_target` (idempotent upsert, grain product_key×customer_key).
- Subset `route_channel='HUG'` & `voucher_eligible=true` & NOT is_holdout → push Hug campaign audience.
- Subset `route_channel='SHOPEE_NATIVE'` & NOT is_holdout → Shopee export list.
- Track riêng: bảng/queue tách khỏi `wh_action_queue` (NBA customer-state).

**Non-functional**
- Read-only warehouse, single-writer cache (tuân `crm/sync` rule).
- TIMESTAMPTZ cast VARCHAR trong SELECT (runtime không pytz — theo `_open_conn`).
- Pinned column contract (fail-fast dbt-rename).

## Related code files
- **Modify:** `crm/sync/duckdb_reader.py` — thêm `_MART_DEADSTOCK_TARGET_COLS` + `fetch_deadstock_targets(conn)`.
- **Modify:** `crm/sync/sqlite_upsert.py` — thêm `upsert_deadstock_target(conn, rows)` (ON CONFLICT(product_key,customer_key)).
- **Modify:** `crm/sync/cache_schema.sql` — `CREATE TABLE IF NOT EXISTS wh_deadstock_target (...)` (grain composite PK product_key+customer_key, route_channel, voucher_eligible, is_holdout, target_rank, reason_fragment, vốn SKU, enrich cols).
- **Modify:** `crm/sync/reverse_etl_warehouse_to_crm.py` — thêm fetch + `_run_step(..., "wh_deadstock_target", su.upsert_deadstock_target, rows)`.
- **Create (Hug campaign config):** `hug_campaign` D1 row "deadstock-resell" (targeting JSON: tier IN eligible AND voucher_eligible; destination = Zalo OA / landing voucher reveal). Xem phase-hug §Data model + admin route `/hug/campaign/upsert`.
- **Create (Shopee leg — manual, KHÔNG dev API):** export script/notebook sinh CSV danh sách MASKED_REPEAT (ngoài git, PII) cho ops thao tác Seller Center. KHÔNG còn blocked — workflow thủ công chốt (open Q #2 resolved, [report](../../reports/researcher-260620-2217-shopee-seller-messaging-masked-buyers-re-engagement-report.md)).

## Implementation steps
1. **duckdb_reader:** pin `_MART_DEADSTOCK_TARGET_COLS` (đúng output schema P1, cast timestamp→VARCHAR); `fetch_deadstock_targets` SELECT từ `mart_deadstock_target_queue` (resolve customer_id qua dim nếu cache cần — theo pattern fact_orders).
2. **cache_schema.sql:** `wh_deadstock_target` với PK (product_key, customer_key), index trên route_channel + is_holdout (lọc subset nhanh).
3. **sqlite_upsert:** `upsert_deadstock_target` — INSERT … ON CONFLICT(product_key,customer_key) DO UPDATE; trả count.
4. **reverse_etl run():** thêm `deadstock_rows = dr.fetch_deadstock_targets(olap_conn)` + `_run_step` (Group 2 insight-style). **Re-raise on error** (theo pattern; reverse_etl scheduled job sẽ red nếu lỗi).
5. **Hug campaign:** định nghĩa "deadstock-resell" row — audience predicate = strategic_tier IN (eligible) AND voucher_eligible AND NOT holdout; offer = voucher self-funding (min-order + SKU-guard loại SKU margin-âm); priority first-match; quota. Push qua admin HMAC route.
6. **Shopee leg (manual — resolved):** KHÔNG có API messaging Shopee (research-confirmed) → export CSV list MASKED_REPEAT (ngoài git, PII), ops chạm tay Seller Center: Chat Broadcast (2 msg/buyer/tuần, ~280–350/433) + Repeat Buyer Voucher (auto, passive) + Follow Prize (~25 phút/đợt, ~99% phủ qua 2 tuần). Verify quota VN khi chạy đợt đầu.
7. **CRM container baked:** crm/sync code baked trong image → sau sửa Python, `docker compose up -d --build crm` để serving thấy code mới (xem memory: new mart CRM integration 2 manual steps).
8. **Serving view (nếu mart cần lộ trên Metabase/360):** bootstrap serving view (stop Metabase trước) — chỉ khi P3 KPI card cần.

## Todo
- [x] `_MART_DEADSTOCK_TARGET_COLS` + `fetch_deadstock_targets` (read-only, timestamp→VARCHAR).
- [x] `wh_deadstock_target` schema (composite PK + index route/holdout).
- [x] `upsert_deadstock_target` (ON CONFLICT composite).
- [x] Wire vào `reverse_etl.run()` + re-raise. (sync OK, 498 rows.)
- [x] `docker compose up -d --build crm`; chạy thử reverse_etl → verify row count: **498 rows** (HUG=309, SHOPEE_NATIVE=189).
- [x] Confirm track riêng (không lẫn wh_action_queue).
- [~] Hug campaign "deadstock-resell" SEEDED nhưng **PAUSED** — còn config voucher (min-order + SKU-guard margin) + destination URL để bật.
- [ ] Shopee leg (manual): export script sẵn sàng → ops Seller Center (Chat Broadcast + Repeat Buyer Voucher + Follow Prize); verify quota VN khi chạy đợt đầu.

## Success criteria
- `wh_deadstock_target` populate đúng grain, count khớp mart.
- Hug campaign "deadstock-resell" active, audience đúng (eligible + voucher_eligible − holdout); voucher có min-order + SKU-guard.
- MASKED_REPEAT subset export list (CSV ngoài git) cho ops Seller Center thủ công, không trộn Hug.
- reverse_etl run pass; queue tách biệt NBA customer-state.

## Risk assessment
| Risk | L×I | Mitigation |
|---|---|---|
| Shopee API messaging không tồn tại (research-confirmed) | đã xảy ra×TB | manual workflow chốt: export list + ops Seller Center (Chat Broadcast + Repeat Buyer Voucher auto + Follow Prize); MASKED_REPEAT leg không block Hug leg |
| Quota VN Chat Broadcast khác hub MY/SG/PH | TB×TB | nguồn report hub khác VN; verify quota VN khi chạy đợt đầu, điều chỉnh nhịp gửi |
| Voucher ăn lãi nhóm full-price | TB×cao | `voucher_eligible=false` cho FULL_PRICE (P1); Hug voucher min-order + SKU-guard margin-âm |
| Sync lỗi red scheduled job | TB×TB | _run_step ghi wh_sync_run failed + re-raise (pattern); fetch trước upsert; idempotent |
| Composite PK mismatch (grain) | thấp×cao | PK (product_key,customer_key) khớp mart grain; test trùng grain ở P1 |
| crm container không thấy code mới | TB×TB | --build crm bắt buộc (code baked image — memory) |
| Quét-lặp Hug phát voucher trùng | thấp×TB | Hug voucher engine: unique gắn customer_id, single-use (phase-hug §5) |

## Security / PII
- `wh_deadstock_target` chứa PII (customer_key→phone, full_name). Sống trong cache.db (không git). KHÔNG export worklist ra repo.
- Shopee export list (nếu fallback) = PII → lưu ngoài git (Google Sheet / local untracked), xóa sau dùng.
- Hug consent gate: chỉ outreach khách có consent kênh tương ứng (phase-hug §8) — voucher push tôn trọng DNC.

## Next steps
→ P3 đọc holdout + vốn SKU từ mart/cache cho measurement + threshold; đo redeem→đơn-lặp qua Hug attribution.
