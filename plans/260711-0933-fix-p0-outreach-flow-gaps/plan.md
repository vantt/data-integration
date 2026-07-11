# Plan: Sửa 4 điểm P0 — vòng lặp Worklist → Call → Log → Callback

Status: **DONE — cả 4 phase đã ship (2026-07-11)**. Implemented qua `/ck:cook --auto --parallel` (2 wave song
song: wave1={phase-01,phase-03}, wave2={phase-02,phase-04} — xếp lại thứ tự so với "độc lập nhau" ở dưới vì
review phát hiện phase-01 và phase-02 CÙNG chạm `screen_customer_360_activity.py`, và phase-02's amendment
CÙNG chạm `c360_call_cockpit_panel.html` mà phase-01/phase-04 cũng chạm — 3 file-conflict cặp thực tế, không
phải 2 như bảng "4 điểm P0" liệt kê ban đầu). Full suite: **1075 passed, 1 skipped** (baseline trước khi bắt
đầu: 1063 passed/1 skipped — tăng 12 test mới từ phase-02, +19 từ phase-03, +6 từ phase-01... tổng khớp
diff). Code review: 8/10, PASS, 0 critical/high, adversarial validation toàn bộ CONFIRMED (không có
disproven claim / reachable regression). Artifact: `reports/harness/` (5 file: context-snippets,
risk-gate, verification, review-decision, adversarial-validation).

Nguồn: `plans/reports/ux-review-260711-0818-worklist-claim-call-log-flow-report.md` (findings P0 1-4) +
`crm/docs/workflows/outreach-worklist-call-log-loop.md` (bảng tương tác, "Đánh giá khép kín").

## Đối chiếu với `plans/260711-0838-worklist-claim-call-log-flow-fixes` (2026-07-11)

Một plan khác chạy song song (cùng nguồn report, phạm vi rộng hơn — 7 phase covering toàn bộ 15
finding, không chỉ 4 P0) đã chạy qua adversarial red-team review (4 reviewer độc lập: Security
Adversary, Failure Mode Analyst, Assumption Destroyer, Scope & Complexity Critic — 15 finding
accepted). Đối chiếu 2 plan: **design của plan `0933` (plan này) cho phase 1/3/4 tốt hơn** — tránh được
đúng cái bẫy mà red-team kia bắt được ở plan khác (resurrect nhánh `source=call_cockpit` dead code;
đổi `source` field gây S15 provenance gap). Plan này giữ nguyên làm base, đã port 2 finding còn áp
dụng (verify lại trực tiếp trên code, không copy mù) vào `phase-01` (amendment: `s14StripOpenDetail`
return_to no-op + worklist-header no-party 404 tiền tồn tại) và `phase-02` (amendment:
`/reason/resolve-async` bypass qua nút "+Nhắn Zalo"). Xem "Amendment" section cuối mỗi phase file đó.

**Không port sang plan này** (không áp dụng / ngoài phạm vi P0):
- IDOR-shaped gap: không có ownership/party-match check trước khi `execute_side_effects` step 7 dismiss
  action/complete task theo id client gửi lên (`action_state.dismiss`/`task_svc.transition_status`
  không verify id thuộc đúng `party_id`/`assignee_user_id`). Đây là **gap tiền tồn tại**, không do 4
  điểm P0 này gây ra hay làm nặng thêm — không block phase 2 vì lý do này, nhưng nên note thành finding
  riêng để user cân nhắc xử lý sau (authz hardening, không phải UX fix).
- Auto-claim-at-call-start (quyết định ③) và dismiss-session bắt buộc log (quyết định ②) — đã explicit
  ngoài phạm vi plan này (xem "Ngoài phạm vi" bên dưới); các gap liên quan (claim race TOCTOU, unclaim
  không ownership check) thuộc `260711-0838`'s phase 6, không thuộc plan này.

## 4 điểm P0

| # | Vấn đề | File chính | Phase | Trạng thái |
|---|---|---|---|---|
| 1 | `HX-Redirect` sau Lưu (M05/M08) luôn đá về Customer 360 toàn trang, phá ngữ cảnh worklist/cockpit đang dở | `screen_modal_task.py`, `screen_customer_360_activity.py`, `modal_m05_create_task.html`, `modal_log_activity.html`, templates gọi 2 modal | [phase-01](phase-01-modal-return-to-invoker.md) | ✅ DONE |
| 2 | Disposition strip resolve action **bất kể outcome** — `no_answer`/`busy` cũng dismiss TTL 30 ngày + done task ghim | `activity_side_effects.py` | [phase-02](phase-02-outcome-aware-resolve.md) | ✅ DONE |
| 3 | Task "Gọi lại"/"Theo dõi" tạo tự động **không có `assignee_user_id`** — rơi vào Hàng Đợi Chung thay vì người đã hẹn | `activity_side_effects.py` | [phase-03](phase-03-callback-task-assignee.md) | ✅ DONE |
| 4 | JS thu thập thông tin trong cockpit (`s14CollectSave`, `s14ToggleReason`, tag multiselect) chỉ định nghĩa trong `{% if script and ap %}` — chết khi khách không có approach script | `c360_call_cockpit_panel.html` | [phase-04](phase-04-cockpit-js-unconditional.md) | ✅ DONE |

## Phụ thuộc

**Cập nhật sau khi implement (2026-07-11)**: "độc lập nhau (chạm file khác nhau)" ở bản gốc KHÔNG chính
xác — thực tế 3 cặp file-conflict: phase-01↔phase-02 (`screen_customer_360_activity.py`, vì phase-02's
amendment đụng `handle_resolve_async` trong cùng file phase-01 đã sửa), phase-01↔phase-04
(`c360_call_cockpit_panel.html`), phase-02↔phase-03 (`activity_side_effects.py`). Đã chạy an toàn theo 2
wave: wave1={phase-01, phase-03} (không conflict), wave2={phase-02, phase-04} (không conflict, chạy sau khi
wave1 xong để tránh 2 conflict còn lại). Xem "Implementation Report" bên dưới.

## Implementation Report (2026-07-11)

- **Test progression**: baseline 1063 passed/1 skipped → sau cả 4 phase: **1075 passed/1 skipped** (0
  failure, 0 regression). Re-verify độc lập bởi orchestrator (không chỉ tin lời agent) + lại bởi
  code-reviewer subagent — cả 2 lần đều khớp số.
- **Code review**: 8/10, PASS. 0 critical, 0 high. 2 medium (không blocking): (1) `screen_modal_task.py`'s
  `return_to=stay` branches (M05 create/edit) chưa có pytest tự động, chỉ verify thủ công — code đã trace
  đúng nhưng thiếu regression guard; (2) IDOR-shaped gap tiền tồn tại trong `resolve_actions_and_tasks()`
  (đã document ở trên, ngoài phạm vi plan này, nhắc lại để dễ thấy).
- **Adversarial validation**: toàn bộ 5 claim quan trọng (resolve-async snooze gate, source=manual
  unchanged, handle_patch_activity return_to, worklist-header 404 tiền tồn tại, reachable-regression hunt)
  đều CONFIRMED bằng evidence cụ thể (trace code path, grep, git log --follow) — không có disproven claim.
- **3-way seam verification** (rủi ro riêng của việc 4 agent sửa song song): tất cả 4 seam đều CONFIRMED
  sạch — không duplicate function definition, không merge artifact, không cross-phase field collision.
- **Known gaps, documented không phải bug**: worklist-header "+ Tạo task" (không chọn khách) xác nhận
  THỰC SỰ 404 (route `POST /customers//tasks` không match path segment rỗng) — tiền tồn tại, KHÔNG do
  plan này gây ra (git log --follow xác nhận nút này có từ trước), KHÔNG sửa ở đây theo đúng phạm vi
  amendment đã note trước khi implement.
- **Artifacts**: `reports/harness/{context-snippets,risk-gate,verification,review-decision,adversarial-validation}.json`.

## Quyết định đã chốt áp dụng trong plan này

- Quyết định ① (2026-07-11): `no_answer`/`busy` → auto-snooze thay vì dismiss. Số ngày mặc định chọn
  **2 ngày** (giữa khoảng 1-3 ngày user đề xuất, chưa có yêu cầu số cụ thể) — xem phase-02 mục "Câu hỏi mở".
- Quyết định ③ (auto-claim khi bấm Gọi) và quyết định ② (dismiss-session bắt buộc log) **KHÔNG** nằm
  trong 4 điểm P0 gốc của report — không thuộc phạm vi plan này.

## Ngoài phạm vi (explicit)

- S15 Task Detail's `[Ghi log & hoàn thành]` vẫn giữ `HX-Redirect /customers/{pid}?tab=timeline` — S15
  không phải modal-launcher-container nên "stay" không áp dụng; đích đúng cho S15 là quay lại `/tasks/{id}`
  nhưng đó là thay đổi UX riêng (S15 closebar dead-input, Medium #6), không phải P0 #1.
- `aqCallNow()` fallback URL bug (`\modals\m08`, Minor #14) — không sửa trong plan này.
- Claim race condition (auto-claim khi bấm Gọi, Medium #9 / quyết định ③) — không sửa trong plan này.
- Dismiss-session bắt buộc log (Medium #10 / quyết định ②) — không sửa trong plan này.

## Test verification (chung cho cả 4 phase)

Chạy trong container `crm` (đã xác nhận đang chạy):
```bash
docker compose exec -T crm sh -c "cd /app/crm/src && python -m pytest tests/<file> -q"
```
Test liên quan có sẵn: `test_task_kind.py`, `test_task_claim_action_types_snapshot.py`,
`test_bulk_resolve_endpoint.py`, `test_claim_context_snooze_r14.py`, `test_quick_outcome_cockpit_post.py`,
`test_activity_disposition_api_routes.py`, `test_disposition_strip_v2.py`, `test_worklist_ranking.py`.
Mỗi phase liệt kê test cụ thể cần chạy/thêm.

## Acceptance criteria tổng

1. Toàn bộ pytest hiện có (`docker compose exec -T crm sh -c "cd /app/crm/src && python -m pytest -q"`) xanh.
2. Bấm "Đặt lịch"/"Tạo task" từ cockpit S14 giữa cuộc gọi → Lưu xong **vẫn ở cockpit**, modal đóng, timer/draft không mất.
3. Bấm 📞/💬 quick-log từ S01 Worklist → Lưu xong **vẫn ở worklist**, danh sách tự refresh.
4. Log outcome `no_answer`/`busy` trong strip → action **snooze N ngày**, KHÔNG dismiss TTL 30 ngày; claimed task liên quan **không tự done**.
5. Sau khi finalize với `create_callback_task=1` hoặc `schedule_followup_at` có giá trị → task mới có `assignee_user_id` = người vừa gọi, xuất hiện trong "của tôi" (Đã Claim), không rơi vào Hàng Đợi Chung.
6. Mở cockpit cho khách KHÔNG có approach script (ST-CALL-NO-SCRIPT) → tick "đã nói" ở rail, bấm `[+]` ở dòng thu thập (zalo/email/sinh nhật/…), bấm chip health_domain → tất cả phản hồi bình thường (không còn im lặng vì hàm JS undefined).
