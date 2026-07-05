# Phase 05 — R14 Warn-with-Ack (D3)

**Status:** DONE | **Priority:** P1 | **Depends on:** Phase 04 (cùng đụng S14 templates — thực hiện sau 04)

## Context links

- Design: `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §6-D3, §6-D4 (custom_fields registry)
- Master plan: `plans/260705-1146-crm-ux-data-loop-improvements/plan.md`
- Spec: `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`, `crm/docs/ui-spec/20-domain-rules.md`

## Current R14 behavior (verified)

Trong `c360_call_cockpit_panel.html`:
```jinja
{% set is_stop = (meta_rec.recommended == false) if meta else false %}
```
Khi `is_stop=true`: toàn bộ hai cột (LEFT + RIGHT) bị ẩn, thay bằng `.s14-frame--stop` với:
- Banner "KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH"
- `ap.reason_if_not_recommended` nếu có
- CTAs: "Tạo task xác minh" (M05) và "Xem hồ sơ 360" (S03)
- **Không có nút unlock.** Hard stop hoàn toàn.

`20-domain-rules.md` R14 hiện dùng từ "STOP state" → cần đổi thành "warn-with-ack".

## Requirements (D3)

1. `recommended=false` → **sticky red banner** "⛔ KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH" + hiện `reason_if_not_recommended` (rationale máy đưa ra).
2. Talk-track + reason rail **thu gọn / che mờ** (CSS `s14-locked`), không bị ẩn hoàn toàn.
3. Nút **"Tôi đã xác minh — vẫn tiếp tục"** ở cuối banner → 1-click intentional friction.
4. Khi ack: (a) POST audit activity; (b) unlock hai cột (remove `s14-locked` CSS); (c) banner collapse.
5. Ack state = **per-session per-customer, client-side** — không persist qua ngày, không cần DB column. Justification: verification intent có thể đổi sau mỗi ca làm việc; stale ack nguy hiểm hơn là phải ack lại.
6. **Không hard-block** (chưa có `consent='denied'` record nào — default contactable).
7. Audit: `activity_type='other'`, `custom_fields={"r14_ack": true, "script_id": ..., "reason_shown": ...}` → manager đếm qua `json_extract` trên `crm_activity_log` export. Không dashboard mới trong phase này (YAGNI).

## Files to modify / create

| File | Thay đổi |
|---|---|
| `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` | Đổi R14 từ hard-stop → warn-with-ack: banner sticky + `s14-locked` overlay + unlock button |
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` | Thêm `POST /customers/{party_id}/r14-ack` endpoint (ghi audit activity) |
| `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` | Cập nhật states ST-CALL-STOP → ST-CALL-R14-WARN; stop_banner region; interaction A-S14-027 (btn_r14_ack) |
| `crm/docs/ui-spec/20-domain-rules.md` | R14 rule text: "STOP state" → "warn-with-ack"; ghi nhận unlock flow |

## Implementation steps

### Step 1 — New endpoint: POST /customers/{party_id}/r14-ack

Thêm vào `screen_customer_360_activity.py` trong `register_activity_routes()`:

```python
@router.post("/customers/{party_id}/r14-ack", response_class=HTMLResponse)
async def handle_r14_ack(request: Request, party_id: str):
    """Log R14 acknowledgment audit activity. Returns 204 (no panel re-render)."""
    form = await request.form()
    script_id = form.get("script_id", "")
    reason_shown = form.get("reason_shown", "")
    actor_id = _current_user_id(request)

    if activity_log is not None:
        try:
            import json, uuid
            from shared.timestamps import utc_now
            from domain.entities.activity import ActivityLog
            activity_log.insert(ActivityLog(
                activity_id=str(uuid.uuid4()),
                party_id=party_id,
                activity_type="other",
                direction="internal",
                subject="R14 override: NV đã xác minh và tiếp tục gọi theo kịch bản",
                body=None,
                created_by=actor_id,
                created_at=utc_now(),
                custom_fields=json.dumps({
                    "r14_ack": True,
                    "script_id": script_id,
                    "reason_shown": reason_shown,
                }),
            ))
            if db is not None:
                db.commit()
        except Exception as exc:
            log.warning("r14_ack: activity write failed %s: %s", party_id, exc)

    return Response(status_code=204)
```

Dependencies: `activity_log` và `db` đã được inject trong `register_activity_routes()` signature — không cần thay đổi factory wiring.

### Step 2 — Template: đổi hard-stop → warn-with-ack

Trong `c360_call_cockpit_panel.html`, phần `{% if is_stop %}`:

**Thay đổi 1:** Giữ hai cột cockpit render bình thường, nhưng wrap trong `div#s14-content` với class `s14-locked` khi `is_stop`:

```jinja
{% if is_stop %}
{# ── R14 warn-with-ack banner (sticky, above two-pane) ─────── #}
<div class="s14-r14-banner" id="s14-r14-banner">
  <div class="s14-r14-banner__icon">⛔</div>
  <div class="s14-r14-banner__body">
    <strong>KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH</strong>
    {% if ap and ap.reason_if_not_recommended %}
    <div class="s14-r14-banner__reason">Lý do: {{ ap.reason_if_not_recommended }}</div>
    {% endif %}
    <div class="s14-r14-banner__ctas">
      <button class="btn btn--ghost btn--sm"
              hx-get="/modals/m05?party_id={{ party_id }}&source=verify_account&prefill_title=Xác+minh+loại+tài+khoản"
              hx-target="#modal-root" hx-swap="innerHTML">Tạo task xác minh</button>
      <a class="btn btn--ghost btn--sm" href="/customers/{{ party_id }}">Xem hồ sơ 360</a>
      <button class="btn btn--danger btn--sm" id="s14-r14-ack-btn"
              hx-post="/customers/{{ party_id }}/r14-ack"
              hx-vals='{"script_id": "{{ (meta.script_id or '') if meta else '' }}",
                        "reason_shown": "{{ (ap.reason_if_not_recommended or '') if ap else '' | truncate(200) }}"}'
              hx-on::after-request="s14UnlockR14()">
        Tôi đã xác minh — vẫn tiếp tục
      </button>
    </div>
  </div>
</div>
<div id="s14-content" class="s14-locked">
{% else %}
<div id="s14-content">
{% endif %}
```

Kết thúc bằng `</div>{# /s14-content #}`.

**Thay đổi 2:** Xóa toàn bộ block `{% if is_stop %}...{% else %}...{% endif %}` cũ bao quanh `.s14-frame--stop`. Hai cột render bình thường trong mọi trường hợp.

**Thay đổi 3:** Thêm inline JS unlock function (INVARIANT §9 — không re-render `#s14-panel-root`):

```html
<script>
function s14UnlockR14() {
  var banner = document.getElementById('s14-r14-banner');
  var content = document.getElementById('s14-content');
  if (banner) banner.style.display = 'none';
  if (content) content.classList.remove('s14-locked');
}
</script>
```

**CSS mới** (thêm vào `ds-extra.css` hoặc inline):
```css
.s14-r14-banner {
  background: var(--coral-100, #fff0f0);
  border: 2px solid var(--coral-500, #e53e3e);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  position: sticky;
  top: 0;
  z-index: 10;
}
.s14-locked {
  opacity: 0.35;
  pointer-events: none;
  user-select: none;
  filter: blur(1px);
}
```

### Step 3 — Spec updates

**S14-call-mode-cockpit.md:**
- States: đổi `ST-CALL-STOP` → `ST-CALL-R14-WARN`: banner visible + content dimmed + unlock button.
- `stop_banner` region description: cập nhật sample hiện "Tôi đã xác minh" button.
- Thêm interaction:
  ```yaml
  - id: A-S14-027
    element: btn_r14_ack
    region: stop_banner
    trigger: click
    action: mutate
    effects: [stop_banner.hide, s14_content.unlock, activity_log.write_r14_ack]
  ```

**20-domain-rules.md R14:**
- Đổi "phải vào STOP state: ẩn talk-track/lời thoại..." → "phải vào WARN state: banner cảnh báo sticky + nội dung che mờ; nút 'Tôi đã xác minh' mở khoá (1-click friction); ghi audit activity r14_ack."
- Thêm: "Hard-block CHỈ khi tương lai có `consent='denied'` thật."

## Tests & validation

| Test | Cách kiểm tra |
|---|---|
| `recommended=false` renders banner | Template render với `meta={"recommended": False, ...}` → có `s14-r14-banner` div + `s14-locked` class |
| `reason_if_not_recommended` shown | `ap.reason_if_not_recommended = "nghi B2B"` → text hiện trong banner |
| `recommended=true` unaffected | `meta={"recommended": True}` → không có banner, không có `s14-locked`, hai cột render bình thường |
| `recommended=None` (no meta) | `meta=None` → không có banner (default không stop) |
| Ack unlocks + writes audit | POST `/customers/{pid}/r14-ack` → 204 + `crm_activity_log` có row `activity_type='other'`, `custom_fields` chứa `r14_ack=true` |
| JS unlock removes lock class | `s14UnlockR14()` sau response → banner hidden, `s14-locked` class removed |
| `script_id` / `reason_shown` in custom_fields | Verify JSON fields khớp với form values truyền vào |
| activity_log unavailable | `activity_log=None` → 204 vẫn trả về, không 500 |

## Risks & rollback

- **Invariant §9:** ack button POST chỉ trả 204 (no HTMX swap of `#s14-panel-root`). Unlock là pure JS. An toàn với invariant.
- **Session state:** nếu NV reload trang giữa cuộc gọi → banner hiện lại, phải ack lại. Đây là intentional (mỗi session xác minh độc lập). Cần cảnh báo NV qua tooltip "xác nhận không lưu qua reload".
- **CSS blur:** `filter: blur(1px)` có thể ảnh hưởng performance trên máy yếu khi content dài. Rollback: đổi `blur(1px)` → `opacity: 0.4` only.
- **`script_id` field:** `wh_approach_script` hiện không có field `script_id` rõ ràng trong code (`meta` dict chỉ có `recommended`, `confidence`, `refreshed_at`). Cần verify hoặc dùng `customer_id` làm proxy. Mark as unresolved.
- **Rollback R14 hard-stop:** nếu cần hoàn tác, xóa banner block + khôi phục `{% if is_stop %}...s14-frame--stop...{% else %}` pattern cũ. Không có migration.

## Unresolved questions

1. **`script_id` for audit:** `wh_approach_script` table có `script_id` column không? Hiện `approach_repo.get_by_customer_id()` trả object nhưng `meta` dict chỉ build `{recommended, confidence, refreshed_at}`. Nếu không có `script_id`, dùng `customer_id` hoặc `refreshed_at` làm identifier. Cần verify `wh_approach_script` schema.
2. **Manager metric follow-up:** `json_extract(custom_fields, '$.r14_ack')` trên export `crm_activity_log` sẽ ra report trong phase sau. Confirm scope không vào phase này.
3. **`hx-vals` escaping:** `reason_if_not_recommended` có thể chứa dấu `"` — cần escape trong `hx-vals` JSON hoặc dùng form hidden inputs thay vì inline JSON string.
