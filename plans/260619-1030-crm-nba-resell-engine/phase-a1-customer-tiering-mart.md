# Phase A1 — Customer Tiering Mart (nền tảng)

> Stage A · Status: 🟢 DEPLOYED (2026-06-19) — built vào warehouse + serving-integrated, runs GREEN; phân bố khớp (4183/1598/1144/433/122/56/27)=7563 · Phụ thuộc: — · Context: [`discussion.md`](./discussion.md) §16–17
> Là **single source of truth** về "khách thuộc nhóm chiến lược nào". Hug (`hug_customer`), NBA engine (Stage B), và A2/A3/A4 đều đọc nó.

## Mục tiêu

Một mart warehouse phân **mọi khách (7,563) vào đúng 1 tier** — rẻ, set-based, dẫn xuất từ `dim_customers`.

## Tier — cây quyết định (first-match, gán đúng 1) · 7 tier

`real` = `source_contact_quality='real'` (SĐT thật) · `masked` = NULL/rỗng/che.
```
1. order_count = 0                                  → NONBUYER         (tạo nhưng chưa mua)
2. real + recency≤90 + order_count>1                → LIVE_CORE        (KH sống, giữ chân)
   real + recency≤90 + order_count=1                → SECOND_ORDER     (mới, đẩy đơn-2)
3. masked + order_count>1                           → MASKED_REPEAT    (Hug identity capture)
4. real + recency 91–365 + (repeat OR value≥SILVER) → DORMANT_VALUABLE (win-back ƯU TIÊN)
5. real + recency>365 + (repeat OR value≥SILVER)    → LAPSED_VALUABLE  (win-back THỬ, đo rồi suppress)
6. else                                             → GRAVEYARD        (suppress)
```

**Phân bố thực — validated read-only 2026-06-19** (parquet dim_customers):
| Tier | Size | Cơ chế phục vụ |
|---|---|---|
| LIVE_CORE | **56** | NBA engine + CS high-touch (Stage B) |
| SECOND_ORDER | **27** | A3 đẩy đơn-2 |
| DORMANT_VALUABLE | **122** | A4 win-back ưu tiên (nguội gần 91–365) |
| LAPSED_VALUABLE | **1,144** | A4 win-back thử (nguội xa 365+, contactable+repeat) |
| MASKED_REPEAT | **433** | A2 Hug identity capture |
| NONBUYER | **1,598** | nuôi lead sau (chưa action v1) |
| GRAVEYARD | **4,183** | suppress |
| **TOTAL** | **7,563** | |

## Quyết định đã chốt

1. ✅ **Mart riêng `mart_customer_tier`** (không cột trên dim_customers) — iterate ngưỡng không cần `--full-refresh`; input = dim_customers.
2. ✅ **Tách SECOND_ORDER** khỏi LIVE_CORE (action khác; đo activation riêng).
3. ✅ **Ngưỡng 90 / 365** (research-backed; giữ dù LIVE_CORE nhỏ).
4. ✅ **Tách NONBUYER** (0 đơn) khỏi GRAVEYARD — để sau nuôi lead riêng.
5. ✅ **Tách LAPSED_VALUABLE** (real + repeat/value + recency>365) khỏi GRAVEYARD — 1.144 khách contactable proven-repeat nguội xa; win-back ưu tiên thấp/test, không suppress nhầm cùng nghĩa địa thật. (data lộ: cap 365 đẩy 1.144 này vào graveyard nếu không tách.)

## Phạm vi

- Mart `mart_customer_tier` (1 dòng/khách): `customer_id`, `strategic_tier`, `tier_reason` (fragments cấu trúc), + các signal dùng để gán (recency, order_count, value_group, is_contactable, channel).
- Sync sang cache.db (CRM) + push subset (`tier, recency_days, value_group, is_contactable`) lên D1 `hug_customer` nightly.

## Related code

- Tạo: `transformation/models/marts/customer/mart_customer_tier.sql` (input dim_customers)
- Sửa: `crm/sync/reverse_etl_warehouse_to_crm.py` (sync tier) + job push `hug_customer` (A2/#6)
- Lưu ý: thêm dbt node → restart data_platform (manifest reload); rebuild serving views nếu cần.

## Todo

- [x] `mart_customer_tier.sql` (7 tier first-match) + tier_reason — `dbt parse` OK
- [x] validate phân bố read-only: 56/27/122/1144/433/1598/4183 = 7563 ✓
- [x] **build vào DB** — deployed (restart manifest + dbt run), runs GREEN, serving view registered (bootstrap, Metabase stop/start)
- [x] **sync tier → cache.db** — `wh_customer_tier` (reverse_etl: duckdb_reader/sqlite_upsert/cache_schema); crm container rebuilt (crm/sync baked in image)
- [ ] (A2) nightly push hug_customer → D1 (thuộc M2/M3)

## Success criteria

- Mỗi khách có đúng 1 `strategic_tier` + `tier_reason`; phân bố khớp ước; không phá KPI/serving.

## Open

- (sau) NONBUYER có nuôi không + cơ chế.
- tier_reason fragment format thống nhất với Hug/engine reason fragments.
