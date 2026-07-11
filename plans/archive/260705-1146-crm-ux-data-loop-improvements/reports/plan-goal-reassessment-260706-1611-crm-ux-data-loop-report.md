# Đánh giá lại mục tiêu plan — CRM UX & Data-Loop (260705-1146)

**Ngày:** 2026-07-06 · **Người thực hiện:** re-verification session (code + warehouse + tests thực tế)
**Kết luận:** ~85–90% mục tiêu đạt thật. Cả 7 phases có code thật, spec cập nhật, dữ liệu chảy về warehouse đêm 06/07. Chưa "hoàn toàn": 6 điểm chưa trọn (chi tiết dưới), 2 điểm ảnh hưởng trực tiếp chất lượng dữ liệu về sau.

## Phương pháp

- Đọc design doc + 7 phase files, đối chiếu từng acceptance criterion với code hiện tại.
- Chạy test trong container `crm`: 85/85 tests mới của plan pass; full suite 749 passed / **9 failed + 1 collection error**.
- Kiểm tra parquet lake (`app_data/data_lake/crm_export/`) + dbt run_results mới nhất + mart.

## Xác minh ĐẠT (bằng chứng)

| Mục | Bằng chứng |
|---|---|
| 5 export mới sinh parquet thật | lake 06/07 03:01: `crm_customer_profile_custom.parquet` 101KB, `crm_note/date=20260705/batch_200155.parquet`, tag/party_tag; private notes bị loại |
| dbt xanh | run_results mới nhất: 4 staging models success + schema tests pass + `mart_crm_activity_log` success |
| Mart D2 | `marts/customer/mart_crm_activity_log.sql:22` `outcome_reason`, `:30` `is_reached` |
| Bulk-resolve + snapshot D4 | `modal_log_activity.html:76-103` hidden inputs + "Sẽ đóng N task · M hành động"; tests `test_bulk_resolve_endpoint.py` pass |
| Enum 2 tầng server-side | `activity_service.py:53-69` validate theo kênh, refused bắt buộc reason (HTTP 400) |
| Phase-07 secondary tick | `c360_call_cockpit_panel.html:918-919` tick "đã nói" → gộp resolve IDs |
| Queue #n/N + Khách kế | `screen_call_cockpit.py:140-168` auto-derive pos; `_wl_row.html:159` S01 truyền `queue_ids` |
| Snooze task | `screen_worklist.py:370-398` PATCH `/tasks/{id}/snooze`, ICT-anchored, doing→open |
| R14 warn-with-ack | banner + `s14-locked` + `POST /r14-ack` ghi audit `r14_ack` (`screen_customer_360_activity.py:370-400`) |
| Phase-06 quick wins | badge VIP/GOLD (`_wl_bands.html:52-55`), wake badge (`_wl_row.html:73-75`), AUTO/💰/🛍/snooze dropdown (`_wl_row.html:212-286`), toast ✓ Đã lưu, tooltip back, collect skin_type/preferred_contact (`c360_call_cockpit_panel.html:91-92`), ★ Đúc kết wired (`5dce0c37`) |

## Điểm CHƯA TRỌN

1. **Pipeline từng chết dù plan DONE:** `ensure_crm_export_placeholder.py` thiếu 5 bảng mới → mọi dbt build realtime/incremental fail vĩnh viễn tới sáng 06/07 (fix `a40974e8`). Bài học: DONE phải kèm bằng chứng pipeline chạy, không chỉ code merge. Cần theo dõi thêm 1–2 đêm nightly.
2. **Free-text `outcome` chưa chết hẳn (vi phạm AC#3):** async-resolve vẫn ghi `"outcome": "async_sent"` (`screen_customer_360_activity.py:347`) thay vì `contact_outcome='pending_reply'` → attempt async có `contact_outcome=NULL`, mart `is_reached` mù kênh messaging.
3. **r14-ack thiếu `script_id`:** registry D4 khai 3 keys, endpoint chỉ ghi 2 → sau này không phân tích được override theo script; chưa có metric override rate.
4. **Test suite KHÔNG xanh:** 9 failed + 1 import error. 6 failures worklist templating/filters (`'request' is undefined`, filter defaults lệch key) là hồi quy quanh vùng plan đụng; import error `wire_approach_script_router` thuộc refactor approach-script dở. Phases 04/05 không có test riêng (claim context, snooze, queue nav, r14 ack) dù phase files có bảng test.
5. **Queue #n/N chỉ sống trên đường S01 full-page;** C360 tab không có wiring (chấp nhận được — không phải queue session, nhưng cần ghi rõ spec); "Khách kế" fallback vẫn render khi không có queue (plan nói ẩn). R14 unlock chạy cả khi POST audit fail (`hx-on::after-request` không check status) → có thể mở khóa không để lại vết.
6. **Spec M08 stale 1 đoạn:** dòng ~260 vẫn ghi "party_insights not wired… deferred" trong khi `5dce0c37` đã wire (vi phạm nhẹ AC#6).

## Vòng lặp dữ liệu: khép đến staging, CHƯA quay

Không consumer nào đọc `stg_crm__party_tag` / `stg_crm__party_insight` / `stg_crm__customer_profile_custom` (chủ đích YAGNI phase-01). Mắt xích cuối của design — "NV thấy dữ liệu mình nhập tạo gợi ý tốt hơn → động lực nhập tăng" — chưa xảy ra. Nền staging sạch (enum chuẩn, TIMESTAMPTZ, tests) đủ tốt để build mart tiếp mà không sửa nền. `crm_party_insight` parquet rỗng (feature mới 1 ngày, bình thường).

## Chấm theo acceptance criteria

| # | Tiêu chí | Kết quả |
|---|---|---|
| 1 | Data loop staging xanh | ✅ (từ sáng 06/07 sau fix placeholder) |
| 2 | 1 outcome đóng N | ✅ |
| 3 | Enum duy nhất | ⚠️ 90% — async còn free-text |
| 4 | 💰/🛍 + #n/N + snooze | ⚠️ #n/N chỉ đường S01 |
| 5 | R14 ack đo được | ⚠️ thiếu script_id, chưa metric |
| 6 | Spec source of truth | ⚠️ 95% — 1 đoạn M08 stale |

→ Action items: `phase-08-reassessment-fixes.md`.

## Câu hỏi chưa giải quyết

1. **B5 dismiss memory:** dismiss gắn `action_id`, warehouse sinh id mới hàng tuần → việc đã bỏ quay lại. Chuyển sang dismiss theo `(party_id, action_type)` + TTL? TTL bao lâu? Manager có xem danh sách dismissed?
2. **Pilot `outcome_reason`:** ai thu thập feedback 2 tuần trước khi khóa mapping mart? Hay khóa ngay / thu thập passive qua query?
