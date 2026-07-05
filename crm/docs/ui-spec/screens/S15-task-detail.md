---
id: S15
type: screen
name: "Task Detail"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R6]
regions: [header, lifecycle, body_contact, body_internal, body_generic, activity_log, close_bar]
---

# S15 — Task Detail

## Purpose

**Task = cam kết bền vững** (có thể kéo dài nhiều ngày / nhiều cuộc gọi). S15 sở hữu vòng đời
task và định tuyến thực thi theo `task_kind`.

Phân biệt với các surface khác:
- **S03** Customer 360 — centric theo khách, không theo task.
- **M05** Create/Edit Task — tạo/sửa nhanh, không phải nơi thực thi.
- **P04 / S07** — hàng đợi / bảng, mở task → S15.
- **S14** Call Mode Cockpit — phiên gọi centric theo khách; task CONTACT không nhúng cockpit
  riêng, thay vào đó **launch vào phiên gọi chung** của khách tại `/customers/{id}/call`.

Quan hệ many-to-many: một task ← nhiều cuộc gọi; một phiên gọi → nhiều task (customer-grained).
Vì vậy task `contact` không nhúng cockpit riêng — nó điều hướng vào phiên dùng chung của khách.

### task_kind routing

`task_kind` là trường mới trên `crm_task`. Backfill bằng **data migration** (suy từ `source`/`source_ref`
→ action_type, `source=verify_account`→internal, `party_id=null`→generic), **KHÔNG hardcode fallback ở
render-time** — dữ liệu phải nhất quán tại nguồn.

| task_kind | Body | Thực thi ở đâu |
|-----------|------|-----------------|
| `contact` | Provenance + lý do + lịch sử thử liên lạc + nút "Vào phiên gọi" | Launch S14 (phiên khách) |
| `internal` | Checklist/bước + facts khách tối thiểu + tool CTAs | Trực tiếp tại S15 |
| `generic` | Mô tả + checklist + links + ghi chú (không có block khách) | Trực tiếp tại S15 |

**Claim-task** (`source=action_queue_claim` — 1 task gộp nhiều action của khách): body_contact **list các
action con** được gộp (badge action_type + rationale + value). Không dựng lại UI mới — tái dùng đúng
pattern đã có: rail "Vì sao gọi" của S14 và action-card ở tab "Value & Behavior" (P01) đã giải quyết
hiển thị này; S15 chỉ liệt kê tóm tắt + nút "Vào phiên gọi" để xử lý tất cả trong một phiên.

## Layout

```yaml ui-layout
areas:
  - [header]
  - [lifecycle]
  - [body_contact]
  - [activity_log]
  - [close_bar]
floating:
  - region: body_internal
    when: "task.task_kind == 'internal'"
    replaces: [body_contact]
  - region: body_generic
    when: "task.task_kind == 'generic'"
    replaces: [body_contact]
samples:
  header: "[← Quay lại]  \"Follow-up sau cuộc gọi\"  [P1] [Quá hạn 2 ngày]  [status chip]  Đến hạn: 20/06/2026  Giao: NV A  [Nguyễn Văn A ↗ 360]"
  lifecycle: "open → doing → done → cancelled  |  [▷ Bắt đầu]  [✎ Sửa]  [⏳ Hoãn]  [✕ Huỷ]"
  body_contact: "Nguồn: action_queue · Lý do: \"Sắp hết hàng...\" · GT: 1.800.000đ  |  Nguyễn Văn A [GOLD] SĐT: 0901234567  [▶ Vào phiên gọi]"
  body_internal: "Nguyễn Văn A [GOLD] LTV 8.2tr  [Xem 360 >]  |  ☑ Tra cứu đơn hàng  ☐ Xác nhận địa chỉ  ☐ Gửi báo giá"
  body_generic: "Mô tả: Cập nhật bảng giá Q3  |  ☑ Thu thập bảng giá  ☐ Upload lên Sapo  |  [https://drive.google.com/…]"
  activity_log: "12/06 10:30 Cuộc gọi — Không bắt  |  13/06 14:00 Zalo — Chưa phản hồi"
  close_bar: "[ghi chú nhanh…]  [✓ Ghi log & hoàn thành]"
elements:
  "Nguyễn Văn A ↗ 360": A-S15-007
  "▷ Bắt đầu": A-S15-001
  "✎ Sửa": A-S15-002
  "⏳ Hoãn": A-S15-003
  "✕ Huỷ": A-S15-004
  "▶ Vào phiên gọi": A-S15-006
  "Xem 360 >": A-S15-007
  "✓ Ghi log & hoàn thành": A-S15-005
  "← Quay lại": A-S15-011
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· [← Quay lại]  "Follow-up sau cuộc gọi"  [P1] [Quá hạn 2 ngày]  [status ch…│
├────────────────────────────────────────────────────────────────────────────┤
│LIFECYCLE                                                                   │
│· open → doing → done → cancelled  |  [? Bắt đầu]  [? Sửa]  [(t) Hoãn]  [x …│
├────────────────────────────────────────────────────────────────────────────┤
│BODY_CONTACT                                                                │
│· Nguồn: action_queue · Lý do: "Sắp hết hàng..." · GT: 1.800.000đ  |  Nguyễ…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIVITY_LOG                                                                │
│· 12/06 10:30 Cuộc gọi — Không bắt  |  13/06 14:00 Zalo — Chưa phản hồi     │
├────────────────────────────────────────────────────────────────────────────┤
│CLOSE_BAR                                                                   │
│· [ghi chú nhanh…]  [v Ghi log & hoàn thành]                                │
└────────────────────────────────────────────────────────────────────────────┘

[STOP variant — when: task.task_kind == 'internal']
┌────────────────────────────────────────────────────────────────────────────┐
│BODY_INTERNAL                                                               │
│when: task.task_kind == 'internal'                                          │
│· Nguyễn Văn A [GOLD] LTV 8.2tr  [Xem 360 >]  |  [x] Tra cứu đơn hàng  [ ] …│
└────────────────────────────────────────────────────────────────────────────┘

[STOP variant — when: task.task_kind == 'generic']
┌────────────────────────────────────────────────────────────────────────────┐
│BODY_GENERIC                                                                │
│when: task.task_kind == 'generic'                                           │
│· Mô tả: Cập nhật bảng giá Q3  |  [x] Thu thập bảng giá  [ ] Upload lên Sap…│
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

### Frame chung (header + lifecycle + close_bar)

```
┌ HEADER ──────────────────────────────────────────────────────────────────────┐
│ [← Quay lại]  "Follow-up sau cuộc gọi"  [P1] [Quá hạn 2 ngày]             │
│ [status chip]  Đến hạn: 20/06/2026  Giao: NV A  [Nguyễn Văn A ↗ 360]     │
│ Nguồn: AUTO / action_queue  · Lý do: "Sắp hết hàng yêu thích"             │
├ LIFECYCLE ───────────────────────────────────────────────────────────────────┤
│ open → doing → done → cancelled                                             │
│ [▷ Bắt đầu]  [✎ Sửa]  [⏳ Hoãn]  [✕ Huỷ]                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                       BODY (adapts by task_kind)                            │
│                       (see per-kind layouts below)                           │
├ ACTIVITY LOG ────────────────────────────────────────────────────────────────┤
│  Timeline hoạt động của task (M08 logs với task_id, contact attempts)       │
│  [activity entry 1]  [activity entry 2]  ...                                │
├ CLOSE BAR (sticky) ──────────────────────────────────────────────────────────┤
│ [ghi chú nhanh…]        [✓ Ghi log & hoàn thành]                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Body — task_kind = contact

```
┌ BODY CONTACT ────────────────────────────────────────────────────────────────┐
│ PROVENANCE                                                                   │
│  Nguồn: action_queue · action_id: AQ-2024-0391                              │
│  Lý do: "Sắp hết hàng yêu thích — chu kỳ 45d, chưa mua 52d"               │
│  Giá trị ước tính: 1.800.000đ                                               │
│                                                                              │
│ KHÁCH HÀNG                                                                  │
│  Nguyễn Văn A  [GOLD]  SĐT: 0901234567  Kênh ưu tiên: Zalo                │
│  [▶ Vào phiên gọi]   ← navigate S14 (customer-grained shared session)       │
│  "xử lý cùng N việc khác trong phiên gọi này"                              │
│                                                                              │
│ LỊCH SỬ THỬ LIÊN LẠC (contact attempts cho task này)                       │
│  12/06 10:30  Cuộc gọi  — Không bắt                                        │
│  13/06 14:00  Zalo      — Chưa phản hồi                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Body — task_kind = internal

```
┌ BODY INTERNAL ───────────────────────────────────────────────────────────────┐
│ FACTS KHÁCH (tối thiểu)                                                      │
│  Nguyễn Văn A  [GOLD]  SĐT: 0901234567  LTV: 8.2tr                        │
│  [Xem 360 >]  [✎ Sửa thông tin]  [+ Tag]                                  │
│                                                                              │
│ CHECKLIST                                                                    │
│  ☑ Tra cứu lịch sử đơn hàng                                                │
│  ☐ Xác nhận địa chỉ giao hàng                                              │
│  ☐ Gửi báo giá                                                             │
│                                                                              │
│ GHI CHÚ NỘI BỘ                                                              │
│  [_____________________________________________]                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Body — task_kind = generic

```
┌ BODY GENERIC ────────────────────────────────────────────────────────────────┐
│ MÔ TẢ                                                                        │
│  Cập nhật bảng giá Q3 trên hệ thống                                        │
│                                                                              │
│ CHECKLIST                                                                    │
│  ☑ Thu thập bảng giá từ kế toán                                            │
│  ☐ Upload lên Sapo                                                          │
│                                                                              │
│ LINKS                                                                        │
│  [https://drive.google.com/…]                                               │
│                                                                              │
│ GHI CHÚ                                                                     │
│  [_____________________________________________]                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Notes (Phase 04)

- **A1 — Provenance block: value + product (migration 0036)**: For `source=action_queue_claim` tasks, the provenance block now shows two additional rows when set: "Tổng giá trị (claim)" (`task.value_at_stake_vnd` SUM at claim time) and "Sản phẩm chính" (`task.top_affinity_product` from highest-value action). These are persisted at claim time, not recomputed at render. Old tasks (pre-migration) show Nothing for these fields.

## States

- **ST-TASK-LOADING**: task fetch in-flight → skeleton.
- **ST-TASK-CONTACT**: task_kind=contact → body_contact rendered; "Vào phiên gọi" CTA visible.
- **ST-TASK-INTERNAL**: task_kind=internal → checklist body + tool CTAs.
- **ST-TASK-GENERIC**: task_kind=generic → description + checklist, no customer block.
- **ST-TASK-DONE**: task.status=done → read-only; lifecycle buttons hidden; activity log still visible.
- **ST-TASK-CANCELLED**: task.status=cancelled → read-only banner; reopen CTA only.

## Interactions

```yaml crm-contract
interactions:
  - id: A-S15-001
    element: btn_start
    region: lifecycle
    trigger: click
    action: mutate
    effects: [task.status.set_doing]
  - id: A-S15-002
    element: btn_edit
    region: lifecycle
    trigger: click
    action: open_overlay
    target: M05
    payload: { task_id: "$task.id" }
  - id: A-S15-003
    element: btn_postpone
    region: lifecycle
    trigger: click
    action: open_overlay
    target: O03
    payload: { task_id: "$task.id", due_at: "$task.due_at" }
  - id: A-S15-004
    element: btn_cancel
    region: lifecycle
    trigger: click
    guard: "task.status != 'done'"
    action: mutate
    effects: [task.status.set_cancelled]
  - id: A-S15-005
    element: btn_log_outcome
    region: close_bar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$task.party_id", task_id: "$task.id", mode: "log" }
  - id: A-S15-006
    element: btn_join_call_session
    region: body_contact
    trigger: click
    action: navigate
    target: S14
    payload: { party_id: "$task.party_id" }
  - id: A-S15-007
    element: btn_view_360
    region: header
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$task.party_id" }
  - id: A-S15-008
    element: internal_checklist_item
    region: body_internal
    trigger: click
    action: mutate
    effects: [checklist.toggle]
  - id: A-S15-009
    element: btn_tool_edit_contact
    region: body_internal
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$task.party_id", tab: "core" }
  - id: A-S15-010
    element: btn_tool_add_tag
    region: body_internal
    trigger: click
    action: open_overlay
    target: M03
    payload: { party_id: "$task.party_id" }
  - id: A-S15-011
    element: btn_back
    region: header
    trigger: click
    action: navigate
    target: S07
```
