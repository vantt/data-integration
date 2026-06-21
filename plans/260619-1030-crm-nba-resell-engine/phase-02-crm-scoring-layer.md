# Phase 02 — CRM Secondary Scoring Layer

> Status: ⛔ BLOCKED (chờ §14.1 trọng số, §14.5 rules repr)
> Phụ thuộc: P1 · Chặng ② trong pipeline
> Context: [`discussion.md`](./discussion.md) §3, §4, §5, §6, §12

## Mục tiêu

Lớp **fusion** thuần CRM (app-side): lấy `base_priority_score` (warehouse) + state sống + dữ liệu định tính rep → `final_score` + lý do điều chỉnh. Đây là phần warehouse KHÔNG làm được.

## Key insights (phép thử ranh giới §4)

CRM scoring đảm nhận điều cần: STATE hôm nay, dữ liệu ĐỊNH TÍNH rep nhập, hoặc trọng số business chỉnh hàng tuần.

## Phạm vi (locked) — mẫu "điểm nền + điều chỉnh" (§5)

```
final_score = base_priority_score
            − vừa liên lạc trong N ngày        (crm_activity)
            − đang có task mở                  (crm_action_state)
            + rep insight boost                (crm_party_insight / crm_note)
            × consent_gate (0 nếu DNC)         (consent per-channel)
            × campaign_suppression             (tránh đụng blast)
```

- Khách chưa có state → `final_score ≈ base_score` (graceful).
- Mỗi delta sinh 1 `adjustment_reason` (cấu trúc) → nối vào chuỗi explainability.

## Related code files

- Tạo: module scoring trong `crm/src/...` (đặt cạnh domain customer; tên snake_case Python)
- Đọc: cache.db (`wh_customer_insight`, `wh_action_queue`), crm.db (`crm_activity`, `crm_action_state`, `crm_party_insight`, `crm_note`, consent)
- Config trọng số: file/bảng (quyết định §14.5)

## Todo (draft)

- [ ] Chốt trọng số ở đâu + dạng công thức (§14.1) ← gate
- [ ] Định nghĩa danh sách adjustment + nguồn dữ liệu
- [ ] Implement scoring service (đọc-only crm.db/cache.db, KHÔNG ghi)
- [ ] Unit test các nhánh điều chỉnh + graceful cold-start

## Success criteria

- `final_score` + `adjustment_reasons[]` tính được cho mọi khách có base score.
- Khách vừa được liên lạc bị hạ ưu tiên đúng; DNC bị gate về 0.

## Open

- Cộng tuyến tính vs nhân/gate cho `final_score` (§14.1).
- Trọng số config-file vs UI chỉnh runtime (§14.1).
- Ngưỡng N ngày "vừa liên lạc".
