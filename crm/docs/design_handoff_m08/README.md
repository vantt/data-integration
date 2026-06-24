# Handoff: M08 — Ghi nhận tiếp xúc (Unified Contact Logging)

## Overview

Redesign của modal M08 trong CRM nội bộ. Thay thế 3 tab cũ (Hoạt động / Liên lạc / Ghi chú) bằng một luồng tuyến tính duy nhất: chọn **hình thức tiếp xúc → kênh cụ thể → kết quả → nội dung → (tuỳ chọn) lưu thành ghi chú hồ sơ → thời gian / đơn liên quan**.

Mục tiêu: giảm nhầm lẫn tab, hỗ trợ đa kênh (điện thoại/Zalo/FB/email/thăm/khác), tích hợp ghi chú hồ sơ trong cùng một POST.

---

## About the Design Files

The files bundled here are **HTML design references** — high-fidelity interactive prototypes showing the intended look, content, and conditional behaviour. They run on React + Babel in the browser for review convenience; the production target is **FastAPI + Jinja2 + HTMX** (SQLite backend).

Your task is to recreate these designs in the existing Jinja2 template system using its established patterns — NOT to ship the HTML prototype directly.

---

## Fidelity

**High-fidelity.** Pixel-accurate colours, typography, spacing, and interaction states. Recreate the UI precisely using the existing Precision Design System CSS classes (see §Design Tokens). The React component (`modal_m08.jsx`) is a live specification of every conditional section and state transition; read it as authoritative behaviour documentation, not as code to copy.

---

## Template to modify

```
crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html
```

---

## Form layout (linear, no tabs)

```
┌───────────────────────────────────────────────────────────┐
│ modal__head                                               │
│   modal__title  "Ghi nhận tiếp xúc"                      │
│   modal__sub    {party_name}                  [✕]        │
├───────────────────────────────────────────────────────────┤
│ modal__body  (flex-column gap-sp-4)                       │
│                                                           │
│  [IF contact_pref_notes]                                  │
│    .caveat.caveat--warn  ⚠ Lưu ý liên hệ: …             │
│                                                           │
│  Step 1 — HÌNH THỨC *                                     │
│    .radioset  6 radio-pills (icons + labels)              │
│                                                           │
│  Step 2 — KÊNH CỤ THỂ  (hidden for Thăm / Khác)         │
│    0 identities: .caveat.caveat--info + <input>           │
│    1 identity:   auto-selected chip + "Dùng khác" link    │
│    2+ identities: vertical radio group + "Khác…" row     │
│                                                           │
│  Step 3 — KẾT QUẢ *  (hidden for Khác)                  │
│    .radioset  (options vary by hình thức)                 │
│                                                           │
│  Step 3b — HẸN GỌI LẠI  (only: Gọi + Hẹn lại)          │
│    .m8-notebox                                            │
│      datetime-local  callback_at                          │
│      .chk-row  create_callback_task  [☑ default]          │
│                                                           │
│  Step 4 — NỘI DUNG  (* required for: Gọi+Đã nghe,       │
│                        Thăm+Gặp được)                    │
│    .inp.inp--area  (placeholder shifts by outcome)        │
│                                                           │
│  Step 5 — .chk-row  "Lưu thành ghi chú hồ sơ"          │
│    [when checked] .m8-notebox                             │
│      note_type select + visibility select                 │
│      pinned radioset                                      │
│                                                           │
│  .m8-rule  (hairline separator)                           │
│                                                           │
│  Step 6 — .field-row (2 cols)                            │
│    datetime-local  occurred_at  (prefilled ICT now)       │
│    text input      related_order_code  "ORD-…"            │
│                                                           │
├───────────────────────────────────────────────────────────┤
│ modal__actions                                            │
│   .btn--ghost  "Hủy"          .btn--primary  "Lưu hoạt động"│
└───────────────────────────────────────────────────────────┘
```

---

## Conditional sections — full decision table

### Step 2: KÊNH CỤ THỂ

| hình_thức | Hiện section? | identity_type filter |
|---|---|---|
| call | ✓ | `phone`, `phone_secondary` |
| zalo | ✓ | `zalo` |
| fb | ✓ | `facebook`, `psid` |
| email | ✓ | `email` |
| visit | ✗ | — |
| other | ✗ | — |

Section label per channel:

| hình_thức | SỐ ĐIỆN THOẠI | TÀI KHOẢN ZALO | TÀI KHOẢN FACEBOOK | ĐỊA CHỈ EMAIL |

**0 matches** → `caveat caveat--info` "Không có {kênh} trong hồ sơ — nhập thủ công hoặc bỏ qua." + `<input class="inp inp--mono">` for custom value.

**1 match** → auto-selected `.m8-chan.m8-chan--on` chip showing formatted value + `(tự chọn · 1 {kênh})` tag. A ghost link "Dùng {kênh} khác" reveals a custom input (replaces auto-selection).

**2+ matches** → vertical `.m8-chanset` list. Each row is `.m8-chan` (border, flex, radio dot). `is_primary` match pre-selected (`.m8-chan--on`). `contact_status=inactive` rows get `.m8-chan--off` (opacity 0.5) + `.m8-chan__tag.m8-chan__tag--off` "NGƯNG DÙNG". Last row is always a `.m8-chan.m8-chan--custom` "Nhập {kênh} khác…" that reveals a text input when selected.

Hidden inputs (for POST):
- `name="channel_identity_id"` — identity_id of selected row, or empty for custom
- `name="channel_value"` — raw value string

### Step 3: KẾT QUẢ

| hình_thức | Outcome options |
|---|---|
| call | Đã nghe · Không bắt · Hẹn lại · Từ chối |
| zalo | Đã phản hồi · Chưa phản hồi · Không phản hồi |
| fb | Đã phản hồi · Chưa phản hồi · Không phản hồi |
| email | Đã phản hồi · Chưa phản hồi · Không phản hồi |
| visit | Gặp được · Không gặp được |
| other | *(section hidden entirely)* |

Hidden input: `name="outcome"` value: `answered` / `no_answer` / `callback` / `refused` / `replied` / `pending` / `no_reply` / `met` / `not_met`.

### Step 3b: HẸN LẠI

Show only when `hình_thức = call` AND `outcome = callback`.

```html
<div class="m8-notebox">
  <label class="field">
    <span class="field__label">HẸN GỌI LẠI LÚC</span>
    <input type="datetime-local" name="callback_at" class="inp inp--mono"
           value="{{ now_ict | add_minutes(120) }}">
  </label>
  <label class="chk-row">
    <span class="chk-box chk-box--on">✓</span>
    <span class="chk-row__text">Tạo task nhắc tự động</span>
    <input type="checkbox" name="create_callback_task" value="1" checked hidden>
  </label>
</div>
```

### Step 4: NỘI DUNG — placeholder & required rules

| hình_thức | outcome | Placeholder | Required? |
|---|---|---|---|
| call | answered | "Nội dung trao đổi với khách…" | ✓ |
| call | no_answer / refused | "Ghi chú thêm (không bắt buộc)" | ✗ |
| call | callback | "Lý do hẹn lại, nội dung cần trao đổi…" | ✗ |
| zalo/fb/email | replied | "Nội dung phản hồi của khách…" | ✗ |
| zalo/fb/email | pending/no_reply | "Ghi chú thêm (không bắt buộc)" | ✗ |
| visit | met | "Kết quả buổi ghé thăm…" | ✓ |
| visit | not_met | "Ghi chú thêm (không bắt buộc)" | ✗ |
| other | — | "Nội dung tiếp xúc…" | ✗ |

In Jinja2, drive this via a JS function `m08UpdateBody()` that reads the selected hình_thức and outcome on every change, then sets `textarea.placeholder` and `textarea.required`.

### Step 5: LƯU THÀNH GHI CHÚ HỒ SƠ

Collapsed by default (checkbox unchecked). When checked, reveal:

```html
<div class="m8-notebox" id="m08-note-opts" style="display:none">
  <div class="field-row">
    <label class="field">
      <span class="field__label">LOẠI GHI CHÚ</span>
      <div class="inp-sel">
        <select name="note_type">
          <option value="outcome">Kết quả</option>
          <option value="general">Chung</option>
          <option value="preference">Sở thích</option>
          <option value="warning">Cảnh báo</option>
          <option value="internal">Nội bộ</option>
        </select>
        <span class="inp-sel__chev">▾</span>
      </div>
    </label>
    <label class="field">
      <span class="field__label">HIỂN THỊ</span>
      <div class="inp-sel">
        <select name="visibility">
          <option value="team">Team</option>
          <option value="private">Riêng tư</option>
        </select>
        <span class="inp-sel__chev">▾</span>
      </div>
    </label>
  </div>
  <label class="field">
    <span class="field__label">GHIM</span>
    <div class="radioset">
      <label class="radio-pill radio-pill--on"><span class="radio-pill__dot"></span>Không ghim
        <input type="radio" name="pinned" value="0" checked hidden></label>
      <label class="radio-pill"><span class="radio-pill__dot"></span>Ghim
        <input type="radio" name="pinned" value="1" hidden></label>
    </div>
  </label>
</div>
```

Default `note_type` by hình_thức (set via JS on channel change):

| hình_thức | default note_type |
|---|---|
| call / zalo / fb / visit | `outcome` |
| email | `general` |
| other | `general` |

---

## JavaScript (inline in template)

```js
function m08Init() {
  // prefill occurred_at with current ICT (UTC+7)
  const d = new Date(Date.now() + 7 * 3600000);
  const p = n => String(n).padStart(2, '0');
  const ict = `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())}T${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
  document.getElementById('m08-occurred-at').value = ict;
  // prefill callback_at = ICT + 2h
  const d2 = new Date(Date.now() + 9 * 3600000);
  document.getElementById('m08-callback-at').value =
    `${d2.getUTCFullYear()}-${p(d2.getUTCMonth()+1)}-${p(d2.getUTCDate())}T${p(d2.getUTCHours())}:${p(d2.getUTCMinutes())}`;
  m08OnHinhThuc(document.querySelector('[name=hinh_thuc]:checked')?.value || 'call');
}

function m08OnHinhThuc(val) {
  // show/hide channel section
  const chSec = document.getElementById('m08-channel-sec');
  chSec.style.display = ['visit','other'].includes(val) ? 'none' : '';
  // show/hide outcome section
  document.getElementById('m08-outcome-sec').style.display = val === 'other' ? 'none' : '';
  // update outcome pills
  m08UpdateOutcomes(val);
  // set default note_type
  const noteTypeSel = document.querySelector('[name=note_type]');
  if (noteTypeSel) noteTypeSel.value = val === 'email' || val === 'other' ? 'general' : 'outcome';
  // reset outcome + hide callback
  document.querySelectorAll('[name=outcome]').forEach(r => r.checked = false);
  m08OnOutcome(null);
  m08UpdateBody(val, null);
}

function m08UpdateOutcomes(ht) {
  const sets = {
    call: [{v:'answered',l:'Đã nghe'},{v:'no_answer',l:'Không bắt'},{v:'callback',l:'Hẹn lại'},{v:'refused',l:'Từ chối'}],
    chat: [{v:'replied',l:'Đã phản hồi'},{v:'pending',l:'Chưa phản hồi'},{v:'no_reply',l:'Không phản hồi'}],
    visit:[{v:'met',l:'Gặp được'},{v:'not_met',l:'Không gặp được'}],
  };
  const group = ht === 'call' ? 'call' : ht === 'visit' ? 'visit' : 'chat';
  const container = document.getElementById('m08-outcome-pills');
  container.innerHTML = (sets[group] || []).map(o =>
    `<label class="radio-pill" onclick="m08OnOutcome('${o.v}');this.classList.add('radio-pill--on');document.querySelectorAll('#m08-outcome-pills .radio-pill').forEach(p=>p!==this&&p.classList.remove('radio-pill--on'))">
       <span class="radio-pill__dot"></span>${o.l}
       <input type="radio" name="outcome" value="${o.v}" hidden>
     </label>`
  ).join('');
}

function m08OnOutcome(val) {
  document.getElementById('m08-callback-sec').style.display =
    (val === 'callback' && document.querySelector('[name=hinh_thuc]:checked')?.value === 'call') ? '' : 'none';
  m08UpdateBody(document.querySelector('[name=hinh_thuc]:checked')?.value, val);
}

function m08UpdateBody(ht, oc) {
  const ta = document.getElementById('m08-body');
  const placeholders = {
    call_answered: 'Nội dung trao đổi với khách…',
    call_callback: 'Lý do hẹn lại, nội dung cần trao đổi…',
    call_: 'Ghi chú thêm (không bắt buộc)',
    chat_replied: 'Nội dung phản hồi của khách…',
    chat_: 'Ghi chú thêm (không bắt buộc)',
    visit_met: 'Kết quả buổi ghé thăm…',
    visit_: 'Ghi chú thêm (không bắt buộc)',
    other_: 'Nội dung tiếp xúc…',
  };
  const chatTypes = ['zalo','fb','email'];
  const group = chatTypes.includes(ht) ? 'chat' : ht;
  const key = `${group}_${oc||''}`;
  ta.placeholder = placeholders[key] || placeholders[`${group}_`] || '';
  const required = (ht==='call'&&oc==='answered') || (ht==='visit'&&oc==='met');
  ta.required = required;
  document.getElementById('m08-body-label').dataset.required = required ? '1' : '';
}

function m08OnSaveAsNote(checked) {
  document.getElementById('m08-note-opts').style.display = checked ? '' : 'none';
}
```

---

## POST endpoint

`POST /customers/{party_id}/log-activity`

| Field | Type | Notes |
|---|---|---|
| `hinh_thuc` | str | `call\|zalo\|fb\|email\|visit\|other` |
| `channel_identity_id` | str? | identity_id of selected channel row |
| `channel_value` | str? | raw value for display / logging |
| `outcome` | str? | see outcome table above |
| `body` | str | activity text / note body |
| `occurred_at` | str | `YYYY-MM-DDTHH:MM` (ICT) |
| `related_order_code` | str? | soft ref, e.g. `ORD-20060812` |
| `callback_at` | str? | `YYYY-MM-DDTHH:MM` (ICT), when outcome=callback |
| `create_callback_task` | `"1"`? | checked by default |
| `save_as_note` | `"1"`? | expand and check |
| `note_type` | str | `outcome\|general\|preference\|warning\|internal` |
| `pinned` | `"0"\|"1"` | default `"0"` |
| `visibility` | str | `team\|private` |

Handler logic:
1. Map `hinh_thuc` → `activity_type` + `direction="out"` + `channel=channel_value`
2. `activity_log.log_activity(act_data)` → `Activity` with `activity_id`
3. If `save_as_note=="1"` and `body.strip()`:  
   `notes.add_note(party_id, body, note_type=note_type, pinned=pinned=="1", visibility=visibility, source_activity_id=activity.activity_id)`
4. Return `HX-Redirect: /customers/{party_id}?tab=timeline`

---

## New CSS classes to add (stylesheet)

Add these to `app.css` or the DS CRM stylesheet. They follow the Precision token system.

```css
/* M08 — channel picker rows */
.m8-chanset { display: flex; flex-direction: column; gap: var(--sp-2); }
.m8-chan {
  display: flex; align-items: center; gap: 9px; cursor: pointer;
  padding: 9px var(--sp-3); border: 1px solid var(--border);
  border-radius: var(--radii-control); color: var(--fg-1);
  transition: all var(--dur-fast) var(--ease-fast);
}
.m8-chan:hover { border-color: var(--border-strong); }
.m8-chan--on {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  color: var(--fg);
}
.m8-chan--on .radio-pill__dot {
  border-color: var(--accent); background: var(--accent);
  box-shadow: inset 0 0 0 2px var(--bg-surface);
}
.m8-chan--off { opacity: 0.5; }
.m8-chan__val { flex: 1; font-size: 14px; }
.m8-chan__auto {
  font-family: var(--font-mono); font-size: 10px;
  letter-spacing: var(--tracking-mono); color: var(--moss-500);
  white-space: nowrap;
}
.m8-chan__tag {
  font-family: var(--font-mono); font-size: 9.5px; text-transform: uppercase;
  letter-spacing: var(--tracking-eyebrow); color: var(--fg-tertiary);
  border: 1px solid var(--border); border-radius: var(--radii-hairline);
  padding: 2px 6px;
}
.m8-chan__tag--off {
  color: var(--coral-500);
  border-color: color-mix(in srgb, var(--coral-500) 30%, transparent);
}
.m8-chan--custom { flex-direction: column; align-items: stretch; gap: 0; }
.m8-chan__head { display: flex; align-items: center; gap: 9px; cursor: pointer; }

/* M08 — inset option box (callback / note opts) */
.m8-notebox {
  display: flex; flex-direction: column; gap: var(--sp-3);
  padding: var(--sp-4); margin-top: var(--sp-3);
  background: var(--bg-surface); border: 1px solid var(--border);
  border-left: 2px solid var(--accent);
  border-radius: 0 var(--radii-control) var(--radii-control) 0;
}

/* M08 — section divider */
.m8-rule { height: 1px; background: var(--border); margin: var(--sp-2) 0; }
```

---

## Migration required

**File:** `crm/migrations/0012_note_source_activity.up.sql`

```sql
ALTER TABLE crm_note
  ADD COLUMN source_activity_id TEXT REFERENCES crm_activity(activity_id);

CREATE INDEX IF NOT EXISTS idx_note_source_activity
  ON crm_note(source_activity_id);
```

---

## Backend changes required

### `profile.py` — Note dataclass

```python
@dataclass
class Note:
    # ... existing fields ...
    source_activity_id: Optional[str] = None
```

### `profile_service.py` — add_note()

```python
async def add_note(
    self, party_id: str, body: str,
    note_type: str = "general",
    pinned: bool = False,
    visibility: str = "team",
    source_activity_id: Optional[str] = None,   # ← new
) -> Note:
```

### `tag_note_repository.py` — SQL

```python
_SQL_INSERT = """
    INSERT INTO crm_note (note_id, party_id, body, note_type, pinned,
                          visibility, source_activity_id, ...)
    VALUES (?, ?, ?, ?, ?, ?, ?, ...)
"""
_SQL_LIST = """
    SELECT note_id, party_id, body, note_type, pinned,
           visibility, source_activity_id, ...
    FROM crm_note WHERE party_id = ?
"""
```

### `screen_customer_360.py` — GET handler

```python
async def handle_modal_m08(party_id: str, ...):
    identities = await party_repo.list_identities(party_id)
    contact_pref_notes = await note_repo.list_pinned_by_type(party_id, "preference")
    return templates.TemplateResponse("fragments/modal_log_activity.html", {
        "party_id": party_id,
        "party_name": party.display_name,
        "identities": identities,           # ← new
        "contact_pref_notes": contact_pref_notes,  # ← new
    })
```

---

## Design Tokens (Precision DS)

All values come from `colors_and_type.css` custom properties. Key tokens used:

| Token | Value | Use |
|---|---|---|
| `--accent` | `#e8a341` (amber) | Selected state border/bg, required asterisk |
| `--moss-500` | `#84b577` | Auto-selected tag, success signals |
| `--coral-500` | `#e0746c` | Inactive identity tag, field errors |
| `--honey-500` | `#d4a548` | Warning caveat mark |
| `--bg-surface` | `#15151a` (approx) | Input, select, notebox background |
| `--bg-raised` | `#1c1c22` (approx) | Modal background |
| `--border` | `1px solid` hairline | Default borders |
| `--border-strong` | stronger hairline | Hover state, checkbox |
| `--sp-2` | 4px | Tight gap (radioset, chanset) |
| `--sp-3` | 8px | Control padding, field-row gap |
| `--sp-4` | 12px | Notebox padding, action gap |
| `--sp-5` | 16px | Modal body/head padding |
| `--radii-control` | 4px | Inputs, buttons, channel rows |
| `--radii-hairline` | 2px | Tags, chips |
| `--radii-pill` | 999px | Radio dot |
| `--dur-fast` | 120ms | Border/bg transitions |
| `--font-mono` | Geist Mono | Labels, field__label, mono values |
| `--font-display` | Fraunces | Modal title |
| `--tracking-eyebrow` | 0.18–0.22em | ALL-CAPS labels |
| `--tracking-mono` | 0.04em | Mono values |

---

## Files in this bundle

| File | Purpose |
|---|---|
| `README.md` | This handoff document |
| `modal_m08.jsx` | Full interactive prototype component — authoritative spec for conditional logic and state |
| `M08 Contact Logging.html` | Review harness — open in browser to interact with all 4 data scenarios |
| `m08_styles.css` | New CSS classes to add to the DS CRM stylesheet (extracted from the prototype) |
