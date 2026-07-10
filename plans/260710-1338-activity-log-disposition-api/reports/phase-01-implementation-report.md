# Phase 01 (P0) — M08 form lightening + quick-outcome pills — Implementation report

Nguồn: `plans/260710-1338-activity-log-disposition-api/phase-01-m08-form-lightening-quick-outcomes.md` + mục IV/V của `plans/reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md`.

## Tóm tắt

Đã implement đầy đủ scope P0: enum `purchased`/`do_not_contact`, M08 outcome-first + accordion "Nâng cao" + compact hình-thức/kênh + checkbox Zalo + pill "Đừng gọi nữa", handler `source`/`zalo_connected`, cockpit 3 nút quick-outcome POST thẳng. Phát hiện và sửa 1 bug tiền-tồn (Jinja scoping) chặn đúng feature này.

## Chi tiết theo file

### `crm/src/domain/entities/activity.py`
- Thêm `"purchased"` vào cuối `CONTACT_OUTCOMES_CALL` (giữ thứ tự cũ).
- Thêm `"do_not_contact"` vào `VALID_OUTCOME_REASONS` kèm comment giải thích hành vi (khác `refused` — loại vĩnh viễn khỏi outreach). KHÔNG thêm vào `REASON_REQUIRED_OUTCOMES` (đúng spec — chỉ `refused` bắt buộc có lý do; `do_not_contact` là 1 giá trị lý do hợp lệ, chọn được khi outcome=refused).

### `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html`
- **Pills**: Jinja init list + JS `OUTCOMES.call` đồng bộ 7 giá trị theo thứ tự enum (answered/no_answer/busy/wrong_number/callback/refused/purchased). `positive` array và `COMPLETE_TASK_OUTCOMES` đã thêm `purchased`. `BODY_PH.call_purchased` thêm gợi ý nhập mã đơn.
- **Outcome-first**: cắt/dán block KẾT QUẢ + LÝ DO + HẸN LẠI + LÊN LỊCH THEO DÕI lên đầu form (trước hình thức/kênh) — không đổi field name/id/JS logic nào.
- **HÌNH THỨC + KÊNH compact**: bọc trong `<details class="m08-htchan">` — dòng tóm tắt (icon + "Cuộc gọi · 0983xxxxxx" + nút "Đổi"), đóng mặc định, bấm mở ra nội dung Step1+Step2 y nguyên. JS `m08UpdateHTChanSummary()` gọi ở mọi điểm channel/hinh_thuc thay đổi (m08OnHinhThuc, m08OnChan, m08ShowCustom, m08OnCustomRow, 3 input tự nhập kênh).
- **Accordion "Nâng cao"**: `<details class="m08-advanced" id="m08-advanced-sec">` đóng mặc định, chứa Step5 (lưu ghi chú) + insight promo (nested details, không đổi) + Step6 (thời gian/đơn liên quan). Step4 (nội dung) và "Đánh dấu task hoàn thành" nằm NGOÀI accordion theo đúng spec.
- **Zalo connected**: checkbox `#m08-zalo-row` ẩn mặc định, JS hiện khi hình thức=call/zalo (trong `m08OnHinhThuc`), gửi `zalo_connected=1`.
- **"Đừng gọi nữa"**: pill riêng `#m08-dnc-btn` bên trong khối LÝ DO, chỉ hiện khi outcome=refused. Cơ chế xác nhận 2 lần bấm (bấm 1 → đổi text "Bấm lần nữa để xác nhận" + màu cảnh báo đậm hơn, tự hủy sau 3s nếu không bấm tiếp; bấm 2 trong 3s → set `outcome_reason=do_not_contact`, style đỏ đậm cố định). Chọn cách này vì nhẹ nhất trong các lựa chọn (không cần modal/confirm() riêng, không chặn luồng bằng `alert()`).
- **Layout không nhảy**: `.modal--scroll` (chỉ áp cho mode=log) giới hạn `max-height:86vh`, `.modal__body` cuộn nội bộ, `.modal__actions` (nút Lưu) luôn cố định ở footer flex — accordion mở/đóng không đẩy nút Lưu ra ngoài màn hình. CSS đặt inline trong file (theo tiền lệ `<style>` đã có sẵn trong `c360_call_cockpit_panel.html` cho `.s14-r14-banner`) vì file CSS chung (`ds-extra.css`) không thuộc phạm vi sở hữu.

### `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`
- Bắt thêm `pref_phone_id` song song `pref_phone`.
- **Bug tiền tồn phát hiện + sửa**: khối tính `pref_phone` dùng `{% set %}` bên trong `{% for %}` — Jinja2 KHÔNG propagate set ra ngoài scope for-loop, nên `pref_phone` LUÔN LÀ `''` (đã verify bằng render trực tiếp với `git show HEAD:...` bản gốc — số điện thoại KHÔNG xuất hiện trong output, kể cả ở khối hiển thị `s14-idbar__phone` sẵn có). Sửa bằng `namespace(phone='', phone_id='')` để giá trị persist đúng ra ngoài loop. Fix này bắt buộc phải làm cùng lúc vì `channel_identity_id`/`channel_value` của 3 nút quick-outcome mới phụ thuộc trực tiếp vào `pref_phone`/`pref_phone_id` — nếu không sửa, nút Không nghe/Bận/Sai số sẽ luôn ghi log với kênh rỗng.
- **3 nút POST thẳng** (Không nghe/Bận/Sai số): `hx-post` tới `/customers/{id}/log-activity` (endpoint có sẵn, không tạo mới), `hx-vals="js:s14QuickOutcomeVals('<outcome>')"` (payload tính động: hinh_thuc=call, contact_outcome, occurred_at=ICT hiện tại, channel_identity_id/channel_value=pref_phone, resolve_action_ids/resolve_task_ids từ 2 hidden field có sẵn, body=quick-note, source=call_cockpit). `hx-target="#s14-outcome-btns"` (id mới trên `.s14-outcome__btns`, KHÔNG động tới `#s14-panel-root` — đúng Invariant §9). `hx-disabled-elt="#s14-outcome-btns button"` disable NGAY tất cả 6 nút trong hàng khi 1 nút đang gửi (chống double-submit chắc hơn chỉ disable nút vừa bấm).
- Giữ nguyên "Gọi được"/"Hẹn lại"/"Đã mua" mở M08 qua `s14OpenOutcome` (client-side, không đổi).
- **Confirmation UX**: CSS `.s14-oc.htmx-request` (opacity + spinner xoay ::after, scoped theo class `.s14-oc` để không lan ra element htmx khác trên trang), `.s14-oc:disabled` (opacity mờ). Server trả fragment nhỏ swap innerHTML của `#s14-outcome-btns` → "✓ Đã ghi: <label tiếng Việt>" + nút nhỏ "Hoàn tác" (gọi lại `s14OpenOutcome(outcome)` có sẵn — mở M08 pre-filled hình thức=call, tái dùng infra hiện có, đúng tiêu chí "rẻ" trong spec).
- Thêm 1 `<script>` block KHÔNG điều kiện (ngoài mọi `{% if %}`) chứa `s14QuickOutcomeVals`/`s14IctNow` — vì nút quick-outcome phải hoạt động cả khi `script=None` (trạng thái ST-CALL-NO-SCRIPT), trong khi hàm `s14OpenOutcome` sẵn có (dùng bởi nút "Hoàn tác" + Gọi được/Hẹn lại/Đã mua) chỉ định nghĩa trong khối `{% if script and ap %}` — đây là gap tiền tồn KHÔNG thuộc phạm vi sửa của phase này, xem mục Unresolved.

### `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py`
- Thêm `zalo_connected: str = Form(default="")` và `source: str = Form(default="")`.
- Gộp điều kiện ghi `custom_fields` để bao cả `zalo_connected` (trước đây chỉ ghi khi có resolve ids) — `cf["zalo_connected"] = True` khi `zalo_connected=="1"`.
- Thêm `_OUTCOME_LABELS_VI` dict cho fragment tiếng Việt.
- Cuối handler: nếu `source.strip() == "call_cockpit"` → trả `HTMLResponse` fragment `<div class="s14-outcome__done">✓ Đã ghi: <label> [Hoàn tác]</div>`, KHÔNG có `HX-Redirect`. Mọi nguồn khác (rỗng, `"timeline"`, ...) giữ nguyên `HX-Redirect` như cũ — verify bằng test `test_no_source_keeps_hx_redirect` + `test_unknown_source_keeps_hx_redirect`.
- Validate `purchased`/`do_not_contact` đi qua đường có sẵn (`ActivityService.log_activity`) — không cần code thêm vì đã tự động pass qua `CONTACT_OUTCOMES_BY_CHANNEL_TYPE`/`VALID_OUTCOME_REASONS` mới cập nhật.

## Tests

- `test_outcome_reason_enum.py`: +`test_call_has_purchased`, +`test_do_not_contact_present_but_not_required_set`, +`test_purchased_accepted_without_reason`, +`test_refused_with_do_not_contact_reason_accepted`. Cập nhật `test_valid_reasons_count` 11→12.
- `test_bulk_resolve_endpoint.py`: 3 lời gọi handler trực tiếp (không qua FastAPI TestClient) đã thêm `zalo_connected=""`/`source=""`/`promote_insight="0"` v.v. explicit — vì handler mới gọi `.strip()` trên các Form field này, mock-closure test bypass FastAPI nên tham số không truyền sẽ giữ nguyên sentinel `Form(...)` object (không có `.strip()`) → AttributeError. Đây là pattern đã có sẵn trong file (comment "pass explicit defaults for direct calls" cho `contact_outcome`), chỉ mở rộng.
- Mới `test_quick_outcome_cockpit_post.py`: 7 test — fragment path (2 outcome khác nhau, không có `HX-Redirect`, có label tiếng Việt + nút Hoàn tác), regression `HX-Redirect` giữ nguyên khi source rỗng/khác, `zalo_connected` ghi/không ghi `custom_fields`, và merge đúng với `resolve_task_ids` cùng lúc.

### Kết quả chạy

```
docker compose exec -T crm pytest crm/src/tests/test_outcome_reason_enum.py \
  crm/src/tests/test_bulk_resolve_endpoint.py crm/src/tests/test_quick_outcome_cockpit_post.py -q
→ 38 passed

docker compose exec -T crm pytest crm/src/tests -q --continue-on-collection-errors
→ 993 passed, 1 failed (test_approach_script_file_repository — flaky file-watch,
  không liên quan), 1 collection error (test_approach_script_handler — import lỗi
  tiền tồn, không liên quan). Baseline trước khi sửa cũng có đúng 2 lỗi này
  (theo memory "2 CRM test fail pre-existing").
```

Ngoài ra render 2 template qua Jinja thật (ngoài pytest) để bắt lỗi cú pháp Jinja và verify các marker id/class tồn tại đúng chỗ (`m08-htchan-sel`, `m08-advanced-sec`, `m08-dnc-btn`, `m08-zalo-row`, `s14-outcome-btns`, `S14_PREF_PHONE_ID` có giá trị đúng sau fix).

## Unresolved

1. **`s14OpenOutcome` chỉ định nghĩa trong `{% if script and ap %}`** — khi khách không có approach-script (ST-CALL-NO-SCRIPT, `script=None`), nút "Gọi được"/"Hẹn lại"/"Đã mua" VÀ nút "Hoàn tác" mới (trong fragment xác nhận) sẽ gọi hàm chưa định nghĩa → lỗi JS im lặng. Đây là gap TIỀN TỒN (3 nút cũ đã phụ thuộc hàm này theo cùng cách trước khi tôi động vào), không phải do phase này gây ra, và nằm ngoài scope P0 (spec không yêu cầu sửa). Đề xuất: phase sau nên dời `s14OpenOutcome` ra khối script không điều kiện (giống cách tôi vừa làm với `s14QuickOutcomeVals`).
2. **Không thêm "Ghi tiếp"/khôi phục hàng nút sau khi đã swap** — sau khi 1 trong 3 nút quick-outcome thành công, hàng nút bị thay hẳn bằng dòng xác nhận (khớp yêu cầu "thay chỗ hàng nút"), không có đường quay lại trạng thái 6-nút trong cùng phiên trừ khi mở lại `[Hoàn tác]` → M08. Chủ đích: khớp state machine T3 "ĐÃ CHỐT" trong report UX (mục IV.b) — coi cuộc gọi đã disposition xong, bước tiếp theo là chuyển khách kế (điều hướng trang mới sẽ re-render panel). Nếu sai giả định, cần bổ sung nút "Ghi tiếp" ở P1.
3. Chưa kiểm tra bằng mắt (không có trình duyệt trong môi trường agent) — chỉ verify qua render Jinja thô + test logic. Đề nghị QA thủ công 1 lượt trên `docker compose restart crm` trước khi để CSKH dùng thật, đặc biệt animation spinner/disable và accordion scroll trên màn hình hẹp.

## Fix UX 260710-1447

Feedback trực tiếp chủ doanh nghiệp sau khi xem UI — 2 fix.

### Fix 1 — M08: "Tác dụng phụ" + bắt note

- `modal_log_activity.html` REASON_PILLS: `l:'Kích ứng/không hợp da'` → `l:'Tác dụng phụ'`. Enum value giữ nguyên `irritation` (data compat).
- Grep toàn `crm/` (`Kích ứng|không hợp da|irritation`) tìm chỗ khác cần đổi đồng bộ: chỉ có `crm/src/domain/entities/activity.py` (comment) và `crm/docs/ui-spec/modals/M08-log-activity-modal.md` (bảng label) — cả 2 đã cập nhật. `test_outcome_reason_enum.py` chỉ test enum value, không có text VI, không cần đổi.
- `activity.py` comment (dòng ~68) viết lại rộng hơn: "tác dụng phụ (kích ứng da, khó chịu tiêu hóa, mệt...) — tín hiệu chất lượng cần escalate, không upsell cùng dòng".
- **Bắt note**: chọn pill "Tác dụng phụ" → `m08OnReason` set `#m08-body` placeholder = "Khách gặp tác dụng phụ gì? (triệu chứng, sản phẩm nào, mức độ...)" + `required=true` + `.focus()`. Chọn lý do khác → gọi lại `m08UpdateBody(m08CurHT, m08CurOut)` để trả về placeholder/required mặc định theo outcome/hình-thức hiện tại (không hardcode `required=false`, tôn trọng rule required-khi-answered/met có sẵn). Client validate trong `m08ValidateSubmit` (alert + focus + chặn submit nếu rỗng). Server chặn độc lập: `ActivityService.log_activity` raise `ValueError` khi `outcome_reason == "irritation"` và `body` rỗng (route trả HTTP 400 qua nhánh `except ValueError` có sẵn — không cần code thêm ở route).

### Fix 2 — Cockpit: "Ghi chú tạm" auto-grow + verify note thực sự bơm vào record

- `c360_call_cockpit_panel.html` `#s14-quick-note`: `rows="1"` → `rows="2"`, thêm `oninput="s14AutoGrowNote(this)"`. JS mới `s14AutoGrowNote()` set `height=auto` rồi clamp `scrollHeight` theo `S14_QUICK_NOTE_MAX_H=122` (px) — hoạt động mọi browser (không phụ thuộc `field-sizing`). CSS `ds-extra.css` `.s14-quick-note`: `font-size 13px→14px` (bằng `.inp`, không nhỏ hơn input thường), `min-height:54px` (~2 dòng), `max-height:122px` (~5 dòng, sau đó `overflow-y:auto`), thêm `field-sizing:content` làm lớp auto-grow CSS-native cho browser hỗ trợ (JS vẫn là cơ chế chính). Bump `ds-extra.css?v=12→13` trong `layout.html` (cache-bust bắt buộc theo quy ước repo).
- **(a) Quick-outcome (Không nghe/Bận/Sai số)**: `s14QuickOutcomeVals()` **đã có sẵn** `body: (#s14-quick-note).value` trong payload trước khi tôi động vào — không phải thêm mới, chỉ verify + khóa lại bằng test (`test_quick_outcome_body_is_persisted` trong `test_quick_outcome_cockpit_post.py`, assert `activity_service.log_activity` nhận đúng `body`). Việc còn thiếu là **clear sau POST thành công**: thêm `hx-on::after-request="if(event.detail.successful){s14ClearQuickNote();}"` vào cả 3 nút; `s14ClearQuickNote()` set `value=''` + reset `style.height` (tự co lại về `min-height` 2 dòng qua CSS).
- **(b) Mở M08 (Gọi được/Hẹn lại/Đã mua)**: đọc lại luồng `s14OpenOutcome()` — bản cũ dùng `htmx.ajax(...).then(fn)` để inject note vào `#m08-body` SAU khi Promise resolve. Đọc `htmx.min.js` (bundled trong repo): `oe(s)` (resolve promise) được gọi trong `p.onload` SAU `M(r,H)` (hàm swap DOM), và swap trong htmx là đồng bộ (không `setTimeout`) — nên về lý thuyết `.then()` **không** race trên bản htmx hiện tại. Tuy nhiên đây là hành vi ngầm định phụ thuộc chi tiết cài đặt của htmx (không phải hợp đồng public), dễ vỡ nếu đổi version/swap-strategy sau này — nên chọn cách chắc chắn tuyệt đối theo gợi ý trong yêu cầu: **chuyển sang server-side prefill**. `s14OpenOutcome()` giờ nối `&prefill_body=<encodeURIComponent(note)>` vào query string GET `/modals/m08`; route `handle_modal_m08`/`handle_modal_log_activity` (`screen_customer_360_activity.py`) nhận `prefill_body: str = ""`, truyền qua `_m08_ctx()` → context key `prefill_body`; `modal_log_activity.html` Step 4 render `<textarea ...>{{ prefill_body }}</textarea>` — giá trị có mặt ngay trong HTML response, không phụ thuộc timing JS nào. Đã bỏ hẳn `.then()` injection cũ (single source of truth).

### Test + verify

```
docker compose exec -T crm pytest crm/src/tests/test_m08_quick_note_prefill.py \
  crm/src/tests/test_outcome_reason_enum.py crm/src/tests/test_quick_outcome_cockpit_post.py -q
→ 40 passed

docker compose exec -T crm pytest -q --ignore=crm/src/tests/test_approach_script_handler.py
→ 1000 passed, 1 failed (test_approach_script_file_repository::test_list_customer_ids_reflects_new_file_without_reinit
  — flaky file-watch, pre-existing, không liên quan tới thay đổi)

docker compose restart crm → OK
GET /healthz (nội bộ, port 8090) → 200
```

Test mới: `test_m08_quick_note_prefill.py` (server render thật qua Jinja2 — `TestM08PrefillBody` verify `prefill_body` render vào `#m08-body`; `TestIrritationReasonLabel` verify label `'Tác dụng phụ'` xuất hiện, `'Kích ứng'` không còn, enum value `irritation` không đổi). `test_outcome_reason_enum.py` +2 test (irritation thiếu body → raise, có body → accept). `test_quick_outcome_cockpit_post.py` +1 test (`body` truyền tới `log_activity` đúng giá trị quick-note).

### Unresolved / Concerns

1. Chưa QA bằng mắt trên trình duyệt thật (không có browser trong môi trường agent) — riêng phần auto-grow textarea (CSS `field-sizing` + JS fallback) và focus/required behavior nên click-test thủ công 1 lượt trước khi để CSKH dùng, đặc biệt trên Firefox/Safari (field-sizing chưa support rộng, phụ thuộc hoàn toàn vào JS fallback ở các browser đó).
2. Phân tích race-condition dựa trên đọc source `htmx.min.js` bundled (suy luận từ minified code, không chạy trình duyệt để trace runtime) — kết luận "không race trên bản hiện tại" là suy luận tĩnh, không phải bằng chứng runtime. Vì vậy đã chủ động chuyển hẳn sang server-side prefill (loại bỏ phụ thuộc timing) thay vì chỉ ghi chú lại — không để ngỏ rủi ro này.

## Fix outcome bar 260710-1512 (root cause + fix)

User test trên browser thật báo 2 lỗi ở outcome bar. Điều tra bằng chứng cụ thể (curl vào container + đọc `htmx.min.js` bundled) trước khi sửa, theo đúng yêu cầu — không guess-fix.

### Lỗi 1 — 3 nút quick-outcome (✗/☎/☠) bấm không phản hồi

**Loại trừ trước:**
- CSRF: `docker compose exec -T crm env | grep CRM_CSRF_ENFORCE` → không set trong `.env` (comment out), default `false` trong `csrf_guard.py` → **log-only, không block**. Không phải nguyên nhân.
- `s14QuickOutcomeVals` bị gate trong `{% if script and ap %}`: đọc file — hàm này đã nằm trong khối `<script>` KHÔNG điều kiện (dòng ~939, thêm ở fix 260710-1447 trước đó). Không phải nguyên nhân của lỗi này (dù đây đúng là 1 gap thật — xem lỗi liên quan bên dưới, ảnh hưởng bug 2 chứ không phải bug 1).
- Curl trực tiếp `POST /customers/{party_id}/log-activity` với đúng field mà `s14QuickOutcomeVals` gửi (`hinh_thuc, contact_outcome, occurred_at, channel_identity_id, channel_value, resolve_action_ids, resolve_task_ids, body, source=call_cockpit`) → **HTTP 200**, trả đúng fragment `s14-outcome__done`. ⇒ server-side hoàn toàn không có vấn đề — bug nằm ở phía trình duyệt, request không bao giờ được gửi đi.

**Root cause tìm thấy (đọc `htmx.min.js` bundled, hàm `bn()`):**
```js
if(e.indexOf("{")!==0){e="{"+e+"}"}
let n;if(t){n=vn(r,function(){return Function("return ("+e+")")()},{})}
```
htmx (v2.0.4, `allowEval:true`) xử lý `hx-vals="js:<expr>"` bằng cách: nếu `<expr>` KHÔNG bắt đầu bằng `{`, tự động bọc thành `{<expr>}` rồi `Function("return ({<expr>})")()`. Markup cũ:
`hx-vals="js:s14QuickOutcomeVals('no_answer')"` → htmx bọc thành `{s14QuickOutcomeVals('no_answer')}` — đây là cú pháp **object-literal không hợp lệ** (một lời gọi hàm trần không phải cặp `key: value` cũng không phải shorthand biến). `Function(...)()` ném `SyntaxError: Unexpected string/token` đồng bộ, KHÔNG có try/catch bao ngoài trong `vn()` → exception văng ra khỏi handler click của htmx, request AJAX **không bao giờ được issue**. Verify bằng Node trực tiếp với đúng code `bn()` lấy từ file: xác nhận throw `SyntaxError: Unexpected string`. Đây khớp 100% triệu chứng "bấm nút không có phản hồi gì, không swap, không lỗi hiển thị" — vì lỗi xảy ra TRƯỚC khi request được gửi, không có response nào để htmx xử lý.

So sánh với 2 nút hx-post đang chạy tốt: `async-resolve` (dòng ~664 cũ) dùng `hx-vals='{"channel":"zalo",...}'` — JSON tĩnh, không qua nhánh `js:`; `r14-ack` không dùng `hx-vals` (chỉ `hx-include`). Cả 2 không đụng code path lỗi này — giải thích tại sao chỉ đúng 3 nút quick-outcome bị ảnh hưởng.

**Fix:** đổi cả 3 `hx-vals` sang cú pháp spread — `js:{...s14QuickOutcomeVals('no_answer')}` (và tương tự `busy`/`wrong_number`). Chuỗi này ĐÃ bắt đầu bằng `{` nên htmx không bọc thêm; `Function("return ({...s14QuickOutcomeVals('no_answer')})")()` là spread hợp lệ, trả đúng object gốc. Verify lại bằng Node: object trả về khớp y hệt bản gốc (`{hinh_thuc:'call', contact_outcome:'no_answer', ...}`).

**Fix kèm (không fail im lặng nữa):** thêm nhánh else vào `hx-on::after-request` của cả 3 nút — `else{s14QuickOutcomeError();}`. Hàm mới `s14QuickOutcomeError()` hiện `<span id="s14-outcome-err">⚠ Ghi thất bại — thử lại</span>` (ẩn mặc định, không dùng `alert()`), `s14ClearQuickNote()` (chạy khi thành công) ẩn lại span này.

### Lỗi 2 — textarea `#s14-quick-note` rows=2 nhưng ngang chỉ ~10 ký tự

**Root cause tìm thấy (đọc CSS + JS liên quan):** `.s14-outcome` là `position:fixed; bottom:0` nhưng KHÔNG có `left/right/width` trong CSS (`ds-extra.css`) — comment ngay tại chỗ ghi rõ "left/width set by JS to match .detail-main". JS đó (`s14AlignBar` IIFE, set `bar.style.left/right/width`) lại nằm bên trong khối `{% if script and ap %}` — chỉ render khi khách CÓ approach-script. Khi `script=None` (trạng thái ST-CALL-NO-SCRIPT, "Chưa có kịch bản tiếp cận" — xác nhận đây KHÔNG phải trạng thái hiếm: query trực tiếp `crm.db` lấy 4 party bất kỳ ngoài top-5 test trước đó, cả 4 đều rơi vào trạng thái này), script align KHÔNG BAO GIỜ chạy → `.s14-outcome` không có `left/right/width` tường minh. Theo CSS 2.1 §10.3.7, `position:fixed` với `left`/`right` đều `auto` và không set `width` → box tự **shrink-to-fit** theo nội dung. Trong container shrink-to-fit, `textarea` (flex:1, min-width:0) nằm cùng hàng với `.s14-outcome__btns` (flex:none, 6 nút không wrap) không có "không gian thừa" nào để `flex-grow` giãn vào — co về gần kích thước intrinsic tối thiểu của textarea (~10 ký tự), khớp chính xác triệu chứng user báo.

Verify bằng render trực tiếp qua HTTP: fetch `/customers/{party_id}/panels/call_cockpit` cho 1 party không có approach-script → `grep -c "s14SwitchChannel\|PRIMARY_MSG"` (marker riêng của khối `{% if script and ap %}`) = **0**, xác nhận khối này (và `s14AlignBar` bên trong) thật sự không render cho party đó.

**Fix (2 phần, theo đúng yêu cầu):**
1. **CSS restructure 2 hàng** đúng thiết kế `IV.b` (`ux-design-260710-1313...report.md`): hàng 1 = `.s14-outcome__row1` chỉ chứa textarea (`flex:1 1 100%; width:100%; min-width:0`) — không còn sibling nào tranh không gian trong cùng hàng nên không phụ thuộc `.s14-outcome` có được set width hay không; hàng 2 = `.s14-outcome__row2` chứa `.s14-outcome__btns` (`flex-wrap:wrap` — chống vỡ ở 1366px) + span lỗi inline mới.
2. **Dời `s14AlignBar` + `s14OpenOutcome` ra khối `<script>` không điều kiện** (cùng chỗ với `s14QuickOutcomeVals`) — xử lý luôn gap đã ghi nhận ở mục "Unresolved #1" phía trên (chưa sửa lúc P0 vì ngoài scope lúc đó; nay sửa cùng lúc vì đây chính là 1 trong 2 root cause của lỗi 2, và `s14OpenOutcome` cùng lớp bug — undefined khi `script=None`, ảnh hưởng nút "Gọi được"/"Hẹn lại"/"Đã mua"/"Hoàn tác"). Verify: render party không-script → `s14AlignBar`/`window.s14OpenOutcome = function` nay xuất hiện trong HTML output (trước đây không).
3. Bump `ds-extra.css?v=13→14` trong `layout.html` (cache-bust bắt buộc theo quy ước repo).

### Test + verify

```
docker compose restart crm → OK
curl /healthz → 200

curl -sS -i -X POST /customers/{party}/log-activity (form fields = s14QuickOutcomeVals payload) → 200 + fragment s14-outcome__done (cả trạng thái trước/sau restart)

docker compose exec -T crm pytest crm/src/tests/test_quick_outcome_cockpit_post.py \
  crm/src/tests/test_m08_quick_note_prefill.py crm/src/tests/test_bulk_resolve_endpoint.py \
  crm/src/tests/test_claim_context_snooze_r14.py crm/src/tests/test_task_detail_and_cockpit.py -q
→ 67 passed (32 + 35, 2 lệnh riêng)
```

Render Jinja thật cho 1 party CÓ script (`794cf94b-...`) và 4 party KHÔNG có script — cả 2 trường hợp 200, không traceback, chứa đủ `s14-outcome__row1/row2/err` + `js:{...s14QuickOutcomeVals(...)}` + (party không-script) `s14AlignBar`/`s14OpenOutcome` nay có mặt.

### Unresolved
- Chưa QA bằng mắt trên trình duyệt thật (môi trường agent không có browser) — đề nghị user xác nhận lại trên browser thật sau khi `docker compose restart crm` + hard-refresh (cache-bust `?v=14` đã bump nên refresh thường cũng đủ).
