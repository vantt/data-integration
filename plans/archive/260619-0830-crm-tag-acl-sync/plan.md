# CRM Tag Anti-Corruption Layer + Inbound Sync

**Ngày:** 2026-06-19 · **Revised:** 2026-07-06 (data-contract fix + mirror reconcile + app-side consumer)
**Mục tiêu:** Thiết kế và implement ACL (Anti-Corruption Layer) cho hệ thống tags — đảm bảo CRM canonical tags độc lập khỏi vocabulary của bất kỳ hệ bán hàng nào (Sapo, Haravan, Shopify…), đồng thời sync tag tự động từ warehouse vào CRM.

---

## Vấn đề

| Vấn đề | Hiện trạng |
|--------|-----------|
| Không có cầu nối Sapo → CRM tag | `customer_group` đọc về `wh_customer_base` nhưng không map vào `crm_party_tag` |
| `crm_party_tag` không track nguồn | Không phân biệt tag do CRM user gán vs tag sync từ ngoài |
| Coupling ẩn | Nếu đổi sang Haravan, toàn bộ mapping phải viết lại |
| Không có mapping table | Không nơi nào định nghĩa "Sapo group WHOLESALE = CRM KH Sỉ" |
| **`customer_group` là JSON blob** | Verified 2026-07-06: cột chứa nguyên object JSON Sapo (`{"id":1812238,"code":"BANLE",...}`), KHÔNG phải code string. Cùng group id xuất hiện với 2 snapshot khác `code` (BANLE → TYPE_RETAIL sau rename) → key theo raw value hoặc code đều không ổn định; chỉ **group `id`** ổn định. `dim_customers.customer_type` hiện dựa vào `LIKE '%WHOLESALE%'` xuyên JSON — hack cần dọn cùng lúc. |

## Giải pháp: ACL pattern (đã có tiền lệ ở `crm_party_external_id`)

```
[Sapo] customer_group JSON {"id":1812239,"name":"WHOLESALE","code":"BANBUON",...}
    ↓  Phase 00: staging parse JSON → customer_group_id/code/name (1 điểm parse duy nhất)
[warehouse] dim_customers.customer_group_id = '1812239'
    ↓  wh_customer_base (cache.db)
    ↓  crm_ext_tag(ext_key='1812239') + crm_ext_tag_map (ACL boundary, trong crm.db)
    ↓  app-side consumer sync_party_tags.py (mirror-reconcile, theo tiền lệ sync_parties.py)
[CRM]  crm_party_tag(tag="KH Sỉ", source='sapo_v2_sync', ext_ref='1812239')

[Haravan] segment="wholesale"   (tương lai)
    ↓  thêm rows vào crm_ext_tag + crm_ext_tag_map — domain CRM không đổi
[CRM]  crm_tag.name="KH Sỉ"   ← không đổi gì
```

**Nguyên tắc kiến trúc (giữ nguyên invariant đã document trong `reverse_etl_warehouse_to_crm.py`):**
- Reverse-ETL/Python pipeline chỉ ghi cache.db. **App CRM là writer duy nhất của crm.db** — tag sync chạy qua consumer CLI trong `crm/src/` (như `sync_parties.py`), KHÔNG cross-write.
- Sync là **mirror cho rows sync-owned**: rows `source='sapo_v2_sync'` = hình chiếu trạng thái Sapo hiện tại (insert mới + xóa rows hết backing). Rows `source='crm_user'` bất khả xâm phạm. Không append-only — tránh CRM trôi khỏi sự thật khi khách đổi group.

---

## Phases

| # | Phase | Trạng thái | Output chính |
|---|-------|-----------|-------------|
| 00 | [Upstream: parse customer_group JSON tại staging](phase-00-customer-group-code-staging.md) | ✅ DONE | dbt staging expose `customer_group_id/code/name`; refactor `customer_type` CASE khỏi LIKE-hack (regression verified 161/662/11 khớp); propagate xuống `wh_customer_base` qua reverse-ETL thật |
| 01 | [Schema ACL + source column](phase-01-schema-acl.md) | ✅ DONE | Migration `0039_tag_acl_ext_mapping`: `crm_ext_tag`, `crm_ext_tag_map`, ALTER `crm_party_tag` ADD `source` + `ext_ref` — applied, verified via PRAGMA, 13 existing rows backfilled |
| 02 | [Seed Sapo mapping](phase-02-seed-sapo-mapping.md) | ✅ DONE | Migration `0040_seed_sapo_tag_mapping`: seed `crm_ext_tag` (6 groups) + `crm_ext_tag_map` (5 active) + 4 crm_tag mới — applied + verified, RETAIL không có map row (xem báo cáo phase-02) |
| 03 | [App-side consumer sync](phase-03-inbound-sync.md) | ✅ DONE | `crm/src/sync_party_tags.py` (mirror-reconcile) + `attach_tag` source-upgrade; chạy sau reverse-ETL cùng chuỗi với `sync_parties.py` — verified live: 939 synced tags, idempotent, 7/7 tests pass |
| 04 | Outbound write-back (gated) | ➡️ Moved | Moved sang [`260707-2343-crm-tag-deferred-followups`](../../260707-2343-crm-tag-deferred-followups/phase-01-outbound-tag-writeback.md) phase 01 — chờ Phase 07 `sync_outbox` |

**v1 scope:** Phase 00 + 01 + 02 + 03. Phase 04 moved sang backlog plan `260707-2343-crm-tag-deferred-followups`.

> **Status:** ✅ Plan hoàn tất (2026-07-07) — phase 00-03 implemented, tested, verified live. Phase 04 moved sang `260707-2343-crm-tag-deferred-followups`.

---

## Dependencies

- Phase 00 → 01 → 02 → 03 (strict sequential — upstream data contract trước, schema, seed, sync sau)
- Phase 04 (moved to `260707-2343-crm-tag-deferred-followups`) depends on Phase 07 (outbox infrastructure)
- `sync_party_tags.py` chạy sau reverse-ETL + sau `sync_parties.py` (cần party đã seed để resolve `crm_party_external_id`)
- **Consumer plans:** `260706-0833` phase-01 cần `source` column (phase 01 plan này); `260706-1738` filter `source='crm_user'` — hai bên đã khớp thiết kế, xem plan tương ứng

---

## Conflict rules (đã chốt)

| Tình huống | Xử lý |
|-----------|-------|
| sync muốn gán tag đã do `crm_user` gán | Giữ nguyên — CRM user wins (`INSERT ... ON CONFLICT DO NOTHING`) |
| sync muốn bỏ tag mà `crm_user` gán | Không bỏ — reconcile CHỈ xóa rows `source='sapo_v2_sync'` |
| CRM user gán tag đã có từ sync | `attach_tag` upgrade: `ON CONFLICT DO UPDATE SET source='crm_user', tagged_by=user` — từ đó sync không đụng nữa (app-side, scope phase 03) |
| Sync lần 2 — tag đã sync rồi | Idempotent — desired set không đổi thì không ghi gì |
| Khách đổi group ở Sapo (BANLE → BANBUON) | **Mirror-reconcile:** row sync-owned cũ bị xóa cứng, row mới insert. `ext_ref` giữ group id để audit. KHÔNG giữ tag cũ (append-only đã bị loại bỏ — xem Revised note) |
| Sapo group bị xóa/rename | ext_key = group **id** nên rename không ảnh hưởng; group biến mất khỏi feed → tags sync-owned tương ứng bị reconcile xóa (đúng ngữ nghĩa mirror) |

---

## Non-goals (v1)

- Không sync tag từ Messenger, Shopee, Zalo (chỉ Sapo customer_group)
- Không outbound write-back (Phase 04, moved sang `260707-2343-crm-tag-deferred-followups`)
- Không UI quản lý mapping (admin tự seed migration; UI governance thuộc `260706-0833` phase 03 — plan đó đã được vá để merge/archive xử lý `crm_ext_tag_map`)
- Không tag hóa group RETAIL mặc định (6.451/7.575 khách, zero information — seed `is_active=0`, bật lại được không cần migration)

> Backlog ý tưởng (Messenger/Shopee/Zalo sync, UI mapping, RETAIL tagging) đã gom vào [`260707-2343-crm-tag-deferred-followups`](../../260707-2343-crm-tag-deferred-followups/plan.md).
