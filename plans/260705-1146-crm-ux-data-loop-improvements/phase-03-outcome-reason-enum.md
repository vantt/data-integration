# Phase 03 — Outcome Reason Enum (D2)

**Status:** DONE  **Ưu tiên:** P1  
**Phụ thuộc:** Phase 02 (cùng đụng M08 template + activity route — không chạy song song)  
**Spec:** `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §6-D2  
**Mục tiêu:** `contact_outcome` (enum) là trường duy nhất; thêm `outcome_reason` 2 tầng; M08 pill 2 bước; warehouse passthrough.

---

## Context links

- Design D2: `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §6-D2
- Entity: `crm/src/domain/entities/activity.py`
- Service: `crm/src/application/activity_service.py`
- Route: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py`
- Repo: `crm/src/adapters/outbound/sqlite/activity_repository.py`
- Template: `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html`
- Export: `orchestration/assets/crm_writeback_assets.py`
- Spec M08: `crm/docs/ui-spec/modals/M08-log-activity-modal.md`

---

## Requirements

### Enum 2 tầng

**Tầng 1 — `contact_outcome` (kết quả tiếp cận, theo kênh)**

| Kênh | Giá trị hợp lệ |
|------|----------------|
| call | `answered` / `no_answer` / `busy` / `wrong_number` / `callback` / `refused` |
| messaging (zalo/fb/email) | `replied` / `no_reply` / `pending_reply` / `refused` / `blocked` |
| visit | `met` / `not_met` |

`busy` và `wrong_number` là giá trị **MỚI** so với enum cũ (chỉ có `no_answer` / `callback` / `refused`).  
`blocked` là giá trị **MỚI** cho messaging.

**Tầng 2 — `outcome_reason` (nullable, bắt buộc khi `refused` hoặc `answered`-không-chốt)**

| Giá trị | Ý nghĩa |
|---------|---------|
| `budget` | giá / ngân sách |
| `timing` | chưa tới lúc |
| `product_fit` | không hợp nhu cầu |
| `competitor` | đã mua chỗ khác |
| `stock` | hết hàng / chờ hàng |
| `trust` | nghi ngại |
| `no_need` | hết nhu cầu |
| `other` | khác |

`outcome_reason` **bắt buộc** khi `contact_outcome == 'refused'`. Tùy chọn (không bắt buộc) khi `answered` (NV có thể bỏ qua nếu gọi thành công không cần lý do bổ sung). Client-side JS enforce; server-side validate cho `refused`.

### Quy tắc ngừng ghi free-text

- `outcome` (cột cũ) → **không ghi mới**. Giữ đọc để hiển thị timeline cũ.
- `contact_outcome` → cột canonical mới, viết enum validated.
- `body` → vẫn là ghi chú tự do (không đổi).
- Backward compat: `last_contact_repo.upsert` hiện check `activity.outcome`; sau Phase 03 cần check `activity.contact_outcome` thay vì (hoặc thêm vào).

### Pilot note (§8.3 design doc)

Enum `outcome_reason` cần NV dùng thử 2 tuần rồi hiệu chỉnh trước khi khoá mart mapping. Ghi rõ trong code comment + spec.

---

## Files cần sửa / tạo

| File | Thay đổi |
|---|---|
| `crm/migrations/0035_activity_outcome_reason.up.sql` | **NEW** — `ALTER TABLE crm_activity_log ADD COLUMN outcome_reason TEXT` |
| `crm/migrations/0035_activity_outcome_reason.down.sql` | **NEW** — `ALTER TABLE crm_activity_log DROP COLUMN outcome_reason` |
| `crm/src/domain/entities/activity.py` | Thêm constants `VALID_CONTACT_OUTCOMES_*` + `VALID_OUTCOME_REASONS` + `REASON_REQUIRED_OUTCOMES`; thêm fields `contact_outcome`, `outcome_reason` vào `Activity` dataclass |
| `crm/src/adapters/outbound/sqlite/activity_repository.py` | Extend INSERT + SELECT để include `contact_outcome`, `outcome_reason` |
| `crm/src/application/activity_service.py` | Validate `contact_outcome` per channel, validate `outcome_reason` required-when; update `last_contact` trigger |
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` | Parse `contact_outcome: str = Form(default="")` + `outcome_reason: str = Form(default="")` |
| `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html` | Pill 2 bước: contact_outcome row → outcome_reason row (conditional) |
| `orchestration/assets/crm_writeback_assets.py` | Thêm `a.outcome_reason` vào export SELECT |
| `transformation/models/marts/crm/mart_crm_activity_log.sql` | **NEW hoặc EXTEND** — passthrough `outcome_reason`, giữ `is_reached` mapping |
| `crm/docs/ui-spec/modals/M08-log-activity-modal.md` | Thêm section pill 2 bước + enum tables |

---

## Implementation steps

### Step 1 — Migration

**`crm/migrations/0035_activity_outcome_reason.up.sql`:**
```sql
-- Migration 0035 UP: structured outcome_reason for activity log (D2 Phase 03)
-- contact_outcome (added 0013) is already present.
-- outcome_reason: nullable; required by server when contact_outcome = 'refused'.
-- Pilot: enum set reviewed after 2 weeks before locking mart mapping (design §8.3).
ALTER TABLE crm_activity_log ADD COLUMN outcome_reason TEXT;
```

**`crm/migrations/0035_activity_outcome_reason.down.sql`:**
```sql
-- Migration 0035 DOWN
ALTER TABLE crm_activity_log DROP COLUMN outcome_reason;
```

Apply: `docker exec crm python -m crm.src.migrations.runner` hoặc cách runner hiện tại.

### Step 2 — Domain entity: constants + fields

`crm/src/domain/entities/activity.py` — thêm sau block `VALID_ACTIVITY_TYPES`:

```python
# ---------------------------------------------------------------------------
# contact_outcome constants (D2 — per channel enum)
# ---------------------------------------------------------------------------
CONTACT_OUTCOMES_CALL = [
    "answered", "no_answer", "busy", "wrong_number", "callback", "refused",
]
CONTACT_OUTCOMES_MESSAGING = [
    "replied", "no_reply", "pending_reply", "refused", "blocked",
]
CONTACT_OUTCOMES_VISIT = ["met", "not_met"]

VALID_CONTACT_OUTCOMES: list[str] = list(
    dict.fromkeys(CONTACT_OUTCOMES_CALL + CONTACT_OUTCOMES_MESSAGING + CONTACT_OUTCOMES_VISIT)
)

# Channel type → valid outcomes mapping (for server-side per-channel validation)
CONTACT_OUTCOMES_BY_CHANNEL_TYPE: dict[str, list[str]] = {
    "call":  CONTACT_OUTCOMES_CALL,
    "zalo":  CONTACT_OUTCOMES_MESSAGING,
    "fb":    CONTACT_OUTCOMES_MESSAGING,
    "email": CONTACT_OUTCOMES_MESSAGING,
    "visit": CONTACT_OUTCOMES_VISIT,
}

# ---------------------------------------------------------------------------
# outcome_reason constants (D2 — nullable, required when refused)
# ---------------------------------------------------------------------------
VALID_OUTCOME_REASONS = [
    "budget", "timing", "product_fit", "competitor",
    "stock", "trust", "no_need", "other",
]
# Server enforces reason when contact_outcome in this set
REASON_REQUIRED_OUTCOMES = {"refused"}
```

`Activity` dataclass — thêm 2 fields sau `channel_type`:
```python
contact_outcome: Optional[str] = None   # enum per D2; replaces free-text outcome for new rows
outcome_reason: Optional[str] = None    # nullable; required when contact_outcome in REASON_REQUIRED_OUTCOMES
```

### Step 3 — Repository: extend INSERT / SELECT

`crm/src/adapters/outbound/sqlite/activity_repository.py`:

INSERT — thêm `contact_outcome`, `outcome_reason` vào column list và VALUES:
```sql
INSERT INTO crm_activity_log (
  activity_id, party_id, activity_type, direction, channel,
  subject, body, outcome, related_order_code,
  staff_user_id, occurred_at, created_at, custom_fields, task_id, channel_type,
  contact_outcome, outcome_reason
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```
Thêm `activity.contact_outcome, activity.outcome_reason` vào params tuple.

SELECT — thêm 2 cột vào SELECT; map vào dataclass constructor.

### Step 4 — ActivityService: validation

`crm/src/application/activity_service.py` — trong `log_activity`:

```python
contact_outcome = (activity_data.get("contact_outcome") or "").strip() or None
outcome_reason  = (activity_data.get("outcome_reason") or "").strip() or None
channel_type    = (activity_data.get("channel_type") or "").strip()

# Validate contact_outcome per channel (if provided)
if contact_outcome:
    valid_for_channel = CONTACT_OUTCOMES_BY_CHANNEL_TYPE.get(channel_type, VALID_CONTACT_OUTCOMES)
    if contact_outcome not in valid_for_channel:
        raise ValueError(f"contact_outcome {contact_outcome!r} not valid for channel_type {channel_type!r}")
    # Validate outcome_reason required-when
    if contact_outcome in REASON_REQUIRED_OUTCOMES and not outcome_reason:
        raise ValueError("outcome_reason is required when contact_outcome is 'refused'")
    if outcome_reason and outcome_reason not in VALID_OUTCOME_REASONS:
        raise ValueError(f"unknown outcome_reason {outcome_reason!r}")
```

Trong Activity constructor:
```python
contact_outcome=contact_outcome,
outcome_reason=outcome_reason,
```

Update `last_contact` trigger — đổi điều kiện từ `activity.outcome` sang ưu tiên `contact_outcome`:
```python
effective_outcome = activity.contact_outcome or activity.outcome
if effective_outcome and self._last_contact_repo is not None:
    self._last_contact_repo.upsert(..., result=effective_outcome, ...)
```

### Step 5 — Web route: parse new form fields

`screen_customer_360_activity.py` — `handle_log_activity` signature:
```python
contact_outcome: str = Form(default=""),
outcome_reason:  str = Form(default=""),
```

Cập nhật `act_data`:
```python
act_data["contact_outcome"] = contact_outcome.strip() or None
act_data["outcome_reason"]  = outcome_reason.strip() or None
# Không set act_data["outcome"] nữa cho new rows.
```

`_m08_ctx` không cần thay đổi (context M08 GET chỉ trả về identities/notes — không cần enum lists vì JS handles pill rendering).

### Step 6 — M08 template: pill 2 bước

`modal_log_activity.html` — trong section log form:

**Đổi hidden field:**
```html
{# contact_outcome replaces outcome for new rows (D2 Phase 03) #}
<input type="hidden" name="contact_outcome" id="m08-out" value="">
```
(Xoá `name="outcome"` trên hidden field; giữ tên `id="m08-out"` để JS cũ vẫn chạy.)

**Đổi outcome pills container — thêm `id="m08-outcome-row1"`:**
Đổi `name="outcome"` → `name="contact_outcome"` trong các radio pill.

**Thêm outcome_reason row (tầng 2) — sau outcome pills, ẩn mặc định:**
```html
{# Step 3b2 — OUTCOME REASON (hiện khi refused hoặc answered) #}
<div id="m08-reason-sec" class="field" style="display:none">
  <span class="field__label">LÝ DO</span>
  <div class="radioset" id="m08-reason-pills">
    {# JS rebuilds content theo outcome context #}
  </div>
  <input type="hidden" name="outcome_reason" id="m08-reason-val" value="">
</div>
```

**Cập nhật JS `m08OnOutcome`** — thêm logic hiện/ẩn reason row và rebuild reason pills:

```javascript
var REASON_PILLS = [
  {v:'budget',l:'Giá/ngân sách'},
  {v:'timing',l:'Chưa tới lúc'},
  {v:'product_fit',l:'Không hợp nhu cầu'},
  {v:'competitor',l:'Đã mua chỗ khác'},
  {v:'stock',l:'Hết hàng'},
  {v:'trust',l:'Nghi ngại'},
  {v:'no_need',l:'Hết nhu cầu'},
  {v:'other',l:'Khác'},
];
var REASON_REQUIRED_OUTCOMES = ['refused'];
// Show reason row for refused (required) or answered (optional, helpful)
var REASON_SHOW_OUTCOMES = ['refused', 'answered'];

// In m08OnOutcome, thêm:
var reasonSec = document.getElementById('m08-reason-sec');
var reasonPills = document.getElementById('m08-reason-pills');
var reasonVal = document.getElementById('m08-reason-val');
if (reasonSec && reasonPills) {
  var showReason = REASON_SHOW_OUTCOMES.indexOf(val) >= 0;
  reasonSec.style.display = showReason ? '' : 'none';
  if (showReason) {
    var required = REASON_REQUIRED_OUTCOMES.indexOf(val) >= 0;
    reasonSec.querySelector('.field__label').textContent = required ? 'LÝ DO *' : 'LÝ DO (tùy chọn)';
    reasonPills.innerHTML = REASON_PILLS.map(function(r) {
      return '<label class="radio-pill" onclick="m08OnReason(\'' + r.v + '\',this)">'
           + '<span class="radio-pill__dot"></span>' + r.l
           + '<input type="radio" name="outcome_reason" value="' + r.v + '" hidden></label>';
    }).join('');
  }
  if (reasonVal) reasonVal.value = '';
}

// Thêm handler:
window.m08OnReason = function(val, pill) {
  document.getElementById('m08-reason-val').value = val;
  document.querySelectorAll('#m08-reason-pills .radio-pill').forEach(function(p) { p.classList.remove('radio-pill--on'); });
  if (pill) pill.classList.add('radio-pill--on');
};
```

**Client-side validation trước submit** (prevent submit nếu refused nhưng chưa chọn reason):
```javascript
// Trên form onsubmit hoặc btn_save onclick:
var reasonReq = document.getElementById('m08-reason-sec') &&
                document.getElementById('m08-reason-sec').style.display !== 'none' &&
                ['refused'].indexOf(document.getElementById('m08-out').value) >= 0;
if (reasonReq && !document.getElementById('m08-reason-val').value) {
  alert('Vui lòng chọn lý do khi outcome là "Từ chối".');
  return false;
}
```

**Backward compat display** — timeline render cũ vẫn đọc `outcome` column (không đổi template hiển thị timeline).

### Step 7 — Export: thêm `outcome_reason`

`orchestration/assets/crm_writeback_assets.py` — trong `export_query` của `crm_activity_log`:

```sql
SELECT a.activity_id, a.party_id, pi.identity_value AS customer_id,
       a.activity_type, a.direction, a.channel, a.outcome,
       a.contact_outcome, a.outcome_reason,           -- thêm outcome_reason
       a.callback_at, a.contact_duration_s,
       a.task_id, a.related_order_code, a.staff_user_id,
       a.occurred_at, a.created_at
FROM crm_activity_log a
LEFT JOIN crm_party_identity pi
       ON pi.party_id = a.party_id AND pi.identity_type = 'sapo_customer'
WHERE a.created_at > '{cursor}'
```

### Step 8 — Warehouse mart

`transformation/models/marts/crm/mart_crm_activity_log.sql` — nếu file chưa tồn tại thì tạo mới; nếu đã tồn tại thì extend:

```sql
-- mart_crm_activity_log: canonical CRM activity mart
-- Passthrough từ stg_crm__activity_log (Phase 01 D1).
-- outcome_reason: pilot, enum set may change after 2-week NV review (design §8.3).
SELECT
    activity_id,
    party_id,
    customer_id,
    activity_type,
    direction,
    channel,
    contact_outcome,
    outcome_reason,                          -- passthrough, nullable
    CASE WHEN contact_outcome IN ('answered','replied','met')
         THEN true ELSE false END AS is_reached,
    callback_at,
    contact_duration_s,
    task_id,
    related_order_code,
    staff_user_id,
    occurred_at,
    created_at
FROM {{ ref('stg_crm__activity_log') }}
```

**Lưu ý:** mart mới → restart `data_platform` (manifest pre-parsed at startup). Nếu CRM đọc mart này → bootstrap serving view (dừng Metabase) + rebuild crm container (per memory bài học tích hợp).

### Step 9 — Spec update M08

`crm/docs/ui-spec/modals/M08-log-activity-modal.md` — thêm:

1. Section "Outcome Enum (D2)" — bảng `contact_outcome` per kênh, bảng `outcome_reason`.
2. Cập nhật Layout log mode: step 3 "KẾT QUẢ" → "KẾT QUẢ (tầng 1)"; thêm "LÝ DO (tầng 2, conditional)".
3. Cập nhật Save Effects: POST field `contact_outcome` thay `outcome`; thêm `outcome_reason`.
4. Ghi note pilot: "Enum `outcome_reason` cần review sau 2 tuần".

Regenerate `crm/docs/ui-spec/generated/` nếu convention yêu cầu (kiểm tra `/ui-spec` skill).

---

## Tests & validation

`crm/src/tests/test_outcome_reason_enum.py` — **NEW** file:

| Test class / case | Kiểm tra |
|---|---|
| `TestContactOutcomeValidation::test_valid_call_outcomes` | tất cả call outcomes pass |
| `TestContactOutcomeValidation::test_busy_wrong_number_accepted` | `busy`, `wrong_number` mới không bị reject |
| `TestContactOutcomeValidation::test_blocked_messaging` | `blocked` cho zalo/email không bị reject |
| `TestContactOutcomeValidation::test_wrong_outcome_for_channel` | `busy` trên visit → ValueError |
| `TestOutcomeReasonValidation::test_reason_required_when_refused` | `contact_outcome=refused`, no reason → ValueError |
| `TestOutcomeReasonValidation::test_reason_optional_when_answered` | `contact_outcome=answered`, no reason → OK |
| `TestOutcomeReasonValidation::test_invalid_reason_rejected` | `outcome_reason=xyz` → ValueError |
| `TestOutcomeReasonValidation::test_all_valid_reasons_accepted` | 8 reasons không throw |
| `TestOldRowsDisplay::test_old_outcome_col_still_readable` | row có `outcome="Gọi được"`, `contact_outcome=None` → render không crash |
| `TestActivityServiceIntegration::test_log_activity_writes_contact_outcome` | service ghi đúng `contact_outcome` + `outcome_reason` vào entity |
| `TestActivityServiceIntegration::test_last_contact_uses_contact_outcome` | `last_contact_repo.upsert` nhận `result=contact_outcome` |

Chạy: `docker exec crm pytest crm/src/tests/test_outcome_reason_enum.py -v`

---

## Risks & rollback

| Rủi ro | Xác suất | Xử lý |
|--------|----------|-------|
| Migration `ADD COLUMN` trên SQLite thất bại do lock | Thấp | Chạy `docker exec crm sqlite3` thủ công nếu runner lỗi |
| Timeline cũ crash vì `outcome` = None | Thấp | Template timeline đọc `activity.outcome or activity.contact_outcome` — cập nhật nếu cần |
| `last_contact` không trigger vì `activity.outcome` là None | Trung bình | Step 4 đã update điều kiện sang `contact_outcome or outcome` |
| Enum set chưa ổn sau pilot → mapping mart phải sửa | Cao (theo thiết kế) | Review sau 2 tuần; chỉ sửa constants + mart — không thêm cột |
| dbt node mới `mart_crm_activity_log` chưa có stg source | Trung bình | Phụ thuộc Phase 01 (D1) đã tạo `stg_crm__activity_log`; nếu Phase 01 chưa xong thì skip mart, chỉ làm export query |

**Rollback:** revert migration 0035 (DROP COLUMN) + revert entity/repo/service/template. Không ảnh hưởng migration trước.

---

## Unresolved questions

1. `stg_crm__activity_log` model (Phase 01 D1) — nếu chưa tồn tại khi Phase 03 chạy, `mart_crm_activity_log` phải trỏ trực tiếp vào parquet export thay vì `{{ ref(...) }}`. Cần confirm Phase 01 đã deploy xong trước khi làm Step 8.
2. Pilot review sau 2 tuần — ai thu thập feedback NV? (§8.3 design doc còn bỏ ngỏ). Cần assign owner trước khi lock mart mapping.
3. `outcome_reason` cho `answered` (cuộc gọi thành công nhưng không chốt) — thiết kế nói "tùy chọn khi answered-không-chốt" nhưng không rõ "không chốt" được xác định thế nào từ server side. Phase 03 chọn cách đơn giản: `answered` → reason hiện nhưng không bắt buộc. Nếu muốn bắt buộc khi `answered` nhưng `related_order_code` rỗng, cần thêm điều kiện — để Phase 06.
