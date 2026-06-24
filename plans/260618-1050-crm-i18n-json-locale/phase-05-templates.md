# Phase 5 — Template Migration

**Status:** Todo  
**Effort:** ~4h (39 files, ~250 strings)  
**Depends on:** Phase 1 (t() available in globals), Phase 2 (locale files complete)

## Overview

Replace hardcoded Vietnamese string literals in all 39 HTML templates with `t("key")` calls. Badge tooltips already handled by Phase 3 (no template change needed there).

## Jinja2 syntax patterns

```html
<!-- Text content -->
Quay lại              →  {{ t("common.back") }}

<!-- Attribute value -->
placeholder="Tìm..."  →  placeholder="{{ t('customer.search_hint') }}"

<!-- Inside {% if %} block — same pattern -->
{% if x %}Chưa có{% endif %}  →  {% if x %}{{ t("common.empty") }}{% endif %}

<!-- Eyebrow / section header (often ALL CAPS in Vietnamese) -->
CHIẾN DỊCH  →  {{ t("campaign.section_eyebrow") }}
```

## Files and key strings per file

### `templates/layout.html`
- Navigation labels: Khách hàng, Đơn hàng, Công việc, Hộp thư, Chiến dịch...
- Add lang toggle button (from Phase 1)

### `templates/base.html`
- Any shared shell strings

### `templates/customer_list.html`
- Page title, search placeholder, table headers, empty state
- Filter labels: "Trạng thái", "Tất cả", "Tìm kiếm"

### `templates/customer_360.html`
- "Quay lại" → `t("common.back")`
- "Ghi log" → `t("action.log_activity")`
- "Task" → `t("nav.tasks")` (or keep as brand term)
- Sidebar section headers: "Thông Tin Cơ Bản", "Liên Lạc", "Chỉ Số"

### `templates/fragments/c360_insight_panel.html`
- Section title, no data state, KPI labels

### `templates/fragments/c360_orders_panel.html`
- "Đơn hàng", empty state, column headers

### `templates/fragments/c360_tasks_panel.html`
- Task section title, empty state, status labels

### `templates/fragments/c360_timeline_panel.html`
- Timeline section title, empty state

### `templates/fragments/c360_notes_panel.html`
- Notes section title, empty state, add note button

### `templates/management.html` (campaigns + segments)
- All campaign strings from Phase 2 `campaign.*` keys
- Modal titles: "Tạo chiến dịch", "Sửa chiến dịch"
- Form labels, button text

### `templates/campaigns.html`
- Campaign list table headers, empty states

### `templates/segments.html`
- Segment table headers, empty states

### `templates/tasks_board.html`
- Board columns: "Chưa bắt đầu", "Đang làm", "Hoàn thành"
- Filter labels, button text

### `templates/inbox.html`
- "Hộp thư", conv status labels
- "Chưa có tin nhắn", "Hội thoại đã đóng"

### `templates/conversation_detail.html`
- Action buttons: "Đổi NV", "Ghi note", "Đóng hội thoại", "Mở lại"
- Read-only states

### `templates/order_detail.html`
- Tab labels, section headers, field labels

### `templates/fragments/order_*.html` (5 files)
- Field labels per tab: items, financial, operations, context, action

### `templates/worklist.html` + `fragments/worklist_fragment.html`
- Worklist column headers, action labels, empty states

### `templates/dedup_review.html`
- Merge review UI labels

### `templates/settings.html`
- Settings page labels

### `templates/modals.html` + modal fragments (8 files)
- Form field labels, button text, modal titles
- Common: "Hủy", "Lưu", "Tạo", "Xác nhận"

## Approach

Process files in this order (dependencies first):
1. `layout.html` / `base.html` — shell, affects all pages
2. Fragment templates — smaller, reused
3. Full-page templates — largest, reference fragments

For each file:
1. Read file
2. Identify Vietnamese literals (not inside `{{ }}` Jinja2 expressions)
3. Assign keys from Phase 2 taxonomy (or add new keys to locale files)
4. Replace and verify template is syntactically valid

## Strings to intentionally NOT translate

- `{{ party.display_name }}` — customer name from DB
- `{{ order.code }}` — order codes
- Status values from DB passed through filters (those go through badge_catalog)
- `"ICT"` timezone suffix — keep as-is
- `"VND"`, `"đ"` — currency symbols
- `"RFM"`, `"VIP"`, `"GOLD"` — brand/domain terms

## Validation

After migration, test with both cookies:
- `lang=vi` → all text renders Vietnamese
- `lang=en` → all text renders English, no raw keys visible
- Missing key scenario: `t("nonexistent.key")` → returns `"nonexistent.key"` (visible fallback, easy to spot)
