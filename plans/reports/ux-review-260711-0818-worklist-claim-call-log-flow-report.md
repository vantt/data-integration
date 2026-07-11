# UX Review — Flow Action-Queue → Worklist → Claim → Gọi → Log → Task hẹn lại

Date: 2026-07-11 · Scope: CRM S01 Worklist, S03 Customer 360, S14 Call Cockpit (disposition strip v2), S15 Task Detail, M05, M08, activity side-effects.
Kind: advisory (không sửa code).

## I. Flow map thực tế (verified từ code)

```
wh_action_queue (warehouse)
  → S01 Worklist "Cơ Hội Hệ Thống" (band 0-4, lazy overflow, filter bar)
      ├─ [Nhận việc]  → claim_customer_actions: 1 task/khách, gộp mọi action    (screen_worklist.py:473)
      ├─ [📞 Gọi]     → S14 cockpit + queue_ids (≤50), KHÔNG cần claim trước    (_wl_row.html:169)
      ├─ [Xem 360]    → S03 same-tab                                            (_wl_row.html:164)
      ├─ row click    → S03 same-tab (trùng Xem 360)                             (_wl_row.html:59)
      └─ [⏰ snooze] [✕ Bỏ qua] → crm_action_state (+ TTL 30d party×type khi dismiss)
  → "Đã Claim" (collapsed): task row → contact_btn(M08) / title→S15 / Trả việc / snooze
  → S15 "Vào phiên gọi" → S14?task_id= (pin primary reason, return_target=task)
  → S14 strip T0→T1 (draft + timer + note autosave) →T2 (7 pills, sheet) →T3
      finalize → execute_side_effects (1 executor duy nhất):
        resolve actions (dismiss) · done tasks · callback task · follow-up task
        · save-as-note · promote insight · auto-claim
  → T3 [Khách kế →] giữ queue_ids. Không auto-advance (đúng chốt UX).
```

**Kết luận tổng**: khung flow ĐÃ khép kín — claim có mặt cả ở worklist lẫn 360 (đúng, không cần bắt qua 360 mới nhận); disposition strip v2 + "một đường ghi duy nhất" (activity_side_effects) là nền tốt. Nhưng có 4 điểm gãy nặng ở các "đường nối" giữa màn hình.

## II. Findings — P0/High (gãy flow)

### 1. HX-Redirect sau M05/M08 kéo staff ra khỏi ngữ cảnh làm việc
- `POST /customers/{pid}/tasks` (M05) → `HX-Redirect /customers/{pid}` (screen_modal_shared.py:36). Hệ quả:
  - Cockpit mid-call bấm **Đặt lịch** (rail) / **Tạo task** (idbar) → lưu xong bị đá sang 360, mất cockpit + mất queue_ids (draft resume chỉ cứu strip khi tự mò về /call).
  - Worklist header **+ Tạo task** (không party) → redirect `/customers/` — lạc khỏi worklist.
- `POST /customers/{pid}/log-activity` (M08) → `HX-Redirect /customers/{pid}?tab=timeline` (screen_customer_360_activity.py:386). Worklist task-row 📞 Gọi → log xong bị đá sang 360 timeline; mất filter/scroll/band state. "Log nhanh từ worklist" thực chất là one-way exit.
- Fix hướng: trả 204 + `HX-Trigger` để caller tự refresh vùng của nó (worklist container / cockpit giữ nguyên); chỉ redirect khi gọi từ chính S03.

### 2. Strip Save resolve action bất kể outcome — đốt tín hiệu sau 1 cú gọi trượt
- `s14StripSave()` luôn gửi `resolve_action_ids/resolve_task_ids` (c360_call_cockpit_panel.html:1216-1223); finalize dismiss + done vô điều kiện (side effects §7).
- Dismiss ghi cả `crm_action_dismissal` TTL **30 ngày** theo (party, action_type) (action_state_repository.py:26,56).
- Hệ quả: outcome "Không bắt / Bận" → action CALL_NOW biến mất khỏi queue 30 ngày, task ghim bị done. Mất cơ chế retry — trái với thiết kế band 4 "Đã liên hệ" + hide_contacted chỉ ẩn positive outcome.
- Fix hướng: gate resolve theo outcome (answered/purchased/refused/wrong_number = resolve; no_answer/busy = auto-snooze 1-3d, giữ task open).

### 3. Task "Gọi lại"/"Theo dõi" tạo ra KHÔNG gán cho người gọi
- `execute_side_effects` §4/§5 gọi `create_task` không có `assignee_user_id`, không `created_by` (activity_side_effects.py:129-154) → task rơi vào **Hàng Đợi Chung** (unassigned) thay vì list của chính staff vừa hẹn khách.
- UI hứa "tạo task nhắc" (strip checkbox, M08 checkbox) nhưng không nhắc *người hẹn* — người khác có thể Nhận nhầm, hoặc không ai nhận.
- Fix: truyền `assignee_user_id=actor_id` (+ `created_by`), source `callback`/`followup` thay vì `manual` để S15 provenance đúng.

### 4. JS cockpit gate `{% if script and ap %}` — khách không có kịch bản mất chức năng thu thập
- `s14ToggleReason`, `s14SetResolveId`, `s14CollectEnable/Save`, `s14TagChipToggle/MultiSave` chỉ define trong block `{% if script and ap %}` (c360_call_cockpit_panel.html:1342), nhưng rail + collect rows render cả khi `script=None` (ST-CALL-NO-SCRIPT).
- Hệ quả: khách no-script → tick "đã nói" và toàn bộ "Thu thập còn thiếu" (zalo/email/sinh nhật/loại da/health…) chết im lặng (JS undefined). Đây là 1 trong các mục tiêu chính của flow ("thu thập thông tin").
- Fix: tách các hàm này ra block unconditional (như strip JS đã làm đúng).

## III. Findings — Medium

5. **Nút kênh không khớp modal**: worklist `💬 Zalo`/`📘 Facebook` gửi `&channel=zalo|facebook`, cockpit Zalo gửi `&hinh_thuc=chat` — handler GET /modals/m08 không nhận 2 param này (screen_customer_360_activity.py:183-195) → modal luôn mở "Cuộc gọi" + outcome set của call. Dễ log sai kênh; nút hứa Zalo nhưng modal nói Gọi.
6. **S15 closebar input chết**: "Ghi chú nhanh khi đóng task…" không name/id/JS (task_detail.html:470) — text gõ vào bị vứt khi bấm "Ghi log & hoàn thành" mở M08. Cần pipe qua `prefill_body` hoặc bỏ input.
7. **Claim feedback biến mất**: "Nhận việc" re-render toàn container; task mới nằm trong section "Đã Claim" mặc định **collapsed** → row biến mất không dấu vết (comment code nói chọn collapse-thay-tab để giữ feedback, nhưng collapsed-by-default nên feedback vẫn mất). Hướng: auto-open Đã Claim + highlight row vừa claim (hoặc toast).
8. **Sau claim, đường vào cockpit dài ra**: action row chưa claim = 1 click vào cockpit (📞 Gọi + queue); sau claim, task row chỉ còn contact_btn → M08 quick-log; muốn cockpit phải title → S15 → "Vào phiên gọi" (3 click). Nghịch lý: khách đã nhận việc (commit cao) lại khó vào công cụ gọi chính hơn. Hướng: thêm link `📞 /customers/{pid}/call?task_id={tid}` trực tiếp trên claim-task row.
9. **Race 2 staff cùng gọi 1 khách**: cockpit không claim khi bắt đầu gọi (quyết định "không claim khi mở cockpit"); auto-claim chỉ chạy sau finalize. Queue 📞 Gọi hiển thị giống nhau cho mọi staff → 2 người có thể cùng bấm gọi 1 khách. Hướng: `s14StripStartCall` (đã là 1 hành động chủ động, khác "mở cockpit") nên auto-claim ngay, hoặc idbar hiện "👤 X đang xử lý" như 360 đã có.
10. **"Hoàn tất ✓" session checklist (P01)** dismiss hàng loạt action không kèm activity log — đường resolve bypass ghi nhận outcome, mất data chất lượng tín hiệu. Cân nhắc: yêu cầu log hoặc ghi activity type=other tự động.

## IV. Findings — Minor

11. Progress bar worklist "Đã xong 0/N" luôn 0% (baseline server-side cố định) — thanh chết, gây hiểu lầm; nên đếm số row đã xử lý trong session hoặc bỏ.
12. `hx-trigger="claimSuccess from:body"` — không nơi nào emit `claimSuccess` → listener chết (claim dùng swap trực tiếp). Dọn hoặc tận dụng làm cơ chế refresh cho finding #1.
13. Snooze claim-task `hx-swap="none"` → không feedback, row giữ due cũ đến khi tự refresh (khác snooze action = row delete ngay).
14. `aqCallNow` fallback dùng `'\modals\m08?...'` (backslash bị JS escape) → URL hỏng; nhánh chính (click tab Gọi) vẫn chạy.
15. Action row: row-click → 360 TRÙNG nút "Xem 360". Đề xuất: row-click đổi thành mở cockpit (hot action) hoặc giữ nguyên nhưng chấp nhận redundancy có chủ đích.

## V. Trả lời trực tiếp 2 câu hỏi

- **"Nhận việc ở worklist hay phải qua 360?"** — Giữ ở worklist là ĐÚNG (đã có, 1 click, claim cả khách). 360 P01 cũng có Nhận việc/Trả việc — hai nơi cùng semantics per-customer, không thừa. Vấn đề không phải vị trí nút mà là *feedback sau claim* (finding 7) và *đường vào cockpit sau claim* (finding 8).
- **"Xem 360 từ worklist có nên new-tab?"** — Hiện tất cả same-tab (chỉ Sapo deep-link là `_blank`). Đề xuất: nút "Xem 360" (hành động tham khảo/inspect) → `target="_blank" rel="noopener"`; row-click và 📞 Gọi (hành động làm việc) giữ same-tab. Lý do: filter nằm trong query-param nên Back khôi phục được, nhưng band expand/overflow đã load thì mất — new-tab cho inspect giữ nguyên vị trí queue.

## VI. Ưu tiên xử lý đề xuất

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | Redirect M05/M08 phá context | S-M | Cao — mỗi lần log/tạo task đều đau |
| 2 | Resolve bất kể outcome (đốt signal 30d) | S | Cao — mất cơ hội thật |
| 3 | Callback/followup task không assignee | XS | Cao — lời hứa nhắc việc sai |
| 4 | JS gate script=None | XS | Cao — collect chết với khách no-script |
| 5-8 | Kênh modal, closebar, claim feedback, cockpit link | XS-S | Trung bình |
| 9-10 | Claim race, dismiss-session no-log | M | Trung bình (policy) |
| 11-15 | Cosmetic/dead code | XS | Thấp |

## User decisions (2026-07-11)
1. Finding 2 — no_answer/busy: **KHÔNG resolve action; auto-snooze** (đề xuất 1-3 ngày) thay vì dismiss TTL 30d.
2. Finding 10 — dismiss-session "Hoàn tất ✓": **bắt buộc kèm log** (không cho resolve action mà không ghi nhận tiếp xúc).

3. Finding 9 — claim-at-call-start: **auto-claim khi bấm "Gọi"** (T0→T1, tạo call draft). Mở cockpit chỉ để xem vẫn KHÔNG claim (giữ quyết định cũ). Bỏ ngang → dùng "Trả việc" có sẵn để nhả.

## Unresolved questions
(none — cả 3 câu đã chốt 2026-07-11)
