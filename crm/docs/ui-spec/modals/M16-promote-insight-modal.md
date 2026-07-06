---
id: M16
type: modal
name: "Promote / Create Insight Modal"
platforms: [desktop]
hosted_by: [P01, P05]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M16 — Promote / Create Insight Modal

## Purpose

Tạo mới hoặc chỉnh sửa `crm_party_insight` — nhận định được rep đúc kết từ nhiều lần tương tác
với khách. Khác crm_note ở chỗ: insight là kết luận tích lũy, không phải sự kiện đơn lẻ.

Có 2 entry points:
- Từ P05 (Notes): "★ Đúc kết thành insight" → prefill body từ note, link source_note_id
- Từ P01 (Insight Panel): "+ Thêm insight" → form trống

Insights surface trong P01 bên cạnh warehouse insights, giúp rep khác và future reps hiểu khách.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Insight: Nguyễn Văn A [✕]"
  body: "Loại insight * [Persona ▼] · Nội dung * [Mua cho shop tại Q7, không phải cá nhân. Cần báo giá sỉ thay vì giá lẻ.] · Độ tin cậy [● Cao ○ Trung bình ○ Thấp] · Nguồn: Ghi chú #45: Gọi lần 3: nói đang mua cho..."
  actions: "[Hủy]  [Lưu insight]"
elements:
  "✕": A-M16-001
  "Hủy": A-M16-002
  "Lưu insight": A-M16-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Insight: Nguyễn Văn A [x]                                                 │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Loại insight * [Persona v] · Nội dung * [Mua cho shop tại Q7, không phải …│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Lưu insight]                                                      │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Layout — Create / Promote

## Insight Types

| Value | Nhãn VI | Ví dụ |
|-------|---------|-------|
| `persona` | Persona | "Mua cho shop Q7, cần giá sỉ" |
| `buying_pattern` | Hành vi mua | "Mua mạnh T10–T12, yếu T4–T6" |
| `decision_style` | Phong cách QĐ | "Hay do dự, cần follow up ≥3 lần" |
| `life_event` | Sự kiện đời sống | "Đang có bầu, tránh push đến T9/2026" |
| `relationship` | Mối quan hệ | "Hay mua cùng bạn tên Lan" |
| `advocate_signal` | Tiềm năng Advocate | "Hay share Facebook khi hài lòng" |

## Confidence Levels

| Value | Meaning |
|-------|---------|
| `high` | Đã xác nhận trực tiếp qua nhiều lần |
| `medium` | Quan sát từ 1–2 lần, chưa confirm |
| `low` | Suy đoán, cần kiểm chứng thêm |

## States

- create: Form trống, không có source_note
- promote: Body prefilled từ note, source_note_id set, nguồn note hiển thị readonly
- edit: Prefilled từ existing insight (insight_id passed)
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M16-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M16-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M16-003
    element: btn_save
    region: actions
    trigger: click
    guard: "form.insight_type != null && form.body != ''"
    action: mutate
    effects: [party_insight.save, modal.close, ui.toast.show, P01.rep_insights.reload]
```
