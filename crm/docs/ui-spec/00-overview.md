# CRM UI Spec — Overview

Internal Retail CRM · ~10 users · Desktop-first · Go + templ/HTMX · SQLite WAL

---

## Surface Index

### Screens

| ID | Name | Module | Personas |
|---|---|---|---|
| S01 | Worklist / Dashboard | M4 | Sales Rep |
| S02 | Customer List & Search | M1 | All |
| S03 | Customer 360 Detail | M2, M3 | Sales Rep, CSKH |
| S04 | Dedup Review | M1 | Manager |
| S05 | Inbox (Conversations) | M5 | CSKH |
| S06 | Conversation Detail | M5 | CSKH |
| S07 | Tasks Board | M4 | All |
| S08 | Segments List | M6 | Manager |
| S09 | Segment Builder | M6 | Manager |
| S10 | Campaigns List | M6 | Manager |
| S11 | Campaign Detail / Targets | M6 | Manager, Sales Rep |
| S12 | Ads Tracking | M6 | Manager |
| S13 | Settings | — | Admin, Manager |

### Panels (hosted inside S03)

| ID | Name | Tab |
|---|---|---|
| P01 | Insight Panel | Insight |
| P02 | Order History Panel | Đơn hàng |
| P03 | Activity Timeline Panel | Timeline |
| P04 | Tasks Panel | Tasks |
| P05 | Notes Panel | Ghi chú |
| P06 | Conversations Panel | Chat |

### Modals

| ID | Name | Opens from |
|---|---|---|
| M01 | Merge Confirm Modal | S04 |
| M02 | Create Party Modal | S02, M11 |
| M03 | Tag Management Modal | S03 |
| M04 | Assign Owner Modal | S03 |
| M05 | Create / Edit Task Modal | S01, S03, S07, P04 |
| M06 | Custom Fields Edit Modal | S03 |
| M07 | Create / Edit Campaign Modal | S10, S11 |
| M08 | Log Activity Modal | S03, S01, S06, P02, P03, P04, P05 |
| M09 | Assign Conversation Modal | S05, S06 |
| M10 | Close Conversation Modal | S06 |
| M11 | Link Party to Conversation Modal | S06 |
| M12 | Record Conversion Modal | S11 |
| M13 | Custom Field Definition Modal | S13 |
| M14 | Create Tag Modal | S13, M03 |

### Overlays

| ID | Name | Opens from |
|---|---|---|
| O01 | Confirm / Toast Overlay | S03, S05, S13, P05 |
| O02 | Quick Customer Preview Overlay | S01, S07 |
| O03 | Postpone Task Overlay | P04, S07 |

### Components

| ID | Name | Hosts |
|---|---|---|
| C01 | Sidebar Nav | All screens |
| C02 | Global Customer Search | S02, S03 |
| C03 | Action Queue Card | P01, S01 |
| C04 | Tag Chips | S02, S03, S04 |
| C05 | Filter Bar | S01, S02, S05, S07, S10, S11 |
| C06 | Freshness Badge | S01, S03, S12, P01, P02 |

### Flows

| ID | Name | PRD Journey |
|---|---|---|
| F01 | Morning Worklist → Call → Re-sell | J1 |
| F02 | Win-back At-risk Customer | J2 |
| F03 | Inbound Chat → Resolve PSID → Link Party | J3 |
| F04 | Enrich Profile + Dedup Merge | J4 |
| F05 | Build Segment → Run Campaign → Measure Conversion | J5 |
| F06 | Ad → Lead → Attribution | J6 |

---

## Directory Tree

```
crm/docs/ui-spec/
├── spec.config.yaml
├── 00-overview.md              ← this file
├── 15-system-events.md
├── 20-domain-rules.md
├── 30-states-and-errors.md
├── schema/
│   └── surface-contract.schema.json
├── tools/                      ← compiler (extract, validate, build, interpret)
│   └── node_modules/
├── generated/                  ← build output (gitignore-able)
├── screens/
│   ├── S01-worklist-dashboard.md
│   ├── S02-customer-list-search.md
│   ├── S03-customer-360-detail.md
│   ├── S04-dedup-review.md
│   ├── S05-inbox.md
│   ├── S06-conversation-detail.md
│   ├── S07-tasks-board.md
│   ├── S08-segments-list.md
│   ├── S09-segment-builder.md
│   ├── S10-campaigns-list.md
│   ├── S11-campaign-detail-targets.md
│   ├── S12-ads-tracking.md
│   └── S13-settings.md
├── panels/
│   ├── P01-insight-panel.md
│   ├── P02-order-history-panel.md
│   ├── P03-activity-timeline-panel.md
│   ├── P04-tasks-panel.md
│   ├── P05-notes-panel.md
│   └── P06-conversations-panel.md
├── modals/
│   ├── M01-merge-confirm-modal.md
│   ├── M02-create-party-modal.md
│   ├── M03-tag-management-modal.md
│   ├── M04-assign-owner-modal.md
│   ├── M05-create-edit-task-modal.md
│   ├── M06-custom-fields-edit-modal.md
│   ├── M07-create-edit-campaign-modal.md
│   ├── M08-log-activity-modal.md
│   ├── M09-assign-conversation-modal.md
│   ├── M10-close-conversation-modal.md
│   ├── M11-link-party-to-conversation-modal.md
│   ├── M12-record-conversion-modal.md
│   ├── M13-custom-field-def-modal.md
│   └── M14-create-tag-modal.md
├── overlays/
│   ├── O01-confirm-toast-overlay.md
│   ├── O02-quick-customer-preview-overlay.md
│   └── O03-postpone-task-overlay.md
├── components/
│   ├── C01-sidebar-nav.md
│   ├── C02-global-customer-search.md
│   ├── C03-action-queue-card.md
│   ├── C04-tag-chips.md
│   ├── C05-filter-bar.md
│   └── C06-freshness-badge.md
└── flows/
    ├── F01-morning-worklist-call-resell.md
    ├── F02-win-back-at-risk-customer.md
    ├── F03-inbound-chat-resolve-link-party.md
    ├── F04-enrich-profile-dedup-merge.md
    ├── F05-build-segment-run-campaign-measure.md
    └── F06-ad-lead-attribution.md
```

---

## Domain Rules Summary

| Rule | Name | Key surfaces |
|---|---|---|
| R1 | Consent Gating | S09, S10, S11, M07 |
| R2 | No-Recompute Insight | S01, S03, P01, P02, S12 |
| R3 | Value-Link No-FK | S03, P02, S11 |
| R4 | Merge Reversibility | S04, M01 |
| R5 | Phone E.164 Normalization | S02, S04, M01, M02 |
| R6 | ICT Display Convention | S01, S03, S05, S06, S11, S12 |
| R7 | realized_margin_pct Only | P01, S03 |
| R8 | Idempotent Task Generation | S01, S07 |
| R9 | Dedup Fuzzy → Candidate Queue | S04, M01 |
| R10 | Segment Dynamic Consent Re-eval | S09, S10 |
| R11 | Conversion Attribution Window | S11, S07 |
| R12 | Messenger Read-Only v1 | S05, S06 |

---

## Key System Events (SSE)

| Event | Surfaces that listen |
|---|---|
| `cache.refreshed` | S01, S03, P01 |
| `chat.message.received` | S05, S06 |
| `dedup.candidate.created` | S04 |
| `campaign.target.converted` | S11 |
| `segment.materialized` | S08, S09 |
| `party.merged` | S03, S04 |
| `conversation.assigned` | S05, S06 |
