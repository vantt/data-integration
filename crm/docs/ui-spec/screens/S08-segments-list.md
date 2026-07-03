---
id: S08
type: screen
name: "Segments List"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R1, R10]
regions: [topbar, sidebar, segment_list]
---

# S08 — Segments List

## Purpose

Manager xem danh sách tất cả segment động và tĩnh (`crm_segment`). Mỗi row hiển thị: tên segment,
loại (dynamic/static), số thành viên hiện tại, ngày cập nhật cuối, trạng thái materialization.
SSE cập nhật member_count khi job materialize xong.

Manager có thể tạo segment mới, xem chi tiết/chỉnh sửa rule, hoặc xóa segment (nếu không đang dùng
trong campaign nào).

## Layout

```yaml ui-layout
columns: [1fr, 4fr]
areas:
  - [sidebar, topbar]
  - [sidebar, segment_list]
samples:
  sidebar: "(C01 global nav)"
  topbar: "Segments  [+ Tạo segment]  [Search tên...]"
  segment_list: "Win-back GOLD Q3 · dynamic · 87 thành viên · hôm nay  |  VIP tay - tháng 6 · static · 12 · 12/06"
elements:
  "+ Tạo segment": A-S08-001
  "Search tên...": A-S08-004
```

<!-- ui-layout:ascii:start -->
```
┌───────────────┬────────────────────────────────────────────────────────────┐
│SIDEBAR        │TOPBAR                                                      │
│· (C01 global …│· Segments  [+ Tạo segment]  [Search tên...]                │
│               ├────────────────────────────────────────────────────────────┤
│               │SEGMENT_LIST                                                │
│               │· Win-back GOLD Q3 · dynamic · 87 thành viên · hôm nay  |  …│
└───────────────┴────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: Segments   [+ Tạo segment]   [Search tên...]        │
│               ├──────────────────────────────────────────────────────────────┤
│               │  SEGMENT LIST                                                │
│               │  ┌───────────────────────────────────────────────────────── │
│               │  │ Tên                    Loại     Thành viên  Cập nhật     │
│               │  ├─────────────────────────────────────────────────────────  │
│               │  │ Win-back GOLD Q3       dynamic  87          hôm nay      │
│               │  │ Reactivation tháng 7   dynamic  34          hôm nay      │
│               │  │ VIP tay - tháng 6      static   12          12/06        │
│               │  └───────────────────────────────────────────────────────── │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

## States

- ST-SEGMENT-MATERIALIZING: Job đang chạy → spinner trên row
- ST-SEGMENT-EMPTY-MEMBERS: 0 members sau materialize → warning icon
- ST-LOADING: List loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S08-001
    element: btn_create_segment
    region: topbar
    trigger: click
    action: navigate
    target: S09
  - id: A-S08-002
    element: segment_row
    region: segment_list
    trigger: click
    action: navigate
    target: S09
    payload: { segment_id: "$segment.id" }
  - id: A-S08-003
    element: segment_use_in_campaign
    region: segment_list
    trigger: click
    action: navigate
    target: S10
    payload: { prefill_segment_id: "$segment.id" }
  - id: A-S08-004
    element: search_input
    region: topbar
    trigger: input
    action: mutate
    effects: [segment_list.filter_by_name]
  - id: A-S08-LSN01
    listens_to: segment.materialized
    action: mutate
    effects: [segment_list.update_member_count]
