# Phase 06 — Capture & UX Quick Wins (P2)

**Status:** DONE
**Priority:** P2 — chạy sau 02→03→04→05 (đụng M08 + S14 template cuối cùng)
**Scope:** 7 independent items — mỗi item ship riêng không phá item khác

## Context links

- Design: `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §4-B/C, §5, §7
- Cockpit template: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`
- Cockpit shell: `crm/src/adapters/inbound/web/templates/call_cockpit.html`
- M08 template: `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html`
- M16 template: `crm/src/adapters/inbound/web/templates/fragments/modal_m16_promote_insight.html`
- Inline contact handler: `crm/src/adapters/inbound/web/screens/modals/screen_modal_contact.py`
- Custom fields handler: `crm/src/adapters/inbound/web/screens/modals/screen_modal_custom_fields.py`
- Worklist ranking: `crm/src/application/worklist_ranking.py` (`_BAND_META`, `rank_worklist`)
- Bands template: `crm/src/adapters/inbound/web/templates/fragments/_wl_bands.html`
- Row template: `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html`
- Tasks board template: `crm/src/adapters/inbound/web/templates/tasks_board.html`
- Toast CSS: `crm/src/adapters/inbound/web/static/ds-extra.css` (`.toast-stack`, `.toast`)
- Seed: `crm/migrations/0003_customer_profile_custom_fields_tags.up.sql`
  - `skin_type` = `cfd-00000000-0001`, type=`select`, options `["dầu","khô","hỗn hợp","nhạy cảm","thường"]`
  - `preferred_contact` = `cfd-00000000-0003`, type=`select`, options `["phone","zalo","messenger","email"]`

---

## Item 1 — Custom fields vào Collect block (cockpit)

**Requirement:** Hiển thị `skin_type` + `preferred_contact` là 2 dòng inline capture ở `#s14-collect-root`. Nếu field đã có giá trị, hiện pill đọc + nút "Sửa"; nếu chưa, hiện pill chọn (như Zalo/email row). Tương tác tái dùng cùng `?inline=1` POST → swap `_s14_collect_row.html`.

**Files to modify:**
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` — bổ sung rows custom field vào `collect_rows` Jinja loop (lines ~83–87)
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_contact.py` — thêm handler `POST /customers/{id}/custom-field-inline` nhận `field_key + value + inline=1`, gọi `profile.upsert_profile()`, trả `_s14_collect_row.html`
- `crm/src/adapters/inbound/web/templates/fragments/_s14_collect_row.html` — thêm variant `kind='custom_select'` render pill choices thay dropdown
- **Spec:** `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` — cập nhật sample Collect row + action A-S14-020/021

**Implementation steps:**
1. Đọc `party.custom` (JSON) trong cockpit template context để biết giá trị hiện tại của `skin_type`/`preferred_contact`.
2. Trong vòng lặp `collect_rows` (c360_call_cockpit_panel.html ~line 83), append 2 dict: `{'key':'skin_type','label':'Loại da','kind':'custom_select','options':['dầu','khô','hỗn hợp','nhạy cảm','thường'],'current': party_custom.get('skin_type','')}` và tương tự cho `preferred_contact` — chỉ khi chưa có giá trị hoặc `data_gaps` gợi ý.
3. Trong `_s14_collect_row.html`, branch mới `kind=='custom_select'`: render các span pills (`.radio-pill`); click pill → POST `/customers/{{party_id}}/custom-field-inline` với `field_key + value + inline=1`.
4. Thêm route `POST /customers/{party_id}/custom-field-inline` trong `screen_modal_contact.py` (hoặc tách file riêng nếu > 200 lines sau khi thêm); gọi `profile.upsert_profile(party_id, custom={field_key: value})`; trả `_s14_collect_row.html` với `saved=True`.
5. Ghi context var `party_custom` vào cockpit screen (`screen_call_cockpit.py`) — parse `party.custom` JSON nếu chưa có.

**Tests & validation:**
- Unit: `screen_modal_contact.py` handler trả fragment `_s14_collect_row.html` với `saved=True`.
- Template: kiểm tra cockpit render 2 dòng custom field khi `party.custom` trống; không hiện dòng khi cả 2 đã có giá trị.

**Risks & rollback:** Merge conflict với phase 04/05 nếu chúng sửa `c360_call_cockpit_panel.html`. Resolve bằng cách phase 06 chạy sau; `git diff --check` trước khi apply.

---

## Item 2 — "★ Đúc kết" insight inline trong M08

**Requirement:** Trong M08 (modal_log_activity.html) ở `mode='log'`, thêm checkbox "★ Đúc kết thành insight" phía dưới `textarea` ghi chú. Khi tick → expand mini-form: insight_type pills (6 loại) + confidence slider/pills (Low/Med/High) + body prefill từ textarea. Submit M08 → nếu checkbox tick, backend tạo `crm_party_insight` với `source_note_id=<note_id vừa tạo>` sau khi save note, dùng `POST /customers/{id}/insights` endpoint (đã có, phục vụ M16).

**Files to modify:**
- `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html` — thêm collapse section "★ Đúc kết" (hidden input `promote_insight=1|0`, insight_type pill group, body textarea, confidence)
- `crm/src/adapters/inbound/web/screens/modals/screen_modals.py` (hoặc handler log-activity) — sau khi save note, kiểm tra `promote_insight==1`; nếu có, call service tạo insight với `source_note_id=<note_id>`, `insight_type`, `body`, `confidence`
- `crm/src/adapters/inbound/http/insight_handler.py` — xác nhận `POST /customers/{id}/insights` nhận `source_note_id` (đã có field theo profile entity)
- **Spec:** `crm/docs/ui-spec/modals/M08-log-activity-modal.md`, `M16-promote-insight-modal.md` — ghi nhận luồng tắt M16 từ M08

**⚠ Merge-conflict-sensitive:** M08 template bị phase 02 (bulk resolve) + phase 03 (outcome pills) sửa trước. Phase 06 chỉ append section cuối `<form>`, trước nút Submit.

**Implementation steps:**
1. Cuối `modal_log_activity.html` form body (mode=log), thêm `<details class="m08-insight-promo">` với summary "★ Đúc kết thành insight".
2. Bên trong: hidden `<input name="promote_insight" value="0">` được JS đổi thành `1` khi toggle; `<select name="insight_type">` (6 option); `<textarea name="insight_body">` prefill từ note textarea (JS `oninput` sync hoặc `onchange`); pill group cho `insight_confidence` (low/medium/high).
3. Handler `POST /customers/{party_id}/log-activity`: sau khi lưu note, đọc `promote_insight`; nếu `"1"`, gọi `insights_service.create(party_id, insight_type, body, confidence, source_note_id=note_id)`. Fallback: nếu insight creation fails, log warning nhưng không fail toàn bộ M08 request.
4. Tái dùng `POST /customers/{party_id}/insights` logic; không tạo endpoint mới.
5. Cập nhật M08 + M16 spec: ghi nhận luồng "promote-from-M08" là shortcut của M16.

**Tests & validation:**
- POST log-activity với `promote_insight=1` → tạo được insight kèm `source_note_id`.
- POST với `promote_insight=0` → không tạo insight (hiện trạng).

**Risks & rollback:** Nếu insight service fails, note vẫn lưu được — fallback safe. Không break flow hiện tại.

---

## Item 3 — B1 band "Treo lâu": auto-expand khi có VIP/GOLD

**Requirement:** Band 3 ("Treo lâu") mặc định `is_expanded=False`. Nếu bất kỳ row nào trong band có khách `value_group IN ('VIP','GOLD')` (từ `wh_customer_tier` qua `CacheInsight`/`ActionQueueItem`), đặt `is_expanded=True`; header band hiện thêm badge `⭐ {n} VIP/GOLD`.

**Files to modify:**
- `crm/src/application/worklist_ranking.py` — trong `rank_worklist`, sau khi build `bands_map`, kiểm tra band 3 rows: nếu có row có `value_group in ('VIP','GOLD')` → set `is_expanded=True` trong band dict; thêm key `vip_count` vào band dict
- `crm/src/adapters/inbound/web/templates/fragments/_wl_bands.html` — hiện badge `⭐ {band.vip_count} VIP/GOLD` trong `<summary>` khi `band.id == 3 and band.vip_count > 0`
- **Spec:** `crm/docs/ui-spec/screens/S01-worklist-dashboard.md` — ghi nhận behavior auto-expand B3

**Implementation steps:**
1. Trong `WorklistRow`, `value_group` có sẵn qua `row.payload` (ActionQueueItem/Task). Cần truyền `value_group` vào `WorklistRow` dataclass (thêm field `value_group: str = ""`).
2. Khi build rows từ actions: đọc `getattr(a, 'value_group', '') or ''`.
3. Sau khi group: `vip_rows = [r for r in bands_map[3] if r.value_group in ('VIP','GOLD')]`; nếu `vip_rows`, patch band dict `is_expanded=True`, `vip_count=len(vip_rows)`.
4. Template `_wl_bands.html`: trong `<summary>`, sau `.wl-band__count`, thêm `{% if band.id == 3 and band.vip_count > 0 %}<span class="bdg bdg--warn">⭐ {{ band.vip_count }} VIP/GOLD</span>{% endif %}`.
5. Kiểm tra `wh_customer_tier.value_group` column tồn tại trong `ActionQueueItem` entity (kiểm tra `cache_insight.py` + `cache_repository.py`); nếu chưa có, thêm vào SELECT query trong `cache_repository.py`.

**Tests & validation:**
- `test_worklist_ranking.py`: band 3 với 1 VIP row → `is_expanded=True`, `vip_count=1`.
- Band 3 với toàn SILVER → `is_expanded=False`.

---

## Item 4 — B2 snooze wake badge "⏰ vừa thức dậy"

**Requirement:** Action/task row ở worklist có `snoozed_until` đã qua nhưng trong vòng 1 ngày (0 < now - snoozed_until ≤ 24h) → hiện badge `⏰ vừa thức dậy` trên row. Badge chỉ hiện 1 ngày để NV nhận ra context "đây là việc đã hoãn".

**Files to modify:**
- `crm/src/application/worklist_ranking.py` — `WorklistRow`: thêm `wake_badge: bool = False`; khi build action rows, nếu `snoozed_until` đã qua ≤ 1 ngày → `wake_badge=True`
- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` — khu vực badges (line ~63–90), thêm `{% if row.wake_badge %}<span class="badge badge--info" title="Hành động này vừa được đánh thức sau khi hoãn">⏰ vừa thức dậy</span>{% endif %}`
- **Spec:** `crm/docs/ui-spec/screens/S01-worklist-dashboard.md`

**Implementation steps:**
1. `worklist_ranking.py`: trong vòng lặp build action rows, tính `wake_badge`: `snooze_dt = _parse_datetime(getattr(a, 'snoozed_until', None))` → nếu `snooze_dt` và `0 < (now - snooze_dt).total_seconds() <= 86400` → `wake_badge=True`.
2. `_parse_datetime` helper (hoặc tái dùng `_parse_date`): cần so sánh datetime, không chỉ date.
3. Thêm field `wake_badge: bool = False` vào `WorklistRow` dataclass.
4. Template `_wl_row.html`: sau badge "Có kịch bản" (line ~65), render `⏰ vừa thức dậy` badge.
5. `snoozed_until` hiện là `Optional[datetime]` trong `crm_action_state` (xác nhận tại `action_state_repository.py` line 26–50); cần đảm bảo `ActionQueueItem` expose field này (check `cache_repository.py`).

**Tests & validation:**
- Row với `snoozed_until = now - 3h` → `wake_badge=True`.
- Row với `snoozed_until = now - 25h` → `wake_badge=False`.
- Row với `snoozed_until = now + 1h` (chưa đến) → `wake_badge=False`.

---

## Item 5 — B4 source badge [AUTO] cho `action_queue_claim`

**Requirement:** Tasks board (tasks_board.html) hiện chỉ render `<span class="auto-tag">AUTO</span>` khi `source == "action_queue"`. Cần thêm cùng badge cho `source == "action_queue_claim"`.

**Files to modify:**
- `crm/src/adapters/inbound/web/templates/tasks_board.html` — line 107: `{% if t.source == "action_queue" %}` → `{% if t.source in ("action_queue", "action_queue_claim") %}`
- `crm/src/adapters/inbound/web/templates/fragments/c360_tasks_panel.html` — line 88: `{% set is_auto = t.source == 'action_queue' %}` → `{% set is_auto = t.source in ('action_queue', 'action_queue_claim') %}`
- **Spec:** `crm/docs/ui-spec/screens/S07-tasks-board.md`

**Implementation steps:**
1. `tasks_board.html` line 107: extend condition.
2. `c360_tasks_panel.html` line 88: extend `is_auto` condition.
3. Optionally hiện tooltip khác nhau: `action_queue_claim` → title="Nhận từ hàng đợi (gộp claim)"; `action_queue` → title="Gợi ý từ hàng đợi".
4. Không cần thay đổi backend hay domain logic.

**Tests & validation:**
- Template render: task với `source='action_queue_claim'` → có `auto-tag` span.
- Task với `source='manual'` → không có `auto-tag`.

---

## Item 6 — Toast sau Collect inline save

**Requirement:** Khi NV save dòng collect inline trong cockpit (Zalo/email/custom field), hiện toast `✓ Đã lưu` thoáng qua (~2s). CSS cho toast đã có trong `ds-extra.css` (`.toast-stack`, `.toast`). Chưa có JS trigger nào trong templates.

**Files to modify:**
- `crm/src/adapters/inbound/web/templates/fragments/_s14_collect_row.html` — khi `saved=True`, thêm `HX-Trigger: {"showToast": {"msg": "✓ Đã lưu"}}` response header; hoặc đơn giản hơn: trả thêm 1 div tự-fade trong fragment
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` — thêm `<div id="s14-toast-root" class="toast-stack"></div>` nếu chưa có; wiring `htmx:afterSwap` listener gọi `showToast()`
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_contact.py` — thêm `Response.headers["HX-Trigger"] = '{"showToast": {"msg": "✓ Đã lưu"}}'` trong inline response
- **Spec:** `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`, `crm/docs/ui-spec/overlays/O01-confirm-toast-overlay.md`

**Lưu ý chọn approach:** Hiện không có JS `showToast()` function trong codebase. Có 2 cách:
- **Cách A (đơn giản hơn — ưu tiên):** `_s14_collect_row.html` khi `saved=True` thêm `<div class="toast" id="s14-save-toast" aria-live="polite" style="position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%);z-index:300">✓ Đã lưu</div>` rồi JS `setTimeout(() => el.remove(), 2000)` inline. Không cần HX-Trigger.
- **Cách B (đúng hơn, reusable):** implement `showToast(msg)` trong `<script>` của `layout.html` + lắng nghe `htmx:afterRequest` event với `HX-Trigger: showToast`. Reusable cho toàn app.
- **Chọn Cách A** cho phase này (ít file chạm, không đụng layout.html — file được nhiều phase chia sẻ).

**Implementation steps:**
1. `screen_modal_contact.py` inline branch: sau render `_s14_collect_row.html`, thêm template var `saved=True`.
2. Trong `_s14_collect_row.html`, khi `saved=True`, append div toast tự fade; JS inline: `document.currentScript.previousElementSibling.querySelector('.s14-save-toast')` → setTimeout remove.
3. Test bằng cách POST inline Zalo/email → row swap có toast div → tự remove 2s.

**Tests & validation:**
- Template unit: `_s14_collect_row.html` render với `saved=True` có element `.s14-save-toast`.
- Render với `saved=False` không có element đó.

---

## Item 7 — Tooltip back-button cockpit

**Requirement:** Nút "← Worklist" và "← Quay lại task" ở `call_cockpit.html` topbar cần `title` attribute rõ ràng để NV hiểu context.

**Files to modify:**
- `crm/src/adapters/inbound/web/templates/call_cockpit.html` — thêm `title` vào cả 2 `<a>` back buttons
- **Spec:** `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`

**Implementation steps:**
1. `call_cockpit.html` line 33: `<a … title="Quay lại worklist">`
2. Line 42: `<a … title="Quay lại task">`
3. Nút "Khách kế →" (line 61): `title="Khách tiếp theo trong hàng đợi hôm nay"`
4. Không cần thay đổi backend.

**Tests & validation:**
- Template render: element `a.s14-back` có `title` attribute.
- Visual: hover tooltip hiện khi trỏ vào nút.

---

## Spec files cần update sau khi ship

| Item | Spec file(s) cần update |
|------|------------------------|
| 1 | `S14-call-mode-cockpit.md` |
| 2 | `M08-log-activity-modal.md`, `M16-promote-insight-modal.md` |
| 3 | `S01-worklist-dashboard.md` |
| 4 | `S01-worklist-dashboard.md` |
| 5 | `S07-tasks-board.md` |
| 6 | `S14-call-mode-cockpit.md`, `O01-confirm-toast-overlay.md` |
| 7 | `S14-call-mode-cockpit.md` |

Sau khi update spec, regenerate: `crm/docs/ui-spec/generated/` (action-registry.csv, coverage-report.md, navigation-graph.yaml, surface-registry.yaml, chip-audit.md) bằng spec tools.

---

## Merge-conflict-sensitive files

| File | Phases đụng trước phase 06 |
|------|---------------------------|
| `modal_log_activity.html` | 02 (bulk resolve fields), 03 (outcome/reason pills) — item 2 append CUỐI form, sau nút submit |
| `c360_call_cockpit_panel.html` | 04 (queue counter, snooze UI), 05 (R14 banner) — item 1 + item 6 chỉ sửa vùng collect (line ~681+) |
| `call_cockpit.html` | 05 (R14 topbar banner?) — item 7 chỉ thêm `title` attr vào 2 `<a>` tags |

**Protocol:** trước khi apply phase 06, `git diff main -- <file>` để xác nhận vùng sửa không overlap.

---

## Risks & rollback

- **Item 1:** Nếu `screen_call_cockpit.py` chưa pass `party_custom` dict vào template, cockpit không biết giá trị hiện tại → hiện row dù field đã có giá trị. Rollback: ẩn custom-field rows khỏi `collect_rows` list (1-line revert).
- **Item 2:** Insight creation failure trong M08 có thể mask bằng `try/except + log.warning` — note vẫn lưu; không có dữ liệu mất.
- **Item 3:** `value_group` chưa có trong `ActionQueueItem` → `rank_worklist` không crash (default `""`), band 3 chỉ không auto-expand; cần kiểm tra `cache_repository.py` SELECT có include `value_group` từ `wh_customer_tier`.
- **Item 4:** `snoozed_until` là TIMESTAMPTZ; `_parse_date` hiện dùng `date`, cần `datetime` comparison — tạo `_parse_datetime` riêng.
- **Items 5, 7:** Pure template change — rollback bằng revert 1 file.
- **Item 6:** Toast approach A không touch `layout.html` — safe.

---

## Unresolved questions

1. `ActionQueueItem` entity (cache_insight.py) có field `value_group` không? Nếu không, cần thêm vào entity + `cache_repository.py` SELECT query — xác nhận trước khi implement item 3.
2. `ActionQueueItem` có expose `snoozed_until` (datetime) không? Cache repo join với `crm_action_state` để lấy trường này chưa? Xác nhận trước item 4.
3. Item 2: `POST /customers/{id}/log-activity` handler nằm ở file nào — `screen_modals.py` hay file riêng? (grep `/log-activity` trong `screen_modals.py` để xác nhận.)
4. Item 1: `screen_call_cockpit.py` có truyền `party_custom` (parsed JSON dict) vào template context chưa, hay chỉ truyền `party.custom` (string)?
