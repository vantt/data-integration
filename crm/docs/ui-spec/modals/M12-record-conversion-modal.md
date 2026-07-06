---
id: M12
type: modal
name: "Record Conversion Modal"
platforms: [desktop]
hosted_by: [S11]
status: active
design_ref: ""
rules: [R11]
regions: [header, body, actions]
---

# M12 — Record Conversion Modal

## Purpose

Ghi thủ công `converted_order_code` cho campaign target khi NV xác nhận khách đã đặt đơn
(trước khi hệ thống tự khớp — R11). NV nhập order_code từ Sapo, hệ thống validate tồn tại
trong `wh_order_hdr` và tính `converted_revenue_vnd`.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Ghi chuyển đổi: Nguyễn Văn A [✕]"
  body: "Chiến dịch: Win-back Q3 · Mã đơn hàng * [ORD-____________] → Doanh thu: (tự tính từ wh_order_hdr) · Hoặc: [✓] Đơn chưa có — ghi nhận thủ công · Doanh thu ước tính [__________] đ"
  actions: "[Hủy]  [Ghi nhận]"
elements:
  "✕": A-M12-001
  "Hủy": A-M12-002
  "Ghi nhận": A-M12-004
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Ghi chuyển đổi: Nguyễn Văn A [x]                                          │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Chiến dịch: Win-back Q3 · Mã đơn hàng * [ORD-____________] → Doanh thu: (…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Ghi nhận]                                                         │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- default: Order code input empty
- validating: Lookup in wh_order_hdr in-flight
- error: Order code không tìm thấy trong wh_order_hdr

## Interactions

```yaml crm-contract
interactions:
  - id: A-M12-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M12-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M12-003
    element: order_code_input
    region: body
    trigger: blur
    action: mutate
    effects: [order.lookup_revenue, form.revenue.prefill]
  - id: A-M12-004
    element: btn_record
    region: actions
    trigger: click
    guard: "form.order_code != '' || form.manual_revenue != null"
    action: mutate
    effects: [target.converted_order_code.set, target.converted_revenue_vnd.set, target.status.set_converted, modal.close, ui.toast.show]
