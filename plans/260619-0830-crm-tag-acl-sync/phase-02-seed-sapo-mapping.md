# Phase 02 — Seed Sapo Mapping vào ACL Tables

**Context:** [plan.md](plan.md) · Requires: Phase 01 done

## Overview
- **Priority:** P1
- **Status:** ⬜ TODO
- Seed `crm_ext_tag` với các Sapo customer_group đã biết, map sang canonical `crm_tag` hiện có. Đây là bước "khai báo biên" — mọi Sapo group đều phải có entry ở đây để sync biết cách translate.

## Key Insights
- Sapo dùng `customer_group` dạng code string (TYPE_WHOLESALE, TYPE_RETAIL…) — lấy từ `wh_customer_base.customer_group` trong warehouse.
- Một số `customer_group` Sapo có thể không map được 1:1 sang canonical tag hiện có → cần tạo thêm `crm_tag` seed mới hoặc bỏ qua (is_active=0 trong map).
- `direction='inbound'` cho tất cả Sapo mapping ở v1 (chưa write-back).
- Migration này là **data migration** — không có DDL mới, chỉ INSERT OR IGNORE.

## Cần xác nhận trước khi viết migration

Chạy query để lấy danh sách `customer_group` thực tế trong warehouse:

```sql
-- Chạy trên DuckDB/Metabase
SELECT DISTINCT customer_group, COUNT(*) AS cnt
FROM main_marts.dim_customers
WHERE customer_group IS NOT NULL
GROUP BY 1
ORDER BY cnt DESC;
```

Kết quả sẽ quyết định nội dung seed trong migration 0023.

## Mapping dự kiến (cần verify với query trên)

| Sapo ext_key | ext_label | crm_tag canonical | Ghi chú |
|---|---|---|---|
| `TYPE_WHOLESALE` | KH Sỉ | "KH Sỉ" (tạo mới, category=vip_tier) | |
| `TYPE_RETAIL` | KH Lẻ | "KH Lẻ" (tạo mới, category=demographic) | hoặc bỏ qua nếu mặc định |
| `VIP` | VIP | "VIP" (tag-00000000-0001 đã seed) | |
| *(các giá trị khác từ query)* | | | xác nhận sau |

## Related Code Files
- **Tạo:** `crm/migrations/0023_seed_sapo_tag_mapping.up.sql`
- **Đọc:** `crm/migrations/0003_customer_profile_custom_fields_tags.up.sql` (seed crm_tag hiện có)
- **Đọc:** `crm/migrations/0014_custom_field_section_tag_category.up.sql` (category enum)
- **Chạy query:** `crm/sync/duckdb_reader.py` → `fetch_customer_base` (đây là nguồn customer_group)

## Implementation Steps

1. **Trước khi viết migration:** chạy query DISTINCT customer_group trên warehouse, ghi nhận kết quả.
2. Với mỗi group value chưa có `crm_tag` canonical tương ứng → thêm `INSERT OR IGNORE INTO crm_tag`.
3. `INSERT OR IGNORE INTO crm_ext_tag` cho từng Sapo group.
4. `INSERT OR IGNORE INTO crm_ext_tag_map` nối ext_tag → crm_tag với `direction='inbound'`, `is_active=1`.
5. Nhóm nào không rõ ý nghĩa / không muốn sync → insert crm_ext_tag nhưng để `is_active=0` trong map (có thể bật sau mà không cần migration).

## Todo
- [ ] Chạy query DISTINCT customer_group trên warehouse
- [ ] Quyết định mapping từng value
- [ ] `0023_seed_sapo_tag_mapping.up.sql`
- [ ] Apply + verify bằng SELECT trên crm_ext_tag_map

## Success Criteria
- Mọi `customer_group` value thực tế trong warehouse đều có entry trong `crm_ext_tag`
- Mỗi entry có ít nhất 1 row trong `crm_ext_tag_map` (active hoặc inactive)
- `SELECT count(*) FROM crm_ext_tag_map WHERE is_active=1` > 0

## Risk
- `customer_group` trong warehouse có thể là NULL hoặc empty → sync phải skip NULL (WHERE customer_group IS NOT NULL)
- Sapo thay đổi group code sau khi seed → cần quy trình: thêm row mới vào `crm_ext_tag` + `crm_ext_tag_map`, không xóa row cũ (idempotency)
