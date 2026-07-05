# S14 Call Cockpit v2 — Implementation Notes (codegen handoff)

> Lives in `notes/` (outside the ui-spec `surface_dirs`) so the compiler never scans it — it is NOT a surface.
> Companion to `../screens/S14-call-mode-cockpit.md` (contract = source of truth). This doc pins the **code-level HOW** the ui-spec intentionally omits, so codegen reuses the existing codebase instead of reinventing. Not a spec artifact — do not feed to the ui-spec compiler.

## Scope

Redesign tab "Gọi" (embedded in S03) + add full-screen `/customers/{id}/call`, sharing one cockpit component. Decisions locked: **A** (full-width, hide S03 sidebar) · reason-queue **separate** from talking points · **inline** collect · consent=denied **warn-only** (không chặn).

## File touch map

| File | Change |
|---|---|
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py` | `call_cockpit` branch: enrich context (see §1). Add full-screen route (see §4). |
| `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` | Rewrite to 2-pane (LEFT hot-path / RIGHT rail) + identity_bar + alert_row + collect. Keep existing talk-track/points/objection/guardrails/outcome JS. |
| `crm/src/adapters/inbound/web/templates/fragments/_s14_collect_row.html` | **NEW** partial — one collect row + its ✓-done swap target. |
| `crm/src/adapters/inbound/web/static/ds-extra.css` | Reuse `.s14-*`; add `:has()` sidebar-hide + `.s14-rail/.s14-reason/.s14-collect/.s14-alert/.s14-snapshot`. |
| `crm/src/adapters/inbound/web/screens/modals/screen_modal_contact.py` | Add `inline=1` branch to `post_contact` + `post_core` → return `_s14_collect_row.html` fragment instead of `redirect_to_customer`. |
| `crm/src/adapters/inbound/web/templates/fragments/c360_insight_panel.html` | `aqCallNow()` → navigate `/customers/{id}/call` (was: click "Gọi" tab). |
| `crm/src/adapters/inbound/web/templates/{worklist.html,fragments/worklist_fragment.html}` | Task row "Vào chế độ gọi" → `/customers/{id}/call`. |
| `crm/src/adapters/inbound/web/templates/customer_360.html` | (Optional) nothing structural — sidebar hide is pure CSS via `:has`. |

## 1. Panel handler context (call_cockpit branch)

Currently passes only `script`, `meta`. Add (all cache/SQLite — cheap):

```python
_, ids = _load_base(party_id)          # → party360, identities
ins = _load_insight(ids)               # CacheInsight (has .actions, .insight)
# warning_notes: reuse notes.list_notes(party_id) filtered note_type=='warning', not deleted
# resolved_action_ids: action_task_resolver.resolved_action_ids(party_id) if available
context = {
  **ctx, "party": party360, "identities": ids, "insight": ins,
  "warning_notes": warning_notes, "resolved_action_ids": resolved_ids,
  "geo_region": geo_region(party360.province),
  "script": script_dict, "meta": meta_dict,
}
```

Entities (already defined):
- `Party360` (`domain/entities/profile.py`): `display_name, status, gender, birthday, primary_email, consent_contact, address_line, ward, district, province, owner_user_id`.
- `PartyIdentity` (`domain/entities/party.py`): `identity_type, identity_value, is_preferred, contact_status(active|invalid|unreachable), display_label`.
- `CacheInsight` / `CustomerInsight` / `ActionQueueItem` (`domain/entities/cache_insight.py`): see §2/§3.

## 2. Snapshot — cache-first, DuckDB-fallback (decision 1)

Use `insight.insight` (cache) for LTV/AOV/orders/cycle/recency:
- LTV = `lifetime_contribution_margin`, AOV = `avg_order_spend`, cycle = `avg_days_between_orders`, orders = `len(insight.recent_orders)`, recency = from `recent_orders[0].date_key`.

**Only if `insight is None`** (cache miss) → fallback `customer_dim_metrics.get_by_customer_id(sapo_id)` (olap.duckdb, `read_only=True`). Do NOT hit DuckDB when cache present. `dim_metrics` also gives `lifecycle_stage/geo_region/product_affinity` if you want extra snapshot chips.

## 3. Reason-to-call — read-context, tick client-side (decision 2)

Source: `insight.sorted_actions` (`ActionQueueItem`: `action_type, rationale_vi, value_at_stake_vnd, last_order_code, last_purchase_date, estimated_depletion_date`). Mark handled visually via `resolved_action_ids`.
- Render with existing `.aq-card` markup style from `c360_insight_panel.html` (badge helpers `bdg_cls/bdg_tip('action_type')`, `fmt_vnd`).
- Tick "đã nói" (A-S14-025) = **client-side only** (like talking points; no server write). Do NOT rebuild claim/dismiss here — that stays in P01.
- "Đặt lịch" (A-S14-024) → reuse `hx-get /modals/m05` with `hx-vals` prefill (copy pattern from P01 aq-card `Đặt lịch`).

## 4. Endpoints

**Full-screen route** — new handler (same module or a thin wrapper), renders a page shell (topbar: back/queue/next) that embeds the SAME cockpit fragment:
```
GET /customers/{party_id}/call   → templates full page → includes c360_call_cockpit_panel.html
```
Reuse `_resolve_to_party_id` + the enriched context from §1. Queue counter `#n/N` / next-in-queue: source from worklist queue if available; else omit gracefully (A-S14-010 hidden when no queue context).

**Inline collect** — extend M15 POSTs with `inline: str = Form("0")`:
- `post_contact` (add_channel for zalo/email/phone_secondary) and `post_core` (birthday/gender): when `inline=="1"` → return `TemplateResponse("fragments/_s14_collect_row.html", {..., "done": True, "label": ..., "value": ...})` instead of `redirect_to_customer`. Repo writes unchanged (`insert_identity_full` / `upsert_profile`).
- Address stays modal (A-S14-022 → M15 tab=address) — 4 fields, not inline.

## 5. Collect derivation (RIGHT rail)

Compute "missing" server-side, pass a small list to template:
- no identity `zalo` → row "Zalo"; no `email` → "Email"; no `phone_secondary` → "Số phụ" (optional).
- `party.birthday` falsy → "Sinh nhật"; `party.gender` in (None,'','unknown') → "Giới tính".
- any identity with `contact_status=='invalid'` → "SĐT lỗi → [Sửa]" (A-S14-023 → M15 tab=contacts).
- append `script.data_gaps[]` as read-only prompts.

## 6. Alert row (issues to discover)

Chips from: `script.risk.headline`; `insight.insight.customer_status` in (at_risk,churned); `is_high_cancel_risk`; `is_high_discount_sensitivity`; `is_margin_negative`; any `contact_status!='active'`; `party.consent_contact`; `warning_notes`. Consent=denied → red chip, **do not disable** call/zalo buttons (decision 4).

## 7. CSS

```css
/* hide S03 static sidebar + go full-width when cockpit present (embedded tab) */
.detail-grid:has(#s14-panel-root){ grid-template-columns: 1fr; }
.detail-grid:has(#s14-panel-root) .detail-sidebar{ display: none; }
```
Reuse existing `.s14-*` (talk-track, tp, obj, guard, outcome, trust). New blocks: `.s14-rail` (RIGHT column), `.s14-reason`, `.s14-collect`, `.s14-alert`, `.s14-snapshot`. Full-screen wrapper `.s14-fs-topbar`. Desktop-only (spec platforms:[desktop]) — rail stacks under main below ~1100px is nice-to-have, not required.

## 8. Reuse map (DRY)

| Need | Reuse (don't rebuild) |
|---|---|
| Reason cards | `.aq-card` markup + `bdg_cls/bdg_tip`, `fmt_vnd` (from `c360_insight_panel.html`) |
| Talk-track/points/objection/outcome | existing `.s14-*` markup + inline `<script>` in the panel (keep verbatim) |
| Snapshot format | jinja filters `format_vnd`, `recency_days_label`, `fmt_date_key` |
| Inline write | M15 repo methods (`insert_identity_full`, `upsert_profile`) |
| Schedule / verify | M05 (`/modals/m05`), M15 (`/modals/m15`), M08 (`/modals/m08`) |

## 9. INVARIANT (critical)

Talking-point ticks, objection accordion, reason "đã nói", channel toggle are **client-side only** (not persisted). Therefore **every HTMX call inside the cockpit MUST target its own sub-region** (`hx-target` the row/section, `hx-swap=outerHTML`). **Never** re-render `#s14-panel-root` from within the cockpit, or all call-state is lost. Inline collect swaps only its `_s14_collect_row.html`.

## 10. Interaction → code map

| Action | Element | Wiring |
|---|---|---|
| A-S14-020 | collect channel [+] | POST `/customers/{id}/contact?inline=1` (add_channel) → swap row |
| A-S14-021 | collect core [+] | POST `/customers/{id}/core?inline=1` (birthday/gender) → swap row |
| A-S14-022 | collect address | `hx-get /modals/m15?party_id=&tab=address` |
| A-S14-023 | fix invalid contact | `hx-get /modals/m15?party_id=&tab=contacts` |
| A-S14-024 | reason "Đặt lịch" | `hx-get /modals/m05` + hx-vals prefill (P01 pattern) |
| A-S14-025 | reason "đã nói" tick | client JS toggle (mirror `s14ToggleTP`) |
| A-S14-001..011 | (existing) | unchanged — keep current handlers/JS |

## 11. Outcome bulk-resolve + async-resolve contract — IMPLEMENTED (phase-02)

> **Status:** bulk-resolve UI wiring IMPLEMENTED (phase-02); async-resolve endpoint IMPLEMENTED.
> See `test_bulk_resolve_endpoint.py` (5 endpoint-level tests) and `test_outcome_bulk_resolve.py` (23 unit tests).

## 11. Outcome bulk-resolve + async-resolve contract (Phase 04)

### Outcome bulk-resolve — extended `handle_log_activity`

**Endpoint:** `POST /customers/{party_id}/log-activity`  
**Module:** `screen_customer_360_activity.py` → `register_activity_routes()`

Two new optional form fields added alongside the existing fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `resolve_action_ids` | `str` | `""` | Comma-separated `action_id` values to dismiss via `action_state.dismiss()` |
| `resolve_task_ids` | `str` | `""` | Comma-separated `task_id` values to transition to `"done"` via `task_svc.transition_status()` |

**Behaviour:**
- Runs after the existing activity log write, auto-claim, save-as-note, schedule-followup, and single `complete_task=1` steps.
- Each id resolved independently; a failure on one never aborts the others (logged at WARNING).
- `skip_task_id` guard: if `complete_task=1` and `task_id` is set, that same `task_id` is excluded from the bulk `resolve_task_ids` loop to prevent double-transition.
- `action_state` must now be wired into `register_activity_routes()` (added as `action_state=` kwarg); `composition.py` passes `sqlite_repos["action_state"]`.
- Response unchanged: `HX-Redirect` to `/customers/{party_id}?tab=timeline`.

**Cockpit outcome bar binding** (for ui-port):
```html
<form hx-post="/customers/{{ party_id }}/log-activity" ...>
  <!-- existing fields … -->
  <input type="hidden" name="resolve_action_ids" value="{{ rail_primary.action_id or '' }}">
  <input type="hidden" name="resolve_task_ids"   value="{{ rail_primary.task_id or '' }}">
</form>
```

---

### Async-resolve (A-S14-026) — new endpoint

**Endpoint:** `POST /customers/{party_id}/reason/resolve-async`  
**Module:** `screen_customer_360_activity.py` → `register_activity_routes()` (same module, same deps)

**Purpose:** Resolve a rail item via an async channel (Zalo/email) WITHOUT logging a call.

| Form field | Type | Default | Description |
|---|---|---|---|
| `channel` | `str` | `""` | `"zalo"` or `"email"` — determines `activity_type` (chat/email) |
| `action_id` | `str` | `""` | Optional; single id to dismiss via `action_state.dismiss()` |
| `task_id` | `str` | `""` | Optional; single id to transition to `"done"` |
| `note` | `str` | `""` | Optional free-text logged as activity body |

**Behaviour:**
- Logs an outbound activity: `direction="out"`, `outcome="async_sent"`, `activity_type` derived from `channel`.
- Calls `bulk_resolve(action_ids, task_ids, …)` — same helper as bulk-resolve above.
- Returns **204 No Content** — HTMX target should be the specific rail item (`hx-swap="outerHTML"`). The cockpit panel (`#s14-panel-root`) is NOT re-rendered (preserves call state per §9 invariant).

**Rail item binding** (for ui-port):
```html
<button hx-post="/customers/{{ party_id }}/reason/resolve-async"
        hx-vals='{"channel": "zalo",
                  "action_id": "{{ item.action_id or '' }}",
                  "task_id":   "{{ item.task_id or '' }}"}'
        hx-target="#rail-item-{{ item.action_id or item.task_id }}"
        hx-swap="outerHTML">
  Gửi Zalo
</button>
```

---

### Helper module

Pure-logic helpers (no FastAPI dep) live in:  
`crm/src/adapters/inbound/web/screens/customer360/outcome_resolve_helpers.py`  
— `parse_id_list(raw: str) → list[str]`  
— `bulk_resolve(action_ids, task_ids, action_state, task_svc, skip_task_id="", actor_id="") → None`

Unit tests: `crm/src/tests/test_outcome_bulk_resolve.py` (23 tests, pure-logic, no FastAPI).

## 12. Out of scope / confirm

- R1 relax (consent warn-not-block) is a product decision — see `ST-CALL-CONSENT-WARN`. If policy hardens later, gate call/zalo buttons here.
- Queue navigation (#n/N, next) only in full-screen; embedded tab omits topbar.
- No new DB migration, no new entity — pure re-composition + 2 endpoint tweaks + 1 route.

## Interactions

```yaml crm-contract
interactions: []
```
