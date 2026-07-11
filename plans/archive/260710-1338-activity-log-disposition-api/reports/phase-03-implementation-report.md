# Phase 03 (P2) — Disposition Strip v2 (state machine T0-T3) — Implementation report

Nguồn: `plans/260710-1338-activity-log-disposition-api/phase-03-disposition-strip-v2.md` + mục IV/IV.b của `plans/reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md` + API contract từ `reports/phase-02-implementation-report.md`.

## Tóm tắt

Thay hoàn toàn `outcome_bar` tĩnh (1 hàng, `s14OpenOutcome` mở M08 mỗi lần) bằng disposition strip 4 pha (T0 idle → T1 in-call → T2 disposition (sheet-up) → T3 saved, không auto-advance), wiring thẳng vào API draft/PATCH/finalize của Phase 2 qua `fetch()` thuần (không `htmx.ajax`, mirror đúng pattern `s14StartCallSession` cũ). Phím tắt 1-7 + Enter, mid-call reload recovery (draft → T1/T2 tự động, không tạo draft thứ 2), Zalo follow-up tạo activity riêng sau `no_answer`. M08 co lại đúng 2 exception: `[⋯ Ghi thủ công]` (T0) và `[⋯ Chi tiết]` (T1-T3). Spec S14 cập nhật cùng thay đổi này (region/ASCII/interactions), verify bằng ui-spec skill's `validate.mjs`/`build.mjs` (0 warning). Full suite 1046 passed / 1 skipped / 0 failed (1031 baseline + 15 test mới, 1 skip có lý do rõ — xem mục Tests).

## Kiến trúc

### 1. `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`
Thay toàn bộ block `.s14-outcome` (div + inline `<style>` + inline `<script>` chứa `s14OpenOutcome`/`s14QuickOutcomeVals`/`s14ClearQuickNote`/`s14QuickOutcomeError`/`s14AutoGrowNote`/`s14StartCallSession`/`s14AlignBar`) bằng `#s14-strip` — **không giữ 2 đường song song**.

- **Jinja**: `call_identities` (phone/mobile identities cho dropdown "▾ số khác"), `OUTCOME_PILLS` (7, đúng thứ tự mockup báo cáo IV.b: `answered/purchased/callback/no_answer/busy/refused/wrong_number` — số thứ tự hiển thị == phím tắt 1-7), `REFUSAL_REASON_PILLS` (6, subset `VALID_OUTCOME_REASONS`: `still_stocked/wait_promo/budget/product_fit/irritation/competitor`), `_initial_phase` suy từ `draft_activity` (`t0` không draft, `t1` draft chưa có outcome, `t2` draft đã có outcome trước khi reload).
- **Markup**: `#s14-strip` root `data-phase`, 4 sub-block `#s14-strip-t0..t3` (hiện/ẩn qua `[hidden]`, không tách route — đúng Invariant §9 "chỉ swap sub-region của chính nó", ở đây swap hoàn toàn client-side, không HTMX call nào re-render `#s14-panel-root`). Sheet `#s14-strip-sheet` (`position:absolute; bottom:100%`, max-height 180px) chứa 5 body con (answered/purchased/callback/refused/wrong_number), server-render sẵn cả 5, JS chỉ toggle `hidden`.
- **JS state machine** (toàn bộ trong 1 `<script>` không điều kiện — strip phải hoạt động cả khi `script=None`, giống outcome_bar cũ):
  - `s14StripStartCall()` — `POST /api/parties/{id}/call-sessions` (idempotent, Phase 2) → T1, KHÔNG mở M08 (khác hẳn `s14StartCallSession` cũ). Dùng chung cho cả nút Gọi ở identity_bar (đã đổi onclick) lẫn nút T0 trong strip.
  - `s14StripOpenManual()` (T0 "⋯ Ghi thủ công") / `s14StripOpenDetail()` (T1-T3 "⋯ Chi tiết", `mode=edit_activity&activity_id=<draft>`) — 2 exception còn lại của M08.
  - T1: `s14StripNoteInput`/`FlushNote` (debounce 1.5s + blur → `PATCH body`), `s14StripZaloToggle` (PATCH `custom_fields.zalo_connected` ngay lập tức), `s14StripEndCall` → T2.
  - T2: `s14StripPickOutcome` (PATCH `contact_outcome` ngay khi bấm pill — "mỗi lần commit field" đúng spec API mục III; outcome cần thêm info mở sheet tương ứng), `s14StripPickReason`/`s14StripDoNotContact` (PATCH `outcome_reason`, `do_not_contact` là escalation riêng — **REFERENCE plan 260709-1638, không thêm cột party**), `s14StripPickFollowup`/`s14StripPickCallbackChip` (tính ICT-local string, cùng format `_ict_local_to_utc()` parser đã có), `s14StripFlushOrderCode`, `s14StripEditNote` (quay lại T1's textarea sửa nháp), `s14StripSave` (POST finalize, resolve_action_ids/resolve_task_ids đọc từ 2 hidden input **không đổi** — nguyên contract bulk-resolve cũ).
  - T3: hiện `✓ Đã lưu: <outcome> (<reason>) · <duration>` (duration = giá trị timer client tại thời điểm bấm Lưu — xấp xỉ đúng bằng `finalize_at - started_at` server tính vì cùng round-trip; không fetch lại từ response finalize vì route đó chỉ trả fragment nhỏ cố định, không có duration). `[＋Nhắn Zalo]` chỉ hiện khi outcome=`no_answer` → `s14StripZaloFollowup()` gọi `POST /customers/{id}/reason/resolve-async` (A-S14-026 có sẵn, **không viết endpoint mới**) tạo activity thứ 2 riêng. `[Khách kế →]` dùng `queue_total`/`queue_next_party_id` khi có (full-screen host), fallback `/customers` khi không (embedded S03 tab — đúng A2 scope note đã ghi trong spec Phase 04).
  - Phím tắt: `1`-`7` chọn pill theo `OUTCOME_ORDER` (đọc trực tiếp từ `OUTCOME_PILLS` Jinja qua `tojson`, không lặp lại thứ tự tay), `Enter` = Lưu — **chỉ active khi `data-phase="t2"`** và guard `document.activeElement` (textarea/input/contenteditable) để không bắt phím khi đang gõ. Đây là listener `keydown` toàn cục DUY NHẤT trong fragment — `s14ToggleTP`/`s14ToggleObj` bind qua `onclick`, không có xung đột.
  - Init IIFE: đọc `draft_activity` (JSON server-render) → resume T1/T2 đúng state, KHÔNG bắt buộc bấm lại "Gọi" (draft đã tồn tại thì `create_draft` phía server cũng idempotent — belt & suspenders).
  - `s14AlignStrip` (đổi tên từ `s14AlignBar`, selector `.s14-outcome`→`.s14-strip`) — kỹ thuật giữ nguyên (JS set `left/right/width` theo `.detail-main`).
- Đổi nút "Gọi" identity_bar (line ~243): `onclick="s14StartCallSession('{{ party_id }}')"` → `onclick="s14StripStartCall()"`.

### 2. `crm/src/adapters/inbound/web/static/ds-extra.css`
Thay `.s14-outcome*`/`.s14-oc*`/`.s14-quick-note` (theo đúng vị trí cũ — cockpit CSS convention của file này đã ở `ds-extra.css`, không phải inline, khác pattern R14 banner vì đó là style MỚI thêm còn đây là REPLACE style sẵn có) bằng `.s14-strip*`/`.s14-pill*` (timer, note, pills, sheet 180px, row layouts, media query wrap ≤750px). Thêm `.btn--sm`/`.btn--danger` (dùng ở cả R14 ack button lẫn "■ Kết thúc" — 2 class này TỒN TẠI trong markup từ trước (R14 banner) nhưng CHƯA TỪNG có rule CSS nào, gap tiền tồn đóng luôn ở đây vì rẻ). Bump `layout.html` `ds-extra.css?v=14→15` cùng commit (nguyên tắc cache-bust).

### 3. `crm/src/application/activity_service.py`
Thêm `find_open_draft(staff_user_id, party_id)` — public wrapper mỏng quanh `self._repo.find_open_draft` (mirror đúng pattern `get_activity` sẵn có), CẦN THIẾT vì phase file yêu cầu controller truyền `draft_activity` vào context nhưng trước đó không có method public nào cho việc này. **Deviation nhỏ khỏi "Files you may modify" nêu trong nhiệm vụ** (không liệt kê file này) — biện minh: phase-02 (cùng plan) đã sửa đúng file này cho lý do tương tự (thêm `create_draft`/`patch_activity`/`finalize_activity`), tiền lệ rõ ràng trong `reports/phase-02-implementation-report.md` mục 4.

### 4. `crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py`
Thêm hàm module-level `build_draft_activity_ctx(activity_log, current_user, party_id)` — tra `find_open_draft`, shape thành dict JSON-serializable (`activity_id, started_at, contact_outcome, outcome_reason, body, related_order_code, zalo_connected`), `None` khi thiếu `activity_log`/`current_user`/không có draft/lỗi tra cứu (try/except, log warning, không để crash trang). Dùng chung cho cả 2 host (full-screen + embedded). Thêm param `activity_log=None` vào `register_call_cockpit_route`, wire `draft_activity` vào context `call_cockpit.html`.

### 5. `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py`
Import `build_draft_activity_ctx` từ file trên, thêm param `activity_log=None` vào `register_panel_routes`, wire `draft_activity` vào context nhánh `call_cockpit` (panel embedded trong S03).

### 6. `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py`
Thêm `activity_log=activity_log` vào 2 call site (`register_panel_routes(...)`, `register_call_cockpit_route(...)`) — wiring composition tối thiểu, không đổi behaviour gì khác.

### 7. `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`
Cập nhật **cùng thay đổi** với template (đúng quyết định VI của plan — không để spec đi trước/sau code):
- `regions:` frontmatter + `ui-layout` area + `samples.disposition_strip` (thay `outcome_bar`).
- `region: outcome_bar` → `region: disposition_strip` ở A-S14-009/A-S14-010 (`replace_all`).
- A-S14-006 (Gọi) đổi `action: open_overlay target: M08` → `action: mutate effects: [...]` (không còn mở M08).
- A-S14-009 đổi từ "mở M08" sang "PATCH autosave + chuyển T1→T2"; thêm A-S14-009b ("Lưu & Khách kế →" = finalize) và A-S14-028 (Zalo follow-up, T3, tái dùng A-S14-026).
- Sửa prose còn sót "outcome bar"/"Outcome bar resolve..." → "disposition strip"/"Disposition strip (finalize) resolve...".
- Thêm section mới `## Implementation Notes (Phase 03 — 260710 disposition strip v2)` mô tả đầy đủ 4-state machine, sheet-up + phương án B bị loại, phím tắt, mid-call reload recovery, vai trò M08 co lại, gap tiền tồn `s14OpenOutcome` trong `screen_customer_360_activity.py`.
- **Regenerate ASCII qua tool skill** (`node .skills/ui-spec/tools/build.mjs --root ./crm/docs/ui-spec`) thay vì tay sửa — tránh drift (VR-ASCII-DRIFT); `validate.mjs` chạy sau đó → **0 warning**.

## Deviation khỏi phase file (có lý do, không tự ý bỏ scope)

1. **`activity_service.py` bị đụng** dù không có tên trong "Files you may modify" của nhiệm vụ — biện minh ở mục Kiến trúc #3, tiền lệ phase-02.
2. **Không viết route/API mới nào trong `screen_customer_360_activity.py`** — strip mới gọi thẳng 3 endpoint Phase 2 (`call-sessions`, `PATCH /api/activities/{id}`, `finalize`) qua `fetch()` thuần, không qua `htmx.ajax`. Vì vậy T3's duration hiển thị lấy từ timer client tại thời điểm bấm Lưu, KHÔNG đọc lại từ response finalize (route đó chỉ trả fragment `✓ Đã chốt: <label>` cố định, không có số đo — sửa route để trả thêm duration sẽ vượt phạm vi file-ownership của phase này và không cần thiết vì sai số giữa 2 giá trị chỉ là latency round-trip, không đáng kể).
3. **Sheet "Đã nghe" (`answered`) đơn giản hơn bảng mục IV gốc**: chỉ có chip theo dõi +7/+14/+30 + nút "🛒 Đã mua" — KHÔNG có "reason pills (tùy chọn)" vì mục IV (viết trước IV.b) không liệt kê cụ thể set lý do nào cho nhánh `answered` (khác `refused` có 6 lý do rõ ràng); tự bịa ra reason set không có trong spec sẽ vi phạm "resolve ambiguity before coding, not after" — để trống nhánh này thay vì đoán.
4. **`screen_customer_360_activity.py`'s `s14OpenOutcome` reference còn sót** trong fragment "Hoàn tác" của route `POST /customers/{id}/log-activity` `source=call_cockpit` (dòng ~382) — nay là dead code không thể chạm tới nữa (không còn UI nào set `source=call_cockpit`, 3 nút quick-outcome cũ đã bị xoá hoàn toàn) nhưng file này KHÔNG nằm trong danh sách file được sửa của nhiệm vụ này. Verify: test `test_quick_outcome_cockpit_post.py` (route-level, không chạm JS) vẫn xanh nguyên — không phải regression sống, chỉ là code chết cần dọn ở phase khác.

## Tests

- `crm/src/tests/test_disposition_strip_v2.py` (16 test mới, 15 pass + 1 skip):
  - `ActivityService.find_open_draft` (3): trả `None` không có draft; trả đúng draft khi có; `staff_user_id`/`party_id` rỗng → `None` không raise.
  - `build_draft_activity_ctx` (5): `None` khi thiếu `activity_log`; `None` khi thiếu `current_user`; `None` khi không có draft; shape dict đúng (dùng `ActivityService` thật trên `seeded_crm_db`, PATCH `body`+`zalo_connected` rồi verify ctx phản ánh đúng); `None` khi lookup raise exception (không crash trang).
  - `TestDispositionStripInitialPhase` (5, `TestClient` thật qua `register_call_cockpit_route`, middleware inject `request.state.current_user`): không có `activity_log` → T0; có `activity_log` nhưng không draft → T0; draft chưa có outcome → **T1** (mid-call reload); draft đã có outcome → **T2** (chọn outcome trước khi reload); gọi `/call` 2 lần liên tiếp KHÔNG tạo draft thứ 2 (đếm row `status='draft'` trong DB thật == 1).
  - `TestOldOutcomeBarFullyRemoved` (3): không còn lời gọi/định nghĩa hàm cũ (check pattern `name(` để không false-positive với comment mô tả lịch sử); có đủ identifier mới (`#s14-strip`, `s14StripStartCall`, `s14StripPickOutcome`, `s14StripSave`, `s14StripZaloFollowup`, `data-phase`); spec doc không còn `outcome_bar` — **skip có lý do** vì `crm/docs/` không được bind-mount vào container CRM (chỉ `src/migrations/ops/sync/userscripts` — verify bằng `docker compose exec crm ls /app/crm`), spec/template parity thay vào đó verify qua ui-spec skill tools (mục Kiến trúc #7).
- Không sửa file test nào khác — đúng backward-compat vì `register_panel_routes`/`register_call_cockpit_route` chỉ thêm 1 kwarg `activity_log=None` (mặc định, mọi call site cũ không truyền vẫn y hệt hành vi trước).

### Kết quả chạy

```
docker compose exec -T crm pytest crm/src/tests/test_disposition_strip_v2.py -q
→ 15 passed, 1 skipped

docker compose exec -T crm pytest crm/src/tests/test_outcome_reason_enum.py \
  crm/src/tests/test_bulk_resolve_endpoint.py crm/src/tests/test_claim_context_snooze_r14.py \
  crm/src/tests/test_task_detail_and_cockpit.py crm/src/tests/test_quick_outcome_cockpit_post.py \
  crm/src/tests/test_activity_disposition_api_routes.py crm/src/tests/test_activity_draft_lifecycle.py -q
→ 114 passed

docker compose exec -T crm pytest -q
→ 1046 passed, 1 skipped, 0 failed (1031 baseline + 16 test mới, full suite xanh)
```

### Verify live

```
docker compose restart crm → OK
curl http://127.0.0.1:3007/healthz → 200
GET /customers/{id}/call (real party) → 200, data-phase="t0" (chưa login → không draft), 60 lần "s14-strip", 0 lần "s14-outcome"/"s14OpenOutcome("
GET /customers/{id}/panels/call_cockpit → 200
POST /api/parties/{id}/call-sessions (chưa login) → 401 (đúng thiết kế Phase 2, không đổi)
node .skills/ui-spec/tools/validate.mjs --root ./crm/docs/ui-spec → 0 warning (trước: 2 warning VR-ASCII-DRIFT + wireframe stale)
node .skills/ui-spec/tools/build.mjs --root ./crm/docs/ui-spec → ASCII S14 regenerated, wireframe-v2.html rebuilt
```

## Manual test script (browser-required scenarios — KHÔNG claim đã pass, môi trường agent không có browser)

1. **T0→T1→T2→T3 full walkthrough**: mở `/customers/{id}/call`, xác nhận strip 1 hàng ~52px `[📞 Gọi ...][⋯ Ghi thủ công]`. Bấm 📞 → strip đổi ngay sang `⏱ 00:00 · [nháp...] ☑Zalo [⋯ Chi tiết][■ Kết thúc]`, KHÔNG modal nào mở. Gõ vài chữ vào nháp, blur ra ngoài → mở DevTools Network xác nhận có `PATCH /api/activities/{id}` với `body=...`. Tick Zalo → 1 PATCH riêng `zalo_connected=1`. Bấm `■ Kết thúc` → strip 2 hàng, timer + note summary + 7 pill. Bấm pill "🚫 Từ chối" → sheet mọc lên trên (đo chiều cao ≤ ~180px, không tràn), chọn 1 lý do → nút "Lưu & Khách kế →" bật; bấm → strip 1 hàng "✓ Đã lưu: Từ chối (<lý do>) · <duration>" + "Khách kế →". Xác nhận KHÔNG tự chuyển trang.
2. **Reload giữa T1**: ở bước "in call" (chưa bấm Kết thúc), F5 trang → strip phải hiện lại NGAY ở T1 (timer tiếp tục chạy từ đúng mốc, không reset về 0, không mở lại T0/nút Gọi). Kiểm tra DB/log không có draft thứ 2 (2 activity row).
3. **Phím tắt**: ở T2, bấm phím `1`-`7` (không click chuột) → đúng pill tương ứng thứ tự hiển thị được chọn + sheet mở nếu cần. Focus vào ô nháp (chuyển về T1 qua "sửa nháp") và gõ số "3" trong textarea → KHÔNG được trigger chọn pill "Hẹn lại" (đảm bảo `document.activeElement` guard hoạt động). Quay lại T2, chọn outcome hợp lệ, bấm `Enter` → trigger đúng "Lưu & Khách kế →"; bấm `Enter` khi CHƯA chọn outcome nào → không có gì xảy ra.
4. **Zalo follow-up tách activity**: chốt outcome "Không bắt" → T3 hiện `[＋Nhắn Zalo]`, bấm → verify (qua timeline C360 hoặc DB) có ĐÚNG 2 activity riêng biệt cho phiên này (1 call outcome=no_answer, 1 chat outcome=pending_reply), KHÔNG gộp field vào activity call.
5. **Không auto-advance**: sau khi bấm "Lưu & Khách kế →" ở bước 1, xác nhận trang KHÔNG tự chuyển sang khách tiếp theo — phải bấm nút `[Khách kế →]` một lần nữa (chủ động) mới điều hướng.
6. **Spec/template parity**: đã tự động hoá bằng `validate.mjs` (0 warning) — review chéo bằng mắt: mở `S14-call-mode-cockpit.md` section Implementation Notes Phase 03 song song với code, xác nhận mọi id/action mô tả (T0-T3, 7 pill, phím tắt, Zalo follow-up) khớp với `c360_call_cockpit_panel.html` thật.

## Unresolved

1. `screen_customer_360_activity.py`'s `s14OpenOutcome` reference trong fragment "Hoàn tác" (route legacy `log-activity` `source=call_cockpit`) — dead code không thể chạm tới, nhưng chưa dọn (file ngoài phạm vi sửa của phase này). Đề xuất: dọn trong 1 phase/PR nhỏ riêng khi có dịp chạm lại file đó.
2. Sheet "Đã nghe" (`answered`) không có reason pills tùy chọn (xem Deviation #3) — nếu sprint sau cần, phải chốt cụ thể set lý do trước khi code (không có trong spec hiện tại).
3. Chưa QA bằng mắt trên trình duyệt thật (môi trường agent không có browser) — xem mục "Manual test script" ở trên cho 6 kịch bản cần verify tay, đặc biệt: mid-call reload timer liên tục đúng thật (không giật/reset), sheet-up không che khuất nội dung quan trọng trên màn hình thật ≥1200px, và phím tắt không xung đột với bất kỳ input nào khác chưa lường trước trong DOM thật (browser test).
4. T3's duration hiển thị = giá trị timer client tại thời điểm bấm Lưu, không phải giá trị `contact_duration_s` server tính (finalize route không trả lại số đó trong fragment hiện có) — sai số chỉ bằng latency 1 round-trip, chấp nhận được, nhưng nếu cần hiển thị CHÍNH XÁC số server ghi thì route finalize cần trả thêm field này trong response (out of scope, đã note ở Deviation #2).

Status: DONE
Summary: Disposition strip v2 (T0-T3) thay hoàn toàn outcome_bar cũ, wiring thẳng draft/PATCH/finalize API (Phase 2) qua fetch(), phím tắt 1-7+Enter guard đúng, mid-call reload recovery, Zalo follow-up tách activity, spec S14 cập nhật + verify bằng ui-spec skill (0 warning); 1046/1047 test xanh (1031 cũ + 16 mới, 1 skip có lý do do môi trường container không mount docs/); container restart + healthz 200 + smoke test live OK.
Concerns: (1) chưa QA browser thật — xem manual test script; (2) s14OpenOutcome dead-code sót lại trong file ngoài phạm vi; (3) sheet "Đã nghe" chưa có reason pills (spec không định nghĩa cụ thể); (4) T3 duration là xấp xỉ client-side, không phải giá trị server chính xác.

## 2026-07-11 — Bug fix: refused-outcome PATCH always 422'd end-to-end + silent PATCH error swallowing

Code-reviewer reproduced (scratch pytest against real ActivityService/SQLiteActivityRepository) 2 blocking bugs trong strip vừa ship:

### BUG 1 — refused-outcome PATCH always fails end-to-end

**Root cause**: strip's `s14StripPickOutcome` PATCHes `contact_outcome:'refused'` NGAY khi bấm pill, TRƯỚC khi biết reason (sheet mở sau). `patch_activity` (`activity_service.py`) validate `REASON_REQUIRED_OUTCOMES` trên MỌI intermediate PATCH — tính `next_reason` từ activity hiện có, mà trên draft mới thì vẫn `None` → guard `if next_outcome in REASON_REQUIRED_OUTCOMES and not next_reason: raise ValueError` bắn ngay ở PATCH đầu tiên (422). PATCH reason theo sau "thành công" nhưng `contact_outcome` chưa từng commit (call đầu đã raise trước khi update). Finalize sau đó luôn 409 (`ActivityFinalizeConflictError: contact_outcome is required...`).

**Fix**: relocate cross-field "phải có trước khi commit" validation ra khỏi `patch_activity`, enforce DUY NHẤT ở `finalize_activity` (commit point thật). Đọc hết cả 2 method trước khi sửa — phát hiện method còn 1 check cùng loại (không chỉ riêng reason-required): `if next_reason == "irritation" and not (next_body or "").strip(): raise ValueError(...)` (body bắt buộc cho reason='irritation') — cùng bug pattern (nếu outcome+reason='irritation' PATCH tách 2 lần trước khi có body thì cũng bị chặn sớm sai). Relocate CẢ HAI check sang `finalize_activity`, dùng `ActivityFinalizeConflictError` (không phải `ValueError` — xác nhận qua route layer: `handle_finalize_activity` chỉ catch `ActivityNotFoundError`/`ActivityFinalizeConflictError`, KHÔNG catch `ValueError`, nên nếu dùng ValueError sẽ 500 chứ không 409 sạch).

**Giữ nguyên trong `patch_activity`** (không relocate, vì không phải "cross-field required" mà là per-field enum/format validation, không phụ thuộc thứ tự field khác):
- `contact_outcome` hợp lệ theo `channel_type` (dòng 242-249 cũ)
- `outcome_reason` là 1 trong `VALID_OUTCOME_REASONS` (dòng 252-253 cũ)

**Caller khác của `patch_activity` đã check, không bị ảnh hưởng**: M08 `edit_activity` mode (`modal_log_activity.html`) submit `contact_outcome` + `outcome_reason` CÙNG LÚC trong 1 form POST/PATCH duy nhất (không tách 2 request như strip) — verify qua grep template (dòng 203/223 `modal_log_activity.html`, cả 2 field cùng 1 `<form>`). Route bulk `log-activity` `source=call_cockpit` (dòng 280-301 `screen_customer_360_activity.py`) cũng patch cả 2 field trong CÙNG 1 dict `patch_fields` trước khi finalize. Cả 2 caller này không dựa vào early-PATCH rejection để hoạt động đúng — relocate an toàn, không phá behavior nào.

### BUG 2 — silent PATCH error swallowing

`patchDraft()` (`c360_call_cockpit_panel.html` ~line 1030) dùng `fetch(...).catch(...)` — `fetch()` chỉ reject khi network failure, KHÔNG reject trên 4xx/5xx, nên response lỗi (422/409) không bao giờ bị bắt, khác `s14StripStartCall`/`s14StripSave` (đã check `r.ok`).

**Fix**: thêm `r.ok` check + đọc response body làm message lỗi, surface VISIBLE bằng `window.alert(...)` — reuse ĐÚNG pattern `s14StripSave`'s catch path đã dùng (`window.alert('Lưu thất bại — thử lại.')`), không tạo toast/inline element mới (không có element như vậy sẵn có trong strip — grep xác nhận, chỉ có `alert()` là pattern hiện có cho lỗi visible trong fragment này).

### Files changed
- `crm/src/application/activity_service.py`: `patch_activity` bỏ 2 check (reason-required, irritation-body-required); `finalize_activity` thêm lại 2 check đó dùng `ActivityFinalizeConflictError`, cộng docstring giải thích rationale ở cả 2 method.
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`: `patchDraft()` thêm `r.ok` check + `window.alert()` visible error. Không đụng `<style>`/`ds-extra.css` → KHÔNG cần bump cache-bust version (vẫn `?v=15`).
- `crm/src/tests/test_activity_draft_lifecycle.py`: thêm `TestTwoStepPatchThenFinalize` (3 test): (1) regression chính — PATCH `contact_outcome:'refused'` riêng, PATCH `outcome_reason:'budget'` riêng (2 call tách biệt, đúng y hệt sequence click thật), rồi finalize → thành công, activity có cả 2 field + status='final'; (2) verify enforcement KHÔNG bị xoá, chỉ relocate — finalize vẫn raise `ActivityFinalizeConflictError` khi refused thiếu reason; (3) tương tự cho irritation thiếu body.

### Kết quả test

```
docker compose exec -T crm pytest crm/src/tests/test_activity_draft_lifecycle.py -q
→ 16 passed (13 cũ + 3 mới)

docker compose exec -T crm pytest crm/src/tests/test_disposition_strip_v2.py \
  crm/src/tests/test_outcome_reason_enum.py crm/src/tests/test_bulk_resolve_endpoint.py \
  crm/src/tests/test_claim_context_snooze_r14.py crm/src/tests/test_task_detail_and_cockpit.py \
  crm/src/tests/test_quick_outcome_cockpit_post.py crm/src/tests/test_activity_disposition_api_routes.py \
  crm/src/tests/test_activity_draft_lifecycle.py -q
→ 132 passed, 1 skipped (skip pre-existing, lý do như report gốc)

docker compose exec -T crm pytest -q
→ 1049 passed, 1 skipped, 0 failed (1046 baseline + 3 test mới — full suite xanh)

docker compose restart crm → OK
curl http://127.0.0.1:3007/healthz → 200 (sau vài giây khởi động lại reverse-ETL/sync_parties)
docker compose logs crm (tail) → startup sạch, không lỗi
```

### Unresolved / Deferred (theo yêu cầu, KHÔNG động tới)
- Auth check thiếu trên PATCH/finalize routes — deferred, ngoài scope fix này.
- Keyboard-Enter-on-focused-button edge case — deferred.
- `s14OpenOutcome` dead reference (đã note ở Unresolved #1 gốc) — vẫn dead code, chưa dọn, ngoài scope.

Status: DONE
Summary: 2 bug chặn (refused-outcome PATCH luôn 422/409, silent PATCH error) đã fix — relocate REASON_REQUIRED_OUTCOMES + irritation-body check từ patch_activity sang finalize_activity (dùng ActivityFinalizeConflictError đúng theo route layer's exception handling); patchDraft() thêm r.ok check + visible alert(). Regression test 2-step patch→finalize xanh, full suite 1049/1050 xanh (1046 baseline + 3 mới), container restart + healthz 200 OK.

---

## Addendum 2026-07-11 — vòng review thứ 2 phát hiện + vá lỗ hổng do fix trên tạo ra

Review độc lập lần 2 (verify riêng fix ở trên) phát hiện: relocate check sang `finalize_activity` bỏ sót case **M08 `edit_activity` trên row đã FINAL** — path đó gọi `patch_activity(is_edit_mode=True)` nhưng KHÔNG BAO GIỜ gọi lại `finalize_activity` (row đã final rồi, không có "future commit point" nào để bắt lỗi nữa). Kết quả: sau fix trên, sửa 1 activity đã final thành `contact_outcome='refused'` không kèm `outcome_reason` sẽ được server chấp nhận im lặng — guard duy nhất còn lại là client-side JS `m08ValidateSubmit()`, bypass được bằng cách PATCH trực tiếp (devtools/curl với session cookie hợp lệ).

**Fix**: thêm lại đúng 2 check đó (`_reason_required_violation`, `_irritation_body_violation` — 2 helper function mới, dùng chung bởi cả `patch_activity` lẫn `finalize_activity`, tránh lặp logic) vào `patch_activity`, CHỈ kích hoạt khi `activity.status == ACTIVITY_STATUS_FINAL` (case edit-final, không có finalize tương lai) — case DRAFT (strip's 2-step PATCH) vẫn không bị chặn sớm như thiết kế ban đầu, vì finalize_activity vẫn sẽ chạy sau đó.

**Files changed thêm**:
- `crm/src/application/activity_service.py`: 2 helper module-level function mới; `patch_activity` gọi 2 helper đó khi `activity.status == ACTIVITY_STATUS_FINAL`; `finalize_activity` refactor dùng chung 2 helper (giảm trùng lặp).
- `crm/src/tests/test_activity_draft_lifecycle.py`: thêm 3 test trong `TestEditActivityAudit` — reject refused-thiếu-reason trên row final, reject irritation-thiếu-body trên row final, và 1 sanity test xác nhận refused CÓ reason vẫn edit được bình thường (guard không chặn quá tay).

**Kết quả test**:
```
docker compose exec -T crm python -m pytest crm/src/tests/test_activity_draft_lifecycle.py \
  crm/src/tests/test_disposition_strip_v2.py crm/src/tests/test_activity_disposition_api_routes.py -q
→ 44 passed, 1 skipped

docker compose exec -T crm python -m pytest crm/src/tests -q
→ 1052 passed, 1 skipped, 0 failed (full suite, sau cả 2 vòng fix)

docker compose restart crm → OK, healthz 200 sau ~8s
```

Status: DONE
Summary: Lỗ hổng do fix vòng 1 tạo ra (edit M08 trên row final mất server-side reason-required check) đã vá bằng cách giữ lại check đó riêng cho case FINAL trong `patch_activity`, dùng chung helper với `finalize_activity`. 3 test mới, full suite 1052 passed/1 skipped/0 failed.
Concerns/Blockers: none — cả 2 review pass đều xanh sau vòng fix này.
Concerns: none — verified M08 edit_activity caller không bị ảnh hưởng (submit cả 2 field cùng lúc, không tách như strip).
