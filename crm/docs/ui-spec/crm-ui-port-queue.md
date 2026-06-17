# CRM UI Port Queue

Danh sách tất cả surfaces cần `/ui-port` để sync spec → implementation.

Priority: ★★★ = spec changed this session | ★★ = has implementation, spec unchanged | ★ = spec-only, no implementation yet

---

## Screens

| ID | Name | Spec | Priority | Notes |
|----|------|------|----------|-------|
| S01 | Worklist Dashboard | screens/S01-worklist-dashboard.md | ★★★ | task rows + contact_pref inline + quick-action [Gọi]/[Zalo] |
| S02 | Customer List & Search | screens/S02-customer-list-search.md | ★★ | |
| S03 | Customer 360 Detail | screens/S03-customer-360-detail.md | ★★★ | left col restructure: Cảnh báo, Liên lạc, Địa chỉ sections |
| S04 | Dedup Review | screens/S04-dedup-review.md | ★★ | |
| S05 | Inbox / Conversation List | screens/S05-inbox.md | ★★ | |
| S06 | Conversation Detail | screens/S06-conversation-detail.md | ★★ | |
| S07 | Tasks Board | screens/S07-tasks-board.md | ★★ | |
| S08 | Segments List | screens/S08-segments-list.md | ★★ | |
| S09 | Segment Builder | screens/S09-segment-builder.md | ★★ | |
| S10 | Campaigns List | screens/S10-campaigns-list.md | ★★ | |
| S11 | Campaign Detail & Targets | screens/S11-campaign-detail-targets.md | ★★ | |
| S12 | Ads Tracking | screens/S12-ads-tracking.md | ★ | |
| S13 | Settings | screens/S13-settings.md | ★★ | |

---

## Panels (embedded in S03)

| ID | Name | Spec | Priority | Notes |
|----|------|------|----------|-------|
| P01 | Insight Panel | panels/P01-insight-panel.md | ★★★ | two-layer: 🤖 Warehouse + 👤 Rep insights; M16 entry points |
| P02 | Order History Panel | panels/P02-order-history-panel.md | ★★ | |
| P03 | Activity Timeline Panel | panels/P03-activity-timeline-panel.md | ★★ | |
| P04 | Tasks Panel | panels/P04-tasks-panel.md | ★★ | |
| P05 | Notes Panel | panels/P05-notes-panel.md | ★★★ | PINNED section + type tabs + "★ Đúc kết thành insight" |
| P06 | Conversations Panel | panels/P06-conversations-panel.md | ★★ | |

---

## Modals

| ID | Name | Spec | Priority | Notes |
|----|------|------|----------|-------|
| M01 | Merge Confirm | modals/M01-merge-confirm-modal.md | ★★ | |
| M02 | Create Party | modals/M02-create-party-modal.md | ★★ | |
| M03 | Tag Management | modals/M03-tag-management-modal.md | ★★ | |
| M04 | Assign Owner | modals/M04-assign-owner-modal.md | ★★ | |
| M05 | Create/Edit Task | modals/M05-create-edit-task-modal.md | ★★ | |
| M06 | Custom Fields Edit | modals/M06-custom-fields-edit-modal.md | ★★★ | fields grouped by section + entity_type=customer only |
| M07 | Create/Edit Campaign | modals/M07-create-edit-campaign-modal.md | ★★ | |
| M08 | Log Activity | modals/M08-log-activity-modal.md | ★★★ | 4 modes: activity/contact_attempt/note_only/edit_note |
| M09 | Assign Conversation | modals/M09-assign-conversation-modal.md | ★★ | |
| M10 | Close Conversation | modals/M10-close-conversation-modal.md | ★★ | |
| M11 | Link Party to Conversation | modals/M11-link-party-to-conversation-modal.md | ★★ | |
| M12 | Record Conversion | modals/M12-record-conversion-modal.md | ★★ | |
| M13 | Custom Field Def | modals/M13-custom-field-def-modal.md | ★★★ | entity_type selector + section field |
| M14 | Create Tag | modals/M14-create-tag-modal.md | ★★★ | category now enum dropdown (6 values) |
| M15 | Edit Contact & Core Info | modals/M15-edit-contact-core-info-modal.md | ★★★ | NEW — 3-tab modal (Liên lạc / Địa chỉ / Thông tin cơ bản) |
| M16 | Promote / Create Insight | modals/M16-promote-insight-modal.md | ★★★ | NEW — crm_party_insight CRUD |

---

## Port Order (recommended)

1. S03 — hub screen, all panels live here
2. P01, P05 — most spec changes
3. S01 — quick-action buttons
4. M08, M15, M16 — new/redesigned modals
5. M06, M13, M14 — updated field defs
6. Remaining ★★ surfaces
