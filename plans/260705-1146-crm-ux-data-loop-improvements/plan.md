# Plan — CRM UX & Data-Loop Improvements

**Status:** DONE (all 6 phases implemented 2026-07-05)
**Created:** 2026-07-05
**Design source:** `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` (decisions D1–D4, issues A1–A4, B1–B5, C-group)
**Goal:** Đóng vòng lặp dữ liệu CRM → warehouse và nâng UX cho NV CSKH: đúng việc, đúng lúc, giữ ngữ cảnh, capture dữ liệu tối đa với friction thấp nhất.

## Phases

| # | Phase file | Scope | Depends on | Priority |
|---|---|---|---|---|
| 01 | `phase-01-warehouse-exports-data-loop.md` | D1: 4 export mới (`crm_note`, `crm_tag`+`crm_party_tag`, `crm_party_insight`, `crm_customer_profile.custom`) + staging models `stg_crm__*` + consumption hooks | — | P0 |
| 02 | `phase-02-bulk-resolve-outcome.md` | A3: bind endpoint bulk-resolve, M08 nhận mảng `resolve_task_ids`/`resolve_action_ids`, ghi snapshot vào `custom_fields` | — | P0 |
| 03 | `phase-03-outcome-reason-enum.md` | D2: cột `outcome_reason` + enum 2 tầng, pill UI 2 bước trong M08, ngừng ghi free-text `outcome`, mapping `mart_crm_activity_log` | 02 (cùng đụng M08/activity) | P1 |
| 04 | `phase-04-cockpit-context-queue-snooze.md` | A1: denormalize `value_at_stake_vnd`+`top_affinity_product` vào task claim; A2: queue counter #n/N + "Khách kế →"; A4: snooze trực tiếp task claim | — | P1 |
| 05 | `phase-05-r14-warn-with-ack.md` | D3: banner cảnh báo + nút "Tôi đã xác minh" + audit `r14_ack` vào `custom_fields` + metric override | 04 (cùng đụng template S14) | P1 |
| 06 | `phase-06-capture-ux-quick-wins.md` | P2 UI: custom fields vào Collect cockpit, nút "★ Đúc kết" insight trong M08, B1 band Treo lâu, B2 badge snooze thức dậy, B4 badge nguồn task, toast Collect, tooltip back | 03, 05 (đụng M08 + S14 sau cùng) | P2 |

**Execution order:** 01 ∥ 02 → 03 ∥ 04 → 05 → 06. (01 độc lập hoàn toàn — warehouse side.)

## Acceptance criteria (top-level)

1. Notes/tags/insights/custom-fields NV nhập xuất hiện trong warehouse (parquet + staging model chạy xanh) — vòng lặp dữ liệu khép kín.
2. Một cuộc gọi giải quyết N task/action → 1 lần ghi outcome đóng đủ N (số liệu completion đúng).
3. `contact_outcome` + `outcome_reason` là dữ liệu enum duy nhất; M08 không còn ghi free-text outcome mới.
4. Task claim giữ được 💰 value + 🛍 product; cockpit hiện #n/N; snooze được task claim.
5. R14 `recommended=false` → NV thấy lý do, phải ack mới mở talk-track; override đo được.
6. Mỗi thay đổi UI surface có cập nhật spec tương ứng trong `crm/docs/ui-spec/` (spec là source of truth).

## Constraints

- CRM code chỉ trong `crm/` (hexagonal: port trước adapter, wiring duy nhất ở `composition.py`).
- Export/dbt: orchestration + transformation; dbt node mới cần restart `data_platform` (manifest pre-parsed).
- Mart mới cho CRM đọc: bootstrap serving view (dừng Metabase) + rebuild crm container.
- TIMESTAMPTZ/UTC lưu trữ, ICT hiển thị; VND INTEGER.
- Apply CRM code: `docker compose restart crm` (bind-mounted), không rebuild trừ khi đổi requirements.

## Review notes (2026-07-05)

- **Phase-02 discovery:** backend bulk-resolve đã implement sẵn (helpers, POST handler, async-resolve endpoint, 23 unit tests) — phase chỉ còn 4 việc UI wiring. Effort thấp hơn dự kiến.
- **Migration numbering:** phase-03 = `0035_activity_outcome_reason`, phase-04 = `0036_task_claim_context_fields` (đã sửa collision; renumber theo số trống thực tế lúc triển khai).
- **Follow-up backlog (ngoài 6 phases):** outcome bar S14 hiện chỉ truyền IDs của rail PRIMARY vào bulk-resolve; aggregate thêm SECONDARY rail items để "đóng đủ N" trọn vẹn — chưa nằm trong phase nào, cần thêm khi làm phase-06 hoặc phase riêng.
- **Chốt với user trước khi chạy production phase-01:** note `visibility='private'` loại hẳn khỏi export (recommended) hay mask body.

## Reports

`plans/260705-1146-crm-ux-data-loop-improvements/reports/`
