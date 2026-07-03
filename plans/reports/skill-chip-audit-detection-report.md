# Chip Audit Detection — Implementation Report

## What was done

Added a chip-coverage audit to the ui-spec skill. The audit mechanically detects every `[token]` chip drawn in any `samples:` value of a `yaml ui-layout` fence and flags those with no matching key in `elements:` as **unmapped**. This surfaces the gap class "sample draws a control but nothing backs it" automatically on every build.

---

## Files created / modified

| Path | Change |
|---|---|
| `.agents/skills/ui-spec/tools/wireframe/chip-audit.mjs` | NEW — exports `auditChips(surfaces)`, `renderChipAuditMd(result)`, CLI |
| `.agents/skills/ui-spec/tools/wireframe/chip-audit.test.mjs` | NEW — 9 tests, no framework |
| `.agents/skills/ui-spec/tools/build.mjs` | MODIFIED — import + call; phase 7.5 wired after ASCII injection |
| `.agents/skills/ui-spec/references/ui-layout-authoring.md` | MODIFIED — new §12 Chip coverage audit |
| `.agents/skills/ui-spec/SKILL.md` | MODIFIED — `chip-audit.md` added to build outputs list |
| `crm/docs/ui-spec/generated/chip-audit.md` | GENERATED — tracked, not gitignored |

---

## Test results

```
chip-audit.test: 9 passed, 0 failed
```

Tests cover: token extraction with Vietnamese diacritics and emoji (`Party 🔍`, `Xem thêm →`), mapped-vs-unmapped classification, deterministic sort (surfaceId → region → token), surfaces with null layout skipped, idempotent output.

---

## Build results

```
✓ ascii: 40 surface(s) with layout — all up to date
✓ chip-audit: 286 tokens · 155 mapped · 131 unmapped → generated/chip-audit.md
✓ built generated/wireframe-v2.html
```

Second build: `chip-audit.md` NOT rewritten (idempotent — write-only-if-changed).

Validate: `0 error(s) · 0 warning(s)` — unchanged.
Verify-runtime: `PASS — 0 errors`.

---

## Critical verification — 7 known unmapped tokens

All present in `generated/chip-audit.md`:

| Surface | Audit line |
|---|---|
| P02 | `\| toolbar \| \`Xem thêm →\` \|` |
| S07 | `\| topbar \| \`Priority ▼\` \|` |
| S07 | `\| topbar \| \`Party 🔍\` \|` |
| S07 | `\| topbar \| \`Status ▼\` \|` |
| S11 | `\| topbar \| \`Kích hoạt\` \|` |
| S15 | `\| header \| \`← Quay lại\` \|` |
| M15 | `\| actions \| \`Hủy\` \|` |
| M13 | `\| body \| \`+ Thêm tùy chọn\` \|` |

---

## Unmapped counts per surface type

| Type | Surfaces with unmapped chips | Unmapped chip rows |
|---|---|---|
| M* (modals) | 16 | 58 |
| P* (panels) | 5 | 12 |
| S* (screens) | 9 | 59 |
| O* (overlays) | 1 | 2 |
| **Total** | **31** | **131** |

Notable high-count surfaces: S14 (23 — mostly badge chips in alert/outcome rows), M05 (8 — inline field placeholders), M13 (8 — inline form field samples), S01 (11 — KPI strip placeholders).

The majority of the 131 unmapped chips are legitimately display-only (type c): status badges like `[GOLD]`, `[active]`, `[P1]`, inline placeholders (`[___]`, `[datetime ICT]`), and KPI template strings. A smaller set are real interactions awaiting `elements:` mapping (type a/b) — e.g., S07 filters, S11 `Kích hoạt`, M15 `Hủy`.

---

## gitignore decision

`generated/.gitignore` already ignores `wireframe.html`, `wireframe-v2.html`, `screenshots/`. `chip-audit.md` is NOT in the ignore list — `git status` confirms it appears as an untracked file ready to be staged. Consistent with the 4 other tracked registry artifacts (`surface-registry.yaml`, `navigation-graph.yaml`, `action-registry.csv`, `coverage-report.md`).

---

## Design notes

- `auditChips()` and `renderChipAuditMd()` are pure functions with no `config.mjs` dependency. CLI uses dynamic `import()` so test contexts never trigger `loadConfig()`.
- Token regex `[^\[\]]+` — matches one-or-more non-bracket chars, so `[x]` single-char tokens like checkbox glyphs are caught, empty `[]` is skipped.
- Duplicate tokens in same sample (e.g., `[✎][✎][✎]` in M15 body) produce one row per occurrence — intended, each chip position is an independent hit.
- Surface ID falls back to filename stem if frontmatter is missing (`id` field).

---

## Unresolved questions

None.

---

Status: DONE
Summary: New `chip-audit.mjs` module (2 pure exports + CLI) detects unmapped `[token]` chips across all 40 surfaces with layout models; wired into `build.mjs` phase 7.5; 9 tests pass; all 7 known gap tokens confirmed; build idempotent; validate + verify-runtime still green.
