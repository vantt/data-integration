# Phase 05 — hosts/hosted_by sweep

**Effort:** 1.5h  
**Blocker:** Phase 02 (VR-HOSTED-BY + VR-HOSTS-BIDIR must exist before migration so validate catches regressions)  
**File ownership:** All non-screen files in `crm/docs/ui-spec/` except S03 (owned by Phase 04). Specifically: panels/, components/, modals/, overlays/, flows/, `15-system-events.md`, `20-domain-rules.md`.

---

## Context

`hosts:` is currently overloaded:
- On **screens**: "I host these panels/components" (container → children, correct direction)
- On **non-screens** (panels, components, modals, overlays, flows, cross-cutting): "these surfaces host me" (opposite direction — should be `hosted_by:`)

After Phase 02, VR-HOSTS-BIDIR warns on every non-screen file that has `hosts:` listing a screen, because the screen's `hosts:` doesn't list them back in the expected direction.

Migration rule: rename `hosts:` → `hosted_by:` on every non-screen file. Screens keep `hosts:`.

---

## File inventory (verified via grep `^hosts:` across spec)

### Panels — rename `hosts:` → `hosted_by:` (6 files)
| File | Current `hosts:` value |
|---|---|
| `panels/P01-insight-panel.md` | `[S03]` |
| `panels/P02-order-history-panel.md` | `[S03]` |
| `panels/P03-activity-timeline-panel.md` | `[S03]` |
| `panels/P04-tasks-panel.md` | `[S03]` |
| `panels/P05-notes-panel.md` | `[S03]` |
| `panels/P06-conversations-panel.md` | `[S03]` |

### Components — rename `hosts:` → `hosted_by:` (6 files)
| File | Current `hosts:` value |
|---|---|
| `components/C01-sidebar-nav.md` | `[S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12, S13]` |
| `components/C02-global-customer-search.md` | `[S02, S03]` |
| `components/C03-action-queue-card.md` | `[S01]` |
| `components/C04-tag-chips.md` | `[S02, S03, S04]` |
| `components/C05-filter-bar.md` | `[S01, S02, S05, S07, S10, S11]` |
| `components/C06-freshness-badge.md` | `[S01, S03, S12, P01, P02]` |

Note: C06 lists P01 and P02 (panels) as hosts. These are valid `hosted_by` entries — panels can embed components too. VR-HOSTED-BY validates that P01 and P02 are known surfaces (they are).

### Modals — rename `hosts:` → `hosted_by:` (16 files)
| File | Current `hosts:` value |
|---|---|
| `modals/M01-merge-confirm-modal.md` | `[S04]` |
| `modals/M02-create-party-modal.md` | `[S02]` |
| `modals/M03-tag-management-modal.md` | `[S03, S15]` |
| `modals/M04-assign-owner-modal.md` | `[S03]` |
| `modals/M05-create-edit-task-modal.md` | `[S01, S03, S07, P04, S15]` |
| `modals/M06-custom-fields-edit-modal.md` | `[S03]` |
| `modals/M07-create-edit-campaign-modal.md` | `[S10, S11]` |
| `modals/M08-log-activity-modal.md` | `[S03, S01, S06, S15, P02, P03, P04, P05]` |
| `modals/M09-assign-conversation-modal.md` | `[S05, S06]` |
| `modals/M10-close-conversation-modal.md` | `[S06]` |
| `modals/M11-link-party-to-conversation-modal.md` | `[S06]` |
| `modals/M12-record-conversion-modal.md` | `[S11]` |
| `modals/M13-custom-field-def-modal.md` | `[S13]` |
| `modals/M14-create-tag-modal.md` | `[S13, M03]` |
| `modals/M15-edit-contact-core-info-modal.md` | `[S03, S15]` |
| `modals/M16-promote-insight-modal.md` | `[P01, P05]` |

Note: M14 lists M03 as a host — a modal hosting another modal (opened from within M03). Valid `hosted_by` entry. M05, M08 list panels (P04, P02, P03, P04, P05) — also valid.

### Overlays — rename `hosts:` → `hosted_by:` (3 files)
| File | Current `hosts:` value |
|---|---|
| `overlays/O01-confirm-toast-overlay.md` | `[S03, S05, S13, P05]` |
| `overlays/O02-quick-customer-preview-overlay.md` | `[S01, S07]` |
| `overlays/O03-postpone-task-overlay.md` | `[P04, S07, S15]` |

### Flows — replace `hosts: []` with `hosted_by: []` (6 files)
Flows have no hosting relationship. Change key name for consistency. All are empty arrays.

| File |
|---|
| `flows/F01-morning-worklist-call-resell.md` |
| `flows/F02-win-back-at-risk-customer.md` |
| `flows/F03-inbound-chat-resolve-link-party.md` |
| `flows/F04-enrich-profile-dedup-merge.md` |
| `flows/F05-build-segment-run-campaign-measure.md` |
| `flows/F06-ad-lead-attribution.md` |

### Cross-cutting files — replace `hosts: []` with `hosted_by: []` (2 files)
| File |
|---|
| `15-system-events.md` |
| `20-domain-rules.md` |

### Screens — NO CHANGE (13+ screen files keep `hosts:`)
S01–S15 all keep `hosts:`. S03's `hosts: [P01..P06]` is the primary bidirectional anchor.

**Total edits: 33 files** (6 panels + 6 components + 16 modals + 3 overlays + 6 flows + 2 cross-cutting).

---

## Bidirectional consistency check

After migration, VR-HOSTS-BIDIR checks: for every `X.hosted_by: [Y, ...]`, Y must have `hosts: [X, ...]`.

Screens currently have:
- S03: `hosts: [P01, P02, P03, P04, P05, P06]` — panels migrated to `hosted_by: [S03]` ✓
- S01–S15 (except S03): `hosts: []`
- S04: `hosts: []` — but M01 will have `hosted_by: [S04]`. This will produce a VR-HOSTS-BIDIR warn (S04.hosts doesn't list M01).

Assessment: screens don't currently list modals, components, or overlays in their `hosts:` arrays — only panels are listed in S03. This means ~28 of the 33 migrated files will generate VR-HOSTS-BIDIR warns (the modals, components, overlays, and non-P01-P06 panels won't be backed by a screen `hosts:` entry).

**Decision:** VR-HOSTS-BIDIR is **warn-only** (not error). This is intentional — `hosted_by:` is informational and the screens' `hosts:` arrays only track embedded panels, not every modal/component that can open from a screen. Accept the warns as known-informational; do not add modals/components to screen `hosts:` arrays (that would pollute the semantic meaning of `hosts:` on screens).

Document this in CONVENTION.md (add to Phase 03 or as a follow-on note): "VR-HOSTS-BIDIR warns but does not error. `hosts:` on screens lists only permanently-embedded panels; `hosted_by:` on modals/components is informational and may not have a matching screen `hosts:` entry."

---

## Implementation steps

1. For each of the 33 files, perform a single-line frontmatter edit:
   - Find: `hosts:` (line 6 in all files — verified by grep `^hosts:` pattern)
   - Replace: `hosted_by:`
   - Value unchanged.
2. Run validate+build. Check that:
   - VR-HOSTED-BY: 0 errors (all referenced surface IDs are known).
   - VR-HOSTS-BIDIR: warns appear only for modals/components/overlays (expected, see above).
   - No new errors vs. end of Phase 02 state.

---

## Validation command

```bash
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

**Expected outcome:**
- 0 errors.
- VR-HOSTS-BIDIR: ~28 warns (modals, components, overlays with `hosted_by:` that have no matching `hosts:` on their container screens). These are pre-accepted informational warns.
- VR-HOSTS-BIDIR: 0 warns for P01–P06 (covered by S03.hosts).
- All pre-existing warns from Phase 02 still present (VR-PAYLOAD-GRAMMAR, VR-EFFECT-SURFACE). No new error class introduced.
- Exit 0.

---

## Risk / Rollback

**Risk (Low×High):** One of the 33 files has `hosts:` on a different line than line 6 (grep showed all at line 6, but verify before bulk edit).  
Mitigation: Use `grep -n "^hosts:"` per file before editing; or regex-replace `^hosts:` anchored to start-of-line.

**Risk (Low×Med):** Some downstream tooling (outside this skill) reads `hosts:` from frontmatter on panels/modals to build surface graphs. No such tooling found in repo (only validate.mjs and build.mjs read frontmatter). Safe.

**Rollback:** `git checkout HEAD -- crm/docs/ui-spec/panels/ crm/docs/ui-spec/components/ crm/docs/ui-spec/modals/ crm/docs/ui-spec/overlays/ crm/docs/ui-spec/flows/ crm/docs/ui-spec/15-system-events.md crm/docs/ui-spec/20-domain-rules.md`
