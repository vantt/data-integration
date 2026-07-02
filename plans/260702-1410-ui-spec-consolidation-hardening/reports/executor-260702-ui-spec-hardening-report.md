# Executor Report — UI-Spec Consolidation + Hardening

Plan: `plans/260702-1410-ui-spec-consolidation-hardening/`  
Branch: `feature/task-detail-cockpit-backend`  
Date: 2026-07-02

---

## Phase 01 — De-vendor tools ✅

**Status:** completed

**Actions:**
- `npm install --prefix .agents/skills/ui-spec/tools` — installed node_modules in canonical tools
- `git rm -r crm/docs/ui-spec/tools/` — removed 26 tracked files
- `rm -rf crm/docs/ui-spec/tools/` — removed remaining node_modules
- Edited `.agents/skills/ui-spec/SKILL.md`: removed vendored-tools language, updated init command, Modes 1/2/3 step references, propagation table header, rename tool reference
- Edited `.claude/skills/ui-spec/SKILL.md`: replaced "vendored copy" sentence with centralized invocation note
- Edited `.agents/skills/ui-spec/references/CONVENTION.md` §6: replaced `cd tools && npm run check` with `node .agents/.../validate.mjs --root` commands

**Validate output (post-deletion):** 54 files, 311 actions, 52 surfaces; 14 pre-existing VR-OVERVIEW warns (R1–R14 in overview listed as surfaces — pre-existing, not introduced). Exit 0.  
**Build output:** surfaces=54 actions=311 flows=6. Exit 0.

---

## Phase 02 — Schema + validator hardening ✅

**Status:** completed

**Actions:**
- Both schema files: added `show_panel` to action enum; extended allOf[0] to require `target` for `show_panel`
- `validate.mjs`: moved `surfaceTypeById` to pass-1 scope, added 7 new rules: VR-SHOW-PANEL, VR-REGION-PARENT, VR-EFFECT-SURFACE, VR-HOSTED-BY, VR-HOSTS-BIDIR (panel/component only per controller decision — modals/overlays exempt), VR-PAYLOAD-GRAMMAR, VR-ELEMENT-UNIQUE; G1 modal detection fix (type-only), G2 submit acceptance + message fix, G3 element uniqueness warn
- `build.mjs`: verified existing `pushEdge` loop already captures `show_panel` edges — no code change needed

**Validate output (post-hardening, pre-migration):** Exit 0.
- VR-PAYLOAD-GRAMMAR: 8 warns (C03×3, C04×2, C05×1, C06×2)
- VR-HOSTS-BIDIR: 0 warns (restricted to panel/component; no panels/components had `hosted_by:` yet)
- VR-EFFECT-SURFACE: 0 warns (P01.insight.reload effect — P01 is known surface, no false positive)
- VR-REGION-PARENT: 0 (no dotted regions yet)
- Total: 22 warnings (14 pre-existing + 8 new VR-PAYLOAD-GRAMMAR)

---

## Phase 03 — Convention + SKILL.md docs ✅

**Status:** completed

**Actions:**
- `CONVENTION.md`: added §3.5 promotion rules table, `show_panel` example block, §9 payload grammar, listener ID note update, §6 `--vendor` note, `hosts:`/`hosted_by:` frontmatter note in §1
- `.agents/skills/ui-spec/SKILL.md`: added `show_panel` + `hosted_by` rows to propagation table
- Templates: renamed `hosts:` → `hosted_by:` in panel.md, component.md, modal.md, overlay.md, flow.md

**Validate output:** identical to Phase 02 end — no new errors/warns from doc/template changes. Exit 0.

---

## Phase 04 — S03 spec migration ✅

**Status:** completed

**Actions:**
- `S03-customer-360-detail.md`: removed `tab_labels:` key; expanded `regions:` to include dotted sidebar sub-regions; migrated A-S03-004–009 from `action: mutate + effects` to `action: show_panel + target: Pxx`; refined A-S03-010/013/014/015/016/017 region from `sidebar` to dotted paths; kept A-S03-018 as `mutate` with inline comment

**Validate output:** 0 new errors, 0 VR-REGION-PARENT warns, 0 VR-SHOW-PANEL errors. navigation-graph.yaml contains 6 show_panel edges. Exit 0.

---

## Phase 05 — hosts/hosted_by sweep ✅

**Status:** completed

**Actions:**
- Renamed `hosts:` → `hosted_by:` in 39 non-screen files (via `sed -i`): 6 panels, 6 components, 16 modals, 3 overlays, 6 flows, 2 cross-cutting files
- VR-HOSTS-BIDIR scope: panels/components only → modals/overlays/flows get 0 VR-HOSTS-BIDIR warns

**Validate output:** 0 errors. VR-HOSTED-BY: 0 errors (all targets known, including P01/P02 in C06 and M03 in M14). VR-HOSTS-BIDIR: 30 warns for components (C01×13, C02×2, C03×1, C04×3, C05×6, C06×5) — expected informational (screens only list panels in `hosts:`, not components). Total: 52 warnings. Exit 0.

---

## Phase 06 — Payload grammar sweep ✅

**Status:** completed

**Actions:**
- `C04-tag-chips.md`: fixed `$party_id` → `$party.id` in A-C04-001 and A-C04-002 payloads (2 fixes, C04 warns cleared)
- `C03-action-queue-card.md`, `C05-filter-bar.md`, `C06-freshness-badge.md`: added Props/API prose note documenting remaining VR-PAYLOAD-GRAMMAR warns as accepted component-prop pattern

**Validate final output:** Exit 0.
- VR-PAYLOAD-GRAMMAR: 6 (C03×3, C05×1, C06×2) — all documented as accepted
- VR-HOSTS-BIDIR: 30 (components, accepted informational)
- VR-OVERVIEW: 14 (R1–R14, pre-existing)
- VR-EFFECT-SURFACE, VR-REGION-PARENT, VR-SHOW-PANEL, VR-ELEMENT-UNIQUE: 0
- Total: 50 warnings, 0 errors. Exit 0.
- navigation-graph.yaml: 6 `show_panel` edges (S03→P01..P06) confirmed ✅

---

## Final Acceptance Criteria Check

1. `crm/docs/ui-spec/tools/` deleted (26 tracked files git-rm'd, node_modules rm'd) ✅; centralized validate+build exit 0 ✅
2. All hardening items implemented: VR-SHOW-PANEL, VR-REGION-PARENT, VR-EFFECT-SURFACE, VR-HOSTED-BY, VR-HOSTS-BIDIR, VR-PAYLOAD-GRAMMAR, G1/G2/G3 in canonical validate.mjs + both schema files (show_panel enum + allOf) + CONVENTION.md + SKILL.md ✅
3. S03: dotted regions expanded ✅, 6 tab interactions migrated to show_panel ✅, sidebar regions refined ✅, A-S03-018 kept as mutate with documented exception ✅; hosted_by sweep: 39 files ✅; C04 payload tokens normalized ✅; validate exit 0 ✅; navigation-graph.yaml contains S03→P01..P06 show_panel edges ✅
4. No stale `cd docs/ui-spec/tools` or `npm run check` wording in any skill doc ✅
5. `git status` changes only within `.agents/skills/ui-spec/`, `.claude/skills/ui-spec/`, `crm/docs/ui-spec/`, `plans/` ✅

---

## Post-execution refinement (controller, 2026-07-02 14:40)

Executor finished with 50 accepted warns — all three families were systematic false positives, fixed at the validator root instead of accepting:

1. **VR-HOSTS-BIDIR** (30 warns): scope narrowed to `panel` type only — screens curate `hosts:` as embedded panels by design; component placement is one-way via `hosted_by`. Also fixed warn attribution (`[null]` → child surface file).
2. **VR-PAYLOAD-GRAMMAR** (6 warns): bare `$prop` tokens inside component `emits` payloads are the documented component-prop pattern — rule now skips them.
3. **VR-OVERVIEW** (14 warns): overview row matching now restricted to configured `surface_id_prefixes` — domain-rule rows (R1..R14) no longer misread as surface index entries.

Docs synced: CONVENTION.md §2 rule 11 + §9 notes (removed phase reference per stable-artifacts rule), SKILL.md propagation table.

Final state: validate exit 0, **0 warnings**; build exit 0; navigation-graph.yaml carries S03→P01..P06 show_panel edges.
