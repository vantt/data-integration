# CRM Tag Anti-Corruption Layer + Inbound Sync

**Ngày:** 2026-06-19  
**Mục tiêu:** Thiết kế và implement ACL (Anti-Corruption Layer) cho hệ thống tags — đảm bảo CRM canonical tags độc lập khỏi vocabulary của bất kỳ hệ bán hàng nào (Sapo, Haravan, Shopify…), đồng thời sync tag tự động từ warehouse vào CRM.

---

## Vấn đề

| Vấn đề | Hiện trạng |
|--------|-----------|
| Không có cầu nối Sapo → CRM tag | `customer_group` đọc về `wh_customer_base` nhưng không map vào `crm_party_tag` |
| `crm_party_tag` không track nguồn | Không phân biệt tag do CRM user gán vs tag sync từ ngoài |
| Coupling ẩn | Nếu đổi sang Haravan, toàn bộ mapping phải viết lại |
| Không có mapping table | Không nơi nào định nghĩa "Sapo TYPE_WHOLESALE = CRM KH Sỉ" |

## Giải pháp: ACL pattern (đã có tiền lệ ở `crm_party_external_id`)

```
[Sapo] customer_group="TYPE_WHOLESALE"
    ↓  crm_ext_tag + crm_ext_tag_map (ACL boundary)
[CRM]  crm_tag.name="KH Sỉ" category="vip_tier"

[Haravan] segment="wholesale"   (tương lai)
    ↓  thêm rows vào crm_ext_tag + crm_ext_tag_map
[CRM]  crm_tag.name="KH Sỉ"   ← không đổi gì trong domain
```

---

## Phases

| # | Phase | Trạng thái | Output chính |
|---|-------|-----------|-------------|
| 01 | [Schema ACL + source column](phase-01-schema-acl.md) | ⬜ | Migration 0022: `crm_ext_tag`, `crm_ext_tag_map`, ALTER `crm_party_tag` ADD `source` + `ext_ref` |
| 02 | [Seed Sapo mapping](phase-02-seed-sapo-mapping.md) | ⬜ | Migration 0023: seed `crm_ext_tag` từ Sapo customer_groups đã biết; map sang canonical `crm_tag` |
| 03 | [Inbound sync trong reverse-ETL](phase-03-inbound-sync.md) | ⬜ | `crm/sync/tag_sync.py`: đọc `wh_customer_base.customer_group` → lookup ACL → upsert `crm_party_tag(source='sapo_v2_sync')` |
| 04 | [Outbound write-back (gated)](phase-04-outbound-writeback.md) | ⬜ Deferred | Tích hợp vào Phase 07 Sapo writeback — CRM tag thay đổi → enqueue `sync_outbox` |

**v1 scope:** Phase 01 + 02 + 03. Phase 04 deferred theo Phase 07.

> **Status:** Not started (updated 2026-06-24: untouched by 260623 audit work; owner-sequenced; all phases ⬜)

---

## Dependencies

- Phase 01 → 02 → 03 (strict sequential — schema trước, seed sau, sync sau)
- Phase 04 depends on Phase 07 (outbox infrastructure)
- Reverse-ETL phải chạy sau Phase 01 migration đã apply (crm.db updated)

---

## Conflict rules (đã chốt)

| Tình huống | Xử lý |
|-----------|-------|
| sync muốn gán tag đã do `crm_user` gán | Giữ nguyên — CRM user wins |
| sync muốn bỏ tag mà `crm_user` gán | Không bỏ — source='crm_user' protected |
| CRM user gán tag đã có từ sync | Update `source='crm_user'`, `tagged_by` = user |
| Sync lần 2 — tag đã sync rồi | ON CONFLICT DO NOTHING (idempotent) |

---

## Non-goals (v1)

- Không sync tag từ Messenger, Shopee, Zalo (chỉ Sapo customer_group)
- Không outbound write-back (Phase 04 deferred)
- Không UI quản lý mapping (admin tự seed migration)
