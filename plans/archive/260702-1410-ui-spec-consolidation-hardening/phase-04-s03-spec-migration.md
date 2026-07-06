# Phase 04 — S03 spec migration (dotted regions + show_panel)

**Effort:** 1h  
**Blocker:** Phase 02 (schema must accept `show_panel`; VR-SHOW-PANEL must exist before migrating)  
**File ownership:** `crm/docs/ui-spec/screens/S03-customer-360-detail.md` only

---

## Context

S03 currently expresses tab switching as `action: mutate, effects: [main_col.show_panel_Pxx]` — invisible to VR-TARGET and absent from navigation-graph display edges. Sidebar interactions all use the broad `region: sidebar` when each button targets a specific sub-section. The `tab_labels` ad-hoc frontmatter key has no convention backing.

After Phase 02 the validator accepts `action: show_panel` and VR-SHOW-PANEL enforces `target: Pxx`.

---

## Current state (verified from `crm/docs/ui-spec/screens/S03-customer-360-detail.md`)

**Frontmatter (lines 1–12):**
```yaml
id: S03
type: screen
name: "Customer 360 Detail"
platforms: [desktop]
hosts: [P01, P02, P03, P04, P05, P06]
tab_labels: ["Value & Behavior", "Ghi chú", "Đơn hàng", "Timeline", "Tasks", "Chat", "Gọi"]
status: active
design_ref: ""
rules: [R2, R3, R6, R7, R13]
regions: [topbar, sidebar, main_col, tab_bar]
```

**Tab interactions (action: mutate → migrate to show_panel):**
| ID | element | current effects | target panel |
|---|---|---|---|
| A-S03-004 | tab_insight | `[main_col.show_panel_P01]` | P01 |
| A-S03-005 | tab_orders | `[main_col.show_panel_P02]` | P02 |
| A-S03-006 | tab_timeline | `[main_col.show_panel_P03]` | P03 |
| A-S03-007 | tab_tasks | `[main_col.show_panel_P04]` | P04 |
| A-S03-008 | tab_notes | `[main_col.show_panel_P05]` | P05 |
| A-S03-009 | tab_chat | `[main_col.show_panel_P06]` | P06 |
| A-S03-018 | tab_call_cockpit | `[main_col.show_panel_call_cockpit]` | *(no registered panel — keep as mutate)* |

**Sidebar interactions (region: sidebar → refine to dotted):**
| ID | element | current region | new region |
|---|---|---|---|
| A-S03-010 | btn_edit_custom_fields | sidebar | sidebar.core_info |
| A-S03-013 | btn_edit_contacts | sidebar | sidebar.contact |
| A-S03-014 | btn_edit_address | sidebar | sidebar.contact |
| A-S03-015 | btn_edit_core_info | sidebar | sidebar.core_info |
| A-S03-016 | contact_channel_quick_action | sidebar | sidebar.contact |
| A-S03-017 | btn_edit_tags | sidebar | sidebar.tags |

---

## Changes

### 1. Frontmatter

**Remove** the `tab_labels` key entirely. Tabs are now expressed by `show_panel` interactions; the label mapping lives in prose ("## Sidebar Sections" / "## Layout") not in machine-readable frontmatter.

**Update `regions:`** — add dotted sidebar sub-regions. Keep parent `sidebar` entry so VR-REGION-PARENT does not warn:

```yaml
regions: [topbar, sidebar, sidebar.warning, sidebar.core_info, sidebar.head_line, sidebar.contact, sidebar.dates, sidebar.tags, main_col, tab_bar]
```

`sidebar.head_line` and `sidebar.warning` and `sidebar.dates` have no interactions currently (those sidebar sections are display-only), but declaring them in `regions[]` makes them available for future interactions and documents the layout structure.

### 2. Tab interactions — migrate 6 of 7 to `show_panel`

For A-S03-004 through A-S03-009, replace:
```yaml
action: mutate
effects: [main_col.show_panel_Pxx]
```
with:
```yaml
action: show_panel
target: Pxx
```
Drop `effects:` key entirely (no side effects beyond the show_panel).

**A-S03-018 (tab_call_cockpit) — keep as `mutate`:**  
`main_col.show_panel_call_cockpit` targets an informally-embedded HTML fragment (`c360_call_cockpit_panel.html`), not a registered panel surface. Migrating to `show_panel` would require creating a new panel surface (P07 or similar) — out of scope. Keep the interaction as:
```yaml
- id: A-S03-018
  element: tab_call_cockpit
  region: tab_bar
  trigger: click
  action: mutate
  effects: [main_col.show_panel_call_cockpit]
```
Add an inline comment in prose above the contract block noting this exception.

### 3. Sidebar interaction regions

Update the 6 interactions listed in the table above — change `region: sidebar` to the specific dotted path per the mapping table.

---

## Full contract block after migration (contract section only — replace existing block)

```yaml crm-contract
interactions:
  - id: A-S03-001
    element: btn_back
    region: topbar
    trigger: click
    action: navigate
    target: S02
  - id: A-S03-002
    element: btn_assign_owner
    region: topbar
    trigger: click
    action: open_overlay
    target: M04
    payload: { party_id: "$party.id" }
  - id: A-S03-003
    element: btn_add_tag
    region: topbar
    trigger: click
    action: open_overlay
    target: M03
    payload: { party_id: "$party.id" }
  - id: A-S03-004
    element: tab_insight
    region: tab_bar
    trigger: click
    action: show_panel
    target: P01
  - id: A-S03-005
    element: tab_orders
    region: tab_bar
    trigger: click
    action: show_panel
    target: P02
  - id: A-S03-006
    element: tab_timeline
    region: tab_bar
    trigger: click
    action: show_panel
    target: P03
  - id: A-S03-007
    element: tab_tasks
    region: tab_bar
    trigger: click
    action: show_panel
    target: P04
  - id: A-S03-008
    element: tab_notes
    region: tab_bar
    trigger: click
    action: show_panel
    target: P05
  - id: A-S03-009
    element: tab_chat
    region: tab_bar
    trigger: click
    action: show_panel
    target: P06
  - id: A-S03-010
    element: btn_edit_custom_fields
    region: sidebar.core_info
    trigger: click
    action: open_overlay
    target: M06
    payload: { party_id: "$party.id" }
  - id: A-S03-011
    element: btn_log_activity
    region: topbar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id" }
  - id: A-S03-012
    element: btn_create_task
    region: topbar
    trigger: click
    action: open_overlay
    target: M05
    payload: { party_id: "$party.id" }
  - id: A-S03-013
    element: btn_edit_contacts
    region: sidebar.contact
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "contacts" }
  - id: A-S03-014
    element: btn_edit_address
    region: sidebar.contact
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "address" }
  - id: A-S03-015
    element: btn_edit_core_info
    region: sidebar.core_info
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "core" }
  - id: A-S03-016
    element: contact_channel_quick_action
    region: sidebar.contact
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "contact_attempt", channel: "$channel.type" }
  - id: A-S03-017
    element: btn_edit_tags
    region: sidebar.tags
    trigger: click
    action: open_overlay
    target: M03
    payload: { party_id: "$party.id" }
  - id: A-S03-018
    element: tab_call_cockpit
    region: tab_bar
    trigger: click
    action: mutate
    effects: [main_col.show_panel_call_cockpit]
    # NOTE: call cockpit is an embedded HTML fragment, not a registered panel surface.
    # Migrate to show_panel when a formal P0x panel surface is registered for it.
  - id: A-S03-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [P01.insight.reload]
  - id: A-S03-LSN02
    listens_to: party.merged
    action: mutate
    effects: [topbar.merged_banner.show]
  - id: A-S03-LSN03
    listens_to: tag_chips.add_requested
    action: open_overlay
    target: M03
    payload: { party_id: "$event.party_id" }
  - id: A-S03-LSN04
    listens_to: tag_chips.remove_requested
    action: mutate
    effects: [party_tag.remove, tags_display.reload]
  - id: A-S03-LSN05
    listens_to: tag_chips.chip_clicked
    action: mutate
    effects: [ui.tag_filter.set]
```

Note: YAML comments (`#`) are stripped by the YAML parser and ignored by the compiler. The note on A-S03-018 is purely for human readers; it will not appear in `action-registry.csv` or `navigation-graph.yaml`.

---

## Implementation steps

1. Open `crm/docs/ui-spec/screens/S03-customer-360-detail.md`.
2. Remove `tab_labels:` line from frontmatter.
3. Replace `regions:` line with the expanded dotted list.
4. In the contract block: apply all changes described in the table above (6 show_panel migrations + 6 region refinements). A-S03-018 stays as mutate.
5. Add a prose note above the Interactions section explaining the call cockpit exception.

---

## Validation command

```bash
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

**Expected outcome:**
- 0 new errors.
- VR-REGION-PARENT: 0 warns (parent `sidebar` is in `regions[]`).
- VR-SHOW-PANEL: 0 errors (P01–P06 are known panels).
- VR-EFFECT-SURFACE: the existing `P01.insight.reload` effect in A-S03-LSN01 triggers 1 warn (P01 is a known surface — this is actually valid. The VR-EFFECT-SURFACE rule warns on *unknown* surfaces, so P01 is known → 0 warn from this. The `main_col.show_panel_call_cockpit` effect in A-S03-018 has segment `main_col` which does not match `[A-Z]{1,2}\d+` pattern → 0 warn).
- `navigation-graph.yaml` now contains 6 display edges with `action: show_panel`.
- Exit 0.

---

## Risk / Rollback

**Risk (Low×Med):** YAML comment syntax inside the contract block fails the YAML parser.  
Mitigation: The `gray-matter` + `js-yaml` stack supports inline comments. Verify by running validate immediately after edit.

**Risk (Low×Low):** `tab_labels` removal breaks a downstream consumer.  
Mitigation: `tab_labels` is ad-hoc frontmatter not referenced by any validator rule or build output. It was not in the schema. Safe to remove.

**Rollback:** `git checkout HEAD -- crm/docs/ui-spec/screens/S03-customer-360-detail.md`
