# CRM UI Surface Conventions

Framework: Jinja2 HTML templates + HTMX · Python FastAPI
Templates live in: `crm/src/adapters/inbound/web/templates/`

---

## Two-mechanism convention

Every surface is locatable in **two** ways:

### (A) Source banner — top of every UI file

Use a Jinja2 comment as the **very first thing** in the file:

```jinja2
{# @surface  S01 · Worklist / Dashboard
   @source   crm/docs/ui-spec/screens/S01-worklist-dashboard.md
   @kind     SCREEN #}
```

Partial files (HTMX fragments that are sub-parts of a surface) reference their **parent** surface and add `(partial)`:

```jinja2
{# @surface  P01 · Insight Panel (partial — hosted in S03)
   @source   crm/docs/ui-spec/panels/P01-insight-panel.md
   @kind     PANEL #}
```

`@kind` values: `SCREEN · PANEL · MODAL · OVERLAY · COMPONENT · LAYOUT`

### (B) Runtime marker — outermost element of each top-level surface root

Add `data-surface` to the outermost rendered element:

```html
<div class="crm-page page-enter" data-surface="S01" data-surface-name="Worklist">
```

For modals, the marker goes on the dialog root (the `.modal-scrim`):

```html
<div class="modal-scrim" data-surface="M02" ...>
```

**Hard rule: exactly ONE marker per rendered surface.** Partials get the banner only — never a nested marker inside the same surface.

---

## Why `data-surface`, not `id` or comment

| Mechanism | Problem |
|---|---|
| HTML comment | Compiled away — invisible at runtime; useless for DevTools inspection |
| `id` attribute | Must be unique per document — breaks when a surface renders more than once |
| `data-surface` | Inert metadata, no uniqueness constraint, queryable via `document.querySelector('[data-surface="S01"]')`, survives SSR |

---

## Filename encodes the ID

Name template files with the surface ID prefix so both human and grep can find them instantly:

```
S01-worklist-dashboard.html   ← future naming target
templates/worklist.html       ← existing (ID visible in banner + runtime marker)
```

The existing templates pre-date this convention; new templates should use the `ID-kebab-name.html` form.

---

## Surface map

> **S12 note:** The ui-spec (`00-overview.md`) assigned S12 to "Ads Tracking" (unbuilt). The Python port repurposed S12 for Order Detail. Both are documented here; S12 = Order Detail in running code.

### Screens

| ID | Name | Template | Spec source | Built | Marker |
|---|---|---|---|---|---|
| S01 | Worklist / Dashboard | `worklist.html` | `crm/docs/ui-spec/screens/S01-worklist-dashboard.md` | ✓ | `data-surface="S01"` |
| S02 | Customer List & Search | `customer_list.html` | `crm/docs/ui-spec/screens/S02-customer-list-search.md` | ✓ | `data-surface="S02"` |
| S03 | Customer 360 Detail | `customer_360.html` | `crm/docs/ui-spec/screens/S03-customer-360-detail.md` | ✓ | `data-surface="S03"` |
| S04 | Dedup Review | `dedup_review.html` | `crm/docs/ui-spec/screens/S04-dedup-review.md` | ✓ | `data-surface="S04"` |
| S05 | Inbox (Conversations) | `inbox.html` | `crm/docs/ui-spec/screens/S05-inbox.md` | ✓ | `data-surface="S05"` |
| S06 | Conversation Detail | `conversation_detail.html` | `crm/docs/ui-spec/screens/S06-conversation-detail.md` | ✓ | `data-surface="S06"` |
| S07 | Tasks Board | `tasks_board.html` | `crm/docs/ui-spec/screens/S07-tasks-board.md` | ✓ | `data-surface="S07"` |
| S08 | Segments List | `segments.html` | `crm/docs/ui-spec/screens/S08-segments-list.md` | ✓ | `data-surface="S08"` |
| S09 | Segment Builder | `segments.html` (dual-view) | `crm/docs/ui-spec/screens/S09-segment-builder.md` | ✓ | `data-surface="S09"` |
| S10 | Campaigns List | `campaigns.html` | `crm/docs/ui-spec/screens/S10-campaigns-list.md` | ✓ | `data-surface="S10"` |
| S11 | Campaign Detail / Targets | `campaigns.html` (dual-view) | `crm/docs/ui-spec/screens/S11-campaign-detail-targets.md` | ✓ | `data-surface="S11"` |
| S12 | Order Detail *(spec: Ads Tracking)* | `order_detail.html` | `crm/docs/ui-spec/screens/S12-ads-tracking.md` | ✓ | `data-surface="S12"` |
| S13 | Settings | `settings.html` | `crm/docs/ui-spec/screens/S13-settings.md` | ✓ | `data-surface="S13"` |

### Panels (inside S03)

| ID | Name | Fragment | Spec source | Built |
|---|---|---|---|---|
| P01 | Insight Panel | `fragments/c360_insight_panel.html` | `crm/docs/ui-spec/panels/P01-insight-panel.md` | ✓ |
| P02 | Order History Panel | `fragments/c360_orders_panel.html` | `crm/docs/ui-spec/panels/P02-order-history-panel.md` | ✓ |
| P03 | Activity Timeline Panel | `fragments/c360_timeline_panel.html` | `crm/docs/ui-spec/panels/P03-activity-timeline-panel.md` | ✓ |
| P04 | Tasks Panel | `fragments/c360_tasks_panel.html` | `crm/docs/ui-spec/panels/P04-tasks-panel.md` | ✓ |
| P05 | Notes Panel | `fragments/c360_notes_panel.html` | `crm/docs/ui-spec/panels/P05-notes-panel.md` | ✓ |
| P06 | Conversations Panel | *(not built)* | `crm/docs/ui-spec/panels/P06-conversations-panel.md` | — |

### Modals

| ID | Name | Template | Built |
|---|---|---|---|
| M02 | Create Party Modal | `modals.html` | ✓ |
| M04 | Assign Owner Modal | `modals.html` | ✓ |
| M07 | Create / Edit Campaign Modal | `management_modals.html` | ✓ |
| M08 | Log Activity Modal | `fragments/modal_log_activity.html` | ✓ |
| M12 | Record Conversion Modal | `management_modals.html` | ✓ |
| M01,M03,M05,M06,M09–M11,M13,M14 | (various) | *(not built in Python port yet)* | — |

### Components

| ID | Name | Template | Built | Marker |
|---|---|---|---|---|
| C01 | Sidebar Nav | `layout.html` (`<nav>`) | ✓ | `data-surface="C01"` |
| C02 | Global Customer Search | `layout.html` (`<form class="search">`) | ✓ | `data-surface="C02"` |
| C03 | Action Queue Card | `fragments/worklist_fragment.html` | ✓ | *(no marker — inline fragment)* |
| C04 | Tag Chips | inline in S02/S03 | ✓ | *(inline, no dedicated file)* |
| C05 | Filter Bar | inline in S01/S02 | ✓ | *(inline, no dedicated file)* |
| C06 | Freshness Badge / Caveat | `fragments/worklist_fragment.html` | ✓ | `data-surface="C06"` |
| C07 | Theme Switcher Panel | `layout.html` (`#theme-panel`) | ✓ | `data-surface="C07"` |

---

## Agent usage rule

When creating or editing any UI file:

1. Add the `@surface` banner (Jinja2 `{# ... #}` comment) as **line 1**
2. Add `data-surface="ID"` on the **outermost element** of each top-level surface root only
3. Partials: banner only — no nested marker
4. When delegating UI work to sub-agents, instruct them to read this file first

Full spec: `crm/docs/ui-spec/00-overview.md`
