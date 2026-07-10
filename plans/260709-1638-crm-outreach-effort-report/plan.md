# Báo cáo hiệu quả tiếp cận khách hàng — đo theo nỗ lực & thông tin thu thập (KHÔNG theo đơn hàng)

> Status: Phase 0-3 DONE 2026-07-10/11 — Phase 0 (mart 12 cột mới, contacts_reached định nghĩa đổi; reports/phase-00-implementation-report.md) + Phase 1 (migrations 0043/0044 production, exports+staging+suppression; reports/phase-01-implementation-report.md) + Phase 2 (`int_crm_outreach_effort_events`, grain task_id×action_type; reports/phase-02-implementation-report.md) + Phase 3 (`mart_crm_outreach_effort_by_action_weekly`; reports/phase-03-implementation-report.md). Post-implementation fix 2026-07-11: Phase 2's `staff_user_id` was wired from the linked activity's staff (NULL for ~all rows pre-first-call) instead of `crm_task.assignee_user_id` as spec'd — corrected in `int_crm_outreach_effort_events.sql`, Phase 3's redundant task-table re-join for that column removed, both models rebuilt+retested (dbt run/test PASS, mart now shows real `staff_key` on all 4 rows instead of near-all-NULL). Phase 4 Track A dashboard DONE 2026-07-10 — deployed sau khi serving-view blocker (báo cáo phase-04 ban đầu BLOCKED) được fix cùng ngày; xác nhận sống qua Metabase log (dashboard id 147, query 200/202 lúc 22:54). Phase 4 Track B card vẫn pending (chờ vài tuần dữ liệu action_type sau cutover + serving-view bootstrap).
> Bối cảnh: `mart_staff_performance_weekly` hiện có (staff × tuần: activities, reach_rate, tasks, orders_sold, revenue) nhưng KHÔNG tách theo action_type, và không đo "thông tin mới thu thập" (tag sức khỏe, note outcome). Đo theo đơn hàng hiện không đáng tin vì sales đang rất ế (xem hội thoại 2026-07-09). Cần đo bằng **leading indicator**: nỗ lực gọi + reach rate + thông tin/tình trạng khách thu thập được (tag `health_concern`, note `outcome`), tách theo `action_type` khi có thể.

## Sự thật đã xác minh (không phải giả định)

1. **`crm_task` KHÔNG có cột `action_type`.** Với luồng claim hiện tại (`action_queue_claim`, chiếm đa số) — `source_ref = party_id`, không phải action_id. 1 task claim = TOÀN BỘ action đang chờ của khách đó gộp lại; **action_type không được lưu lại**, chỉ tính lại real-time lúc render (`screen_task_detail.py:138-142`). ⇒ Không thể tách hiệu quả theo action_type cho các claim đã xảy ra trong quá khứ — chỉ có thể fix-forward.
2. **`crm_activity_log` không có cột nối tới action/action_type** — chỉ có `task_id`. Muốn biết activity nào ứng với action_type nào phải đi qua task, mà task (claim flow) đã mất thông tin action_type như mục 1.
3. **`crm_party_tag` không có cột nối tới activity/task nào cả** — 1 tag sức khỏe gắn được vào khách bất cứ lúc nào, không biết gắn trong bối cảnh cuộc gọi nào. `TagService.attach_tag()` (`crm/src/application/tag_service.py:30-52`) không nhận tham số nguồn gốc.
4. **Điểm sáng: `note_type='outcome'` đã là default thật, đang chạy** — form "Log Activity" (M08, `screen_customer_360_activity.py:181`) mặc định lưu note với `note_type='outcome'` và `source_activity_id` = activity vừa tạo (`:266-275`). Đây là mảnh dữ liệu "thông tin thu thập" đã có sẵn, đáng tin, không cần sửa gì.
5. **4 staging model đã tồn tại đầy đủ**: `stg_crm__task`, `stg_crm__activity_log`, `stg_crm__note`, `stg_crm__party_tag` — không cần tạo mới nguồn. Export qua Dagster asset `crm_writeback_assets.py` (task/note = incremental, party_tag = snapshot, activity_log = incremental).
6. **Gap export có sẵn (chưa liên quan action_type)**: `crm_task_export` + `stg_crm__task.sql` đang bỏ sót cột `outcome, task_kind, channel, value_at_stake_vnd, top_affinity_product` dù đã tồn tại trong `crm_task` — cần bổ sung vì `channel` (phone/zalo/sms) hữu ích cho báo cáo effort.
7. **Bridge party_id ↔ customer_key đã có sẵn**, không cần xây: `crm_party_identity(identity_type='sapo_customer')`.

## Quyết định kiến trúc (đọc kỹ trước khi implement)

Vì action_type không lưu được cho các claim quá khứ, chia làm **2 track độc lập**, ship track A trước, không chờ track B:

- **Track A — ship ngay, không đổi schema**: mở rộng `mart_staff_performance_weekly` thêm cột "thông tin thu thập" (note outcome, tag health_concern mới, channel mix). Đo được NGAY hôm nay, không tách action_type, chỉ theo staff × tuần.
- **Track B — cần 2 cột mới, chỉ đúng từ ngày ship trở đi**: thêm `crm_task.claimed_action_types` (JSON snapshot lúc claim) + `crm_party_tag.source_activity_id` (nối tag về đúng cuộc gọi) → mart mới tách theo `(staff, tuần, action_type)`. Lịch sử trước ngày cutover sẽ KHÔNG có action_type (NULL), phải nói rõ trong dashboard, không suy diễn ngược.

**Không làm**: không cố gắng backfill action_type cho các task/tag đã tồn tại — dữ liệu gốc không đủ để suy ngược chính xác (1 claim có thể gộp nhiều action_type, không có cách nào tách lại đúng).

## Bổ sung 2026-07-10 — plan này là hệ đo của "Sprint Gọi Ra 45 ngày"

> Nguồn: `plans/reports/strategy-advisor-260710-1202-outbound-call-sprint-goal-kpi-report.md`. Sprint gọi ~203 khách (142 OVERDUE/DUE_SOON + 61 SILVER/GOLD/VIP churned), tem QR chưa sản xuất được → **kết bạn Zalo trong cuộc gọi = capture thay tem**. Plan này phải đo được phễu: quay số → reach → conversation → (Zalo connect / hứa mua / đơn 7 ngày).

Mapping KPI sprint → nơi đo (sự thật đã verify trong code):

| KPI sprint | Nguồn dữ liệu | Trạng thái | Phase |
|---|---|---|---|
| Cuộc gọi/tuần (dial, kể cả không nghe máy) | `stg_crm__activity_log` direction='out', channel_type='call' | ✅ có sẵn, cần cột `calls_dialed` riêng (activities_outbound đang gộp mọi channel) | 0 |
| Reach rate | `contact_outcome` — enum call: answered/no_answer/busy/wrong_number/callback/refused | ⚠️ định nghĩa `contacts_reached` hiện tại (`answered,replied,met`) **bỏ sót `callback` + `refused`** — đều là người thật nghe máy | 0 |
| Conversation rate | `contact_duration_s` (đã có) + note outcome đính activity | ✅ derive được: answered AND (duration ≥60s OR có outcome note) | 0 |
| SĐT chết (làm sạch danh sách) | `contact_outcome='wrong_number'` | ✅ enum có, cần cột đếm | 0 |
| Zalo connect (capture thay tem) | ❌ chưa tồn tại ở đâu | cần checkbox "Đã kết bạn Zalo" trong Log Activity → `custom_fields.zalo_connected` (JSON có sẵn, không đổi schema DB) + export + cột mart | 1 |
| "Đừng gọi nữa" (suppression) | ❌ `outcome_reason` chưa có giá trị này | thêm `do_not_contact` vào `VALID_OUTCOME_REASONS` + loại party khỏi worklist khi có reason này | 1 |
| Hứa mua | `crm_task.outcome` — cột tồn tại nhưng đang bị bỏ sót trong export (gap #6 đã ghi) | phase 1 export sẽ vá | 1 |
| Đơn 7 ngày sau gọi | `orders_sold` weekly đã có | đủ dùng giai đoạn 1; attribution 7-ngày để sau (YAGNI) | — |
| Tách theo lô sprint (lô 1/2/3) | `claimed_action_types` (Track B) ≈ lô (OVERDUE→lô 1, WIN_BACK→lô 2) | Track B; tạm thời sprint chỉ 1 người gọi tệp cố định → cắt theo staff×tuần của Track A là đủ | 1-3 |
| VOC (10 cuộc) | — | **KHÔNG đưa vào hệ thống** (n=10, YAGNI) — track tay trong operating-board | — |

## Phases

| # | Phase | File | Ghi chú |
|---|---|---|---|
| 0 | Extend `mart_staff_performance_weekly` (Track A, no schema change) | [phase-00-quick-win-extend-staff-performance-mart.md](phase-00-quick-win-extend-staff-performance-mart.md) | ✅ DONE 2026-07-10 |
| 1 | Schema fix: snapshot action_type lúc claim + nối tag về activity (Track B) | [phase-01-schema-attribution-fix.md](phase-01-schema-attribution-fix.md) | ✅ DONE 2026-07-10 |
| 2 | Intermediate model: effort events tách theo action_type | [phase-02-effort-events-intermediate-model.md](phase-02-effort-events-intermediate-model.md) | ✅ DONE 2026-07-10 — `int_crm_outreach_effort_events` (reports/phase-02-implementation-report.md); chưa có claim thật 2+ action_type để verify explode end-to-end, verify bằng synthetic query |
| 3 | Mart tuần theo (staff, action_type) + dbt tests | [phase-03-outreach-effort-weekly-mart.md](phase-03-outreach-effort-weekly-mart.md) | ✅ DONE 2026-07-11 — `mart_crm_outreach_effort_by_action_weekly` (Bảng A only, per phase file's own decision; Bảng B intentionally not built, already covered by Phase 0). reports/phase-03-implementation-report.md |
| 4 | Reporting surface (Metabase blueprint) + validation thủ công | [phase-04-reporting-surface-and-validation.md](phase-04-reporting-surface-and-validation.md) | ✅ Track A DONE 2026-07-10 (dashboard id 147, `docs/analytics-handbook/blueprints/metabase/crm_outreach_effort_weekly.md`; reports/phase-04-dashboard-track-a-implementation-report.md — báo cáo ghi BLOCKED nhưng serving-view đã fix +deploy sau đó cùng ngày, đã verify sống). Track B card chờ phase 2-3 cutover. |

Phase 1-3 có thể để sau nếu Track A đã đủ dùng tạm; không block nhau.

## Acceptance criteria (tổng — chi tiết từng phase xem phase file)

- [x] `mart_staff_performance_weekly` có thêm outcome_notes_count, health_concern_tags_new, other_tags_new, channel breakdown — không đổi grain cũ (Phase 0)
- [x] Phễu gọi sprint đo được từ mart: `calls_dialed`, `contacts_reached` (đã sửa định nghĩa gồm callback+refused), `conversations_count`, `wrong_number_count` (Phase 0 + dashboard id 147 sống)
- [~] Log Activity có checkbox "Đã kết bạn Zalo" — UI ✅ (disposition strip T1, `custom_fields.zalo_connected`) + export/staging ✅ (phase 1: `stg_crm__activity_log` derive boolean); **`zalo_connected_count` CHƯA lên `mart_staff_performance_weekly`** — không phase nào trong plan này sở hữu việc thêm cột đó, gap thật, cần 1 phase mới (mini) trước khi dashboard hiển thị được số này.
- [x] `outcome_reason='do_not_contact'` tồn tại và party có reason này biến mất khỏi worklist (Phase 1, `list_do_not_contact_party_ids()`)
- [x] `crm_task.claimed_action_types` được ghi đúng lúc claim (Phase 1 migration 0043; Phase 2 model xác nhận đọc được, dù dữ liệu thật vẫn 100% NULL vì chưa có claim 2+ action nào sau cutover)
- [~] `crm_party_tag.source_activity_id` — schema/write-path sẵn sàng (Phase 1, migration 0044, `TagService.attach_tag()` nhận param) nhưng **UI wiring chưa xong**: không có form tag nào trong cockpit/M08 gửi `source_activity_id` khi gắn tag (verified 2026-07-11: 0 match grep trong `c360_call_cockpit_panel.html`/`modal_log_activity.html`) — cột luôn NULL trong thực tế, đúng như phase-01 report đã cảnh báo ("Handoff wiring" chưa có người nhận). Ngoài scope 2 plan đang cook.
- [x] Mart mới `mart_crm_outreach_effort_by_action_weekly` (staff × tuần × action_type) built + tested 2026-07-11; hiện 100% `action_type=NULL` vì chưa có claim thật nào sau cutover mang 2+ action_type — đúng theo thiết kế fix-forward, sẽ có dữ liệu action_type thật khi claim mới xảy ra
- [~] Dashboard/blueprint hiển thị được cả 2 track — Track A ✅ sống (dashboard 147); Track B card chưa làm (Phase 4 Track B pending, chờ data + serving-view bootstrap)

## Câu hỏi mở

1. `claimed_action_types` snapshot NGAY LÚC claim — nếu action-queue refresh (dbt chạy lại) đổi action_type của khách đó SAU khi đã claim (VD REORDER_PREEMPT → REORDER_OVERDUE do quá hạn), snapshot cũ có còn đúng ý nghĩa "effort bỏ ra cho action_type nào" không, hay nên snapshot lại lúc `completed_at`? Đề xuất: giữ snapshot lúc claim (đúng ý "khách được tiếp cận vì lý do gì tại thời điểm quyết định gọi"), phase-01 sẽ chốt.
2. Threshold "health_concern_tags_new" tính theo tag gắn LẦN ĐẦU cho khách đó hay mỗi lần gắn (kể cả lặp lại tag cũ)? Đề xuất: đếm theo `(party_id, tag_id)` lần đầu xuất hiện — tránh 1 khách được hỏi lại nhiều lần cùng 1 vấn đề bị đếm trùng, phase-00 sẽ chốt logic.
3. Có cần backfill `channel`/`outcome`/`task_kind` cho `crm_task_export` ảnh hưởng dashboard hiện có nào không (kiểm tra trước khi đổi cột export) — phase-00 sẽ kiểm tra.
4. *(2026-07-10)* Sửa định nghĩa `contacts_reached` (thêm callback+refused) đổi ngữ nghĩa cột đang có — mart còn trẻ, lịch sử ngắn, chấp nhận đổi tại chỗ hay thêm cột mới `contacts_reached_v2`? Đề xuất: đổi tại chỗ + ghi chú trong schema.yml (tránh 2 cột gần trùng gây nhầm dashboard) — phase-00 chốt.
5. *(2026-07-10)* Suppression `do_not_contact`: loại khỏi worklist bằng cách nào — filter runtime trong `worklist_query_service` hay cờ trên party (tag `risk`/archived)? Đề xuất: filter runtime từ activity gần nhất có reason này (không đổi schema party) — phase-01 chốt.
6. *(2026-07-10)* `contact_duration_s` staff có nhập đều không? Nếu đa số NULL → `conversations_count` fallback về proxy "có outcome note đính activity". Kiểm tra tỷ lệ NULL trong 2 tuần đầu sprint rồi chốt ngưỡng 60s.
7. *(2026-07-11, phát hiện lúc sync-back)* `zalo_connected_count` chưa có cột nào trong `mart_staff_performance_weekly` dù UI+export đã sẵn sàng — không phase nào trong plan này claim sở hữu việc thêm cột mart đó. Cần 1 phase mini (hoặc thêm vào phase 0's scope retroactively) trước khi dashboard hiển thị được KPI "Zalo connect ≥50%" mà Sprint Gọi Ra cần.
8. *(2026-07-11, phát hiện lúc sync-back)* `crm_party_tag.source_activity_id` write-path đã sẵn (phase 1) nhưng KHÔNG có form nào trong CRM thực sự gửi giá trị này khi gắn tag — cột sẽ mãi NULL cho tới khi ai đó wiring UI (2 hướng (a)/(b) đã đề xuất trong phase-01 report, mục "Handoff"). Ngoài scope 2 plan hiện tại, cần 1 task riêng.
