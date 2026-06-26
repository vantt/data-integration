# Phase 01 — Branch-Tree Schema + PoC Script

**Status:** pending  
**Effort:** 1h  
**Blockers:** user schema approval (branch-tree-schema.md)  
**File ownership:** `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/603264280.json` (add `nodes` + `entry_node` keys; all other fields untouched)

---

## Context

The existing `603264280.json` is the real pilot script for Thanh Tuyền (SILVER, DUE_SOON reorder case). It currently has the v2 flat schema. This phase adds the `nodes`/`entry_node` keys alongside existing flat fields — no field removed, no other file touched.

The full worked tree is already defined in `branch-tree-schema.md` Section 7. This phase is about writing it into the actual file and validating the JSON is well-formed.

---

## Implementation Steps

### 1. Validate JSON shape (before touching the file)

Mentally confirm the schema invariants against the proposed tree:

- Every `options[].next` value is either `null` or a key that exists in `nodes`. Cross-check:
  - `root` → `reached_interest_check` ✓, `null` ✓
  - `reached_interest_check` → `pitch_reorder`, `handle_objection_timing`, `handle_objection_price`, `handle_objection_need`, `null` ✓
  - `pitch_reorder` → `handle_objection_price`, `handle_objection_timing`, `null` ✓
  - `handle_objection_price` → `null` ✓
  - `handle_objection_timing` → `null` ✓
  - `handle_objection_need` → `null` ✓
- Every node has `id`, `kind`, `say`, `options`.
- `entry_node` value (`"root"`) is a key in `nodes`.
- No node is unreachable (all non-root nodes are referenced by at least one `options[].next`).

### 2. Add `nodes` and `entry_node` to `603264280.json`

Append at the top level of the JSON object, after the existing `approach` key and before `confidence`:

```json
"nodes": {
  "root": {
    "id": "root",
    "kind": "opening",
    "say": "Dạ em chào Anh/Chị Thanh Tuyền ạ, em gọi từ cửa hàng mình từng đặt Thực phẩm bảo vệ sức khỏe Shark Cartilage Extract. Dạ bên em thấy cũng đã một thời gian mình chưa đặt lại, nên em gọi hỏi xem Anh/Chị còn nhu cầu dùng tiếp sản phẩm này không để em hỗ trợ lên đơn giao COD cho tiện ạ.",
    "hint": "Đây là lời mở gốc. Đợi phản hồi đầu tiên của khách trước khi tiếp.",
    "options": [
      { "label": "Gọi được — khách nghe",  "outcome": "reached",          "next": "reached_interest_check" },
      { "label": "Không nghe máy",          "outcome": "no_answer",        "next": null },
      { "label": "Hẹn gọi lại",             "outcome": "callback",         "next": null },
      { "label": "Cúp máy / từ chối nghe",  "outcome": "refused",          "next": null }
    ]
  },
  "reached_interest_check": {
    "id": "reached_interest_check",
    "kind": "probe",
    "say": "Dạ không biết Anh/Chị còn nhu cầu dùng tiếp Shark Cartilage Extract không ạ?",
    "hint": "Lắng nghe ngay — không cắt ngang. Khách đang Churned nên không ép.",
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
    "say": "Dạ vậy em hỗ trợ lên đơn COD cho mình nhé, sản phẩm Shark Cartilage Extract giao tận nhà, Anh/Chị chỉ nhận hàng là xong ạ. Ngoài ra nếu Anh/Chị quan tâm, bên em còn có Bột uống Bone's Calcium for Kids dùng kết hợp rất tốt ạ.",
    "hint": "COD theo thói quen. Gợi cross-sell nhẹ; không giảm giá sâu (biên khỏe).",
    "options": [
      { "label": "Đồng ý mua",            "outcome": "purchased",         "next": null },
      { "label": "Hỏi giá / ưu đãi",      "outcome": "objection_price",   "next": "handle_objection_price" },
      { "label": "Cần thêm thời gian",     "outcome": "objection_timing",  "next": "handle_objection_timing" }
    ]
  },
  "handle_objection_price": {
    "id": "handle_objection_price",
    "kind": "objection",
    "say": "Dạ em kiểm tra ưu đãi phù hợp cho đơn đặt lại của mình nhé. Mình từng dùng dòng Shark Cartilage Extract rồi nên em ưu tiên hỗ trợ theo đúng sản phẩm Anh/Chị quen dùng, giao COD cho tiện ạ.",
    "hint": "KHÔNG giảm giá sâu ngay từ đầu — chỉ ưu đãi vừa phải nếu cần (do_not[3]).",
    "options": [
      { "label": "Đồng ý",        "outcome": "purchased", "next": null },
      { "label": "Vẫn từ chối",   "outcome": "refused",   "next": null }
    ]
  },
  "handle_objection_timing": {
    "id": "handle_objection_timing",
    "kind": "objection",
    "say": "Dạ được ạ, em không ép mình đâu. Em gửi lại thông tin sản phẩm và hỗ trợ giữ đơn COD, khi nào Anh/Chị cần dùng tiếp thì nhắn em lên đơn nhanh cho mình ạ.",
    "hint": "Kết thúc mở — để lại điểm liên lạc, không đóng cơ hội.",
    "options": [
      { "label": "Hẹn gọi lại sau",  "outcome": "callback", "next": null },
      { "label": "Từ chối hẳn",      "outcome": "refused",  "next": null }
    ]
  },
  "handle_objection_need": {
    "id": "handle_objection_need",
    "kind": "objection",
    "say": "Dạ vâng, em cảm ơn Anh/Chị đã cho em biết. Nếu sau này Anh/Chị cần, em sẵn sàng hỗ trợ ạ.",
    "hint": "Kết thúc lịch sự. Không tạo callback task khi khách từ chối hẳn.",
    "options": [
      { "label": "Kết thúc lịch sự", "outcome": "refused", "next": null }
    ]
  }
},
"entry_node": "root"
```

### 3. Verify JSON is valid after edit

Run in the container or locally:

```bash
python -m json.tool 603264280.json > /dev/null && echo "valid"
```

Or PowerShell on host:

```powershell
Get-Content 603264280.json | ConvertFrom-Json | Out-Null; Write-Host "valid"
```

---

## Data Flow

```
603264280.json (file)
  └─ FileApproachScriptRepository.get_by_customer_id(603264280)
       └─ ApproachScript.data["nodes"]  ← new key, absorbed by data:dict
       └─ ApproachScript.data["entry_node"]  ← new key
       [no entity code change needed]
```

---

## Validation

- JSON parses without error.
- `ApproachScript.from_json()` still succeeds — it reads `data["approach"]["recommended"]` which is unchanged.
- Legacy flat fields (`opening_message`, `talking_points`, etc.) still present in `approach` — no breakage to existing template render if `is_branching` detection fails.

---

## Rollback

Delete the added `nodes` and `entry_node` keys from `603264280.json` (or restore from git). No other files changed.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JSON syntax error in hand-edited file | Medium | Low | Validate with `json.tool` immediately after edit |
| Node cross-reference typo (`next` points to nonexistent node) | Low | Medium | Backend interpreter returns `entry_node` as fallback (Phase 02 spec) |
