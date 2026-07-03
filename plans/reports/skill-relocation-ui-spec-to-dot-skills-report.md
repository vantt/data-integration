# Skill Relocation: ui-spec → .skills/

**Date:** 2026-07-03  
**Branch:** feature/task-detail-cockpit-backend

---

## Summary

`git mv .agents/skills/ui-spec .skills/ui-spec` (history preserved for all 40+ tracked files). Wrappers created/updated at `.agents/skills/ui-spec/SKILL.md` and `.claude/skills/ui-spec/SKILL.md`. All tool paths and self-references updated.

---

## Moved File Count

40 files renamed (tracked by git as R — rename):
- SKILL.md, references/CONVENTION.md, references/METHODOLOGY.md, references/ui-layout-authoring.md
- templates/* (9 files: README.md, spec.config.yaml, schema/, surfaces/*.md)
- tools/* (config.mjs, validate.mjs, build.mjs, extract.mjs, rename.mjs, interpret.mjs, interpret-wireframe.mjs, hook-validate-on-edit.mjs, package.json, package-lock.json, .gitignore)
- tools/wireframe/* (14 files: all .mjs including tests)
- tools/test/* (run-tests.mjs + fixture-spec/* files)

---

## Wrappers

| Location | Action | Points to |
|---|---|---|
| `.agents/skills/ui-spec/SKILL.md` | Created (new) | `.skills/ui-spec/SKILL.md` |
| `.claude/skills/ui-spec/SKILL.md` | Updated path references | `.skills/ui-spec/SKILL.md` |

Both wrapper directories contain ONLY `SKILL.md` — no source files remain in either.

---

## Path Fixes

### Depth-sensitive (directory level changed from 4–5 levels to 3–4 levels)

| File | Change |
|---|---|
| `tools/hook-validate-on-edit.mjs` | REPO_ROOT fallback: `../../../..` → `../../..` (4→3 levels); comment updated |
| `tools/test/run-tests.mjs` | repoRoot: `../../../../../` → `../../../../` (5→4 levels); comment updated |
| `tools/wireframe/verify-runtime.mjs` | legacy fallback: `../../../../../frontend/…` → `../../../../frontend/…` (5→4 levels); comment updated |

### Self-reference strings (`.agents/skills/ui-spec` → `.skills/ui-spec`)

Files with `replace_all` applied:
- `.skills/ui-spec/SKILL.md` (7 occurrences — CLI examples, source-of-truth note)
- `.skills/ui-spec/references/CONVENTION.md` (6 occurrences — tool invocation examples)
- `.skills/ui-spec/references/ui-layout-authoring.md` (6 occurrences — Visual QA loop commands)
- `.skills/ui-spec/tools/wireframe/chip-audit.test.mjs` (1 — run comment)
- `.skills/ui-spec/tools/wireframe/extract-layout.test.mjs` (1 — run comment)
- `.skills/ui-spec/tools/wireframe/generate-ascii.test.mjs` (1 — run comment)
- `.skills/ui-spec/tools/wireframe/generate-ascii.mjs` (2 — CLI comment + usage line)
- `.skills/ui-spec/tools/wireframe/screenshot.mjs` (1 — error message)
- `.claude/skills/ui-spec/SKILL.md` (3 — all references in wrapper)

### Hook config

| File | Change |
|---|---|
| `.claude/settings.json` | PostToolUse hook command: `.agents/skills/ui-spec/tools/hook-validate-on-edit.mjs` → `.skills/ui-spec/tools/hook-validate-on-edit.mjs` |

### Pre-commit hook

`.git/hooks/` contains only `.sample` files — no active pre-commit hook referencing ui-spec paths. No changes needed.

---

## Verification Outputs

All commands run from repo root `D:\Vantt\app\data-integration`:

```
node .skills/ui-spec/tools/wireframe/extract-layout.test.mjs
  → 11 passed, 0 failed

node .skills/ui-spec/tools/wireframe/generate-ascii.test.mjs
  → 33 passed, 0 failed

node .skills/ui-spec/tools/wireframe/chip-audit.test.mjs
  → 9 passed, 0 failed

node .skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec
  → Scanned 54 spec files, 319 actions, 52 surfaces. ✓ validation passed (0 warning(s)).

node .skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
  → ✓ built generated/: surface-registry.yaml, navigation-graph.yaml, action-registry.csv,
      coverage-report.md  surfaces=54 actions=319 flows=6
  → ✓ ascii: 40 surface(s) with layout — all up to date
  → ✓ chip-audit: 286 tokens · 163 mapped · 123 unmapped
  → ✓ built generated/wireframe-v2.html

node .skills/ui-spec/tools/wireframe/verify-runtime.mjs --root crm/docs/ui-spec
  → Surfaces exercised: 54, Flows exercised: 6, Errors: 0
  → RESULT: PASS -- all assertions clean, zero runtime errors

node .skills/ui-spec/tools/wireframe/screenshot.mjs --root crm/docs/ui-spec --surface S14
  → S14 → ...screenshots/S14.png ... OK (162 KB)

node .skills/ui-spec/tools/test/run-tests.mjs
  → Suite 1 (fixture): 25 passed
  → Suite 2 (crm spec): 2 passed
  → Suite 3 (schema sync): 1 passed
  → Results: 28 passed, 0 failed
```

---

## Residual `.agents/skills/ui-spec` References

Post-move grep across `.skills/` and `.claude/`: **0 files** — clean.  
Historical mentions in `plans/` and `plans/reports/` left untouched (read-only historical docs).

---

## Unresolved Questions

None.
