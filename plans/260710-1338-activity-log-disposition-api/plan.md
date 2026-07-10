# Activity Log: API mịn theo field + tích hợp streamline vào Call-Cockpit

> Nguồn thiết kế: [ux-design-260710-1313-activity-log-api-cockpit-integration-report.md](../reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md) — MỌI nội dung plan này phải khớp report đó, không mở lại quyết định.

## Status
- **P0 — approved 2026-07-10**, làm ngay trước ngày gọi đầu của Sprint Gọi Ra 45 ngày.
- P1-P2 — pending, làm khi sprint gọi đang chạy (tuần 1-2), không block sprint.

## Phases

| # | Phase | File | Scope | Trạng thái |
|---|---|---|---|---|
| 1 | M08 form lightening + quick outcomes | [phase-01-m08-form-lightening-quick-outcomes.md](phase-01-m08-form-lightening-quick-outcomes.md) | pill busy/wrong_number/purchased, outcome-first + accordion "Nâng cao", 3 quick-outcome pill POST thẳng không modal | ✅ DONE 2026-07-10 (reports/phase-01-implementation-report.md; 993 tests pass) |
| 2 | Draft + PATCH + finalize API | [phase-02-draft-patch-finalize-api.md](phase-02-draft-patch-finalize-api.md) | 3 endpoint mới, edit_activity mode, duration tự đo, draft lifecycle | ✅ DONE 2026-07-10 (reports/phase-02-implementation-report.md; 1031 tests pass) |
| 3 | Disposition Strip v2 (state machine T0-T3) | [phase-03-disposition-strip-v2.md](phase-03-disposition-strip-v2.md) | outcome_bar → disposition strip đầy đủ, sheet-up, phím tắt, spec S14 update | P2 — pending |

## Dependencies

- **Song song với `plans/260709-1638-crm-outreach-effort-report`** (mart/schema đo hiệu quả) — KHÔNG duplicate scope: plan đó sở hữu `mart_staff_performance_weekly`, `crm_task.claimed_action_types`, `crm_party_tag.source_activity_id`; plan này chỉ REFERENCE các cột đó (VD `contacts_reached` phải gồm `purchased` — đã ghi trong phase-00 của plan kia, không lặp lại đây).
- File ownership tách bạch: plan này chỉ đụng `crm/src/domain/entities/activity.py`, `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py`, `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html`, `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`, `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`, `crm/src/tests/*`. Plan 260709-1638 đụng `transformation/models/marts/**`, `crm_task`/`crm_party_tag` export. Không có file trùng — chạy song song an toàn.
- Phase 2 phụ thuộc Phase 1 (đảo form + enum `purchased` phải xong trước khi có draft/PATCH dùng enum đó). Phase 3 phụ thuộc Phase 2 (state machine T0-T3 cần draft/finalize API).

## Acceptance criteria (tổng)

- [ ] `CONTACT_OUTCOMES_CALL` có `purchased`; mọi filter `contacts_reached` (kể cả mart bên plan 260709-1638) tương thích enum mới.
- [ ] M08 có đủ 3 pill mới (busy/wrong_number/purchased) ở cả HTML lẫn JS `OUTCOMES.call`.
- [ ] M08 form outcome-first; Step 5 (save-as-note) + insight + Step 6 (thời gian/đơn) nằm trong 1 accordion "Nâng cao" đóng mặc định.
- [ ] Cockpit outcome_bar: bấm ✗ Không bắt / ☎ Bận / ☠ Sai số → POST thẳng `/log-activity`, KHÔNG mở modal, trả fragment (không HX-Redirect) khi `source=call_cockpit`.
- [x] (P1) Draft/PATCH/finalize endpoint hoạt động đúng contract mục III của ux report; `contact_duration_s` tự đo từ `finalize_at − started_at`.
- [x] (P1) M08 có mode `edit_activity` dùng chính PATCH API.
- [ ] (P2) Disposition strip theo state machine T0-T3; spec S14 (`outcome_bar` → `disposition_strip`) cập nhật cùng commit với template.
- [ ] Không có regression: test suite `crm/src/tests/*` hiện tại (test_outcome_reason_enum.py, test_bulk_resolve_endpoint.py, test_claim_context_snooze_r14.py) vẫn pass.

## Câu hỏi mở
- (kế thừa từ ux report) Tỷ lệ dùng thật save-as-note/insight/visibility trong M08 — chờ 2 tuần data sprint rồi quyết cắt hẳn hay giữ trong accordion "Nâng cao". Không chặn P0.
