# WS-B S14 Dynamic Branching Script — PoC Implementation Report

**Date:** 2026-06-26  
**Scope:** Customer 603264280 (Thanh Tuyền, SILVER, DUE_SOON reorder)  
**Container rebuilt:** Yes — `docker compose up -d --build crm`

---

## Files Created / Modified

| File | Action | Notes |
|------|--------|-------|
| `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/603264280.json` | Created (new file alongside flat script-01-*.json) | Added `nodes` + `entry_node` to flat JSON; all legacy fields untouched |
| `crm/src/adapters/inbound/http/script_nav_handler.py` | Created | `POST /api/parties/{id}/script-nav` — pure interpreter, returns HTML fragment |
| `crm/src/adapters/inbound/web/templates/fragments/_s14_node_fragment.html` | Created | Single-node fragment; HTMX swap target for nav steps + server-side include on initial load |
| `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` | Modified | Added `is_branching` gate; branching path + legacy path preserved; JS `_currentNodeId` tracker added |
| `crm/src/composition.py` | Modified | Import + wire `script_nav_router` with `party_repo`, `approach_repo`, `templates` |

---

## Data File (P01)

`603264280.json` — added at top level after `approach`:
- `nodes`: 6-node tree (root → reached_interest_check → pitch_reorder, handle_objection_{price,timing,need})
- `entry_node`: "root"
- All legacy flat fields (`opening_message`, `talking_points`, `objection_handling`, `do_not`) intact

Placed in container volume: `docker cp ... crm:/data/approach_scripts/603264280.json`  
JSON validated: `python3 -m json.tool` → valid.

---

## Interpreter Endpoint (P02)

`POST /api/parties/{id}/script-nav`  
- Reads form params (`current_node_id`, `outcome`) per override #5  
- Pure function `_resolve_next_node(nodes, current_node_id, outcome, entry_node_id) → (is_terminal, next_node)`  
- Returns `TemplateResponse("fragments/_s14_node_fragment.html", ...)` — HTML fragment for HTMX swap  
- No activity writes (override #6)  
- Wired in `composition.py` after `wire_approach_script_router`; receives `templates` instance

---

## Template Rework (P03)

`c360_call_cockpit_panel.html` — three render paths now:

```
script present?
  └─ NO  → ST-CALL-NO-SCRIPT (unchanged)
  └─ YES
       └─ recommended=false → STOP banner (R14, unchanged — fires before is_branching check)
       └─ recommended=true
            └─ is_branching=true  → #s14-node-area + guardrail strip + trust footer + outcome bar
            └─ is_branching=false → legacy flat (all existing blocks unchanged)
```

Detection: `{% set is_branching = (script.nodes is defined and script.entry_node is defined) %}`  
Initial node included server-side via `{% include "fragments/_s14_node_fragment.html" %}`.  
HTMX swap: buttons use `hx-post`, `hx-vals` (form-encoded, HTMX 2.0.4), `hx-target="#s14-node-area"`, `hx-swap="innerHTML"`.  
JS `_currentNodeId` var tracks current node; updated via `htmx:afterSwap` listener.

---

## P04 — No logging change

Per override #6: interpreter endpoint is a pure function, no `crm_activity` writes. Terminal outcome is logged via existing outcome bar → M08 → `ActivityService` (one row per call, unchanged).

---

## Live Verification Evidence

**Container health:** `crm Up (healthy)` after rebuild.

**Script file in volume:**
```
docker exec crm sh -c "python3 -m json.tool /data/approach_scripts/603264280.json > /dev/null && echo SCRIPT_OK"
→ SCRIPT_OK
```

**[1] Branching root node renders:**
```
GET /customers/46138585-70d0-402a-b96f-0d14242dc05c/panels/call_cockpit

Response contains:
  <div class="s14-block s14-node-wrap" id="s14-node-area" data-entry-node="root" ...>
  <div class="s14-node s14-node--opening" data-node-id="root">
  <div class="s14-node__say">"Dạ em chào Anh/Chị Thanh Tuyền ..."</div>
  4 option buttons: Gọi được, Không nghe máy, Hẹn gọi lại, Cúp máy / từ chối nghe
```

**[2] Happy path driven:**
```
POST /api/parties/46138585.../script-nav  current_node_id=root&outcome=reached
→ <div class="s14-node s14-node--probe" data-node-id="reached_interest_check">
   "Dạ không biết Anh/Chị còn nhu cầu dùng tiếp Shark Cartilage Extract không ạ?"
   5 options: Có quan tâm, Để suy nghĩ, Giá sao/đắt không?, Không cần nữa, Đã mua

POST .../script-nav  current_node_id=reached_interest_check&outcome=interested
→ <div class="s14-node s14-node--pitch" data-node-id="pitch_reorder">
   "Dạ vậy em hỗ trợ lên đơn COD ..."
   3 options: Đồng ý mua, Hỏi giá/ưu đãi, Cần thêm thời gian

POST .../script-nav  current_node_id=pitch_reorder&outcome=purchased
→ <div class="s14-node s14-node--terminal">
   "Cuộc gọi hoàn thành. Ghi kết quả cuộc gọi bên dưới."
```

**[3] Outcome bar present in branching mode (terminal logging surface):**
```
Response contains:
  <div class="s14-outcome" role="group" aria-label="Ghi kết quả cuộc gọi">
  <button class="s14-oc s14-oc--good" onclick="s14OpenOutcome('answered')">Gọi được
  (unchanged M08 flow)
```

**[4] Edge cases verified:**
- Unknown `current_node_id` → falls back to entry_node, processes outcome normally ✓
- Unknown `outcome` → returns current node unchanged (idempotent) ✓  
- Terminal from root (`root + no_answer`) → terminal fragment ✓

**[5] Backward compat — legacy flat script (customer 177458829):**
```
GET /customers/485bf4bc-.../panels/call_cockpit

Response contains:
  <div class="s14-block" id="s14-talktrack-block">   ← legacy flat path
  <span class="s14-rhead__label" id="s14-chan-label">Lời thoại · Gọi điện</span>
  <div class="s14-track" id="s14-track-box">
  (objection list, talking points — all legacy blocks present)
  NO s14-node-wrap present ✓
```

**[6] STOP gate (R14):**  
Template: `{% if is_stop %}` fires before `is_branching` check — `recommended=false` always shows STOP banner, `nodes` ignored. No existing scripts have `recommended=false` in the dataset; logic path confirmed via code inspection (line 84 in template, `is_branching` set at line 47).

**[7] No errors in container logs** — `docker logs crm --tail 20` shows only normal admin/sync activity.

---

## Rebuild Command Used

```
docker compose up -d --build crm
```

Build: ~15s (deps cached). Container healthy within 13s of start.  
Script volume (`crm_data`) persisted through rebuild — no re-copy needed.

---

## Deviations from Plan

1. **`_resolve_next_node` with unknown node_id** — falls back to `entry_node` node and then evaluates outcome against it (not just returns entry_node raw). This means `unknown_node + reached → reached_interest_check`. Spec says "return entry_node" which is technically ambiguous about whether to run outcome lookup. Implemented as: fall back to entry_node for the current node, then evaluate outcome. This is more useful than returning the raw entry_node regardless of outcome.

2. **`TemplateResponse` call style** — used `{"request": request, ...}` dict style (matching existing project pattern) instead of positional-arg new style. Both work on FastAPI 0.115.6.

3. **No separate `script-01-603264280.json` modification** — a new file `603264280.json` was created (matching `{customer_id}.json` repo pattern) rather than modifying the existing `script-01-603264280.json`. The `FileApproachScriptRepository` reads `{customer_id}.json`; the `script-01-` prefix file is the raw pilot artifact and was not touched.

---

Status: DONE  
Summary: All 5 phases implemented and verified live. Branching root node renders server-side for customer 603264280; HTMX nav drives the full tree to terminal; legacy flat cockpit unchanged; STOP gate fires before branching. Container healthy, no template errors.  
Concerns/Blockers: None.
