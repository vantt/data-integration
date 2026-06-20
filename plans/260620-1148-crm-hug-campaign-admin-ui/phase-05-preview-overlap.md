# Phase 5 — Preview (Count + Sample) + Overlap Warning

## Context Links
- Predicate engine (Phase 3): `crm/src/hug/targeting_engine.py` — `matches_targeting`, `preview_match_customers`
- UI router (Phase 4): `crm/src/adapters/inbound/web/screen_hug_campaign.py`
- Customer data: `cache.db wh_customer_tier` (~7.5k rows), columns: `customer_id, strategic_tier, recency_days, value_group, is_contactable`
- Edge matching reference: `webhook_receiver/cloudflareD1/src/hug-handler.ts` lines 148–203
- Design intent: `discussion-hug.md §7` — "preview khớp ~bao nhiêu khách + khách mẫu", "cảnh báo chồng lấp"

## Overview
- **Priority:** P2
- **Status:** pending (blocked on Phase 3; integrates with Phase 4 UI)
- **Goal:** Two endpoints added to the campaign admin: (1) preview — count matched customers + sample rows; (2) overlap — detect which existing active campaigns share a non-empty intersection with the new/edited campaign's targeting.

## Key Insights

### Preview accuracy limitation (document prominently in UI)
- Preview runs `matches_targeting` against `wh_customer_tier` rows — covers customer-level attrs: `tier, recency_days, value_group, is_contactable`.
- `op_type` and `channel` are per-scan (touchpoint-level) — cannot be counted against customers. If the targeting includes `op_type` or `channel`, preview strips those attrs and shows: "Lưu ý: op_type / channel là thuộc tính theo lượt quét, không tính được theo khách hàng. Kết quả preview bỏ qua điều kiện này."
- `is_contactable` in `wh_customer_tier` is the warehouse value. The CRM overlay (from `crm_identity_link`) is NOT applied in preview (would require joining crm.db — adds complexity, marginal accuracy gain). Document: "is_contactable từ kho dữ liệu, chưa phản ánh số mới Hug capture."

### Overlap detection algorithm (v1: exact pairwise intersection)
For each pair of (new campaign, existing active campaign), compute whether their targetings can simultaneously match any context:
- **List attrs** (tier, op_type, channel, value_group, is_contactable): intersection = `set(A) ∩ set(B)`. If either side is absent (unconstrained) → treat as universe (always overlaps on that attr).
- **Range attr** (recency_days): interval intersection `[max(A.gte,B.gte), min(A.lte,B.lte)]` — overlap if `max_low ≤ min_high`. Missing bound = ±∞.
- **Overall**: overlap exists if ALL present attrs have non-empty intersection (AND semantics — same as matching).
- Emit warning per overlapping campaign: name, priority, whether it would shadow or be shadowed by the new one (priority comparison).

## Requirements

### Functional
- `GET /hug/campaign/preview?targeting=<json_encoded>` → JSON `{"matched": int, "total": int, "sample": list[dict], "warning": str|null}`. Used by the edit form to show a live count badge (form action triggers a GET via form `method=get action=/hug/campaign/preview` rendered in an `<iframe>` or a `<details>` block — no JS XHR required).
- `GET /hug/campaign/overlap?targeting=<json_encoded>&exclude_id=<id>` → JSON `{"overlaps": list[{campaign_id, name, priority, shadows_new: bool}]}`. Called from the form before save or on a "Check Overlap" button submit.
- Alternative (simpler, KISS): both preview and overlap are triggered by the **main form POST** and included in the re-rendered form response (no separate AJAX endpoints). The form has a "Preview" submit button (name=`action` value=`preview`) distinct from the "Save" submit button. On `action=preview` the router runs preview + overlap and re-renders the form with results panel; it does NOT save. This eliminates the need for JS and iframe tricks.

**Recommended approach: single-form multi-action (KISS).** Two submit buttons in the form:
```html
<button name="action" value="preview">Xem trước</button>
<button name="action" value="save">Lưu & Đẩy D1</button>
```
Router checks `action` field: `preview` → run preview+overlap, re-render form with results; `save` → validate+upsert+push.

### Non-Functional
- Preview runs in-process (no subprocess, no DB server). ~7.5k rows × simple dict comparison ≈ <50ms.
- Overlap check: O(N²) over active campaigns (N ≤ 50 expected) — trivially fast.
- Module ≤ 150 lines.
- FastAPI-free overlap logic — testable directly.

## Architecture

```
crm/src/hug/
  campaign_overlap.py   ← targeting_can_overlap(t_a, t_b) + find_overlapping_campaigns() — NEW

crm/src/adapters/inbound/web/screen_hug_campaign.py   ← MODIFY: add preview action branch
crm/src/adapters/inbound/web/screen_hug_campaign_html.py  ← MODIFY: _render_preview_panel()
```

**Data flow (preview action in form POST):**
```
POST /hug/campaign/new  action=preview
  → parse targeting dict from form fields
  → validate_targeting(targeting)   [Phase 3]
  → preview_match_customers(targeting, cache_db)   [Phase 3]  → {matched, total, sample}
  → find_overlapping_campaigns(conn, targeting, exclude_id=None)   [Phase 5]  → overlaps list
  → re-render form with preview panel + overlap warnings (no DB write)
```

**Data flow (overlap logic):**
```python
# campaign_overlap.py
def targeting_can_overlap(t_a: dict, t_b: dict) -> bool:
    # For each key present in either targeting:
    #   if key in both:  check intersection non-empty per type (list/range/scalar)
    #   if key in only one: unconstrained in other → always overlaps on this attr
    # Return True if all attrs overlap (AND semantics)

def find_overlapping_campaigns(
    conn, new_targeting: dict, exclude_id: str | None = None
) -> list[dict]:
    # list_campaigns(conn, status='active')
    # filter out exclude_id (the campaign being edited)
    # for each: targeting_can_overlap(new_targeting, existing_targeting_dict)
    # return list of {campaign_id, name, priority} for overlapping ones
```

## Related Code Files

**Create:**
- `crm/src/hug/campaign_overlap.py`

**Modify:**
- `crm/src/adapters/inbound/web/screen_hug_campaign.py` — handle `action=preview` in POST handlers
- `crm/src/adapters/inbound/web/screen_hug_campaign_html.py` — add `_render_preview_panel(preview_result, overlaps, new_priority)`

**Read-only:**
- `crm/src/hug/targeting_engine.py` (Phase 3)
- `crm/src/hug/campaign_repository.py` (Phase 1)

## Implementation Steps

1. **`campaign_overlap.py`**:
   - `_list_intersection(a_vals, b_vals) → bool` — set intersection non-empty
   - `_range_overlaps(a_range, b_range) → bool` — interval intersection
   - `targeting_can_overlap(t_a: dict, t_b: dict) → bool` — main logic
   - `find_overlapping_campaigns(conn, new_targeting, exclude_id=None) → list[dict]`

2. **Form multi-action modification in `screen_hug_campaign.py`**:
   ```python
   action = form_data.get("action", "save")
   if action == "preview":
       errors = validate_targeting(targeting)
       preview = preview_match_customers(targeting, cache_db_path()) if not errors else {}
       overlaps = find_overlapping_campaigns(conn, targeting, exclude_id=campaign_id) if not errors else []
       return HTMLResponse(_render_form(..., preview=preview, overlaps=overlaps))
   # else: save path
   ```

3. **`_render_preview_panel(preview, overlaps, new_priority)`** in `_html.py`:
   - Preview box: "Khớp ~**N**/M khách hàng" with sample table (customer_id, tier, recency_days, value_group).
   - Limitation notice if preview stripped op_type/channel.
   - Overlap list: for each overlap: "⚠️ Chồng lấp với **{name}** (priority {p})" + shadow direction text ("campaign này sẽ bị {name} ưu tiên" if existing priority < new).

4. **Tests** `crm/tests/hug/test_campaign_overlap.py`:
   - `targeting_can_overlap({}, {})` → True (both DEFAULT).
   - `targeting_can_overlap({"tier": ["VIP"]}, {"tier": ["CORE"]})` → False (disjoint sets).
   - `targeting_can_overlap({"tier": ["VIP", "CORE"]}, {"tier": ["CORE"]})` → True.
   - `targeting_can_overlap({"recency_days": {"gte": 30}}, {"recency_days": {"lte": 20}})` → False.
   - `targeting_can_overlap({"tier": ["VIP"]}, {})` → True (one unconstrained).
   - `targeting_can_overlap({"tier": ["VIP"], "op_type": ["package_insert"]}, {"tier": ["VIP"], "op_type": ["loyalty_card"]})` → False.

## Todo

- [ ] Write `campaign_overlap.py` with `targeting_can_overlap` + `find_overlapping_campaigns`
- [ ] Add `action=preview` branch to `screen_hug_campaign.py` POST handlers
- [ ] Add `_render_preview_panel` to `screen_hug_campaign_html.py`
- [ ] Add "Xem trước" submit button to form HTML (alongside "Lưu & Đẩy D1")
- [ ] Unit tests for overlap logic
- [ ] Manual test: create two overlapping campaigns, verify warning appears

## Success Criteria

- "Xem trước" button in form returns count + sample without saving.
- Overlap warning appears when two active campaigns share a targeting intersection.
- Preview strips `op_type`/`channel` and shows the limitation notice.
- `targeting_can_overlap` returns correct result for all 6 test cases above.
- Re-rendered form preserves all entered field values after preview action.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Form field values lost on preview re-render (multi-action POST) | Medium | Medium | Router must pass all form values back to `_render_form`; use a `FormValues` dataclass to carry state cleanly |
| Overlap false positives for scalar attrs (e.g. is_contactable=1 vs [1]) | Low | Low | Normalise all values to lists before intersection check |
| preview_match_customers slow if cache.db has >50k rows in future | Low | Low | Current: ~7.5k rows. Add a `LIMIT 10000` guard as comment; performance review at 50k |
| Unconstrained (absent) attr in one campaign always causes overlap | Medium | Medium | This is correct per AND semantics (unconstrained = matches any). Make it clear in UX: "Chồng lấp xảy ra vì campaign kia không giới hạn attr X." |

## Security Considerations
- `targeting` query param / form field: JSON-decoded server-side, then passed through `validate_targeting` before use. Malformed JSON → error message, no exception propagated.
- Cache.db opened read-only.

## Next Steps
- Phase 6 adds rollback link to edit form (history list endpoint).
- Future: expose preview as a standalone JSON endpoint if a richer UI (e.g. live count while typing) is desired.
