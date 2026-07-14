---
id: M14
type: modal
name: "Create Tag Modal"
platforms: [desktop]
hosted_by: [S13, M03]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M14 — Create Tag Modal

## Purpose

Tạo tag mới trong `crm_tag`. Dùng từ Settings (S13) hoặc inline từ Tag Management Modal (M03).
Tag có name (slug), display_label, category (enum chuẩn — selectbox), và optional color.
Sau khi tạo, tag khả dụng ngay trong toàn hệ thống.

Category là enum cố định (selectbox, không cho nhập tay) để warehouse có thể group tags khi phân tích.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
content:
  header:
    - row:
        - { h: "Tạo tag mới" }
        - { btn: "✕", action: A-M14-001 }
  body:
    - row:
        - { text: "Tag name (slug) *" }
        - { input: "vip-repeat" }
    - row:
        - { text: "Nhãn hiển thị *" }
        - { input: "VIP Repeat" }
    - row:
        - { text: "Phân loại *" }
        - { select: "Phân tầng VIP" }
    - text: "Màu (optional)"
    - checklist: ["[x] Xanh", "Đỏ", "Vàng"]
  actions:
    - row:
        - { btn: "Hủy", action: A-M14-002 }
        - { btn: "Tạo tag", action: A-M14-003, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tạo tag mới [x]                                                           │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Tag name (slug) * [input: vip-repeat] · Nhãn hiển thị * [input: VIP Repea…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Tạo tag]                                                           │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Tag Category Enum

| Value | Nhãn VI | Dùng cho |
|-------|---------|---------|
| `behavioral` | Hành vi mua | Hay mua cuối tuần, thích flash sale |
| `demographic` | Đặc điểm KH | Doanh nghiệp, cá nhân, bà mẹ bỉm sữa |
| `preference` | Sở thích SP | Thích dòng gentle, không dùng retinol |
| `vip_tier` | Phân tầng VIP | Gold, Silver, Wholesale |
| `risk` | Rủi ro | Nợ xấu, hay hoàn hàng |
| `source` | Nguồn gốc | Từ ads, referral, walk-in |

## States

- default: Form trống
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M14-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M14-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M14-003
    element: btn_create_tag
    region: actions
    trigger: click
    guard: "form.name != '' && form.display_label != '' && form.category != null"
    action: mutate
    effects: [tag.create, modal.close, ui.toast.show]
```
