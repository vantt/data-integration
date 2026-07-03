# Phase 08b — Modals ui-layout Draft Report

**Date:** 2026-07-02  
**Validator result:** ✓ passed (1 warning: stale wireframe — ignored per instructions)

---

## Per-File Status

| File | Status | Notes |
|------|--------|-------|
| M05-create-edit-task-modal.md | DONE | Single-column [header, body, actions]; `task_kind_select` is body-only JS-reveal (no separate region) |
| M06-custom-fields-edit-modal.md | DONE | Single-column [header, body, actions]; dynamic section groups stay inside `body` (no sub-regions) |
| M07-create-edit-campaign-modal.md | DONE | Single-column [header, body, actions] |
| M08-log-activity-modal.md | DONE | `contact_pref_banner` → `floating` with `when: "party.contact_pref_note_pinned == true"` (conditional banner, not inline row); added new `## Layout` section before the two mode-specific layout sub-sections |
| M09-assign-conversation-modal.md | DONE | Single-column [header, body, actions] |
| M10-close-conversation-modal.md | DONE | Single-column [header, body, actions] |
| M11-link-party-to-conversation-modal.md | DONE | Single-column [header, body, actions]; search results list stays inside `body` |
| M12-record-conversion-modal.md | DONE | Single-column [header, body, actions] |
| M13-custom-field-def-modal.md | DONE | Single-column [header, body, actions]; options sub-section JS-toggled, stays inside `body` |
| M14-create-tag-modal.md | DONE | Single-column [header, body, actions] |
| M15-edit-contact-core-info-modal.md | DONE | 4-row [header, tab_bar, body, actions]; added new `## Layout` section before the 3 tab-specific sub-sections; body sample taken from the contacts tab (richest ASCII) |
| M16-promote-insight-modal.md | DONE | Single-column [header, body, actions]; added new `## Layout` section before `## Layout — Create / Promote` sub-section |

---

## Judgment Calls

1. **M08 `contact_pref_banner` as `floating`** — region is conditional (only shows when a pinned contact_pref note exists). Treat as floating (same pattern as S14's `stop_banner`) rather than a permanent row in `areas`. Condition string `"party.contact_pref_note_pinned == true"` is my approximation of the spec prose.

2. **M08 single YAML for two render modes** — `log` and `note_only/edit_note` use the same frontmatter regions; only body content differs (handled by JS per interactions). One layout block covers both.

3. **M15 body sample from Liên lạc tab** — chosen as richest ASCII. Address and core-info tabs render into the same `body` region; variant blocks not added since tab switching is JS-driven (no distinct region names per tab).

4. **M16 added `## Layout` before sub-heading** — original file had `## Layout — Create / Promote` with no plain `## Layout`. Added parent section to host the YAML, keeping sub-heading untouched.

5. **No 2-column layouts** — all 12 modals show single-column ASCII; no side-by-side panes visible.

6. **JS-reveal sub-sections not given separate regions** — e.g., M08 callback/follow-up date sections, M13 options section. All stay inside `body` as prose/interaction notes rather than layout regions, matching the frontmatter which doesn't declare them as regions.

---

## Unresolved Questions

- M08 `contact_pref_banner` `when:` condition string is paraphrased from prose ("crm_note.note_type='contact_pref' AND pinned=true"). If a canonical boolean flag name exists on the party/note object, update accordingly.

---

Status: DONE  
Summary: Added `yaml ui-layout` blocks to all 12 modals (M05–M16); validator passes with zero VR-LAYOUT errors and one ignored stale-wireframe warning.
