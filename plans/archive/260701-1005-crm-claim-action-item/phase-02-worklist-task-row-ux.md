---
phase: 2
title: "WorkList Task Row UX"
status: pending
priority: P2
dependencies: [1]
---

# Phase 2: WorkList Task Row UX

## Overview

Cải thiện task row trong WorkList để nhân viên thấy được ngữ cảnh sau khi claim: khách hàng là ai, action type gì, và đường dẫn nhanh sang C360 để log kết quả. Hiện tại task row chỉ có title + done/cancel button, không có link khách hàng.

## Requirements

- **Functional:**
  - Task row hiển thị: action type badge + tên khách + "Xem khách →" link
  - "Xem khách →" link → `/customers/{party_id}?tab=tasks` (tab tasks của C360)
  - Nếu `party_id` là None (task manual không gắn khách) → không hiện link
  - "Nhận việc" button thêm vào action item row (template change từ Phase 1)

- **Non-functional:**
  - Không thêm mới HTTP endpoint — chỉ thay đổi template
  - Action type badge: parse prefix `[CALL_NOW]` từ `task.title` hoặc derive từ `task.source_ref` nếu action còn trong cache

## Architecture

```
WorkList Template (worklist.html / worklist_fragment.html)
  ↓
_wl_my_tasks section (my_tasks: list[Task])
  └─ task row:
       [CALL_NOW] badge  |  Nguyễn Văn A  |  [Xem khách →]  |  [✓ Done] [✗ Cancel]

Action item row (all_actions: list[ActionQueueItem])
  └─ existing row:  rationale | value | [Snooze ▾] [Dismiss] [Nhận việc]  ← thêm nút này
```

**Action type badge:** `task.title` format là `[CALL_NOW] Tái đặt SP X`. Parse bằng regex `^\[([A-Z_]+)\]` để lấy badge text. Nếu không match → không hiện badge.

**"Xem khách →" URL:** `/customers/{task.party_id}?tab=tasks` — tab tasks của C360 sẽ hiện task của khách đó và M08 modal để log kết quả.

## Related Code Files

- Modify: template file hiển thị task rows trong WorkList
  - Tìm file bằng: `grep -rn "my_tasks\|task_row\|task\.task_id" crm/templates/ --include="*.html" -l`
  - Likely: `crm/templates/fragments/_wl_my_tasks.html` hoặc inline trong `worklist.html`
- Modify: template file hiển thị action item rows
  - Tìm file bằng: `grep -rn "action\.action_id\|action_row\|dismiss" crm/templates/ --include="*.html" -l`
  - Likely: `crm/templates/fragments/_wl_action_row.html` hoặc `_wl_row.html`
- Modify: `crm/src/adapters/inbound/web/screen_worklist.py`
  - Không cần thêm route, nhưng nếu cần resolve app_user names cho task rows → thêm `AppUserReader` protocol

## Implementation Steps

1. **Tìm template files chính xác:**
   ```bash
   grep -rn "task\.task_id\|task_id.*done\|hx-patch.*done" crm/templates/ --include="*.html" -l
   grep -rn "action_id.*dismiss\|dismiss.*action_id\|snooze" crm/templates/ --include="*.html" -l
   ```

2. **Task row template — thêm context:**
   ```html
   {# Trong loop my_tasks #}
   <div class="task-row" id="task-{{ task.task_id }}">
     {# Action type badge — parse từ title #}
     {% set badge = task.title | regex_search('^\[([A-Z_]+)\]') %}
     {% if badge %}
       <span class="bdg bdg--action-type">{{ badge }}</span>
     {% endif %}

     {# Customer link #}
     {% if task.party_id %}
       <a href="/customers/{{ task.party_id }}?tab=tasks" class="task-customer-link">
         {{ party_extras.get(task.party_id, {}).get('preferred_identity', {}).display_name
            if task.party_id in party_extras else task.title }}
         →
       </a>
     {% else %}
       <span class="task-title">{{ task.title }}</span>
     {% endif %}

     {# Existing actions #}
     <button hx-patch="/tasks/{{ task.task_id }}/done" hx-swap="outerHTML"
             hx-target="closest .task-row" class="btn btn--sm">✓</button>
     <button hx-patch="/tasks/{{ task.task_id }}/cancel" hx-swap="delete"
             hx-target="closest .task-row" class="btn btn--sm btn--ghost">✗</button>
   </div>
   ```

   **Lưu ý Jinja2:** `regex_search` không phải filter mặc định — cần thêm custom filter hoặc pre-process trong Python. Đơn giản hơn: xử lý trong `_load_worklist_data()` bằng cách enrich tasks với `action_type_badge` field.

   **Phương án đơn giản hơn (recommended):** Enrich tasks trong `_load_worklist_data()`:
   ```python
   import re
   _BADGE_RE = re.compile(r'^\[([A-Z_]+)\]')
   for t in my_tasks:
       m = _BADGE_RE.match(t.title or "")
       t._badge = m.group(1) if m else ""  # dynamic attr, hoặc dùng dict
   ```
   Hoặc trả về `task_badges: dict[task_id, str]` sang template.

3. **Action item row — thêm "Nhận việc" button:**
   ```html
   {# Thêm vào cuối action row, sau Snooze/Dismiss #}
   <button
     hx-patch="/worklist/actions/{{ action.action_id }}/claim"
     hx-swap="outerHTML"
     hx-target="closest .action-row"
     hx-indicator=".htmx-indicator"
     class="btn btn--sm btn--primary">
     Nhận việc
   </button>
   ```

4. **My Tasks section refresh sau claim:**
   Cách đơn giản nhất cho v1: sau khi "Nhận việc" thành công, dùng `HX-Redirect` để reload WorkList page. Nếu muốn tránh full reload:
   ```html
   {# My Tasks container có id để HTMX target #}
   <div id="my-tasks-section"
        hx-get="/worklist/fragment"
        hx-trigger="claimSuccess from:body"
        hx-target="#my-tasks-section"
        hx-swap="outerHTML">
     {# ... tasks ... #}
   </div>
   ```
   `HX-Trigger: {"claimSuccess": true}` từ backend sẽ trigger reload section này.

   **Phương án đơn giản hơn cho v1:** `HX-Redirect: /worklist` (full page reload sau claim). Ít code, ít bug.

## Success Criteria

- [ ] Task row trong My Tasks section hiển thị action type badge (parse từ title)
- [ ] Task row có "Xem khách →" link dẫn đến `/customers/{party_id}?tab=tasks` khi `party_id` không None
- [ ] "Nhận việc" button xuất hiện trên action item row
- [ ] Sau claim: action item row biến mất, My Tasks section cập nhật (reload hoặc HTMX trigger)
- [ ] Task row không có `party_id` (manual task) vẫn render bình thường, không lỗi

## Risk Assessment

- **Template path không biết chắc:** Bước đầu tiên là grep tìm đúng file. Sai file → không có effect.
- **Jinja2 custom filter:** Nếu template cần regex, phải đăng ký filter trong `templating.py`. Phương án pre-process trong Python tránh vấn đề này.
- **party_extras cho tasks:** `_load_worklist_data()` hiện build `party_extras` từ cả actions và tasks (`party_id` của tasks đã được collect). Kiểm tra xem `preferred_identity` của task party có được load không — nếu không, fallback về `task.title`.
