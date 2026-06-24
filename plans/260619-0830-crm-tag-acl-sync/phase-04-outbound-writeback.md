# Phase 04 — Outbound Write-back: CRM Tag → Sapo (Deferred)

**Context:** [plan.md](plan.md) · Requires: Phase 01-03 + Phase 07 (sync_outbox infrastructure)

## Overview
- **Priority:** P2 — **DEFERRED sau v1**
- **Status:** ⬜ Deferred
- Khi CRM user gán/bỏ tag có `direction='outbound'` hoặc `'both'` trong `crm_ext_tag_map` → translate ngược sang Sapo field (customer_group / native tag) → enqueue vào `sync_outbox`.

## Dependency cứng

Phase 07 (Sapo writeback) phải có trước:
- `crm_sync_outbox` table
- `crm_sapo_writeback_map` table
- Worker poll + retry + conflict guard

Phase này chỉ **thêm trigger enqueue** khi tag thay đổi.

## Thiết kế sơ lược

```
CRM user gán tag "KH Sỉ" (crm_tag_id=X)
  → lookup crm_ext_tag_map(crm_tag_id=X, direction IN ('outbound','both'), is_active=1)
  → tìm crm_ext_tag(ext_tag_id) → source_system='sapo_v2', ext_key='TYPE_WHOLESALE'
  → lookup crm_party_external_id(party_id, source_system='sapo_v2') → external_key (Sapo customer_id)
  → INSERT INTO sync_outbox {
      entity_type: 'party',
      entity_id: party_id,
      target_system: 'sapo_v2',
      operation: 'update_customer_group',
      payload: {customer_id: X, customer_group: 'TYPE_WHOLESALE'},
      idempotency_key: hash(party_id + crm_tag_id + 'assign')
    }
```

## Câu hỏi mở (chặn implement)

1. **Sapo cho ghi `customer_group` không?** — cần API spike (xem Phase 07 spike plan)
2. **Sapo hỗ trợ nhiều group không?** — nếu 1 customer chỉ có 1 group → CRM phải quyết định group nào "win" khi có nhiều tag outbound
3. **Conflict guard:** Sapo `modified_on` mới hơn lần CRM ghi → skip hay override?

## Todo (khi ungate)
- [ ] Xác nhận Sapo API write scope (từ Phase 07 spike)
- [ ] Implement trigger enqueue trong tag attach/detach handler (Python)
- [ ] Worker xử lý `operation=update_customer_group`
- [ ] Test conflict guard

## Non-goals của phase này
- Không sync tag ngược về Sapo tự động theo batch — chỉ event-driven khi CRM user thay đổi
- Không xóa customer_group ở Sapo khi CRM user bỏ tag (safe default — chỉ add, không delete)
