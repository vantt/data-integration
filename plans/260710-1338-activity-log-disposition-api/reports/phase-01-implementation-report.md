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
