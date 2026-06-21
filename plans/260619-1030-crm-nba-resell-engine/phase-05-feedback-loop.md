# Phase 05 — Feedback Loop + Consent

> Status: ⛔ BLOCKED (chờ P4)
> Phụ thuộc: P4 · Context: [`discussion.md`](./discussion.md) §13, §5

## Mục tiêu

Đóng vòng lặp: outcome CS thao tác (M08) → `crm_action_state` → quay lại warehouse → tinh chỉnh queue ngày sau. Thêm consent per-channel (chặn DNC trước khi gọi hàng loạt). Biến playbook tĩnh thành hệ thống sống.

## Phạm vi (locked)

```
M08 outcome → crm_action_state → reverse-ETL ngược → warehouse
→ điều chỉnh: vừa liên lạc thì hạ ưu tiên; action hay bị "không liên quan" → sửa rule
```

- **Consent per-channel**: phone / email / zalo riêng; gate ở chặng ② (P2).
- **`crm_action_state`**: hoàn thiện schema (dismiss/snooze/done/outcome) + consume.
- **Reverse path**: state CRM → warehouse (chiều ngược reverse-ETL hiện có).

## Related code files

- Sửa: migration `crm/.../0015_action_state` (hoàn thiện + consume)
- Tạo: reverse sync CRM state → warehouse (đối xứng `reverse_etl_warehouse_to_crm.py`)
- Nối: M08 outcome ghi action_state
- Consent: thêm field per-channel (crm.db) + UI ghi từ M08 ("khách xin đừng gọi")

## Todo (draft)

- [ ] Hoàn thiện crm_action_state + consume trong scoring P2
- [ ] M08 outcome → action_state
- [ ] Reverse sync state → warehouse
- [ ] Consent per-channel + gate
- [ ] Đo: action taken rate, "không liên quan" rate → tín hiệu sửa rule

## Success criteria

- Khách vừa được xử lý KHÔNG xuất hiện lại đầu queue hôm sau.
- DNC được tôn trọng tuyệt đối across kênh.
- Có metric efficacy để tinh chỉnh rule.

## Open

- Tần suất reverse sync (real-time vs nightly).
- Định nghĩa "efficacy" + ngưỡng cảnh báo rule kém.
