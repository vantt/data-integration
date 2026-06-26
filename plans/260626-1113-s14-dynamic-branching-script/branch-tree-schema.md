# Branch-Tree Schema — WS-B S14 Dynamic Branching Script

> Proposal for user approval before any build begins.

---

## 1. Design Principles

1. **Absorbed into `data: dict`** — `ApproachScript.data` already holds the entire JSON (`approach_script.py:22`). The entity needs zero change. The template is the only coupling point.
2. **Shallow tree** — max 2 levels (root node → reaction nodes). Depth-3 is out of v1.
3. **Outcome-keyed transitions** — each edge is keyed by an outcome string that maps 1:1 or n:1 to `crm_activity.contact_outcome` (`reached|no_answer|callback|refused`) PLUS script-specific fine-grained outcomes (`interested`, `objection_price`, `objection_need`, `objection_timing`, `purchased`).
4. **Backward-compatible** — a script with no `nodes` key is a legacy flat v2 script; S14 renders it exactly as today.
5. **STOP gate unchanged** — `approach.recommended=false` checked before any node is shown (same R14 logic, same STOP banner). The `nodes` subtree is irrelevant when `recommended=false`.

---

## 2. JSON Schema (proposed)

```json
{
  "profile_read": "...",
  "value_assessment": { ... },
  "opportunity": { ... },
  "risk": { ... },
  "approach": {
    "recommended": true,
    "reason_if_not_recommended": null,
    "primary_channel": "phone",
    "fallback_channel": "sms",
    "timing": "...",

    // ── LEGACY FLAT FIELDS (kept for backward compat + channel toggle) ──────
    "opening_message": "...",
    "fallback_message": "...",
    "talking_points": [],
    "cross_sell": [],
    "objection_handling": [],
    "do_not": []
  },

  // ── NEW: branch tree (absent on legacy scripts — S14 detects by key presence) ─
  "nodes": {
    "root": {
      "id": "root",
      "kind": "opening",
      "say": "Dạ em chào Anh/Chị Thanh Tuyền...",
      "hint": "Đợi phản hồi đầu tiên của khách.",
      "options": [
        { "label": "Gọi được — khách nghe",  "outcome": "reached",      "next": "reached_interest_check" },
        { "label": "Không nghe máy",          "outcome": "no_answer",    "next": null },
        { "label": "Hẹn gọi lại",             "outcome": "callback",     "next": null },
        { "label": "Cúp máy / từ chối nghe",  "outcome": "refused",      "next": null }
      ]
    },

    "reached_interest_check": {
      "id": "reached_interest_check",
      "kind": "probe",
      "say": "Dạ không biết Anh/Chị còn nhu cầu dùng tiếp Shark Cartilage không ạ?",
      "hint": "Lắng nghe ngay — không cắt ngang.",
      "options": [
        { "label": "Có, quan tâm",          "outcome": "interested",        "next": "pitch_reorder" },
        { "label": "Để suy nghĩ",           "outcome": "objection_timing",  "next": "handle_objection_timing" },
        { "label": "Giá sao / đắt không?",  "outcome": "objection_price",   "next": "handle_objection_price" },
        { "label": "Không cần nữa",         "outcome": "objection_need",    "next": "handle_objection_need" },
        { "label": "Đã mua / đã có hàng",   "outcome": "purchased",         "next": null }
      ]
    },

    "pitch_reorder": {
      "id": "pitch_reorder",
      "kind": "pitch",
      "say": "Dạ vậy em hỗ trợ lên đơn COD cho mình nhé, sản phẩm Shark Cartilage Extract giao tận nhà, Anh/Chị chỉ nhận hàng là xong ạ.",
      "hint": "Đề nghị cụ thể, COD theo thói quen khách.",
      "options": [
        { "label": "Đồng ý mua",   "outcome": "purchased",        "next": null },
        { "label": "Hỏi giá",      "outcome": "objection_price",  "next": "handle_objection_price" },
        { "label": "Cần thêm thời gian", "outcome": "objection_timing", "next": "handle_objection_timing" }
      ]
    },

    "handle_objection_price": {
      "id": "handle_objection_price",
      "kind": "objection",
      "say": "Dạ em kiểm tra ưu đãi phù hợp cho đơn đặt lại của mình nhé. Mình đã dùng dòng này rồi nên em ưu tiên hỗ trợ theo đúng sản phẩm quen dùng, giao COD cho tiện ạ.",
      "hint": "Không giảm giá sâu; biên đơn hàng đang khỏe (do_not[3]).",
      "options": [
        { "label": "Đồng ý",       "outcome": "purchased",         "next": null },
        { "label": "Vẫn từ chối",  "outcome": "refused",           "next": null }
      ]
    },

    "handle_objection_timing": {
      "id": "handle_objection_timing",
      "kind": "objection",
      "say": "Dạ được ạ, em không ép mình đâu. Em gửi lại thông tin sản phẩm và giữ đơn COD, khi nào Anh/Chị cần thì nhắn em lên đơn nhanh cho mình ạ.",
      "hint": "Kết thúc mở — không đóng cơ hội, để lại điểm liên lạc.",
      "options": [
        { "label": "Đồng ý hẹn lại", "outcome": "callback", "next": null },
        { "label": "Từ chối hẳn",    "outcome": "refused",   "next": null }
      ]
    },

    "handle_objection_need": {
      "id": "handle_objection_need",
      "kind": "objection",
      "say": "Dạ vâng, em cảm ơn Anh/Chị đã cho em biết. Nếu sau này Anh/Chị cần, em sẵn sàng hỗ trợ ạ.",
      "hint": "Kết thúc lịch sự. Ghi outcome = refused, không cần callback task.",
      "options": [
        { "label": "Kết thúc lịch sự", "outcome": "refused", "next": null }
      ]
    }
  },

  "entry_node": "root",

  "confidence": "medium",
  "data_gaps": [ ... ]
}
```

---

## 3. Field-by-Field Spec

### Top-level additions

| Field | Type | Notes |
|-------|------|-------|
| `nodes` | `dict[str, Node]` | Keyed by node `id`. Absent → legacy flat script. |
| `entry_node` | `str` | ID of the first node to render. Always `"root"` for v1. |

### Node object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `str` | yes | Stable identifier, kebab-case. Never contains plan IDs or phase numbers. |
| `kind` | `str` | yes | `opening` \| `probe` \| `pitch` \| `objection` \| `close`. Drives UI styling. |
| `say` | `str` | yes | The script text for staff to say/read. Replaces `opening_message` for the current node. |
| `hint` | `str` | no | Internal coaching note shown below `say` in a muted style. Never read aloud. |
| `options` | `list[Option]` | yes | Outcome buttons staff taps to advance. |

### Option object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `label` | `str` | yes | Button label in Vietnamese. |
| `outcome` | `str` | yes | The outcome key (see mapping below). |
| `next` | `str \| null` | yes | Next node `id`, or `null` = terminal (call is over / no further script guidance). |

### Outcome → `crm_activity.contact_outcome` mapping

The existing `crm_activity.contact_outcome` enum is `reached|no_answer|callback|refused` (migration 0013). Script-specific fine-grained outcomes are **supplementary** — they are logged in `crm_activity.body` or a future structured column, but the four canonical values are always written to `contact_outcome`.

| Script outcome | `contact_outcome` written | Meaning |
|----------------|--------------------------|---------|
| `reached` | `reached` | Khách nghe máy (first branch) |
| `no_answer` | `no_answer` | Không nghe |
| `callback` | `callback` | Hẹn gọi lại |
| `refused` | `refused` | Từ chối rõ ràng |
| `interested` | `reached` | Nghe + quan tâm (sub-state of reached) |
| `objection_price` | `reached` | Nghe + phản đối giá |
| `objection_need` | `reached` | Nghe + không cần |
| `objection_timing` | `reached` | Nghe + để sau |
| `purchased` | `reached` | Đồng ý mua ngay |

Rule: any `outcome` not in the canonical 4 → write `reached` to `contact_outcome` (they imply the call was answered). Fine-grained outcome is stored in `crm_activity.body` as `[node:handle_objection_price → objection_price]`.

---

## 4. Backward Compatibility

Detection logic in the template (pseudocode, Jinja2):

```jinja2
{% set is_branching = script.nodes is defined and script.entry_node is defined %}
```

| Condition | Render path |
|-----------|-------------|
| `is_branching = true`, `recommended = true` | Dynamic node renderer (new) |
| `is_branching = false`, `recommended = true` | Legacy flat renderer (existing blocks unchanged) |
| `recommended = false` (any) | STOP banner (existing R14 — unchanged) |

No template logic changes required for existing scripts. The existing `{% set ap = script.approach %}` block and all legacy rendering blocks remain in place, gated by `{% if not is_branching %}`.

---

## 5. STOP / Low-Confidence States with Branching

- **STOP (R14)**: `approach.recommended = false` → checked first, before consulting `nodes`. STOP banner renders, `nodes` ignored entirely.
- **Low confidence**: `confidence = low` → branching tree still renders, but a `s14-lowconf` warning banner is prepended above the current node's `say` block (same styling as existing low-conf treatment in template line 142–147).
- **Stale cache (>24h)**: trust footer stale badge unchanged (template line 449–465).
- **Node not found**: if `current_node_id` is not in `nodes` → backend returns the `entry_node`. Never a hard 404.
- **Terminal node** (`next: null`): frontend disables navigation buttons; outcome bar becomes the final logging surface. Staff taps one of the 4 canonical outcome buttons → M08 modal → `crm_activity` written → done.

---

## 6. What the Legacy Flat Fields Become

The current v2 flat fields (`opening_message`, `fallback_message`, `talking_points`, `objection_handling`, `do_not`) have direct counterparts in a branching tree:

| v2 flat field | Branching equivalent |
|---------------|---------------------|
| `opening_message` | `nodes["root"].say` |
| `fallback_message` | kept in `approach.fallback_message` (channel toggle still works) |
| `talking_points` | Pitched content spread across `pitch` and `probe` nodes as `say` text |
| `objection_handling[]` | `objection` kind nodes |
| `do_not[]` | `hint` fields on relevant nodes (internal coaching; not shown as a separate block) |

For a PoC, both can coexist: a script can carry `approach.talking_points` AND `nodes`. The template uses `is_branching` to decide which to render. This lets the pilot run without regenerating scripts.

---

## 7. Fully Worked Example — Customer 603264280 (Thanh Tuyền, SILVER reorder)

This maps directly to `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/script-01-603264280.json`.

The existing flat script has:
- `opening_message`: Lời chào + Shark Cartilage Extract + COD offer
- 2 `objection_handling` entries: "Để suy nghĩ" and "Có ưu đãi gì không"
- 3 `talking_points`
- 4 `do_not` rules

The branching tree above (Section 2) IS the fully worked example for this customer. It:
- Condenses 3 talking points into the `pitch_reorder` node's `say`
- Promotes 2 objection entries into named `objection` nodes
- Encodes 4 do_not rules as `hint` text on the relevant nodes
- Adds the unreachable paths (`no_answer`, `callback`, `refused`) as terminal options on `root`

**Call flow example (happy path):**

```
[root] → Staff says opening → Customer answers
  ↓ outcome: "reached"
[reached_interest_check] → "còn nhu cầu không?" → Customer says "quan tâm"
  ↓ outcome: "interested"
[pitch_reorder] → "em lên đơn COD cho mình nhé" → Customer agrees
  ↓ outcome: "purchased"
[terminal] → Outcome bar logs "purchased" via M08 → crm_activity written
```

**Call flow example (objection path):**

```
[root] → outcome: "reached"
[reached_interest_check] → outcome: "objection_price"
[handle_objection_price] → Staff delivers response → Customer agrees
  ↓ outcome: "purchased" → terminal
```

---

## 8. Second Worked Example — High-churn customer (illustrative, BRONZE tier)

For a BRONZE customer with `next_purchase_signal = OVERDUE` and `confidence = low`, the tree would be shallower — only 2 outcome paths from root matter:

```json
{
  "nodes": {
    "root": {
      "id": "root", "kind": "opening",
      "say": "Dạ em chào...",
      "hint": "Độ tin thấp — kiểm chứng phản hồi, đừng cam kết sâu.",
      "options": [
        { "label": "Gọi được", "outcome": "reached", "next": "winback_probe" },
        { "label": "Không nghe", "outcome": "no_answer", "next": null },
        { "label": "Từ chối",   "outcome": "refused",   "next": null }
      ]
    },
    "winback_probe": {
      "id": "winback_probe", "kind": "probe",
      "say": "Dạ bên em nhớ Anh/Chị, lâu rồi chưa gặp, không biết dạo này Anh/Chị có cần gì không?",
      "hint": "Không giả vờ như khách mới; thừa nhận đã lâu.",
      "options": [
        { "label": "Quan tâm",   "outcome": "interested", "next": null },
        { "label": "Không cần",  "outcome": "refused",    "next": null },
        { "label": "Hẹn lại",   "outcome": "callback",   "next": null }
      ]
    }
  },
  "entry_node": "root"
}
```

This shows minimum viable 2-node tree. No `pitch` node because the BRONZE + low-confidence case should probe first, not pitch.

---

## 9. Open Questions (user must decide before build)

See plan.md and phase files for full list. Schema-specific questions:

**Q1 — Where does `current_node_id` live?**
Options:
- (a) Client-only: JS variable in the rendered page, sent with each nav POST. Simplest; lost on page refresh.
- (b) URL query param: `?node=reached_interest_check`. Bookmarkable; reflects state in URL. Slightly more complex routing.
- (c) Hidden `<input>` form field. Middle ground; survives form submits.

Recommendation: **(a) JS variable + hidden input** for v1. On page refresh, reset to `entry_node` (acceptable UX — staff just started over).

**Q2 — Convert existing v2 scripts or hand-author branching scripts separately?**
Options:
- (a) Convert by hand (paste into GPT, ask it to structure as tree JSON). ~30 min per script. Fine for pilot of 5–10 customers.
- (b) Add `nodes` key to existing file alongside flat fields (coexistence). Zero migration effort; template detects which to render.

Recommendation: **(b) coexistence** for PoC. Only 603264280.json gets `nodes` added; all other files unchanged.

**Q3 — `do_not` rules: dedicated block vs node hints?**
Current flat template renders `do_not` as a visible guardrail strip (template lines 246–257). With branching, these rules are distributed as `hint` fields. Staff still needs to see them somehow.
- Option A: keep a top-level `do_not` guardrail strip (same as today) in addition to per-node hints.
- Option B: show only node-level `hint` — no global guardrail strip in branching mode.

Recommendation: **(A)** for v1 — keep global guardrail strip. The `approach.do_not[]` array is already present; just keep rendering it. Per-node hints add coaching without removing the global guardrails.
