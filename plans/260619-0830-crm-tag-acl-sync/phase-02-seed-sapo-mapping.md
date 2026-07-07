# Phase 02 — Seed Sapo Mapping vào ACL Tables

**Context:** [plan.md](plan.md) · Requires: Phase 00 + 01 done

## Overview
- **Priority:** P1
- **Status:** ✅ DONE
- Seed `crm_ext_tag` với 6 Sapo customer_group đã verify, map sang canonical `crm_tag`. Đây là bước "khai báo biên" — mọi Sapo group đều phải có entry ở đây để sync biết cách translate.

## Key Insights
- **ext_key = Sapo group id** (ổn định qua rename), không phải code. Verified 2026-07-06 bằng query DISTINCT trên cache.db: chỉ có **6 group thực** (8 giá trị raw do 2 group bị rename code giữa chừng).
- `direction='inbound'` cho tất cả Sapo mapping ở v1 (chưa write-back).
- Migration này là **data migration** — không có DDL mới, chỉ INSERT OR IGNORE.
- Group RETAIL là `is_default:true` chiếm 6.451/7.575 khách → tag hóa nó là 6.4k rows zero-information. Seed `is_active=0` — bật lại được bằng UPDATE, không cần migration.
- Category dùng enum sẵn có từ migration 0014: `behavioral | demographic | preference | vip_tier | risk | source`. Tag segment thương mại (KH Sỉ, Ký Gửi, US) dùng `demographic`; KHÔNG dùng `vip_tier`/`risk` cho sync tags — 2 category này được `mart_customer_action_queue` tiêu thụ (plan 260706-1738) và bên đó chỉ tin tag người gán (`source='crm_user'`); tránh cả va chạm ngữ nghĩa lẫn phụ thuộc vào filter của bên kia (defense-in-depth). Ngoại lệ: group VIP map vào tag VIP sẵn có (vip_tier) — an toàn vì 1738 đã filter source, và chỉ có 1 khách.

## Mapping đã verify (query cache.db 2026-07-06)

| ext_key (group id) | ext_label | Số KH | crm_tag canonical | category | is_active | Ghi chú |
|---|---|---|---|---|---|---|
| `1812238` | RETAIL (BANLE/TYPE_RETAIL) | 6.451+184 | — | — | **0** | default group, zero info; bật sau nếu cần |
| `1812239` | WHOLESALE (BANBUON/TYPE_WHOLESALE) | 158+3 | "KH Sỉ" (tạo mới) | demographic | 1 | |
| `2421894` | US (CTN00014) | 662 | "KH US giao hộ" (tạo mới) | demographic | 1 | khớp segment CROSSBORDER; dim đã có flag `is_us_gift_recipient` |
| `2308212` | Selly (CTN00013) | 104 | "Selly" (tạo mới) | source | 1 | kênh reseller — bản chất là nguồn |
| `2281219` | Ký Gửi (KY_GUI) | 11 | "Ký Gửi" (tạo mới) | demographic | 1 | consignment partner |
| `1812240` | VIP | 1 | "VIP" (tag-00000000-0001 đã seed) | vip_tier | 1 | dùng tag sẵn có, không tạo mới |

Giá trị raw `'Unknown'` (1 row, không phải JSON) → `customer_group_id` NULL sau phase 00 → sync tự skip, không cần entry.

## Related Code Files
- **Tạo:** `crm/migrations/0040_seed_sapo_tag_mapping.up.sql` (kế tiếp 0039 của phase 01)
- **Đọc:** `crm/migrations/0003_customer_profile_custom_fields_tags.up.sql` (seed crm_tag hiện có)
- **Đọc:** `crm/migrations/0014_custom_field_section_tag_category.up.sql` (category enum)

## Implementation Steps

1. **Re-verify trước khi viết migration** (dữ liệu có thể đổi giữa lúc plan và lúc implement):
   ```sql
   SELECT customer_group_id, customer_group_name, customer_group_code, COUNT(*)
   FROM main_marts.dim_customers
   WHERE customer_group_id IS NOT NULL
   GROUP BY 1, 2, 3 ORDER BY 4 DESC;
   ```
   Group id mới xuất hiện → thêm dòng vào bảng mapping trên (quyết định map hay `is_active=0`).
2. `INSERT OR IGNORE INTO crm_tag` cho 4 tag mới ("KH Sỉ", "KH US giao hộ", "Selly", "Ký Gửi") — tag_id cố định dạng seed để idempotent.
3. `INSERT OR IGNORE INTO crm_ext_tag` cho 6 group (ext_key = id string).
4. `INSERT OR IGNORE INTO crm_ext_tag_map` nối ext_tag → crm_tag, `direction='inbound'`, `is_active` theo bảng.

## Todo
- [x] Re-verify query group id trên warehouse (sau phase 00) — cùng 6 group, counts trôi nhẹ
- [x] `0040_seed_sapo_tag_mapping.up.sql` (+ down)
- [x] Apply + verify bằng SELECT trên crm_ext_tag_map — 5 active rows, xem báo cáo `reports/phase-02-implementation-report.md`

## Success Criteria
- Mọi `customer_group_id` thực tế đều có entry trong `crm_ext_tag`
- RETAIL có entry nhưng map `is_active=0`
- `SELECT count(*) FROM crm_ext_tag_map WHERE is_active=1` = 5 (4 demographic/source + 1 VIP)

## Risk
- Sapo tạo group mới sau khi seed → sync log `skipped-no-mapping` (phase 03) là tín hiệu để thêm row mới; quy trình: INSERT thêm, không xóa row cũ.
- Group id là số nguyên phía Sapo — lưu TEXT trong ext_key (nhất quán kiểu, tránh lỗi so sánh; DuckDB INTEGER từng silently strip underscore trong seed — tiền lệ dùng VARCHAR).
