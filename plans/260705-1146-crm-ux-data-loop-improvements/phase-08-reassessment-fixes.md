# Phase 08 — Reassessment Fixes (từ đánh giá 2026-07-06)

**Status:** DONE (AI-1,2,3,4,5,6,7,10,11 triển khai 2026-07-06; AI-8 theo dõi nightly + AI-9/AI-12 time-gated/plan riêng còn treo — xem cuối file)  **Priority:** hỗn hợp (xem bảng)  **Depends on:** phases 01–07 (đã DONE)
**Nguồn:** `reports/plan-goal-reassessment-260706-1611-crm-ux-data-loop-report.md`

## Action items

| # | Việc | Ưu tiên | Files | Ghi chú |
|---|------|---------|-------|---------|
| AI-1 | ✅ DONE 2026-07-06 — async-resolve ghi `contact_outcome='pending_reply'` thay free-text. | P0 | `screen_customer_360_activity.py:347` | Phát sinh gap phụ: `task_detail.html:449` chỉ đọc `entry.outcome` → dòng contact_outcome-only hiện "—". Đã fix kèm (fallback `entry.outcome or entry.contact_outcome` + bổ sung label `pending_reply`/`busy`/`wrong_number`/`blocked`). 35 tests pass. |
| AI-2 | ✅ DONE 2026-07-06 (một phần — xem ghi chú) — 8/9 failing tests fixed: tất cả là test/fixture cũ (stale) sau các commit trước, KHÔNG phải hồi quy code (xác minh qua `git log -p`: thiếu 3 filter key mới `adv`/`strategic_tier`/`value_group`, fixture thiếu bảng `wh_customer_tier` mới LEFT JOIN, type-chip chuyển vào "row 2" gấp gọn theo `adv`, CSS class `badge--primary` đã bị xoá, template đọc `request.url.query` cho pagination mà test harness thiếu `request` stub). | P0 | `test_web_templating.py`, `test_worklist_filters.py`, `test_cache_repository_customer_id.py` | `test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit` + `test_approach_script_handler.py` collection error CHỦ Ý loại trừ — thuộc workstream approach-script-codex đang dở, không đụng. Full suite: 783 passed, 1 failed (chỉ còn cái loại trừ này). |
| AI-3 | ✅ DONE 2026-07-06 — r14-ack ghi `script_id` = `ApproachScript.template_version` (không có id per-generation thật, nhưng template_version đúng mục đích D3.4: nhóm override theo phiên bản logic sinh rationale — tốt hơn cả 1 id vô nghĩa). | P1 | `screen_call_cockpit.py` (`meta_dict`), `c360_call_cockpit_panel.html:291-297`, `screen_customer_360_activity.py:384,399` | Agent ban đầu dùng `refreshed_at` làm proxy (chỉ là timestamp, vô dụng cho phân tích) — controller sửa lại dùng field đúng sẵn có trong entity (`template_version`, do 1 workstream song song thêm). 50 tests pass. |
| AI-4 | ✅ DONE 2026-07-06 — R14 unlock chỉ khi `event.detail.successful`; POST fail giữ khoá + báo lỗi nhẹ. | P1 | `c360_call_cockpit_panel.html:292-296` | |
| AI-5 | ✅ DONE 2026-07-06 — "Khách kế →" ẩn khi `queue_total==0` (no queue context); vẫn hiện fallback khi thật sự cuối hàng đợi (`queue_total>0`, hết next item). Spec S14 ghi rõ #n/N chỉ ở đường S01 full-page. | P1 | `call_cockpit.html:70`, `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` | 35 cockpit tests pass. |
| AI-6 | ✅ DONE 2026-07-06 — xác minh `party_insights` đã wire thật (`composition.py:599`, `screen_customer_360_activity.py:235-255`, `party_repository.py:214-217` insert `crm_party_insight`); spec M08 viết lại đúng hành vi hiện tại. | P1 | `crm/docs/ui-spec/modals/M08-log-activity-modal.md` | AC#6: spec là source of truth. |
| AI-7 | ✅ DONE 2026-07-06 — 15 test mới: claim denormalize 💰/🛍, snooze clamp 1-30/doing→open, queue pos auto-correct, r14-ack audit write. | P1 | `crm/src/tests/test_claim_context_snooze_r14.py` (mới) | |
| AI-8 | Theo dõi nightly crm_writeback 2 đêm (07 & 08/07): parquet mới sinh + dbt staging xanh. Nếu ổn → đóng. | P1 | — | Hệ quả sự cố placeholder (`a40974e8`); kiểm tra thủ công hoặc qua health digest. |
| AI-9 | ✅ TÁCH THÀNH PLAN RIÊNG 2026-07-06: `plans/260706-1738-crm-tag-signal-action-queue-consumer/`. Phát hiện thêm khi khảo sát: `stg_crm__party_tag` thiếu `customer_id` (export phase-01 bỏ sót `LEFT JOIN crm_party_identity` mà các export khác đều có) — chặn cứng, cần phase-01 riêng sửa trước. Đã chốt: vip_tier boost priority như VIP tự động, risk → action_type mới `MANUAL_RISK_REVIEW`, sửa customer_id resolution cho cả 4 export CRM luôn. | P2 | → xem plan riêng | — |
| AI-10 | ✅ DONE 2026-07-06 — migration `0038_action_dismissal_ttl` thêm bảng mới `crm_action_dismissal` (PK party_id+action_type, TTL 30d) — TÁCH khỏi `crm_action_state` cũ (giữ nguyên, khác grain: theo action_id, vẫn phục vụ snooze + reason rail). `dismiss()` resolve party_id/action_type qua cùng join `list_all_action_queue()` dùng, ghi cả 2 bảng (dual-write); best-effort — resolve fail thì im lặng bỏ qua, hành vi cũ vẫn chạy (fallback an toàn, controller verified). `cache_repository.py` JOIN lọc dismissal còn hạn ở cả customer-level và SKU-level. 13 test mới. | P2 | `action_state_repository.py`, `cache_repository.py`, `crm/migrations/0038_*`, `20-domain-rules.md` (R15) | 3 endpoint gọi `dismiss()` sẵn có không đổi signature — hưởng lợi tự động. |
| AI-11 | ✅ DONE 2026-07-06 — `GET /tasks/dismissed` (đọc-only, link từ S07 Tasks Board) liệt kê dismissal đang hiệu lực: tên khách (fallback SĐT/"(chưa xác định)" theo phase-09), loại việc (label ngắn qua `bdg_label`), ai bỏ, khi nào, còn ẩn đến ngày. | P2 | `screen_tasks_board.py`, template mới `dismissed_actions.html`, spec S07 | ui-spec validate: 0 lỗi. Full suite: 785 passed, 0 failed (controller re-verified). |
| AI-12 | Pilot `outcome_reason` passive: đến ~2026-07-20 chạy query phân bố reason trên `mart_crm_activity_log` (tỉ lệ `other`, giá trị 0-usage, phân bố theo channel) → đề xuất thêm/bớt giá trị → user duyệt → khóa mapping mart. Trước đó KHÔNG build dashboard downstream phụ thuộc `outcome_reason`. | P2 (đến hạn 20/07) | — (query ad-hoc, report vào `reports/`) | Đã chốt 2026-07-06: passive, không cần manager thu thập. |

## Quyết định đã chốt (user, 2026-07-06)

1. **B5 dismiss:** đổi sang `(party_id, action_type)` + **TTL 30 ngày** (hợp chu kỳ mua lại mỹ phẩm; dismiss nhầm cũng không mất khách quá 1 tháng). → AI-10.
2. **Manager view dismissed:** **Có**, dạng view đơn giản — minh bạch, chống dismiss né việc, NV yên tâm dismiss vì có vết. → AI-11.
3. **Pilot `outcome_reason`:** **Passive** — ~2026-07-20 chạy query phân bố reason, đề xuất hiệu chỉnh, user duyệt rồi mới khóa mapping mart. Không build dashboard phụ thuộc reason trước ngày đó. → AI-12.
4. **Pre-seed enum theo kinh nghiệm (user yêu cầu, ĐÃ LÀM 2026-07-06):** thêm 3 giá trị `still_stocked` (Chưa dùng hết — điều chỉnh chu kỳ replenishment), `wait_promo` (Chờ khuyến mãi — trigger khi có promo), `irritation` (Kích ứng/không hợp da — escalate chất lượng, không upsell cùng dòng). Sửa `activity.py` VALID_OUTCOME_REASONS (8→11), pill M08, spec M08, tests (27 passed), đã restart crm. Mart pass-through, không cần sửa.

## Validation

- AI-1: unit test async-resolve ghi `contact_outcome='pending_reply'`, không ghi `outcome`; mart đếm được attempt async trong `is_reached=false`.
- AI-2: `pytest src/tests` trong container crm → 0 failed, 0 error.
- AI-3/4: r14-ack row có đủ 3 keys; POST fail → vẫn khoá.
- AI-5/6: spec khớp code (chạy ui-spec validate nếu có).
- AI-8: 2 đêm parquet + dbt xanh.

## Risks & rollback

- AI-1 đổi giá trị ghi vào `crm_activity_log`: hành vi cũ đọc `outcome` legacy vẫn hiển thị được (giữ read path). Rollback = revert commit.
- AI-2 nhóm (c) dính refactor approach-script đang dở trong working tree — phối hợp với session đang làm refactor đó, không tự ý revert file uncommitted.
