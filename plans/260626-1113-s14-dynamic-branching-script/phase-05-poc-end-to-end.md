# Phase 05 — PoC End-to-End on Customer 603264280

**Status:** pending  
**Effort:** 1h  
**Blockers:** Phases 01–04 complete  
**File ownership:** none (validation only — no new files)

---

## Purpose

Walk one real call path through the complete stack on customer 603264280 (Thanh Tuyền, SILVER, DUE_SOON) and confirm every layer works together before declaring WS-B v1 shippable.

---

## Pre-conditions Checklist

Before running:

- [ ] `603264280.json` has `nodes` + `entry_node` keys (Phase 01)
- [ ] `script_nav_handler.py` exists and is wired in `composition.py` (Phase 02)
- [ ] `_s14_node_fragment.html` created and `{% include %}`-d in cockpit panel (Phase 03)
- [ ] Activity logging in nav handler wired to `ActivityService` (Phase 04)
- [ ] CRM container rebuilt (`docker compose up -d --build crm`) — templates + static baked in image, not volume-mounted (per project memory: `detailView code baked in image`)
- [ ] CRM reachable at http://localhost:3007 (or LAN equivalent)

---

## Test Scenario A — Happy Path (phone answered, customer buys)

**Script path:** root → reached → reached_interest_check → interested → pitch_reorder → purchased → terminal

### Steps

1. Open S14 for party that maps to customer_id 603264280.
   URL pattern: `/customers/{party_id}?tab=call_cockpit` or direct panel load.

2. **Assert initial render:**
   - Node area shows `root` node
   - `say` text = the opening message (Shark Cartilage + COD offer)
   - 4 option buttons visible: "Gọi được", "Không nghe máy", "Hẹn gọi lại", "Cúp máy / từ chối nghe"
   - Legacy flat blocks (talking-points list, objection accordion) are NOT visible
   - Guardrail strip (`do_not`) IS visible
   - Trust footer visible with freshness timestamp
   - Outcome bar (sticky) visible but visually secondary

3. **Tap "Gọi được — khách nghe":**
   - POST fires to `/api/parties/{party_id}/script-nav` with `{current_node_id: "root", outcome: "reached"}`
   - `#s14-node-area` swaps to `reached_interest_check` node
   - `say` text = "Dạ không biết Anh/Chị còn nhu cầu…"
   - 5 option buttons visible
   - `crm_activity` row written: `outcome=reached`, `body` contains `[node:root → reached → reached_interest_check]`

4. **Tap "Có, quan tâm":**
   - Swaps to `pitch_reorder` node
   - `say` = COD pitch + Bone's Calcium cross-sell mention
   - `crm_activity` row: `outcome=reached`, `[node:reached_interest_check → interested → pitch_reorder]`

5. **Tap "Đồng ý mua":**
   - Response: `{"terminal": true}` → terminal fragment renders
   - Text: "Cuộc gọi hoàn thành. Ghi kết quả bên dưới."
   - No nav buttons on node area
   - `crm_activity` row: `outcome=reached`, `[node:pitch_reorder → purchased → terminal]`

6. **Log via outcome bar:**
   - Tap "Đã mua" on the sticky outcome bar → M08 modal opens
   - Submit → `crm_activity` row from M08 (separate row, normal flow)
   - Redirect to timeline tab → shows 3 nav-step rows + 1 M08 row

**Pass criteria:** All 6 steps succeed, 3 nav-step rows visible in timeline with `[node:...]` body prefix, 1 M08 row with staff's note.

---

## Test Scenario B — Objection Path (price objection, then agrees)

**Script path:** root → reached → reached_interest_check → objection_price → handle_objection_price → purchased → terminal

### Steps

1. Load S14 for same customer.
2. Tap "Gọi được" → node swaps to `reached_interest_check`.
3. Tap "Giá sao / đắt không?" → swaps to `handle_objection_price`.
   - `say` = ưu đãi vừa phải + COD response
   - `hint` visible in muted style: "KHÔNG giảm giá sâu ngay từ đầu"
   - Only 2 option buttons: "Đồng ý" and "Vẫn từ chối"
4. Tap "Đồng ý" → terminal fragment.
5. Log "Đã mua" via outcome bar.

**Pass criteria:** 3 nav-step `crm_activity` rows, path reconstructible from `body` fields.

---

## Test Scenario C — No Answer (terminal from root)

**Script path:** root → no_answer → terminal

### Steps

1. Load S14.
2. Tap "Không nghe máy" on root node.
3. Terminal fragment renders immediately.
4. Tap "Không nghe" on outcome bar → M08 → submit.

**Pass criteria:** 1 nav-step row (`[node:root → no_answer → terminal]`), 1 M08 row. Timeline shows both.

---

## Test Scenario D — Legacy Script Unchanged

Load S14 for any customer whose `.json` file does NOT have `nodes` key (any script other than 603264280).

**Pass criteria:**
- Existing flat render appears: talk-track, talking-points tick-list, objection accordion, guardrails — exactly as before Phase 03.
- No branching elements visible.
- STOP gate still fires for `recommended=false` scripts.

---

## Test Scenario E — Page Refresh Mid-Tree

1. Load S14 for 603264280, tap "Gọi được" to advance to `reached_interest_check`.
2. Refresh the page.

**Pass criteria:** S14 resets to `root` node (state-light acceptable). No error, no blank state.

---

## Verification Queries (SQLite)

After running scenarios A and B, query `crm_activity` directly:

```sql
SELECT activity_id, party_id, outcome, body, occurred_at
FROM crm_activity
WHERE party_id = '<party_id_for_603264280>'
  AND body LIKE '[node:%'
ORDER BY occurred_at DESC
LIMIT 10;
```

Expected: rows with `body` matching `[node:{id} → {outcome} → {next_or_terminal}]` format, `outcome` column values in `{reached, no_answer, callback, refused}` only.

Access path (container):
```bash
docker exec -it crm_data sqlite3 /data/cache.db \
  "SELECT body, outcome, occurred_at FROM crm_activity WHERE body LIKE '[node:%' ORDER BY occurred_at DESC LIMIT 10;"
```

---

## Container Rebuild Command

```bash
docker compose up -d --build crm
```

Run from `D:/Vantt/app/data-integration` (project root). Wait for health check before testing. Templates are baked in — no volume mount workaround needed.

---

## Definition of Done

- [ ] Scenario A: all 6 steps pass, 4 `crm_activity` rows (3 nav + 1 M08)
- [ ] Scenario B: objection path navigates correctly, terminal fires
- [ ] Scenario C: no-answer terminal from root, 2 rows
- [ ] Scenario D: legacy flat script renders identically to pre-WS-B
- [ ] Scenario E: page refresh resets cleanly to root
- [ ] SQLite query confirms nav-step rows have correct format
- [ ] No JS console errors during any scenario
- [ ] STOP gate scenario: load a `recommended=false` script → STOP banner, no node rendered (re-verify R14 still fires)

---

## Rollback

If PoC reveals a blocking issue:

1. Revert `c360_call_cockpit_panel.html` to pre-Phase-03 state.
2. Remove `script_nav_handler.py` and its `composition.py` wiring.
3. Revert `603264280.json` to remove `nodes`/`entry_node` keys.
4. Rebuild container.
5. Nav-step rows in `crm_activity` are harmless (distinct `body` prefix, no FK deps).

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| HTMX `hx-vals` sends form-encoded instead of JSON body | High | High | Pre-check HTMX version (Phase 03 note); switch to JS `fetch` in `s14NavStep` if needed |
| Container rebuild breaks unrelated CRM features | Low | Medium | Run Scenario D (legacy render) immediately after rebuild as smoke test |
| `_s14_node_fragment.html` Jinja2 context leak (variables from parent template bleed in) | Low | Medium | Use `{% include ... only %}` with explicit context dict |
| SQLite `crm_activity` table locked during test (concurrent Dagster writes) | Very Low | Low | Tests are read-heavy; write contention is per-row, not table-lock in WAL mode |

---

## Post-PoC: What to Do with Results

**If PoC passes:** Declare WS-B v1 done. Write a brief outcome note in `plans/260625-1808-s14-approach-script-backend-feed/roadmap-rich-dynamic-script.md` WS-B section. Begin accumulating `crm_activity` nav-step data; revisit flywheel queries after ~50 branching calls.

**If PoC surfaces depth issues** (staff finds 2-level tree insufficient for common objections): extend `handle_objection_price` with a third-level node before scaling to more customers. Do NOT add depth pre-emptively (YAGNI).

**If PoC surfaces HTMX compatibility issues:** switch `script_nav_handler` to return full HTML page fragment via a JS `fetch` + DOM replace instead of HTMX declarative. The interpreter logic (Phase 02) is unchanged; only the transport layer changes.

---

## Generation Note (out of scope for v1)

The offline prompt template (`customer-insight-prompt-template.md`) currently outputs the v2 flat schema. To auto-generate branching trees at scale, the `[OUTPUT SCHEMA]` section would need a `nodes` block added and the `[TASK]` section updated to instruct the LLM to structure objections as named nodes. This is WS-C territory — not in v1. For the PoC, the 603264280 tree is hand-authored (or GPT-assisted in ~30 min) and inserted directly into the JSON file.
