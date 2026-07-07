# CRM Tag System — Deferred Follow-ups Backlog

**Ngày:** 2026-07-07
**Mục tiêu:** Gom các phase deferred + ý tưởng non-goals từ 2 plan tag liên quan vào 1 chỗ để theo dõi, tránh rải rác. Đây là backlog tracking, không phải active workstream — không có phase nào sẵn sàng implement.

**Nguồn:**
- `plans/archive/260619-0830-crm-tag-acl-sync` (phase 04 + non-goals)
- `plans/archive/260706-0833-crm-health-profile-tag-governance` (phase 04 + non-goals)

---

## Phases (moved, có thiết kế sơ lược)

| # | Phase | Trạng thái | Blocked bởi |
|---|-------|-----------|-------------|
| 01 | [Outbound tag write-back (CRM → Sapo)](phase-01-outbound-tag-writeback.md) | ⬜ Blocked | Phase 07 (`crm_sync_outbox` infra) — chưa build |
| 02 | [Approach-script health integration](phase-02-approach-script-health-integration.md) | ⬜ Blocked | Script generator batch pipeline refactor — chưa có kế hoạch |

Nội dung 2 phase này move nguyên vẹn từ phase-04 của 2 plan nguồn (câu hỏi mở, todo, non-goals riêng của từng phase giữ nguyên).

---

## Backlog ý tưởng (chưa có thiết kế, từ mục "Non-goals (v1)")

Các mục dưới đây **không phải phase** — chỉ là ý tưởng đã bị loại khỏi v1, chưa được thiết kế, chưa ưu tiên. Cần user quyết định trước khi tách thành phase file.

### Từ `260619-0830-crm-tag-acl-sync`
- Sync tag từ Messenger, Shopee, Zalo (hiện chỉ Sapo `customer_group`)
- UI quản lý mapping `crm_ext_tag_map` (hiện admin tự seed migration thủ công)
- Tag hóa group RETAIL mặc định (6.451/7.575 khách, zero information — seed `is_active=0`)

### Từ `260706-0833-crm-health-profile-tag-governance`
- LLM auto-suggest tags
- Outbound sync health tags về Sapo (trùng phạm vi Phase 01 ở trên khi unblock)
- Per-customer health history timeline
- NLP fuzzy grouping cho chipify (hiện chỉ exact text group)

---

## Dependencies

- Phase 01 cần Phase 07 (`sync_outbox`) làm trước — không có timeline, không tự unblock được
- Phase 02 cần quyết định kiến trúc script generator batch — không có timeline
- Backlog items: chưa ưu tiên, không block gì, chỉ tham khảo khi cần mở rộng scope

## Non-goals

Tự thân plan này không implement gì — nó là nơi tập trung theo dõi deferred work. Khi 1 item được ưu tiên, tách thành plan riêng với đầy đủ phase/implementation steps.
