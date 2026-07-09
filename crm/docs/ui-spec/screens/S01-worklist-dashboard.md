---
id: S01
type: screen
name: "Worklist / Dashboard"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R2, R6, R8, R15]
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

```yaml ui-layout
columns: [1fr, 4fr]
areas:
  - [sidebar, main]
children:
  main:
    areas:
      - [topbar]
      - [kpi_strip]
      - [filter_bar]
      - [task_list]
samples:
  sidebar: "[≡] CRM  > Worklist ●  Khách hàng  Inbox 3  Tasks  Segments  Chiến dịch  Ads  Cài đặt"
  main: "(right content area — topbar · kpi_strip · filter_bar · task_list)"
  topbar: "Worklist hôm nay  [Làm mới ↺]  [+ Tạo task]"
  kpi_strip: "[ Task mở: N ] [ Hành động AQ: N ] [ Giá trị: Ntr ] [ Khẩn: N ]"
  filter_bar: "Ưu tiên:[↕] Loại:[↕] Sản phẩm:[↕]  [📞 Có thể liên hệ (on)] [💰 Giá trị cao] [✅ Ẩn đã liên hệ] [📋 Có kịch bản]"
  task_list: "▼ 🔴 Quá hạn (3) · [P1] Nguyễn Văn A quá hạn 2 ngày · 🛍 Fine Japan · [📅 Dời hạn][Hủy][📞 Gọi][Xem 360 >]"
elements:
  "Làm mới ↺": A-S01-020
  "+ Tạo task": A-S01-004
  "✅ Ẩn đã liên hệ": A-S01-013
  "📋 Có kịch bản": A-S01-010
  "☎️ Có thể liên hệ": A-S01-023
  "📅 Dời hạn": A-S01-019
  "Hủy": A-S01-018
  "📞 Gọi": A-S01-007
```

<!-- ui-layout:ascii:start -->
```
┌───────────────┬────────────────────────────────────────────────────────────┐
│SIDEBAR        │MAIN                                                        │
│· [≡] CRM  > W…│· (right content area — topbar · kpi_strip · filter_bar · t…│
└───────────────┴────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Row Detail

### Action rows (from `wh_action_queue`)

- Action type badge — short VN label as text (e.g. "Gọi ngay" for CALL_NOW; full mart
  code stays in the hover tooltip only, via `bdg_label`/`bdg_tip` filters)
- Tên khách; nếu thiếu → SĐT ưu tiên (nếu có) hoặc "(chưa xác định)" — KHÔNG BAO GIỜ
  hiển thị `customer_key` (MD5 surrogate key nội bộ)
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
- Overdue-only extra controls: [📅 Dời hạn → M05] [Hủy → cancel + delete row]
  (📅 icon distinguishes the M05 reschedule button from the ⏰ snooze dropdown
  when both appear on the same claimed-and-overdue row)
- [Xem 360 >] → navigate S03 (renamed from "Mở hồ sơ" to match action rows —
  both link to the same destination)

### Section structure (2026-07-09 — claimed vs unclaimed, screen's PRIMARY axis)

The page's primary axis is **claim status**, not row kind — this screen's main focus is the
unclaimed queue (opportunities to decide on); already-claimed work is secondary reference
material. Two top-level sections:

1. **🙋 Đã Claim** (secondary) — `claimed_bands` (bands 4/0/1/2/3): EVERY `kind='task'` row,
   NOT split by source — manual tasks assigned to me AND `action_queue_claim` tasks land in
   the same bands together (Quá hạn/Hôm nay-Khẩn/Trong hạn/Đã liên hệ), exactly like the
   original unsplit banding. A claimed task is a claimed task regardless of how it got an
   owner, so there's no "which kind of claimed" sub-distinction to make. Renders FIRST on
   the page but **collapsed by default** — secondary focus, despite being first.
   `show_overflow=false`: `/worklist/band/{id}/more` always re-ranks actions-only, so it
   can't safely serve this task-only section's overflow (ids 1/2/4 overlap with
   `queue_action_bands` below) — renders uncapped/eager instead; task-per-band volume (a
   rep's own open/claimed tasks) is expected to stay small enough for that to be a safe
   trade, not a silent drop.
2. **🎯 Chưa Claim** (PRIMARY) — everything nobody owns yet. **Expanded by default**
   (unlike Đã Claim). Two named sub-groups so a system opportunity is never confused with a
   manually-created task despite sharing one parent:
   - **📥 Hàng Đợi Chung** (first, per explicit ordering request) — unassigned custom
     (`manual`-source, no assignee) tasks, visible to the whole team. Row UI is the
     standard task row (priority pill, description, due date) with the aside swapped for a
     single **Nhận** button (`PATCH /tasks/{id}/assign-me`).
   - **🎯 Cơ Hội Hệ Thống** (second) — `queue_action_bands` (bands 1/2/3/4): unclaimed
     `wh_action_queue` items (`kind='action'`) — always unclaimed by construction (claiming
     converts an action into a Task and hides it from `all_actions` upstream). Includes
     band 4 ("Đã liên hệ") for actions whose party was recently contacted but still not
     claimed — that row has no owner, so it belongs with the queue, not with Đã Claim. Row
     UI unchanged from the original action row. Sub-band defaults unchanged: 4 collapsed
     (first), 1 "Khẩn" open, 2 "Trong hạn" open, 3 "Treo lâu" collapsed (VIP/GOLD
     auto-expand unchanged). The existing `/worklist/band/{id}/more` overflow route already
     re-ranks actions-only, so it stays correct for every id this list can contain
     (including 4) — `show_overflow=true`.

**Why collapsible `<details>` instead of tabs**: a real tab (separate nav/route) would hide
the "just claimed → moved to Đã Claim" feedback the instant a rep clicks Nhận việc — the row
would land in a hidden tab instead of the same scroll. Collapsed-by-default `<details>` keeps
the page compact without losing that single-glance feedback loop when expanded.

| Band ID | Label | Icon | Default state | Where |
|---|---|---|---|---|
| 4 | Đã liên hệ | ✅ | Collapsed | both sections have their own band-4 sub-group (task side → Đã Claim; action side → Cơ Hội Hệ Thống) |
| 0 | Quá hạn | 🔴 | Open | Đã Claim only (task-only band) |
| 1 | Hôm nay / Khẩn | 🟡 | Open | both sections |
| 2 | Đúng hạn | 🟢 | Open | both sections |
| 3 | Cần chú ý | 🔵 | Collapsed | Cơ Hội Hệ Thống only (action-only band) |

Band 4 collects rows whose `party_id` had ANY contact attempt in last 24h (regardless of
outcome), when `hide_contacted=false`. When `hide_contacted=true`, positive-outcome contacts
are removed from the list entirely — band 4 stays empty on both sides.

`split_worklist_view()` (`application/worklist_ranking.py`) performs this partition from
`rank_worklist()`'s output — no change to urgency/band/sort logic, purely a `kind` filter
(task → claimed_bands, action → queue_action_bands) per band, run before the
`display_capacity` cap-slicing so both views see full row counts.

**Design history**: this replaced 3 earlier iterations within the same day (kind-based split
→ claimed/manual split with a band-0 special case → this claimed/unclaimed reframe) as the
user's actual mental model surfaced through use — see plan.md for the full trail. The
takeaway that stuck: the screen's PRIMARY axis is ownership (claimed vs not), not row
provenance (action vs task) — provenance only matters as a sub-grouping label inside the
unclaimed section, where two different claim mechanisms ("Nhận việc" vs "Nhận") would
otherwise be visually ambiguous.

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
  - id: A-S01-023
    element: filter_contactable_only
    region: filter_bar
    trigger: change
    action: mutate
    effects: [task_list.reload_with_filters]
```

## Notes

- **A1 claim-context badges (Phase 04)**: `action_queue_claim` task rows show 💰 `value_at_stake_vnd` (SUM across all actions) and 🛍 `top_affinity_product` (from highest-value action) when set. Values persisted at claim time (migration 0036) — no recalculation at render.
- **A4 snooze dropdown (Phase 04)**: `action_queue_claim` task rows include a `⏰` snooze `<details>` dropdown with 1/3/7-day options. `PATCH /tasks/{id}/snooze?days=N` shifts `due_at` to today_ICT + N days, resets status to "open" when "doing". Returns 204.
- **A2 call-mode queue (Phase 04)**: Action rows include a "📞 Gọi" link (shortened from "📞 Gọi chế độ" in phase-09 R9; tooltip "Vào chế độ gọi với hàng đợi" unchanged) pointing to `/customers/{pid}/call?queue_ids=<50-id list>`. `queue_party_ids` built from ranked action rows (before band slicing, capped at 50) and threaded through template context.
- **filter_assignee deferred**: `Task.assignee_user_id` exists in `crm_task` but no auth middleware surfaces `user_id` to the request lifecycle. "Của tôi" toggle is NOT rendered until auth context is wired. No spec action ID assigned.
- **Filter bar is inline**: Filters HTMX GET `/worklist/fragment` directly (no C05 emit/listen round-trip). LSN06/LSN07 describe the conceptual contract with C05 and are kept for future compatibility.
- **Last-contact data**: `WorklistQueryService.get_map_for_parties()` is always called (non-optional). Empty dict returned when `last_contact` repo not configured. All rows show the last-contact strip when data is available.
- **Band 4 / hide_contacted interaction**: mutually exclusive presentation. When `hide_contacted=true`, positive-outcome contacts are filtered out server-side and band 4 stays empty. When `hide_contacted=false` (default), any contact in last 24h (any outcome) moves that action to band 4 so the agent can see what they already tried.
- **filter_strategic_tier + filter_value_group**: Both derive from `wh_customer_tier` via `LEFT JOIN` in `list_all_action_queue()`. Show only when data present in unfiltered set (`available_tiers` / `available_value_groups` context vars). Actions only; tasks pass through.
- **filter_contactable_only**: `ActionQueueItem.is_contactable` sourced from `wh_customer_tier.is_contactable` (phone-presence proxy, `dim_customers.sql`; not a consent/DNC signal — see `20-domain-rules.md` R1). Defaults to `true` when the tier row is absent (LEFT JOIN NULL → COALESCE 1), matching the codebase's "default = contactable" policy. Row-1 toggle, first position (before "Giá trị cao"), 📞 icon; **default ON** — `parse_filters` treats the toggle as active unless the request explicitly sends `contactable_only=0` (hidden round-trip input persists the off state only, since on is the default). Actions only, tasks always pass through. Turning it OFF is the non-default state and is what increments `active_filter_count`.
- **Item 3 — B3 VIP/GOLD auto-expand (Phase 06)**: `WorklistRow.value_group` populated from `ActionQueueItem.value_group`. After band sorting, band 3 ("Treo lâu") overrides `is_expanded=True` and adds `vip_count` when any row has `value_group in {'VIP','GOLD'}`. Template shows `⭐ N VIP/GOLD` badge in band summary. Module-level `_BAND_META` is not mutated (dict copy per call).
- **Item 4 — Wake badge (Phase 06)**: `WorklistRow.wake_badge=True` when `snoozed_until` is a datetime that passed within the last 24 hours. Computed per-row in `rank_worklist()` from action's `snoozed_until` (str ISO or datetime). Template shows `⏰ vừa thức dậy` badge inline on action row. Safe no-op when field absent.
