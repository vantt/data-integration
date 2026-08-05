# UI Layout Authoring — Reference

> Source of truth for the `yaml ui-layout` fence. Read before drafting any layout block.

---

## 1. Why this model exists

LLMs generate tokens sequentially (1D). Drawing a 2D box-drawing ASCII grid by hand produces misaligned columns, wrong junction characters, and truncated cells — especially with wide Unicode (CJK/emoji). Any hand-drawn ASCII will drift the moment a region is renamed or reordered.

The solution: **separate model from rendering**.

- The `yaml ui-layout` fence is the model — author edits go here.
- The box-drawing ASCII between `<!-- ui-layout:ascii:start/end -->` markers is a deterministic render of that model. The build pipeline regenerates it idempotently on every `build.mjs` run.
- The interactive CSS-grid wireframe (Layout tab in `wireframe-v2.html`) is also a render of the same model.

**Never edit the generated ASCII.** Edit the YAML fence, then run `build.mjs`. VR-ASCII-DRIFT warns if someone hand-edited the block.

---

## 2. Full schema

> **Single writer:** all schema knowledge (key list, content primitives, walkers, ASCII flatten)
> lives in `tools/wireframe/layout-schema.mjs`. Node tools import it; `html-shell.mjs` inlines it
> (export-stripped) into the browser bundle. When extending the schema, edit that module first —
> never re-declare keys or primitive lists in individual tools.

```yaml
# All keys are optional except areas (required for a valid model).

columns: ["3fr", "2fr"]
# CSS fr-unit strings for column widths. Default: uniform 1fr per column inferred from areas.
# Determines proportional grid widths. Last column absorbs rounding remainder.

row_heights: [auto, "minmax(150px,auto)", auto]
# CSS track strings, ONE per base areas row — gives the wireframe honest vertical
# proportion (dominant regions get minmax(Npx,auto)). Variant prepend/append rows
# get "auto". Length must equal areas row count (VR-LAYOUT-ROWS warn). ASCII ignores it.

areas:
  - [region_a, region_a]    # row 0: region_a spans both columns
  - [region_b, region_c]    # row 1: region_b left, region_c right
# 2D matrix (array of rows). Each row is an array of region name strings.
# Row order = top-to-bottom visual order. All cells in a row must be present.
# CONSTRAINT: every region must form a SOLID RECTANGLE (VR-LAYOUT-RECT).

floating:
  - region: stop_banner
    when: "recommended == false"   # human-readable condition string
    replaces: [region_b, region_c] # cells hidden when banner is active (informational; Grid tab uses this to show toggle)
# Regions rendered as toggle banners outside the base grid.
# NOT placed in the areas matrix — they are overlay/conditional elements.

variants:
  full_screen:
    prepend_rows:
      - [topbar, topbar]      # rows added ABOVE the base areas matrix for this variant
    append_rows:              # rows added BELOW the base areas matrix (optional)
      - [footer_extra, footer_extra]
# Named layout variants. Each adds rows around the base grid.
# Regions in variant rows must still appear in frontmatter regions[].

children:
  sidebar:
    areas:
      - [sidebar.core_info]
      - [sidebar.contact]
      - [sidebar.tags]
    variants: {}              # variants inside a child (rare)
# Sub-layouts for a single region, 1 level deep — no further nesting.
# Keys = region names from the parent areas matrix.
# Children render as stacked sections inside their parent grid cell.
# A child region that also appears in floating (same surface) is SKIPPED in the grid cell
# render to avoid double-rendering.

samples:
  region_a: "Page title [Action Button]"
  region_b: "Realistic content · [Chip] · more text"
# One representative data line per region. Appears in the grid cell (gc-sample) and in
# the Blueprint ASCII. Use the richest realistic content: real names, plausible values.
# [text in brackets] becomes a hoverable chip in the Layout tab.
# Emoji and wide-glyph chars are substituted with ASCII equivalents in the generated ASCII
# (see GLYPH_MAP in generate-ascii.mjs: 📞→>, ⚠→!, ★→*, ☑→[x], ⛔→!!, ⏱→(t), etc.)
# Chars with no mapping are replaced with "?" to preserve monospace alignment.

content:
  region_a:
    - row:
        - { h: "Hoàng Thức" }
        - { badge: GOLD }
        - { btn: "📞 Gọi", action: A-S05-003, primary: true }
    - checklist: ["[x] đã nói", "chưa nói"]
    - table: { cols: [Tên, SĐT], rows: 4 }
# PREFERRED path: typed wireframe elements per region — renders real UI idioms
# (button shapes, input outlines, table/list skeletons, tabs, KPI big-numbers).
# When a region has content, it OVERRIDES that region's samples line everywhere
# (Layout tab render + ASCII flatten) — do not keep a duplicate samples line.
# Element = object whose FIRST registry key is its type; other keys are opts.
# Interactive elements take `action: <action-id>` directly (no elements: map needed);
# `primary: true` marks the region's main CTA. See §2b for the primitive table.

elements:
  "Action Button": A-S05-003
  "Chip": A-S05-007
# LEGACY path (samples-only regions): map from chip text (exact match inside
# [brackets] in samples) to action ID.
# Purpose: the Contract Inspector in wireframe-v2.html shows the full contract when a
# chip is hovered or clicked (element, trigger, action, target, guard, effects).
# RULES:
#   - Map ONLY unambiguous 1:1 pairs. Wrong mapping is worse than missing.
#   - Chip text must match exactly (case-sensitive, trimmed). No normalization.
#   - One text → one action ID per surface.
#   - User-triggered interactions only (not system_event / listens_to).
#   - Validated by VR-ELEMENT-REF (warn): values must be known action IDs.
```

---

## 2b. Content primitives (wireframe elements)

Registry lives in `layout-schema.mjs` (`CONTENT_TYPES`); renderer in `client/render-content.js`; flatten rules in `flattenContentLine`. One element = `{ <type>: <value>, ...opts }`.

| Type | Value | Renders as | ASCII flatten |
|---|---|---|---|
| `h` | string | bold heading | text |
| `text` | string | body prose line | text |
| `btn` | label | button shape; `primary: true` = dark fill; `action:` = hoverable contract | `[label]` |
| `input` | placeholder | outlined empty field, italic muted | `[input: …]` |
| `select` | value | outlined field + ▾ caret | `[… v]` |
| `checklist` | string[] | checkbox rows; `"[x] "` prefix = checked | `[x] a [ ] b` |
| `chips` | string[] | grey display-only pills | `[a] [b]` |
| `badge` | string | amber status badge (display-only) | `[label]` |
| `tabs` | string[] | tab bar; `active:` names active tab (default first); `action:` (whole bar) or `actions: {label: action-id}` (per tab — preferred when each tab has its own contract, e.g. show_panel) | `\|*a*\|\| b \|` |
| `table` | `{cols, rows}` | header + N skeleton rows (capped 8) | `tbl(a \| b) ×N` |
| `list` | `{item, rows}` | item template once + N-1 ghost repeats | `list ×N {item}` |
| `kpi` | `{label, value}` | big number over small label | `label: value` |
| `divider` | `true` | horizontal rule | `────` |
| `slot` | string | hatched grey placeholder (hosted panel / dynamic content) | `<<name>>` |
| `row` | element[] | horizontal flex group (no row-in-row) | children joined by space |

Established idioms (decided during wave-3 pilot review — follow, don't re-judge):

- **Kanban / multi-lane board** (e.g. S07 OPEN/DOING/DONE): a `row:` of `h` lane headers followed by a `row:` of one `list:` per lane. No dedicated lane primitive — this IS the accepted pattern.
- **Hyperlink in prose**: plain `text` (no link primitive). Navigation contracts belong on `btn`.
- **Per-item interactions on `list`/`table` rows** (row click, checkbox, drag): intentionally NOT representable in `content:` — collections are display-only skeletons; the item-level contract stays visible via region hover in the Contract Inspector and the Interactions tab. Do not work around this with fake per-row buttons.

Authoring rules:

- **Actionable types** (`btn`, `tabs`) should carry `action:` — chip-audit flags actionable elements without one as unmapped. Display-only types (`badge`, `chips`, `text`, …) are exempt by type.
- Several elements may share one `action:` (e.g. 7 outcome pills → one contract) — correct, not duplication.
- Unknown type keys render as a red ⚠ pill and warn `VR-CONTENT-TYPE`; unknown `action:` ids warn `VR-CONTENT-ACTION`; content region keys join the `VR-LAYOUT-UNKNOWN` check.
- Repetition (`table`/`list` skeleton rows) and `row_heights` are what make the wireframe reviewable — use them for any region that is a collection or dominates the screen.
- Migration: author `content:` for a region → delete that region's `samples:` line and its `elements:` entries in the same edit (content overrides them; keeping both invites drift).

---

## 3. Worked example — S14 (canonical)

S14 has 14 regions: 12 in base areas, 1 floating, 1 in variant prepend_rows.
(The live S14 file has since migrated `samples:`/`elements:` → `content:` + `row_heights` — read
`crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` for the canonical content-model example;
the geometry below is unchanged and still canonical for areas/floating/variants.)

```yaml
columns: [3fr, 2fr]
areas:
  - [identity_bar, identity_bar]        # full-width
  - [alert_row,    alert_row]           # full-width
  - [talk_track,   reason_to_call]      # left / right (reason_to_call begins here)
  - [strategy_summary, reason_to_call]  # reason_to_call spans rows 3-4
  - [talking_points, snapshot]
  - [objection_handling, collect]       # collect begins here
  - [guardrails,    collect]            # collect spans rows 6-7
  - [trust_footer,  trust_footer]       # full-width
  - [outcome_bar,   outcome_bar]        # full-width
floating:
  - region: stop_banner
    when: "recommended == false"
    replaces: [talk_track, strategy_summary, talking_points, objection_handling,
               guardrails, reason_to_call, snapshot, collect]
variants:
  full_screen:
    prepend_rows:
      - [topbar, topbar]
samples:
  topbar: "[← Worklist]  #9/31  [Khách kế →]"
  identity_bar: "Hoàng Thức [GOLD][active] · Miền Trung · ☎0983***35 [📞Gọi][💬Zalo] [360]"
  # … (one line per region)
elements:
  "📞Gọi": A-S14-006
  "360": A-S14-007
  "📋Copy": A-S14-001
  "⏱Đặt lịch": A-S14-024
```

Key geometry points in S14:
- `reason_to_call` appears in rows 3 and 4 right column → forms a 2×1 rectangle (valid).
- `collect` appears in rows 6 and 7 right column → forms a 2×1 rectangle (valid).
- `stop_banner` is in `floating`, not in `areas` — it renders as a standalone banner.
- `topbar` is in `variants.full_screen.prepend_rows`, not in base `areas`.

---

## 4. Coverage rule

Every region name in the surface frontmatter `regions[]` array must appear somewhere in the layout model — `areas`, `floating[*].region`, `variants[*].prepend_rows/append_rows`, or `children` — else VR-LAYOUT-ORPHAN warns.

Conversely, every name used in the layout must be declared in `regions[]` — else VR-LAYOUT-UNKNOWN errors.

The two lists must agree exactly. Keep them in sync:

1. Declare all regions in frontmatter `regions:` first.
2. Place every declared region in `areas`, `floating`, variant rows, or `children`.
3. Run `validate.mjs` to confirm zero orphans and unknowns.

---

## 5. Validation rules catalog

| Rule | Severity | Trigger | Fix |
|---|---|---|---|
| `VR-LAYOUT-PARSE` | **error** | fence present but YAML broken or `areas` missing — a broken fence would otherwise silently skip ALL layout rules and leave stale ASCII (upgraded from warn 2026-07-14) | Fix YAML syntax; common trap: `- btn: "x", action: id` block-mapping-with-comma is invalid — use flow style `{ btn: "x", action: id }` |
| `VR-LAYOUT-UNKNOWN` | **error** | Region name in `areas`/`floating`/`samples` not in frontmatter `regions[]` | Add missing name to `regions[]` or remove from layout |
| `VR-LAYOUT-RECT` | **error** | Region cells in `areas` matrix don't form a solid rectangle | Fix areas matrix so all cells of a region are contiguous rectangles |
| `VR-LAYOUT-ORPHAN` | warn | Declared region absent from all layout areas + floating + variants + children | Place the region in `areas`, `floating`, variant rows, or `children` |
| `VR-ELEMENT-REF` | warn | `elements` map value is not a known action ID | Fix typo or remove mapping; verify the action ID exists in the surface contract |
| `VR-LAYOUT-ROWS` | warn | `row_heights` length ≠ base `areas` row count | One track string per base row |
| `VR-CONTENT-TYPE` | warn | content element has no known primitive type key | Use a type from the §2b table (check `layout-schema.mjs` CONTENT_TYPES) |
| `VR-CONTENT-ACTION` | warn | content element `action:` is not a known action ID | Fix typo or add the interaction to the contract block |
| `VR-ASCII-DRIFT` | warn | ASCII between markers differs from what the model generates | Do not hand-edit the generated block; run `build.mjs` to regenerate |
| `VR-WIREFRAME-STALE` | warn | `generated/wireframe-v2.html` is older than spec files | Run `build.mjs` to regenerate the wireframe |

---

## 6. Workflow

```
1. Edit the yaml ui-layout fence (and frontmatter regions[] if regions changed)
2. node .skills/ui-spec/tools/validate.mjs --root <spec-root>
   Fix all errors (VR-LAYOUT-UNKNOWN, VR-LAYOUT-RECT); address warnings.
3. node .skills/ui-spec/tools/build.mjs --root <spec-root>
   Build order: parse contracts → surface-registry → navigation-graph →
   action-registry → coverage-report → ASCII injection (writes .md) → wireframe-v2.html
   All idempotent: same model → byte-identical output.
4. Open generated/wireframe-v2.html — Layout tab is default.
```

Combined one-liner:
```bash
node .skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

**ASCII injection is part of `build.mjs`** — no separate step. The generator writes the file only when content differs (idempotent at file level). Markers `<!-- ui-layout:ascii:start -->` and `<!-- ui-layout:ascii:end -->` are placed immediately after the fence on the first build; subsequent builds replace content between existing markers.

---

## 7. Wireframe UX contract

**Layout tab (default):** CSS grid rendered from the `areas` matrix. Each cell shows the region name (small, muted) and sample text (dominant). `[text in brackets]` in samples becomes inline chips.

- **Unmapped chip hover:** tooltip shows chip text + region fallback interactions.
- **Mapped chip hover:** Contract Inspector panel (right side, sticky) shows full contract — action ID, element, trigger, action, target, guard, effects.
- **Mapped chip click:** if `action: navigate` or `open_overlay`, fires the interaction (navigates to target surface).
- **Click to pin:** pins the inspector panel; click outside `.grid-with-inspector` to unpin.
- **Floating toggle:** floating regions appear as red-tinted banners above the grid; click to toggle visibility.
- **Variant switch:** buttons above the grid switch between base layout and named variants.

**Interactions tab:** full contract — region boxes with colored action buttons and dashed listener chips. Regions with no interactions show "(display only)".

**Blueprint tab:** generated ASCII from the model (between markers), followed by any hand-drawn ASCII prose below the markers. First ASCII block found = the generated one.

**Storyboard / Graph tabs:** disabled (Phase 2/3).

---

## 8. Migration recipe for an existing spec corpus

When migrating surfaces that have hand-drawn ASCII but no `yaml ui-layout` fence:

1. **LLM reads the hand ASCII** and the surface prose/interactions to understand the region structure.
2. **LLM drafts the YAML fence** — fills `columns`, `areas`, `floating`, `variants`, `children`, `samples`. Does NOT draw ASCII.
3. Run `validate.mjs` — fix VR-LAYOUT-UNKNOWN (add to `regions[]`) and VR-LAYOUT-RECT (fix non-rectangular placements).
4. Run `build.mjs` — ASCII is generated and injected above the existing hand ASCII.
5. Human diffs generated ASCII against hand ASCII for geometry correctness. The hand ASCII remains in prose (below the markers) as historical reference; it does not affect the model.

**Batch migration:**
- Work by directory (screens/, modals/, panels/ separately).
- Do not run `build.mjs` from parallel worker agents — ASCII injection writes the `.md` files; parallel writes to the same file cause corruption. One agent per directory or sequential runs.
- File ownership must be clear before parallelizing (same rule as multi-agent orchestration).

---

## 8b. Migration recipe — `samples:`/`elements:` → `content:` (agent-runnable)

For surfaces that already have a `ui-layout` fence with `samples:` and need the typed content model. Canonical examples to imitate: S14 (screen, richest), S03 (children + per-tab actions), S02 (table), M08 (form modal), P01 (panel).

Per surface, in this order:

1. **Read the whole surface file** — frontmatter `regions[]`, the fence, prose sections (Row Detail / Sidebar Sections / mode tables…), and the full `{project}-contract` block. The contract's `element` names + `region` fields tell you which actions belong in which region.
2. **Draft `content:` region by region** from the samples line + prose, using §2b primitives:
   - A collection (rows of tasks/customers/channels) → `table:` (uniform columns) or `list:` (item template, `rows: 3-5`). Repetition is the point.
   - A form → `text` label + `input`/`select` pairs grouped in `row:`; option-pill groups → `btn` per pill (same `action:` when they share one interaction) or `chips` if display-only.
   - Stats → `kpi` in a `row:`; statuses → `badge`; nav/section switch → `tabs` (per-label `actions:` when each tab has its own interaction).
   - Hosted panel / dynamic area → `slot:`.
   - Keep realistic Vietnamese sample data from the old samples line; do not invent new business facts.
3. **Map actions**: every `btn`/`tabs` gets `action:`/`actions:` from the contract. If a real button has NO matching interaction, leave it out of actionable types (or use `chips`) and **flag it in your report** — do NOT invent action IDs or edit the contract block.
4. **Delete** the migrated regions' `samples:` lines and ALL their `elements:` entries in the same edit (content overrides both; leftovers = drift). Remove the keys entirely when empty.
5. **Add `row_heights:`** only when one region visibly dominates the real screen (e.g. main content `minmax(300px,auto)`); otherwise omit.
6. **Verify** (from repo root):
   ```bash
   node .skills/ui-spec/tools/validate.mjs --root <spec-root>   # 0 errors required
   node .skills/ui-spec/tools/build.mjs --root <spec-root>      # regenerates ASCII + wireframe
   node .skills/ui-spec/tools/validate.mjs --root <spec-root>   # now 0 warnings too
   node .skills/ui-spec/tools/wireframe/verify-runtime.mjs --root <spec-root>
   node .skills/ui-spec/tools/wireframe/screenshot.mjs --root <spec-root> --surface <ids>
   ```
   Then check `generated/chip-audit.md`: your surfaces must have NO unmapped actionable entries (display-only-by-type is fine).
7. **Report**: per surface — regions migrated, actions mapped, contract gaps flagged (step 3), screenshot paths. A human (or stronger model) does the vision pass on the PNGs against §11's checklist.

---

## 9. Common mistakes

**Non-rectangular region** (VR-LAYOUT-RECT)

```yaml
# ✗ L-shape — invalid
areas:
  - [header, sidebar]
  - [main,   sidebar]
  - [main,   footer]    # "main" now at (1,0) and (2,0), "footer" at (2,1)
                        # "sidebar" at (0,1) and (1,1) — rectangle ✓
                        # "main" at (1,0) and (2,0) — rectangle ✓
                        # "footer" at (2,1) — 1×1 rectangle ✓
                        # Actually valid. Counter-example:
  - [main,   sidebar]
  - [footer, sidebar]
  - [footer, extra]     # "footer" spans (1,0)-(2,0) AND "extra" is at (2,1)
                        # but if main is also at (0,0), footer occupies rows 1-2, col 0 ✓
# The actual failure case:
areas:
  - [a, b]
  - [b, c]   # "b" at (0,1) and (1,0) — not a rectangle (VR-LAYOUT-RECT)
```

The most common failure: trying to "share" a cell at a diagonal boundary. Every region must occupy a contiguous block of rows × columns with no gaps or diagonal cells.

**Orphan region** (VR-LAYOUT-ORPHAN)

Adding a region to frontmatter `regions[]` but forgetting to place it in `areas`, `floating`, variant rows, or `children`. Fix: place the region or remove it from `regions[]`.

**Floating region double-listed in children** (silent render issue)

A region that is both in `floating` and in `children[parent].areas` renders twice if the render-grid code doesn't skip it. The correct pattern: if a region is conditionality-flagged (floating), list it in `floating` for the toggle banner. If it also has a positional slot in a child sub-layout, list it in `children[parent].areas` too — render-grid.js skips child regions that also appear in `floating`, preventing double-render. This is an intentional design (S03 `sidebar.warning` uses this pattern).

**Guessing element mappings** (VR-ELEMENT-REF)

Only map chips where the text inside `[...]` is unambiguously 1:1 with one action. If multiple actions share similar chip text (e.g., outcome buttons where all map to the same modal with different params), skip them. A wrong mapping shows incorrect contract in the inspector — worse than no mapping.

**Editing generated ASCII** (VR-ASCII-DRIFT)

The content between `<!-- ui-layout:ascii:start -->` and `<!-- ui-layout:ascii:end -->` is overwritten on every `build.mjs` run. Any hand-edit will be silently reverted. VR-ASCII-DRIFT warns when the stored ASCII doesn't match the model; the fix is always to run `build.mjs`, not to re-edit the block.

**YAML quoting traps** (tool-dev note)

In `samples` values that contain HTML-like attributes (e.g., style strings with `="`), YAML may interpret the double-quote as a YAML string delimiter. Use single-quoted YAML strings or escape the quotes. This applies when the sample text itself contains `"key="value""` patterns — rare in sample text, more common in internal tool configuration.

**Unregistered region in samples** (VR-LAYOUT-UNKNOWN)

Adding a key to `samples` for a region not in `regions[]` triggers VR-LAYOUT-UNKNOWN. The validator checks sample keys against `regions[]` along with area names. Every key in `samples` must be a declared region.

**Wide glyphs in samples**

Emoji and CJK characters are display-width-2 in monospace terminals. The ASCII generator replaces known wide chars via GLYPH_MAP (e.g., `📞→>`, `⚠→!`, `☑→[x]`, `⛔→!!`, `⏱→(t)`); unknown wide chars become `?`. This is correct and alignment-safe. Do not manually pre-substitute in samples — keep samples readable; let the generator handle normalization.

---

## 11. Visual QA loop

After any change to the wireframe rendering pipeline — or before declaring wireframe work done — screenshot representative surfaces and read the PNGs with vision. Static assertions (validate, verify-runtime) cannot catch visual regressions; only eyes catch proportion drift, chip overflow, and mojibake.

### When mandatory

Run the Visual QA loop after any of these:
- Changes under `tools/wireframe/client/`, `styles*.mjs`, or `html-shell.mjs`
- Bulk spec migrations (new layout model, region rename, ASCII regeneration)
- Before declaring wireframe implementation work done

### Loop

```
1. node .skills/ui-spec/tools/build.mjs --root <spec-root>
2. node .skills/ui-spec/tools/wireframe/screenshot.mjs \
       --root <spec-root> --surface S14,S03,M01
3. Read each PNG with your vision — do NOT skip. verify-runtime proves no JS crash;
   only eyes prove readability and proportion.
4. Judge against the checklist below.
5. Fix; repeat from step 1.
Cap at ~3–4 iterations, then report remaining issues honestly.
```

### Representative surface set

Pick at minimum:
- **The most complex grid** — multi-column, row-spanning, floating regions, and named variants all present. Currently S14.
- **A surface with `children` sub-layouts** — a region renders stacked mini-sections inside its cell. Currently S03.
- **A modal** — must show close controls and a narrower single-column layout. Currently M01.

Phrase the selection by criteria when spec IDs change across projects; these three criteria must always be covered.

### Visual QA checklist

1. **Proportions** — column widths visibly match the `columns` fr ratios; row-spanning regions actually span the declared rows.
2. **Sample content is dominant** — the `samples` text is the main text in each cell; the region label is small and muted above it.
3. **Airy layout** — visible gaps between cells, cell padding present, no content overlap; long chips must not overflow cell edges.
4. **Chips render as interactive elements** — mapped chips are visually distinct from unmapped ones; no raw contract text (action IDs, `trigger → action` strings) appears inside grid cells — that content belongs to the Inspector panel and the Interactions tab, not the Layout grid.
5. **Inspector panel** — visible and not cramping the grid; no horizontal page scroll at the target viewport width.
6. **Floating and variant controls** — floating toggle buttons and the variant switcher are present whenever the layout model declares them.
7. **Vietnamese diacritics and emoji** — render cleanly with no tofu boxes or mojibake.

> **Note:** hover and pin states cannot be captured in a static screenshot — assert those via `verify-runtime.mjs` jsdom sections instead.

---

## 12. Chip coverage audit

After every `build.mjs` run, `generated/chip-audit.md` lists every `[token]` chip found in any `samples:` value, classified as **mapped** (key present in `elements:`) or **unmapped** (no key).

For `content:` regions the audit works by TYPE instead of text: actionable elements (`btn`, `tabs`) with `action:` count as mapped, without as unmapped; display-only types are exempt. Regions that have `content:` are skipped on the samples path (content is their source of truth).

Review the unmapped chips and decide for each one:

- **(a) Should be mapped** — the chip represents a real user action. Add it to `elements:` with the correct action ID.
- **(b) Interaction missing from contract** — the action doesn't exist yet. Add the interaction to the `yaml {project}-contract` block, then add the `elements:` mapping.
- **(c) Legitimately display-only** — the chip is a status badge, placeholder label, or visual indicator with no direct user trigger (e.g., `[GOLD]`, `[active]`, `[P1]`). Leave it unmapped — unmapped is not an error, it is information.

The audit is idempotent: running `build.mjs` twice produces the same `chip-audit.md` if the spec has not changed. The file is a small registry-like artifact and is tracked in git (unlike `wireframe-v2.html` which is gitignored).

---

## 10. Schema key quick-reference

| Key | Type | Required | Description |
|---|---|---|---|
| `columns` | `string[]` | no | fr-unit column widths; inferred from areas if absent |
| `areas` | `string[][]` | **yes** | 2D matrix of region names; solid rectangles enforced |
| `floating` | `object[]` | no | Overlay regions: `region`, `when`, `replaces[]` |
| `variants` | `object` | no | Named layout variants: `prepend_rows`, `append_rows` |
| `children` | `object` | no | 1-level sub-layouts: `{ region: { areas, variants } }` |
| `row_heights` | `string[]` | no | CSS track per base row — vertical proportion (§2) |
| `samples` | `object` | no | `{ region: "display text [chip] more text" }` — legacy/fallback |
| `elements` | `object` | no | `{ "chip text": "action-id" }` for samples-path chips |
| `content` | `object` | no | `{ region: element[] }` — typed wireframe elements (§2b), preferred |
