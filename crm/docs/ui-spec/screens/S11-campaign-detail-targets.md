---
id: S11
type: screen
name: "Campaign Detail / Targets"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R1, R3, R6, R11]
regions: [topbar, summary_bar, target_list, conversion_stats]
---

# S11 — Campaign Detail / Targets

## Purpose

Chi tiết một campaign: summary stats trên đầu (total targets, sent, responded, converted,
conversion rate, attributed revenue), danh sách target `crm_campaign_target` với status lifecycle
`queued → sent → responded → converted/skipped`. NV được gán thấy danh sách khách cần liên hệ,
có thể ghi converted_order_code thủ công hoặc hệ thống tự khớp.

Conversion tracker: order_code mới trong `wh_order_hdr` sau `campaign.scheduled_at` ICT → SSE
`campaign.target.converted` → UI cập nhật stats realtime.

## Layout

```yaml ui-layout
areas:
  - [topbar]
  - [summary_bar]
  - [target_list]
  - [conversion_stats]
samples:
  topbar: "[← Chiến dịch]  Win-back Q3  [Sửa] [Kích hoạt]"
  summary_bar: "Targets: 87 | Sent: 43 | Converted: 13 | Rate: 14.9% | Revenue attributed: 28.500.000đ"
  target_list: "Nguyễn V. A · converted · NV A · ORD-20060901  |  Trần T. B · queued · NV B · —  [Filter: status ▼]"
  conversion_stats: "(conversion rate + attributed revenue tracker; updates via SSE campaign.target.converted)"
elements:
  "← Chiến dịch": A-S11-001
  "Sửa": A-S11-007
  "Filter: status ▼": A-S11-005
  "Kích hoạt": A-S11-008
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│TOPBAR                                                                      │
│· [← Chiến dịch]  Win-back Q3  [Sửa] [Kích hoạt]                            │
├────────────────────────────────────────────────────────────────────────────┤
│SUMMARY_BAR                                                                 │
│· Targets: 87 | Sent: 43 | Converted: 13 | Rate: 14.9% | Revenue attributed…│
├────────────────────────────────────────────────────────────────────────────┤
│TARGET_LIST                                                                 │
│· Nguyễn V. A · converted · NV A · ORD-20060901  |  Trần T. B · queued · NV…│
├────────────────────────────────────────────────────────────────────────────┤
│CONVERSION_STATS                                                            │
│· (conversion rate + attributed revenue tracker; updates via SSE campaign.t…│
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- ST-CAMPAIGN-NO-TARGETS: Segment có 0 member → warning
- ST-CAMPAIGN-CONVERTING: Conversion job running → spinner stats
- ST-LOADING: Target list loading

## Interactions

`btn_activate_campaign` (A-S11-008) fires a native browser confirm ("Xác nhận kích hoạt chiến dịch...? Chiến dịch sẽ bắt đầu chạy ngay.") before mutating — same pattern as A-M15-006 deactivate-channel, not the O01 overlay (O01 is delete-only in this corpus and has no wired backend route beyond that use).

```yaml crm-contract
interactions:
  - id: A-S11-001
    element: btn_back
    region: topbar
    trigger: click
    action: navigate
    target: S10
  - id: A-S11-002
    element: target_row_customer
    region: target_list
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$target.party_id" }
  - id: A-S11-003
    element: btn_mark_converted
    region: target_list
    trigger: click
    action: open_overlay
    target: M12
    payload: { target_id: "$target.id" }
  - id: A-S11-004
    element: btn_mark_skipped
    region: target_list
    trigger: click
    action: mutate
    effects: [target.status.set_skipped]
  - id: A-S11-005
    element: filter_status
    region: target_list
    trigger: change
    action: mutate
    effects: [target_list.reload]
  - id: A-S11-006
    element: filter_assignee
    region: target_list
    trigger: change
    action: mutate
    effects: [target_list.reload]
  - id: A-S11-007
    element: btn_edit_campaign
    region: topbar
    trigger: click
    action: open_overlay
    target: M07
    payload: { campaign_id: "$campaign.id" }
  - id: A-S11-008
    element: btn_activate_campaign
    region: topbar
    trigger: click
    guard: "campaign.status == 'draft'"
    action: mutate
    effects: [campaign.status.set_active, topbar.activate_btn.hide, ui.toast.show]
  - id: A-S11-LSN01
    listens_to: campaign.target.converted
    action: mutate
    effects: [summary_bar.stats.reload, target_list.update_row]
  - id: A-S11-LSN02
    listens_to: filter_bar.changed
    action: mutate
    effects: [target_list.reload_with_filters]
  - id: A-S11-LSN03
    listens_to: filter_bar.cleared
    action: mutate
    effects: [target_list.reload]
