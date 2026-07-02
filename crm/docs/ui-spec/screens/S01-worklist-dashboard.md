---
id: S01
type: screen
name: "Worklist / Dashboard"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R2, R6, R8]
regions: [topbar, sidebar, main, kpi_strip, filter_bar, task_list]
---

# S01 — Worklist / Dashboard

## Purpose

Màn hình chính mà Sales Rep mở mỗi buổi sáng. Hiển thị danh sách task hôm nay được giao cho NV
(từ `crm_task` + `wh_action_queue`), sắp xếp theo due_at + priority. Mỗi task row có tên khách,
lý do hành động (`rationale_vi`), giá trị tiềm năng (`value_at_stake_vnd`), kênh liên lạc ưu tiên,
và `contact_pref` note inline (nếu có) để rep biết cách tiếp cận ngay mà không cần mở S03.

NV nhấn vào task → Customer 360. NV có thể filter theo priority/type/product, ẩn đã liên hệ,
lọc có kịch bản AI, hoặc tạo task mới thủ công. Badge trên sidebar cập nhật theo SSE khi có
task mới hoặc cache refresh.

Data loading architecture: `WorklistQueryService` wraps both action-queue read and last-contact
lookup into a single service boundary (hexagonal). Screen adapter depends on `WorklistSvc`
protocol only — no direct repo access.

## Layout

```
┌─ C01 SIDEBAR ──┬──────────────────────────────────────────────────────────────┐
│  [≡] CRM       │  TOPBAR (pagehead)                                           │
│  > Worklist ●  │  Worklist hôm nay        [Làm mới ↺]  [+ Tạo task]          │
│    Khách hàng  ├──────────────────────────────────────────────────────────────┤
│    Inbox    3  │  KPI STRIP                                                   │
│    Tasks       │  [ Task mở: N ] [ Hành động AQ: N ] [ Giá trị: Ntr ] [ Khẩn: N ] │
│    Segments    ├──────────────────────────────────────────────────────────────┤
│    Chiến dịch  │  FILTER BAR                                                  │
│    Ads         │  Ưu tiên:[↕] Loại:[↕] Phân khúc:[↕] Hạng KH:[↕] Sản phẩm:[↕] Tìm:[________]          │
│    Cài đặt     │  [💰 Giá trị cao] [✅ Ẩn đã liên hệ] [📋 Có kịch bản]      │
│                ├──────────────────────────────────────────────────────────────┤
│  [User: NV A]  │  TASK LIST (5 urgency bands, collapsible)                    │
│                │                                                              │
│                │  ▼ ✅ Đã liên hệ  (2)              ← band 4, collapsed      │
│                │  ▼ 🔴 Quá hạn     (3)              ← band 0, open           │
│                │  ┌──────────────────────────────────────────────────────┐    │
│                │  │ [P1] Nguyễn Văn A                 quá hạn 2 ngày    │    │
│                │  │   "Sắp hết hàng yêu thích — gọi ngay"               │    │
│                │  │   🛍 Fine Japan A / ↩ B   💬 Chỉ Zalo sau 8pm       │    │
│                │  │   📵 2h trước · Không bắt    → lịch sử              │    │
│                │  │   [Dời hạn] [Dọn] [📞 Gọi] [Mở hồ sơ >]           │    │
│                │  └──────────────────────────────────────────────────────┘    │
│                │  ▼ 🟡 Hôm nay / Khẩn  (5)          ← band 1, open           │
│                │  ┌──────────────────────────────────────────────────────┐    │
│                │  │ CALL_NOW  Trần Thị B   📋 Có kịch bản               │    │
│                │  │   "Chưa mua 92 ngày, GOLD"   💰 1.800.000đ          │    │
│                │  │   ✅ 3h trước · Đã nghe → lịch sử                   │    │
│                │  │   [📋 Gọi] [⏰ snooze] [✕ Bỏ qua] [Xem 360 >]      │    │
│                │  └──────────────────────────────────────────────────────┘    │
│                │  ▼ 🟢 Đúng hạn     (8)              ← band 2, open           │
│                │  ▶ 🔵 Cần chú ý    (4)              ← band 3, collapsed      │
│                │                                                              │
│                │  FRESHNESS: cache cập nhật lúc 07:15 ICT ✓                  │
└────────────────┴──────────────────────────────────────────────────────────────┘
```

## Row Detail

### Action rows (from `wh_action_queue`)

- Action type badge (CALL_NOW, WIN_BACK, UPSELL, …)
- Tên khách + số điện thoại key
- `rationale_vi` (lý do từ action_queue)
- Product affinity tags: `top_affinity_product` + `last_purchased_product`
- `contact_pref` note inline (pinned, note_type='contact_pref')
- Last-contact strip: icon + relative time + outcome label (answered/no_answer/…)
- `value_at_stake_vnd` + pending since date
- Neglect badge: shown when action has waited 1–6 days (7+ days → band 3)
- Script badge (📋 Có kịch bản) when customer has AI approach script
- Quick actions: [📋 Gọi → S14] (script path) OR [📞/💬/📘 contact_btn → M08] (normal path)
- Snooze dropdown: 1/3/7 ngày → PATCH dismiss row
- [✕ Bỏ qua] dismiss → PATCH delete row
- [Xem 360 >] → navigate S03

### Task rows (from `crm_task`)

- Priority badge (P1/P2/P3)
- Task title (link to S03 if party_id present)
- `description` note
- `contact_pref` note inline (same as action rows)
- Last-contact strip (same as action rows)
- Due date
- Overdue badge (quá hạn N ngày) — band 0 tasks only
- [📞/💬 contact_btn → M08]
- Overdue-only extra controls: [Dời hạn → M05] [Dọn → cancel + delete row]
- [Mở hồ sơ >] → navigate S03

### Band structure

| Band ID | Label | Icon | Default state |
|---|---|---|---|
| 4 | Đã liên hệ | ✅ | Collapsed |
| 0 | Quá hạn | 🔴 | Open |
| 1 | Hôm nay / Khẩn | 🟡 | Open |
| 2 | Đúng hạn | 🟢 | Open |
| 3 | Cần chú ý | 🔵 | Collapsed |

Band 4 collects action rows whose `party_id` had ANY contact attempt in last 24h (regardless of outcome),
when `hide_contacted=false`. When `hide_contacted=true`, positive-outcome contacts are removed from the
list entirely — band 4 stays empty.

## States

- ST-WORKLIST-EMPTY: Không có task hoặc action nào → empty state + CTA browse customers
- ST-WORKLIST-ALL-DONE: Tất cả done → celebratory message (client-side only — no server state)
- ST-LOADING: Skeleton rows khi HTMX fragment đang load
- ST-STALE-CACHE: `refreshed_at` > 24h → yellow caveat trên freshness footer

## Interactions

```yaml crm-contract
interactions:
  - id: A-S01-001
    element: action_row
    region: task_list
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$action.party_id" }
  - id: A-S01-002
    element: task_row
    region: task_list
    trigger: click
    action: navigate
    target: S15
    payload: { task_id: "$task.id" }
  - id: A-S01-003
    element: task_checkbox
    region: task_list
    trigger: click
    action: mutate
    effects: [task.status.set_done, task.completed_at.set_now]
  - id: A-S01-004
    element: btn_create_task
    region: topbar
    trigger: click
    action: open_overlay
    target: M05
  - id: A-S01-006
    element: filter_priority
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-007
    element: btn_quick_call
    region: task_list
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$row.party_id", mode: "contact_attempt", channel: "phone" }
  - id: A-S01-008
    element: btn_quick_zalo
    region: task_list
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$row.party_id", mode: "contact_attempt", channel: "zalo" }
  - id: A-S01-009
    element: btn_call_mode
    region: task_list
    trigger: click
    action: navigate
    target: S14
    payload: { party_id: "$action.party_id" }
  - id: A-S01-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [freshness_badge.update]
  - id: A-S01-LSN02
    listens_to: task.due.soon
    action: mutate
    effects: [task_list.reload, ui.toast.show]
  - id: A-S01-LSN03
    listens_to: nav.item.selected
    action: navigate
    target: S01
  - id: A-S01-LSN04
    listens_to: action_queue.task_requested
    action: open_overlay
    target: M05
    payload: { source: "action_queue", action_id: "$event.action_id", party_id: "$event.party_id" }
  - id: A-S01-LSN05
    listens_to: action_queue.card_clicked
    action: navigate
    target: S03
    payload: { party_id: "$event.party_id" }
  - id: A-S01-LSN06
    listens_to: filter_bar.changed
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-LSN07
    listens_to: filter_bar.cleared
    action: mutate
    effects: [task_list.reload]
  - id: A-S01-LSN08
    listens_to: action_queue.call_mode_requested
    action: navigate
    target: S14
    payload: { party_id: "$event.party_id" }
  - id: A-S01-010
    element: filter_has_script
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-011
    element: btn_script_call
    region: task_list
    trigger: click
    action: navigate
    target: S14
    payload: { party_id: "$action.party_id", tab: "call_cockpit" }
  - id: A-S01-LSN09
    listens_to: worklist.load_complete
    action: mutate
    effects: [action_rows.badge_has_script.render]
  - id: A-S01-012
    element: filter_product
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-013
    element: filter_hide_contacted
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-014
    element: filter_q
    region: filter_bar
    trigger: input
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-015
    element: filter_min_value
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-021
    element: filter_strategic_tier
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-022
    element: filter_value_group
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-016
    element: btn_dismiss_action
    region: task_list
    trigger: click
    action: mutate
    effects: [action_row.remove]
  - id: A-S01-017
    element: btn_snooze_action
    region: task_list
    trigger: click
    action: mutate
    effects: [action_row.remove]
  - id: A-S01-018
    element: btn_cancel_task
    region: task_list
    trigger: click
    action: mutate
    effects: [task_row.remove]
  - id: A-S01-019
    element: btn_reschedule_task
    region: task_list
    trigger: click
    action: open_overlay
    target: M05
    payload: { task_id: "$task.id" }
  - id: A-S01-020
    element: btn_refresh
    region: topbar
    trigger: click
    action: mutate
    effects: [worklist_container.reload]
```

## Notes

- **filter_assignee deferred**: `Task.assignee_user_id` exists in `crm_task` but no auth middleware surfaces `user_id` to the request lifecycle. "Của tôi" toggle is NOT rendered until auth context is wired. No spec action ID assigned.
- **Filter bar is inline**: Filters HTMX GET `/worklist/fragment` directly (no C05 emit/listen round-trip). LSN06/LSN07 describe the conceptual contract with C05 and are kept for future compatibility.
- **Last-contact data**: `WorklistQueryService.get_map_for_parties()` is always called (non-optional). Empty dict returned when `last_contact` repo not configured. All rows show the last-contact strip when data is available.
- **Band 4 / hide_contacted interaction**: mutually exclusive presentation. When `hide_contacted=true`, positive-outcome contacts are filtered out server-side and band 4 stays empty. When `hide_contacted=false` (default), any contact in last 24h (any outcome) moves that action to band 4 so the agent can see what they already tried.
- **filter_strategic_tier + filter_value_group**: Both derive from `wh_customer_tier` via `LEFT JOIN` in `list_all_action_queue()`. Show only when data present in unfiltered set (`available_tiers` / `available_value_groups` context vars). Actions only; tasks pass through.
