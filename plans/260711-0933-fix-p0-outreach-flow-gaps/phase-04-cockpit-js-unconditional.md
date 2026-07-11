# Phase 04 — JS thu thập thông tin trong cockpit phải chạy cả khi khách không có approach script

## Bối cảnh

`crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` — khối
`<script>` cuối file bọc trong `{% if script and ap %}` (dòng 1342) chứa CẢ những hàm JS thật sự phụ
thuộc kịch bản (talk-track, talking points, objection handling) LẪN những hàm KHÔNG phụ thuộc kịch bản
nhưng UI của chúng luôn render (rail "vì sao gọi", dòng thu thập thông tin, tag multiselect):

- `s14ToggleReason` / `s14SetResolveId` (dòng ~1438-1459) — rail "Vì sao gọi" luôn render kể cả
  `script=None` (xem `{% if not rail_primary %}...{% else %}` ở phần RAIL, không phụ thuộc `script`).
- `s14CollectEnable` / `s14CollectSave` (dòng ~1462-1498) — khối "Thu thập còn thiếu" luôn render
  (không có `{% if script %}` bao ngoài `.s14-railcard` collect).
- `s14TagChipToggle` / `s14TagMultiSave` (dòng ~1501-1527) — dòng `health_domain` collect luôn render.
- Stale-badge freshness check IIFE (dòng ~1530-1545) — element `#s14-trust-freshness` nằm trong TRUST
  FOOTER, **luôn render** (không bọc `{% if script %}`, dùng `confidence = ... if script else 'medium'`
  làm fallback — xem dòng 45).

Khi `script=None` (ST-CALL-NO-SCRIPT), khối `<script>` này **không được emit ra HTML** →
`s14CollectSave`/`s14ToggleReason`/`s14TagMultiSave`/… là `undefined` → bấm nút `[+]` ở dòng thu thập,
tick "đã nói" ở rail, chọn chip health_domain đều **im lặng không phản hồi gì**. Mục tiêu chính "thu
thập thông tin" của cockpit hỏng hoàn toàn với nhóm khách này.

**Bonus bug phát hiện khi đọc code (không liên quan gate, sửa luôn vì đang chạm đúng hàm)**:
`s14TagMultiSave` (dòng ~1523-1525) tham chiếu biến `S` trần (`S.draftId`):
```js
values: { tag_names: selected, category: category, source_activity_id: S.draftId || '' }
```
`S` chỉ tồn tại trong closure của khối `<script>` DISPOSITION STRIP (dòng ~962+, một IIFE khác) — khối
đó có `window.S14_STRIP = S;` để export ra global, nhưng `s14TagMultiSave` không đọc qua
`window.S14_STRIP` mà đọc `S` trần → `ReferenceError: S is not defined` **mọi lúc**, kể cả khi có
script — độc lập với gate `{% if script and ap %}` đang sửa. Sửa cùng lúc vì đang chỉnh đúng dòng này.

## Thiết kế fix

Tách khối `<script>` cuối file thành 2:

1. **Khối MỚI, KHÔNG điều kiện** — đặt trước khối `{% if script and ap %}` hiện tại (ngay sau khối
   `{% if is_stop %}...{% endif %}` R14-unlock script, trước dòng 1341 comment cũ). Chứa nguyên vẹn:
   `s14ToggleReason`, `s14SetResolveId`, `s14CollectEnable`, `s14CollectSave`, `s14TagChipToggle`,
   `s14TagMultiSave` (đã sửa bug `S.draftId`), và stale-badge freshness IIFE.
2. **Khối CŨ, giữ điều kiện** `{% if script and ap %}` — chỉ còn lại phần thực sự phụ thuộc `ap`:
   `PRIMARY_MSG`/`FALLBACK_MSG`/`TP_TOTAL` + `s14SwitchChannel`, `s14CopyOpening`, `s14ToggleTP`,
   `s14ToggleObj`, `s14FilterObj`/`s14ClearObjSearch`, branching node-swap tracking (`{% if
   is_branching %}` — giữ nguyên lồng trong này vì `is_branching` đã ngụ ý `script` truthy).

Không đổi HTML/markup, không đổi endpoint nào — thuần túy di chuyển + tách JS.

## Files to modify

1. `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`

## Implementation steps

1. Xác định 2 mốc trong file (dòng theo bản hiện tại):
   - Điểm chèn khối MỚI: ngay trước dòng 1341 (`{# ── Inline JS: client-side interactions only
     (A-S14-001..005; §9 INVARIANT) ── #}`).
   - Khối cần cắt ra khỏi `{% if script and ap %}` (dòng 1342-1559): các hàm
     `s14ToggleReason`/`s14SetResolveId` (~1438-1459), `s14CollectEnable`/`s14CollectSave`
     (~1462-1498), `s14TagChipToggle`/`s14TagMultiSave` (~1501-1527), stale-badge IIFE (~1530-1545).

2. Chèn khối mới (unconditional) — nội dung lấy nguyên văn từ vị trí cũ, sửa `S.draftId` →
   `(window.S14_STRIP && window.S14_STRIP.draftId) || ''`:

```html
{# ── Rail/collect JS: PHẢI chạy cả khi script=None (ST-CALL-NO-SCRIPT) — rail "Vì sao gọi" và
   dòng "Thu thập còn thiếu" luôn render bất kể có approach script hay không. Trước đây các hàm này
   nằm trong khối {% if script and ap %} bên dưới nên bấm nút không phản hồi gì với khách không có
   kịch bản (P0 fix). ── #}
<script>
(function () {
  // ── A-S14-025: reason "đã nói" tick ───────────────────────────────────
  window.s14ToggleReason = function (cb) {
    var card  = cb.closest('.s14-reason');
    var svg   = cb.parentElement ? cb.parentElement.querySelector('svg') : null;
    if (card) card.classList.toggle('s14-reason--said', cb.checked);
    if (svg)  svg.style.display = cb.checked ? '' : 'none';
    if (!card || card.classList.contains('s14-reason--primary')) return;
    s14SetResolveId('s14-resolve-action-ids', card.getAttribute('data-action-id'), cb.checked);
    s14SetResolveId('s14-resolve-task-ids', card.getAttribute('data-task-id'), cb.checked);
  };

  window.s14SetResolveId = function (inputId, id, add) {
    if (!id) return;
    var input = document.getElementById(inputId);
    if (!input) return;
    var ids = input.value ? input.value.split(',').filter(Boolean) : [];
    if (add) {
      if (ids.indexOf(id) === -1) ids.push(id);
    } else {
      ids = ids.filter(function (x) { return x !== id; });
    }
    input.value = ids.join(',');
  };

  // ── Collect: enable/disable save button ──────────────────────────────
  window.s14CollectEnable = function (key, val) {
    var btn = document.getElementById('s14-crow-add-' + key);
    if (btn) btn.disabled = !(val || '').trim();
  };

  // ── A-S14-020/021: save collect row via HTMX inline POST ─────────────
  window.s14CollectSave = function (key, kind, field) {
    var inp = document.getElementById('s14-collect-inp-' + key);
    if (!inp) return;
    var val = (inp.value || '').trim();
    if (!val) return;
    var target = document.getElementById('s14-crow-' + key);
    if (!target) return;
    var endpoint = kind === 'channel'
      ? '/customers/{{ party_id }}/contact'
      : (kind === 'custom_text'
        ? '/customers/{{ party_id }}/custom-field-inline'
        : '/customers/{{ party_id }}/core');
    var formData = new FormData();
    formData.append('inline', '1');
    if (kind === 'channel') {
      formData.append('action', 'add_channel');
      formData.append('add_identity_type', field);
      formData.append('add_identity_value', val);
    } else if (kind === 'custom_text') {
      formData.append('field_key', field);
      formData.append('value', val);
    } else {
      formData.append(field, val);
    }
    htmx.ajax('POST', endpoint,
      { target: target, swap: 'outerHTML', values: Object.fromEntries(formData) }
    );
  };

  // ── Health domain: tag_multiselect chip toggle ──
  window.s14TagChipToggle = function (key, el) {
    el.classList.toggle('chip-pill--on');
    var chipset = document.getElementById('s14-chipset-' + key);
    var anySelected = chipset && chipset.querySelector('.chip-pill--on');
    var btn = document.getElementById('s14-tagsave-' + key);
    if (btn) btn.disabled = !anySelected;
  };

  // ── Health domain: save selected chips via POST /tags/inline ──
  // source_activity_id đọc qua window.S14_STRIP (export global từ khối disposition-strip) —
  // KHÔNG dùng biến `S` trần (đó là biến cục bộ của closure khác, tham chiếu trần gây
  // ReferenceError trước khi có fix này).
  window.s14TagMultiSave = function (key, category) {
    var chipset = document.getElementById('s14-chipset-' + key);
    if (!chipset) return;
    var selected = Array.prototype.slice.call(chipset.querySelectorAll('.chip-pill--on'))
      .map(function (el) { return el.getAttribute('data-tag-name'); });
    if (!selected.length) return;
    var target = document.getElementById('s14-cr-' + key);
    if (!target) return;
    var draftId = (window.S14_STRIP && window.S14_STRIP.draftId) || '';
    htmx.ajax('POST', '/customers/{{ party_id }}/tags/inline', {
      target: target, swap: 'outerHTML',
      values: { tag_names: selected, category: category, source_activity_id: draftId }
    });
  };

  // ── Stale badge: mark refreshed_at if > 24 h (R2) ────────────────────
  (function () {
    var el = document.getElementById('s14-trust-freshness');
    if (!el) return;
    var ts = {{ (refreshed_at | tojson) if refreshed_at else '""' }};
    if (!ts) return;
    try {
      var d   = new Date(ts);
      var age = (Date.now() - d.getTime()) / 3600000;
      if (age > 24) {
        el.classList.add('s14-trust__item--stale');
        el.title = el.title + ' (quá 24h)';
        el.insertAdjacentHTML('afterbegin',
          '<svg class="ico" width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3 2 13h12L8 3z"/><line x1="8" y1="7" x2="8" y2="10"/><circle cx="8" cy="12" r="0.4" fill="currentColor" stroke="none"/></svg> ');
      }
    } catch (e) {}
  }());
}());
</script>
```

3. Trong khối `{% if script and ap %}` cũ (giờ chỉ còn phần script-dependent), **xóa** các hàm đã
   chuyển ra ngoài (`s14ToggleReason`, `s14SetResolveId`, `s14CollectEnable`, `s14CollectSave`,
   `s14TagChipToggle`, `s14TagMultiSave`, stale-badge IIFE) — không để trùng lặp định nghĩa 2 lần.
   Giữ nguyên: `PRIMARY_MSG`/`FALLBACK_MSG`/`TP_TOTAL`, `s14SwitchChannel`, `s14CopyOpening`,
   `s14ToggleTP`, `s14ToggleObj`, `s14FilterObj`/`s14ClearObjSearch`, khối `{% if is_branching %}`
   branching-node-swap tracking ở cuối.

## Tests

- Không có test JS tự động cho fragment này trong repo hiện tại (kiểm tra
  `grep -rl "s14CollectSave\|s14ToggleReason" crm/src/tests/` trước khi bắt đầu — nếu có test Python
  assert nội dung HTML/JS string, cần cập nhật theo vị trí mới).
- Chạy: `docker compose exec -T crm sh -c "cd /app/crm/src && python -m pytest tests/test_disposition_strip_v2.py tests/test_claim_context_snooze_r14.py -q"`
  (các test render fragment cockpit, đảm bảo template vẫn parse được, không lỗi Jinja).

## Verify thủ công

1. Mở cockpit cho 1 khách **KHÔNG** có approach script (`ST-CALL-NO-SCRIPT` — kiểm tra
   `{data_dir}/approach_scripts/{customer_id}.json` không tồn tại, hoặc chọn khách chưa được sinh
   kịch bản).
2. Ở rail "Vì sao gọi" (nếu có `rail_primary`/`rail_secondary`): tick checkbox "đã nói" trên 1 item
   secondary → phải thấy hidden input `#s14-resolve-action-ids`/`#s14-resolve-task-ids` cập nhật (mở
   DevTools kiểm tra `value`), KHÔNG còn im lặng.
3. Ở khối "Thu thập còn thiếu": nhập giá trị vào ô "Zalo" → nút `[+]` phải enable, bấm → row swap
   "✓ đã lưu".
4. Nếu có dòng `health_domain` (tag_multiselect): chọn 1 chip, bấm "Lưu" → không còn lỗi console
   `ReferenceError: S is not defined`, request POST `/tags/inline` gửi đi thành công.
5. Đối chứng: mở cockpit cho khách CÓ approach script — talk-track/talking-points/objection-handling
   vẫn hoạt động như cũ (không regress).

## Risks / rollback

- Rủi ro thấp: thuần di chuyển JS, không đổi logic bên trong hàm (trừ 1 dòng sửa bug `S.draftId`).
  Rollback = revert diff. Rủi ro chính cần tránh khi thực thi: **không định nghĩa trùng tên hàm 2 lần**
  (bước 3 bắt buộc xóa bản cũ sau khi copy sang khối mới).
