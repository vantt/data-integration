# Plan — CRM UX & Data-Loop Improvements

**Status:** DONE — phases 01–09 tất cả DONE (phase 08+09 triển khai 2026-07-06 sau đánh giá lại). Còn treo: AI-8 (1/2 đêm nightly xác nhận xanh, xem chi tiết phase-08), AI-12 (pilot outcome_reason đến 2026-07-20) — không phải lỗi, chỉ time-gated ngoài scope kỹ thuật ngay lúc này. AI-9 đã DONE, tách plan riêng, archived: `plans/archive/260706-1738-crm-tag-signal-action-queue-consumer/`. Full CRM suite: 785 passed, 0 failed (1 test loại trừ thuộc workstream khác).
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
| 07 | `phase-07-rail-secondary-bulk-resolve.md` | Follow-up phase-02: gom `rail_secondary` items (tick "đã nói") vào bulk-resolve set cùng `rail_primary` | 02, 06 (đụng cùng cockpit template) | P2 |
| 08 | `phase-08-reassessment-fixes.md` | ✅ DONE 06/07 — async_sent→enum, 8 test đỏ fixed, script_id r14-ack (dùng template_version), unlock-on-fail, spec stale fixed, tests 04/05 thêm, B5 dismiss TTL 30d + manager view S07. Treo: AI-8/9/12 (time-gated/plan riêng) | 01–07 | P0–P2 |
| 09 | `phase-09-worklist-label-clarity.md` | ✅ DONE 06/07 — badge action_type dùng label ngắn VN, bỏ hiển thị customer_key hash (fallback SĐT/"(chưa xác định)"), Dọn→Hủy, icon 📅 phân biệt Dời hạn khỏi ⏰, Mở hồ sơ→Xem 360, Gọi chế độ→Gọi | — | P1 |

**Execution order:** 01 ∥ 02 → 03 ∥ 04 → 05 → 06 → 07.

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
- **Follow-up backlog:** RESOLVED bằng phase-07 (2026-07-05) — outcome bar S14 giờ gom `rail_secondary` items đã tick "đã nói" vào bulk-resolve cùng `rail_primary`.
- **Chốt với user (2026-07-05):** note `visibility='private'` loại hẳn khỏi export (không mask body). Đã confirm, khớp default implementation.

## Review notes (2026-07-06 — đánh giá lại)

- Pipeline writeback từng fail vĩnh viễn dù plan DONE (placeholder schemas thiếu 5 bảng, fix `a40974e8` sáng 06/07) — bài học: DONE cần bằng chứng pipeline chạy, không chỉ code merge.
- AC#3 chưa trọn: async-resolve còn ghi free-text `outcome='async_sent'`. AC#5: r14-ack thiếu `script_id`. AC#6: M08 spec stale 1 đoạn. Test suite 9 failed + 1 error. → phase-08.
- Vòng lặp dữ liệu khép đến staging nhưng CHƯA có consumer — mắt xích "dữ liệu nhập → gợi ý tốt hơn" chưa quay (AI-9).

## Reports

`plans/260705-1146-crm-ux-data-loop-improvements/reports/`

- `plan-goal-reassessment-260706-1611-crm-ux-data-loop-report.md` — đánh giá lại toàn diện 2026-07-06 (nguồn phase-08)
