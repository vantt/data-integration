# ui-spec content migration — FINAL: toàn corpus hoàn tất

**Date:** 2026-07-14 · **Status:** DONE — 40/40 surface có ui-layout fence đã sang `content:` model

## Tổng kết chuỗi công việc (2026-07-13 → 07-14)

1. **Nền tảng** (plan `260713-1912`): single-writer `layout-schema.mjs`, `content:` 15 primitives, `row_heights`, viewport frame, legend vào inspector rail — tôi tự làm.
2. **Wave 1** (`260714-0757`): S01 S02 S03 + `tabs actions:` per-label — tôi tự làm (định hình pattern).
3. **Recipe §8b** agent-runnable + **wave 3 pilot** (S07 S15 M16) — Sonnet agent, chứng minh skill tự đứng.
4. **Batch 1–5** — Sonnet agents theo recipe: S04-S06 · S08-S13 · P02-P06+O01-O03 · M01-M07 · M09-M14.

## Kiểm chứng cuối (độc lập, main model chạy lại)

- `grep -rl "^samples:"` screens/modals/panels/overlays/components → **0 file**.
- validate: **0 errors, 0 warnings** · verify-runtime: **PASS** (54 surfaces, 6 flows) · fixture regression: PASS.
- chip-audit: **Surfaces 40 · Tokens 190 · Mapped 190 · Unmapped 0**.
- Vision QA: mỗi batch spot-check ≥1 PNG (S05 S09 P04 M03 + wave trước S14 S03 S01 S02 M08 P01 M01 M16 S07 S15) — đạt checklist §11.

## Tool bug tìm ra & sửa trong quá trình (batch-2 agent phát hiện)

Fence YAML hỏng → `extractLayout()` trả null → validate/build silent-skip, ASCII cũ giữ nguyên, VR-LAYOUT-PARSE là dead code. Fix: `layoutFenceInfo()` (extract-layout.mjs) phân biệt no-fence/broken-fence; VR-LAYOUT-PARSE **warn→error**; build.mjs skip có cảnh báo; +4 unit test; docs cập nhật kèm trap YAML flow-style.

## Gaps contract do agents flag (KHÔNG sửa contract, chờ quyết)

| Surface | Gap |
|---|---|
| S09 | nút "Lưu" topbar không có interaction trong contract (hiển thị display-only) |
| S11 | `filter_assignee` (A-S11-006) không có affordance trong layout model |
| S12 | label "Xem leads" (A-S12-004/005) do agent đặt từ tên element — cần xác nhận wording |
| M03 | label "+ Tạo tag mới" suy từ placeholder — cần xác nhận wording |
| P02 | A-P02-002 khai region toolbar nhưng payload `$order.order_code` ngụ ý per-row — mâu thuẫn có sẵn |

## Unresolved

1. 5 gap contract trên — cần user duyệt từng cái (sửa contract là scope riêng).
2. **Chưa commit** — dồn: skill upgrade (schema/renderer/validator/docs/tests) + 40 spec migrations + plans/reports. Lưu ý S14/P01 từng có sửa đổi uncommitted của user trước chuỗi này, giờ trộn chung trong file.
