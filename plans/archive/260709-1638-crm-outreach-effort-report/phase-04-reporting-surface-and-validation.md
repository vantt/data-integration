# Phase 4 — Reporting surface (Metabase) + validation cuối

## Context
Phụ thuộc Phase 0 (ship ngay được) và Phase 3 (cần thời gian tích lũy dữ liệu sau cutover trước khi có ý nghĩa). Có thể tách 2 lần deploy: deploy dashboard Track A trước, thêm card Track B sau khi có đủ vài tuần dữ liệu (đề xuất: chờ tối thiểu 2-3 tuần sau Phase 1 ship trước khi thêm card action_type-sliced, tránh dashboard trống/nhiễu).

## Requirements

### Blueprint mới: "Hiệu quả tiếp cận khách hàng (theo nỗ lực)"
Dùng skill `.skills/analytics-design/SKILL.md` (Phase 0-6, Design Spec trước) rồi `.skills/metabase-automation/STRATEGY.md` (Phase 7-10, Blueprint + deploy) — theo đúng quy trình 2-skill đã có trong repo, KHÔNG tự chế deploy tay.

**Card nhóm 1 (Track A, `mart_staff_performance_weekly` mở rộng)**:
- Bảng: staff × tuần — activities, reach_rate_pct, outcome_notes_count, health_concern_tags_new, other_tags_new, channel breakdown
- Trend chart: health_concern_tags_new theo tuần (toàn team) — "có đang thu thập thêm thông tin khách hàng theo thời gian không"
- Trend chart: reach_rate_pct theo tuần theo staff

**Card nhóm 2 (Track B, `mart_crm_outreach_effort_by_action_weekly`, sau cutover)**:
- Bảng: action_type × tuần — tasks_claimed, tasks_completed, reach_rate_pct — filter tuần >= ngày cutover Phase 1 (ghi rõ trong card description)
- So sánh reach_rate_pct giữa các action_type (VD REORDER_OVERDUE có reach rate thấp hơn REORDER_PREEMPT không — dấu hiệu khách đã "nguội")

**Text card cảnh báo**: ghi rõ giới hạn — "Track B chỉ có dữ liệu action_type từ [ngày cutover]. Không dùng để so sánh xu hướng trước/sau cutover."

## Files to create
- `docs/analytics-handbook/designs/crm-outreach-effort.md` (Design Spec, Phase 0-6)
- `docs/analytics-handbook/blueprints/metabase/crm_outreach_effort.md` (Blueprint, Phase 7-10)
- Deploy qua `/deploy-metabase-blueprint`

## Validation thủ công cuối (end-to-end, trước khi coi phase 1-3 là DONE)
1. Chọn 1 khách có ≥2 action pending (VD REORDER_PREEMPT + PROGRESS_CHECK cùng lúc) trên worklist thật.
2. Claim khách đó → kiểm tra `crm_task.claimed_action_types` trong `crm.db` có đúng JSON 2 phần tử.
3. Log Activity cho khách đó, tick lưu note (`note_type` mặc định `outcome`), gắn thêm 1 tag `health_concern` ngay trong flow đó.
4. Đánh dấu task hoàn thành.
5. Chạy `dbt run --select int_crm_outreach_effort_events+ mart_crm_outreach_effort_by_action_weekly+`.
6. Query mart: xác nhận có đúng 2 row (2 action_type) cho task đó ở Bảng A, và `mart_staff_performance_weekly` (Track A) tăng đúng 1 ở `outcome_notes_count` và `health_concern_tags_new` cho staff/tuần đó.
7. Mở dashboard Metabase, xác nhận số hiển thị khớp bước 6.

## Acceptance
- [ ] Dashboard Track A live, đúng số liệu tay-verify
- [ ] Dashboard Track B card có, filter đúng cutover date, không lẫn dữ liệu NULL action_type vào so sánh
- [ ] Validation thủ công 7 bước ở trên PASS
- [ ] `docs/analytics-handbook/domains/customer_support.md` (nếu có domain doc CS/outreach) cập nhật trỏ về blueprint mới — kiểm tra file này có tồn tại/đang nói gì trước khi sửa

## Rủi ro / câu hỏi mở
- Nếu reach_rate_pct thấp không phải vì "kịch bản dở" mà vì data chất lượng contact kém (`contact_quality='masked'`) — dashboard cần tách riêng, không quy hết về "hiệu quả tiếp cận" kẻo đổ oan cho rep. Cân nhắc thêm filter/card riêng theo `contact_quality` nếu thấy cần sau khi có dữ liệu thật.
