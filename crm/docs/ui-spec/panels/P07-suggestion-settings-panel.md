---
id: P07
type: panel
name: "Suggestion Settings Panel"
platforms: [desktop]
hosted_by: [S03]
status: active
design_ref: "plans/260805-1216-crm-worklist-suppression-settings-panel"
rules: []
regions: [explainer, group_list]
---

# P07 — Suggestion Settings Panel

## Purpose

Panel tab "Cài đặt gợi ý" trong Customer 360 (S03). Cho NV tắt/mở từng loại cơ hội
(`action_type` × `source_mart`) riêng cho 1 khách, có ngày hết hạn tự chọn — khác 3 cơ chế
suppression khác đã có: "Bỏ qua" trên từng thẻ (1 lần, tự hiện lại), "🚫 Đừng gọi nữa"
(toàn bộ loại, vô thời hạn, dùng khi khách yêu cầu không liên hệ), và cờ tắt toàn hệ thống
trong `seed_action_scenario_registry` (không theo khách). Đọc/viết `crm_action_dismissal`
(migration 0046, key `(party_id, action_type, source_mart)`).

## Data

Nguồn danh mục: `cache.wh_action_scenario_registry` (13 dòng, sync từ
`transformation/seeds/seed_action_scenario_registry.csv` qua Phase 01-02). Grouped theo
`scenario_group`. Mỗi dòng join với `crm_action_dismissal` theo `(action_type, source_mart)`
cho party hiện tại.

## Row States

| State | Điều kiện | Hiển thị |
|-------|-----------|----------|
| Đang bật | không có dismissal, hoặc dismissal đã hết hạn | "Đang bật" |
| Đã tắt | dismissal tồn tại, `dismissed_until > now` | "Đã tắt tới dd/mm/yyyy — bởi {user}" |
| Đã hết hạn | dismissal tồn tại, `dismissed_until <= now` | "Đã hết hạn ngày dd/mm/yyyy — đang bật lại" |
| Tắt toàn hệ thống | `enabled = 0` trong catalog | greyed, non-interactive, tooltip |

## Layout

```yaml ui-layout
areas:
  - [explainer]
  - [group_list]
content:
  explainer:
    - row:
        - { text: "Tắt ở đây = không đề xuất loại này cho khách này nữa tới ngày đã chọn — khác 'Bỏ qua' và 'Đừng gọi nữa'." }
  group_list:
    - list: { item: "Nhóm (scenario_group) → dòng: label · phạm vi · trạng thái · [Tắt] / [Bật lại]", rows: 7 }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│EXPLAINER                                                                   │
│· Tắt ở đây = không đề xuất loại này cho khách này nữa tới ngày đã chọn — k…│
├────────────────────────────────────────────────────────────────────────────┤
│GROUP_LIST                                                                  │
│· list ×7 {Nhóm (scenario_group) → dòng: label · phạm vi · trạng thái · [Tắ…│
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Row Structure

- **Line 1**: `[label]  [grain badge: "Theo khách" | "Theo sản phẩm"]`
- **Line 2**: `[state text]`
- **Action**: `[Tắt]` (opens inline date picker: chips 1 tuần/1 tháng/3 tháng + `<input type="date">`)
  hoặc `[Bật lại]` — mutually exclusive per row, hidden entirely when globally disabled.

## States

- ST-EMPTY-CATALOG: `cache.wh_action_scenario_registry` chưa sync → "Danh mục gợi ý chưa được
  đồng bộ từ kho dữ liệu." (never a hardcoded fallback list)

## Interactions

```yaml crm-contract
interactions:
  - id: A-P07-001
    element: btn_suppress_chip
    region: group_list
    trigger: click
    action: emit_event
    effects: [date_input.set_value]
  - id: A-P07-002
    element: btn_suppress
    region: group_list
    trigger: submit
    action: mutate
    payload: { party_id: "$party.id", action_type: "$row.action_type", source_mart: "$row.source_mart", until_date: "$form.until_date" }
    effects: [dismissal.upsert, group_list.reload]
  - id: A-P07-003
    element: btn_unsuppress
    region: group_list
    trigger: click
    action: mutate
    payload: { party_id: "$party.id", action_type: "$row.action_type", source_mart: "$row.source_mart" }
    effects: [dismissal.delete, group_list.reload]
```

## Related

- Migration: `crm/migrations/0046_action_dismissal_source_mart.up.sql`
- Service: `crm/src/application/suggestion_settings_service.py`
- Screen: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_suggestion_settings.py`
- Template: `crm/src/adapters/inbound/web/templates/fragments/c360_suggestion_settings_panel.html`
- Does NOT touch: `_fetch_actions()` (C360 reason rail) — deliberately unfiltered, verified decision.
