# Phase 01 — De-vendor tools

**Effort:** 45m  
**Blocker:** none  
**File ownership:** `crm/docs/ui-spec/tools/` (delete); `.agents/skills/ui-spec/SKILL.md`; `.claude/skills/ui-spec/SKILL.md`; `.agents/skills/ui-spec/references/CONVENTION.md` (§6 only)

---

## Context

`crm/docs/ui-spec/tools/` holds a vendored copy of the compiler pipeline (11 tracked files + gitignored `node_modules`). D2 decision: delete the vendor copy; all invocations become centralized via `--root` arg. `config.mjs` already supports `--root` and CWD walk-up (verified: `.agents/skills/ui-spec/tools/config.mjs` lines 11–29). The `npm run check` package.json script problem: `node validate.mjs && node build.mjs` — both resolve CWD-relative paths, so the `--root` arg must be passed to each script directly via `node` invocation, not via `npm run check -- --root X` (which only appends to the last command).

---

## Files to modify/delete

### Delete (all tracked files + disk)
```
crm/docs/ui-spec/tools/build.mjs
crm/docs/ui-spec/tools/config.mjs
crm/docs/ui-spec/tools/extract.mjs
crm/docs/ui-spec/tools/interpret-wireframe.mjs
crm/docs/ui-spec/tools/interpret.mjs
crm/docs/ui-spec/tools/package.json
crm/docs/ui-spec/tools/package-lock.json
crm/docs/ui-spec/tools/rename.mjs
crm/docs/ui-spec/tools/validate.mjs
crm/docs/ui-spec/tools/wireframe/  (directory — tracked files within)
crm/docs/ui-spec/tools/node_modules/  (gitignored — delete from disk)
```

### Edit: `.agents/skills/ui-spec/SKILL.md`

**Target text (current, line 13):**
> each spec root (e.g. `crm/docs/ui-spec/`) carries a **vendored copy** of `tools/` + `schema/` so its `npm run check` is self-contained; re-sync vendored copies from here after changing tools.

**Replace with:**
> each spec root (e.g. `crm/docs/ui-spec/`) carries only `schema/` — tool invocations are centralized (see Commands section).

**Also update** the `init` command doc (~line 37) — remove "tools/" from the scaffolded directory tree listing. Add note:

> Default: does **not** copy tools. Use `--vendor` flag only when exporting a spec to a repo that has no access to `.agents/skills/ui-spec/tools/`.

**Also update** Mode 1/2/3 sections — every occurrence of:
```
npm run check
cd docs/ui-spec/tools && npm run check
npm run validate
npm run build
```
Replace with:
```
node .agents/skills/ui-spec/tools/validate.mjs --root <spec-root>
node .agents/skills/ui-spec/tools/build.mjs --root <spec-root>
```
Where `<spec-root>` = path from repo root to the spec (e.g. `crm/docs/ui-spec`). Note: run from repo root.

Occurrences to update (cite file:line after reading):
- Mode 1 step 6, line ~250 (6 of `check` call) [VERIFY: re-read after Phase 01 starts]
- Mode 2 step d, line ~288
- Mode 3 step 4, line ~310
- CONVENTION.md §6 (covered below)

### Edit: `.claude/skills/ui-spec/SKILL.md`

**Current line 11:**
> **Deployed instances**: each spec root (e.g. `crm/docs/ui-spec/`) carries a vendored copy of `tools/` + `schema/` so `npm run check` is self-contained — sync it from `.agents/skills/ui-spec/tools/` when the skill's tools change.

**Replace with:**
> **Tool invocation**: centralized at `.agents/skills/ui-spec/tools/`. Run from repo root: `node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec` (or any spec root). Each spec root keeps only `schema/`.

### Edit: `.agents/skills/ui-spec/references/CONVENTION.md` §6

**Current §6 (~lines 172-179):**
```bash
cd docs/ui-spec/tools
npm install
npm run validate
npm run build
npm run check
```

**Replace with:**
```bash
# From repo root:
npm install --prefix .agents/skills/ui-spec/tools   # one-time
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec
node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
# combined:
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

---

## Implementation steps

1. Verify `node_modules` exists at `.agents/skills/ui-spec/tools/`; if not, run:
   ```bash
   npm install --prefix .agents/skills/ui-spec/tools
   ```
2. Smoke-test centralized invocation before deleting vendor copy:
   ```bash
   node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec
   ```
   Expected: green (existing spec validated from canonical tools).
3. Delete vendor copy:
   ```bash
   rm -rf crm/docs/ui-spec/tools
   ```
4. Apply text edits to SKILL.md (canonical), SKILL.md (wrapper), CONVENTION.md §6.

---

## Validation command (end of phase)

```bash
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

**Expected outcome:** exits 0, prints `✓ validation passed` + `✓ built generated/`. Same output as before the delete since nothing in the spec changed.

---

## Risk / Rollback

**Risk (Low×High):** `node_modules` absent in canonical tools → validate fails.  
**Mitigation:** Step 1 checks and installs before deleting vendor copy.

**Risk (Low×Low):** Other scripts in tools (rename, interpret, interpret-wireframe) break because they import from the same directory.  
**Mitigation:** `--root` is a config.mjs concern; other scripts use the same config module. Centralized invocations work identically.

**Rollback:** If canonical tools fail, vendor copy is still in git history (`git checkout HEAD -- crm/docs/ui-spec/tools/`). Do not commit until validate+build green.
