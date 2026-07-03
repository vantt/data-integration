# Visual QA Loop — screenshot.mjs Tool Report

**Date:** 2026-07-03
**Branch:** feature/task-detail-cockpit-backend

---

## Deliverables

### 1. New tool — `.agents/skills/ui-spec/tools/wireframe/screenshot.mjs`

**~165 lines.** CLI tool that:
- Accepts `--root <spec-root> --surface <ids> [--out-dir] [--width] [--height]`
- Validates surface IDs against `generated/surface-registry.yaml` before launching any browser (exit 1 with known-IDs list on unknown input)
- Discovers browser: `UISPEC_BROWSER` env → msedge.exe → chrome.exe, each in x86/x64/LOCALAPPDATA paths; exits 1 listing all paths checked + env hint on miss
- Runs `--headless=new --disable-gpu --window-size=<w>,<h> --virtual-time-budget=8000 --screenshot=<abs-path>` per surface
- Success gate: PNG must exist **and** be ≥ 20 KB (blank shells are smaller)
- Fails fast with clear message if `wireframe-v2.html` missing
- Default out-dir: `<spec-root>/generated/screenshots/`

### 2. Docs — Visual QA loop section

Added **§11 Visual QA loop** to `.agents/skills/ui-spec/references/ui-layout-authoring.md`:
- When mandatory (client changes, bulk migrations, before declaring done)
- 5-step loop with 3–4 iteration cap
- Representative surface criteria (not hardcoded IDs — described by structural properties)
- 7-item visual checklist
- Note that hover/pin states must use verify-runtime instead

### 3. SKILL.md — screenshot command entry

Added `screenshot` entry to Commands section with usage, out-dir default, browser discovery note, size gate, and pointer to §11.

### 4. `.gitignore` — screenshots/ added

`crm/docs/ui-spec/generated/.gitignore` now covers `screenshots/`.

---

## Verification outputs

### build.mjs
```
✓ built generated/: surface-registry.yaml, navigation-graph.yaml, action-registry.csv, coverage-report.md
  surfaces=54 actions=311 flows=6
✓ ascii: 40 surface(s) with layout — all up to date
✓ built generated/wireframe-v2.html
```

### screenshot.mjs — S14, S03, M01
```
  S14 → ...screenshots\S14.png ... OK (162 KB)
  S03 → ...screenshots\S03.png ... OK (143 KB)
  M01 → ...screenshots\M01.png ... OK (120 KB)
All 3 screenshot(s) written to: ...generated/screenshots
```

### Visual QA — checklist assessment from reading the 3 PNGs

**S14 (Call Mode / Strategy Cockpit)** — most complex grid
1. Proportions: 3fr/2fr columns visible; reason_to_call and collect each span 2 rows correctly. ✓
2. Sample content dominant: region labels small/muted above sample text. ✓
3. Airy: cell gaps and padding present; no overflow observed. ✓
4. Chips: Gọi, Zalo, 360, Copy, Đặt lịch render as interactive elements; no raw action IDs in cells. ✓
5. Inspector: visible right-side panel; no horizontal scroll at 1600 px. ✓
6. Floating/variant: stop_banner toggle visible at bottom; default/full_screen variant switcher present. ✓
7. Vietnamese + emoji: "Hoàng Thức", "Miền Trung", "sắp churn 11d", emoji chips — all clean. ✓

**S03 (Customer 360 Detail)** — has children sub-layouts
1. Proportions: 2-column layout, sidebar narrower than main content area. ✓
2. Sample content dominant. ✓
3. Airy layout. ✓
4. Chips: "Gán NV", "Tag", "Tạo task" as interactive elements. ✓
5. Inspector visible. ✓
6. Floating: sidebar.warning toggle present. ✓
7. Vietnamese: "Nguyễn Văn A", "Quay lại" — clean. ✓
8. Children sub-layout: sidebar renders 5 stacked mini-sections (SIDEBAR.CORE_INFO → SIDEBAR.TAGS). ✓

**M01 (Merge Confirm Modal)** — modal
1. Proportions: single-column layout (header/body/actions), correct for a modal. ✓
2. Sample content dominant. ✓
3. Airy; comfortable padding. ✓
4. Chips: "Hủy" and "Xác nhận Merge" as button chips; no raw action IDs. ✓
5. Inspector visible. ✓
6. No floating/variant declared — correct, controls absent. ✓
7. Vietnamese: "Hủy", "Xác nhận Merge" — clean. ✓

**No checklist violations observed.**

### Error paths

```
Test 1 — bogus surface ID:
  ERROR: Unknown surface ID(s): BOGUS999
    Known IDs: S01, S02, S03, ...
  exit: 1 ✓

Test 2 — UISPEC_BROWSER nonexistent:
  ERROR: UISPEC_BROWSER="..." is set but the file does not exist.
  Unset it or point it to a valid msedge.exe / chrome.exe.
  exit: 1 ✓
```

### validate.mjs
```
Scanned 54 spec files, 311 actions, 52 surfaces.
✓ validation passed (0 warning(s)).
```

### verify-runtime.mjs
```
Surfaces exercised : 54 | Flows exercised : 6 | Errors : 0
RESULT: PASS -- all assertions clean, zero runtime errors
```

### git status
`screenshots/` not listed as untracked — gitignore effective. ✓

---

## Implementation notes

- `--virtual-time-budget=8000` gives JS 8 s of virtual time to initialize the wireframe before the screenshot is captured; needed because the surface list and grid renderer run on DOMContentLoaded.
- Surface ID validation reads `surface-registry.yaml` via js-yaml (already in `tools/node_modules`). Skips validation gracefully if the registry is absent or unparseable — the tool degrades to the 20 KB gate only.
- The `UISPEC_BROWSER` env resolves differently in Git Bash vs PowerShell: Bash prefixes the path with the POSIX root (`C:/Program Files/Git/...`) when a bare POSIX path is passed; the tool checks the exact env value so the error message reflects what the env actually contains.

---

## Unresolved questions

None.

---

Status: DONE
Summary: screenshot.mjs tool created and verified end-to-end (3 PNGs captured, all checklist items pass, error paths exit 1 cleanly); Visual QA loop encoded in ui-layout-authoring.md §11 and SKILL.md; screenshots/ gitignored; validate and verify-runtime remain green.
