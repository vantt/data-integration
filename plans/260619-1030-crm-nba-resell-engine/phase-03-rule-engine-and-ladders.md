# Phase 03 — Rule Engine + Objective & Contactability Ladders

> Status: ⛔ BLOCKED (chờ §14.2 objective ladder, §14.3 contactability state)
> Phụ thuộc: P1, P2 · Chặng ③ trong pipeline
> Context: [`discussion.md`](./discussion.md) §3, §7, §8, §9, §10

## Mục tiêu

Rule engine config-driven: lấy `scored_candidates` (P2) + objective ladder + contactability ladder → chốt **1 action chính + phương án thay thế + reason đầy đủ**. Declarative, priority-ordered, first-match-wins. KHÔNG hard-code, KHÔNG ML (YAGNI).

## Key insights

- Objective ladder = mục tiêu ưu tiên cao nhất CHƯA bị chặn thắng (§7).
- Contactability ladder = logic **có state** bên trong action (phone→email→zalo), cần nhớ "đã thử kênh nào, bao lâu chưa phản hồi" (§8).
- Mỗi gợi ý mang reason code cấu trúc → ghép chuỗi 3 chặng cho CS (§10).

## Phạm vi (locked)

- **Objective ladder** (§7): T0 nền tảng liên lạc → T1 rủi ro/quan hệ → T2 tái bán đúng lúc → T3 tăng trưởng.
- **Contactability ladder** (§8): fallback tuần tự + nhảy về T0 nếu không có kênh.
- **Rule store**: dạng DATA (bảng/config), versioned, business sửa được.
- **Output**: `{primary_action, alternatives[], full_reason}`.

## Related code files

- Tạo: rule engine module trong `crm/src/...`
- Tạo/sửa: rule config store (DB table vs YAML — §14.5)
- Đọc/ghi state ladder: `crm_action_state` (schema — §14.3)

## Todo (draft)

- [ ] Chốt objective ladder + ưu tiên cứng (§14.2) ← gate
- [ ] Chốt contactability state schema (§14.3) ← gate
- [ ] Chốt rules representation (§14.5)
- [ ] Implement engine (priority-ordered, first-match) + reason assembler
- [ ] Test: ladder fallback qua nhiều ngày; tie-break giữa objectives

## Success criteria

- Mỗi khách có ≥1 candidate → ra đúng 1 primary action + alternatives + chuỗi reason đầy đủ.
- Đổi 1 rule trong config → đổi output mà KHÔNG cần rebuild dbt/redeploy nặng.

## Open

- VIP-at-risk có LUÔN thắng overdue-reorder? (§14.2)
- Contactability state schema (§14.3).
- DB table vs YAML cho rules (§14.5).
