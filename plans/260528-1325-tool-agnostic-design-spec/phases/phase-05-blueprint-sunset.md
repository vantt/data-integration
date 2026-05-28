---
title: "Phase 5 — Blueprint Sunset"
status: not_started
priority: P3
depends_on: [phase-03]
created: 2026-05-28
updated: 2026-05-28
duration_estimate: "0.5 day"
---

## Goal

Archive the blueprint folder and remove legacy tooling. After this phase, only the v2 Design
Spec path exists; no active code or docs reference the blueprint format.

## Scope

**IN**:
- Archive `docs/analytics-handbook/blueprints/*.md` → `blueprints/_archive_2026-06/`
- Investigate `blueprints/rill/` sub-folder before archiving (may be live system)
- Remove or archive legacy scripts: `deploy_from_markdown.js`, `create_blueprint.js`
- Remove `blueprint_template.md`
- Evaluate `markdown_parser.js`: grep references before removing; keep if reused elsewhere
- Update `CLAUDE.md`, `AGENTS.md`, slash commands to reference v2 path only

**OUT**:
- Removing the markdown parser if it is referenced by non-blueprint code
- Any changes to `designs/` or `domains/` (frozen after Phase 3/4)

## Steps

1. **Investigate `blueprints/rill/`**:
   - Check if any active deployment scripts or CI jobs reference this folder
   - `grep -r "rill" .skills/ .claude/ CLAUDE.md AGENTS.md`
   - If live: exclude from archive, note as separate target; if inert: archive with rest

2. **Grep before removing `markdown_parser.js`**:
   - `grep -r "markdown_parser" .skills/ scripts/`
   - If referenced only by `deploy_from_markdown.js` (which is itself being removed): safe to archive
   - If referenced by other scripts: keep, update comment to note it is no longer blueprint-specific

3. **Archive blueprints**:
   - Create `docs/analytics-handbook/blueprints/_archive_2026-06/`
   - Move all `blueprints/*.md` (except `rill/` if live) into archive folder
   - Add `_archive_2026-06/README.md`: "Archived after v2 Design Spec migration (Phase 3).
     Use `docs/analytics-handbook/designs/` for all active specs."

4. **Remove legacy scripts** (or move to `_archive/` sub-folder if hard delete feels risky):
   - `deploy_from_markdown.js` → remove (or `scripts/_archive/`)
   - `create_blueprint.js` → remove
   - `blueprint_template.md` → remove
   - `markdown_parser.js` → remove if safe per Step 2

5. **Update slash commands**:
   - `create-metabase-blueprint.md`: delete or replace with redirect note pointing to
     `/design-dashboard` + `deploy_from_design_spec.js`
   - `deploy-metabase-blueprint.md`: delete (replaced by v2 deploy path documented in Phase 2)

6. **Update project root docs**:
   - `CLAUDE.md` (project): remove blueprint references from skill commands table;
     update deployment commands section to show `deploy_from_design_spec.js` only
   - `AGENTS.md`: remove blueprint workflow references; update Quick References section

7. **Verify nothing breaks**:
   - `grep -r "blueprint" .claude/ CLAUDE.md AGENTS.md` — must return 0 active references
     (archive folder and historical notes are acceptable)
   - Run `validate-analytics-artifacts.js` on all `designs/*.md` — must still pass

## Files Touched

- 🗄️ `D:\Vantt\app\data-integration\docs\analytics-handbook\blueprints\*.md` → `_archive_2026-06/`
- 🗄️ `D:\Vantt\app\data-integration\.skills\metabase-automation\scripts\deploy_from_markdown.js` → remove/archive
- 🗄️ `D:\Vantt\app\data-integration\.skills\metabase-automation\scripts\create_blueprint.js` → remove
- 🗄️ `D:\Vantt\app\data-integration\.skills\metabase-automation\templates\blueprint_template.md` → remove
- 🗄️ `D:\Vantt\app\data-integration\.skills\metabase-automation\lib\markdown_parser.js` → evaluate; remove if unreferenced
- 🔧 `D:\Vantt\app\data-integration\.claude\commands\create-metabase-blueprint.md` → delete or redirect
- 🔧 `D:\Vantt\app\data-integration\.claude\commands\deploy-metabase-blueprint.md` → delete
- 🔧 `D:\Vantt\app\data-integration\CLAUDE.md` — remove blueprint command table entries
- 🔧 `D:\Vantt\app\data-integration\AGENTS.md` — remove blueprint workflow references

## Success Criteria

- [ ] `blueprints/_archive_2026-06/` contains all migrated blueprints with archive README
- [ ] `blueprints/rill/` disposition documented (archived or explicitly kept as live)
- [ ] No active references to blueprint format in `.claude/`, `CLAUDE.md`, `AGENTS.md`
- [ ] Legacy scripts removed or archived; `grep "deploy_from_markdown\|create_blueprint" .skills/` returns 0
- [ ] `validate-analytics-artifacts.js` passes on all `designs/*.md` after cleanup
- [ ] Slash commands point to v2 path only

## Risks

- **`blueprints/rill/` is a live deployment target**: archiving it breaks an active workflow.
  Mitigation: grep + manual check in Step 1 before any move; exclude from archive if active.
- **`markdown_parser.js` reused by non-blueprint code**: silent breakage if removed carelessly.
  Mitigation: grep all references in Step 2; only remove if exclusively used by sunset scripts.

## Cross-references

- **Decisions**: [D1 skip blueprint / sunset](../decisions.md#d1-skip-blueprint-file-direct-deploy) · [D5 per-tool deployer](../decisions.md#d5-per-tool-deployer-pattern)
- **Reference**: [`../reference/key-files.md`](../reference/key-files.md) §5.2 Blueprints list · §6 Slash Commands legacy status
