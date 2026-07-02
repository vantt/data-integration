---
title: "ui-spec skill consolidation + hardening"
description: "De-vendor tools, fix validator holes, migrate crm spec to new conventions (dotted regions, show_panel, hosted_by, payload grammar)"
status: completed
priority: P1
effort: 7h
branch: feature/task-detail-cockpit-backend
tags: [ui-spec, tooling, refactor]
created: 2026-07-02
---

# UI-Spec Consolidation + Hardening

## Context

Canonical skill: `.agents/skills/ui-spec/` — owns SKILL.md, references/, templates/, tools/.
Discovery wrapper: `.claude/skills/ui-spec/SKILL.md` (thin).
Deployed spec: `crm/docs/ui-spec/` (15 screens, 6 panels, 16 modals, 3 overlays, 6 components, 6 flows).
Orphan `.skills/ui-spec/` already deleted.

## Decisions (pre-locked, do not re-litigate)

- D1: `.agents/skills/ui-spec/` is canonical. `.claude/skills/ui-spec/SKILL.md` = thin wrapper.
- D2: Delete `crm/docs/ui-spec/tools/`. All tool invocations centralized via `--root` arg.
- D3: 5 hardening items (dotted regions, show_panel, hosts split, payload grammar, minor fixes).

## Phases

| # | Name | Effort | Blocker | Status |
|---|------|--------|---------|--------|
| 01 | [De-vendor tools](phase-01-de-vendor-tools.md) | 45m | — | completed |
| 02 | [Schema + validator hardening](phase-02-schema-validator-hardening.md) | 2h | 01 | completed |
| 03 | [Convention + SKILL.md docs](phase-03-convention-skill-docs.md) | 1h | 02 | completed |
| 04 | [S03 spec migration (dotted regions + show_panel)](phase-04-s03-spec-migration.md) | 1h | 02 | completed |
| 05 | [hosts/hosted_by sweep](phase-05-hosts-hosted-by-sweep.md) | 1.5h | 02 | completed |
| 06 | [Payload grammar sweep](phase-06-payload-grammar-sweep.md) | 45m | 02 | completed |

Phases 03–06 are independent of each other (disjoint file ownership). Phase 02 must complete first.

## Acceptance Criteria

1. `crm/docs/ui-spec/tools/` deleted; `node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec` exits 0.
2. All D3 items implemented in canonical skill + both schema files + docs.
3. crm spec migrated: S03 dotted regions, 6 tab interactions as `show_panel`, hosts → hosted_by on all non-screen files, C04 payload tokens normalized.
4. SKILL.md (canonical + wrapper) and CONVENTION.md updated consistently; no stale vendored-tools language.
5. No changes outside `.agents/skills/ui-spec/`, `.claude/skills/ui-spec/`, `crm/docs/ui-spec/`, `plans/`.

## File Ownership by Phase

| Phase | Exclusive files |
|---|---|
| 01 | `crm/docs/ui-spec/tools/` (delete); SKILL.md (canonical + wrapper); CONVENTION.md §6 |
| 02 | `validate.mjs`, `build.mjs`, both `schema/surface-contract.schema.json` |
| 03 | `CONVENTION.md` (full), SKILL.md (canonical), templates/surfaces/*.md |
| 04 | `crm/docs/ui-spec/screens/S03-*.md` |
| 05 | `crm/docs/ui-spec/{panels,components,modals,overlays,flows}/*.md`, `15-system-events.md`, `20-domain-rules.md` |
| 06 | `crm/docs/ui-spec/components/C04-*.md` (norm); C03/C05/C06 warn-only |

No file appears in more than one phase.
