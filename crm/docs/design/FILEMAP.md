# FILEMAP — retailCRM Design Handoff
<!-- Surface ID → Source file → React component / export name -->
<!-- Authoritative source: ui-spec/generated/surface-registry.yaml -->

## Screens

| Surface | Name (EN) | Tên (VI) | File | Component |
|---------|-----------|----------|------|-----------|
| S01 | Worklist / Dashboard | Worklist | `crm/screens_lists.jsx` | `S01_Worklist` |
| S02 | Customer List & Search | Khách hàng | `crm/screens_lists.jsx` | `S02_CustomerList` |
| S03 | Customer 360 Detail | Hồ sơ 360 | `crm/screens_360.jsx` | `S03_Customer360` |
| S04 | Dedup Review | Dedup | `crm/screens_lists.jsx` | `S04_Dedup` |
| S05 | Inbox (Conversations) | Inbox | `crm/screens_inbox.jsx` | `S05_Inbox` |
| S06 | Conversation Detail | Hội thoại | `crm/screens_inbox.jsx` | `S06_Conversation` |
| S07 | Tasks Board | Tasks | `crm/screens_inbox.jsx` | `S07_Tasks` |
| S08 | Segments List | Segments | `crm/screens_growth.jsx` | `S08_Segments` |
| S09 | Segment Builder | Segment Builder | `crm/screens_growth.jsx` | `S09_Builder` |
| S10 | Campaigns List | Chiến dịch | `crm/screens_growth.jsx` | `S10_Campaigns` |
| S11 | Campaign Detail / Targets | Chi tiết chiến dịch | `crm/screens_growth.jsx` | `S11_Campaign` |
| S12 | Ads Tracking | Ads | `crm/screens_growth.jsx` | `S12_Ads` |
| S13 | Settings | Cài đặt | `crm/screens_growth.jsx` | `S13_Settings` |

## Panels (tab views inside S03)

| Surface | Name | Tab label | File | Component |
|---------|------|-----------|------|-----------|
| P01 | Insight Panel | Insight | `crm/screens_360.jsx` | `P01_Insight` |
| P02 | Order History Panel | Đơn hàng | `crm/screens_360.jsx` | `P02_Orders` |
| P03 | Activity Timeline Panel | Timeline | `crm/screens_360.jsx` | `P03_Timeline` |
| P04 | Tasks Panel | Tasks | `crm/screens_360.jsx` | `P04_Tasks` |
| P05 | Notes Panel | Ghi chú | `crm/screens_360.jsx` | `P05_Notes` |
| P06 | Conversations Panel | Chat | `crm/screens_360.jsx` | `P06_Convs` |

## Modals

| Surface | Name | Host(s) | File | Component / key in MODALS |
|---------|------|---------|------|---------------------------|
| M01 | Merge Confirm | S04 | `crm/modals.jsx` | `"M01"` |
| M02 | Create Party | S02 | `crm/modals.jsx` | `"M02"` |
| M03 | Tag Management | S03 | `crm/modals.jsx` | `"M03"` |
| M04 | Assign Owner | S03 | `crm/modals.jsx` | `"M04"` |
| M05 | Create / Edit Task | S01 · S03 · S07 · P04 | `crm/modals.jsx` | `"M05"` |
| M06 | Custom Fields Edit | S03 | `crm/modals.jsx` | `"M06"` |
| M07 | Create / Edit Campaign | S10 · S11 | `crm/modals.jsx` | `"M07"` |
| M08 | Log Activity | S03 · S06 · P02 · P03 · P05 | `crm/modals.jsx` | `"M08"` |
| M09 | Assign Conversation | S05 · S06 | `crm/modals.jsx` | `"M09"` |
| M10 | Close Conversation | S06 | `crm/modals.jsx` | `"M10"` |
| M11 | Link Party to Conversation | S06 | `crm/modals.jsx` | `"M11"` |
| M12 | Record Conversion | S11 | `crm/modals.jsx` | `"M12"` |
| M13 | Custom Field Definition | S13 | `crm/modals.jsx` | `"M13"` |
| M14 | Create Tag | S13 · M03 | `crm/modals.jsx` | `"M14"` |

## Overlays

| Surface | Name | Host(s) | File | Component |
|---------|------|---------|------|-----------|
| O01 | Confirm / Toast Overlay | S03 · S05 · S13 · P05 | `crm/modals.jsx` + `crm/helpers.jsx` | `"O01"` modal + `ToastStack` |
| O02 | Quick Customer Preview | S01 · S07 | `crm/src.jsx` | `QuickPreview` |

## Components

| Surface | Name | Host(s) | File | Component |
|---------|------|---------|------|-----------|
| C01 | Sidebar Nav | All screens | `crm/src.jsx` | `Sidebar` |
| C02 | Global Customer Search | S02 · S03 (header) | `crm/src.jsx` | `GlobalSearch` |
| C03 | Action Queue Card | P01 · S01 | `crm/helpers.jsx` | `AQCard` |
| C04 | Tag Chips | S02 · S03 · S04 | `crm/helpers.jsx` | `TagChips` |
| C05 | Filter Bar | S01 · S02 · S05 · S07 · S10 · S11 | `crm/helpers.jsx` | `FilterBar` |
| C06 | Freshness Badge | S01 · S03 · S12 · P01 · P02 | `crm/helpers.jsx` | `FreshBadge` |

## Harness-only (DELETE when porting)

| Artifact | File | Notes |
|----------|------|-------|
| `HarnessRail` | `crm/src.jsx` | Surface jump-nav for design review — not a product feature |
| `CleanNav` | `crm/src.jsx` | ←/→ surface flipper for review — not a product feature |
| `ThemePanel` | `crm/src.jsx` | Design-time theme switcher — replace with user-preferences API |
| `RegRow` / `regActive` | `crm/src.jsx` | Registry row renderers for harness only |
| `window.REG` | `crm/registry.js` | Surface registry for harness; `SURF` map is useful reference |
| `SURFACE_ORDER` / `loadClean` | `crm/src.jsx` | Clean-view helpers |
| Harness + clean-view CSS | `crm/crm-extra.css` | See README §CSS Split for class list |

## Shared helpers (`crm/helpers.jsx`)

| Export | Purpose |
|--------|---------|
| `fmtVND` / `fmtVNDShort` | Currency formatter (vi-VN locale) |
| `fmtDate` / `fmtDateOnly` / `fmtTime` / `fmtDateTime` | UTC → ICT display (R6) |
| `relTime` | Relative-time string in Vietnamese |
| `Icon` | All inline SVGs (16px box, 1.3 stroke, round caps) |
| `Avatar` | Initials avatar |
| `Bdg` / `Chip` / `GroupBadge` / `StatusBadge` | Badge atoms |
| `Modal` / `ModalActions` | Modal shell (scrim + header + body + actions) |
| `Field` / `Inp` / `InpSel` / `RadioSet` / `ChkRow` | Form primitives |
| `ToastStack` | Auto-dismiss toast overlay |
| `FreshBadge` (C06) | Freshness badge with color ramp |
| `AQCard` (C03) | Action Queue card |
| `TagChips` (C04) | Tag chip list |

## Data layer (`crm/data.js`)

| Collection | DB table equivalent | Notes |
|------------|---------------------|-------|
| `DB.parties` | `crm_party` + `crm_customer_profile` | 10 seed records |
| `DB.orders` | `wh_order_hdr` (cache.db) | Keyed by party id |
| `DB.activities` | `crm_activity` | Keyed by party id |
| `DB.notes` | `crm_note` | Keyed by party id |
| `DB.tasks` | `crm_task` | Flat list |
| `DB.conversations` | `crm_conversation` + messages | Flat list |
| `DB.dedup` | `crm_dedup_candidate` | 4 pending records |
| `DB.segments` | `crm_segment` + `crm_segment_rule` | 5 records |
| `DB.campaigns` | `crm_campaign` | 3 records |
| `DB.targets` | `crm_campaign_target` | Keyed by campaign id |
| `DB.ads` | `crm_ad_spend` + leads | 2 campaigns |
| `DB.fieldDefs` | `crm_custom_field_def` | 4 definitions |
| `DB.tags` | `crm_tag` | 8 tags |
| `DB.users` | `crm_user` | 6 users |
