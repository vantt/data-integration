---
title: "Parser & Deployer Contracts"
status: reference
created: 2026-05-28
updated: 2026-05-28
---

See [research-foundation.md](research-foundation.md) for sources.

## 1. Parser Contract

File: `.skills/metabase-automation/lib/design-spec-parser.js` (Phase 2; may relocate to `analytics-design` when 2nd tool added)

### Signature

```typescript
parse(filePath: string) → DesignSpec
```

### DesignSpec Interface

```typescript
DesignSpec {
  frontmatter: Frontmatter
  brief: Brief                         // structured from markdown text
  constraints: Constraint[]            // business constraints (hardcoded filters)
  filters: InteractiveFilter[]         // user-facing filters
  views: View[]                        // tabs
  widgets: Widget[]                    // unified across views via tab assignment
  tabStandards: TabStandards
  actionMap: ActionMapEntry[]
}

Widget {
  id: string                           // slug after "W:"
  view: string                         // tab name
  row: string                          // composition row letter (A, B, C...)
  card: string                         // human name
  role: 'hero' | 'supporting' | 'trend' | 'breakdown' | 'detail' | 'annotation'
  viz: VizConfig
  layout: { width: SizeToken, height: SizeToken, textSize: TextSizeToken }
  data: DataBinding                    // metric_ref OR inline SQL
  comparisons: Comparison[]
  format: FormatConfig                 // merged with dashboard defaults
  conditionalFormat: ConditionalFormat[]
  overrides: Record<tool, any>
}
```

### Parser Responsibilities

- Validate against JSON Schema (catches malformed YAML, missing required fields, invalid enum values — fast feedback in editor + CLI)
- Resolve `inherit_from: defaults` references against frontmatter defaults
- Compute grid coordinates from size tokens (input: row letter + width + accumulated heights)
- Resolve `metric_ref` to SQL via aggregation engine (Phase 4+) OR pass through inline SQL (Phase 0-3)
- Validate row width sum = `grid_base`
- Validate unique widget IDs within dashboard

### Version Detection

- No `spec_version` field → treated as v1 (composition table only, no widget details)
- `spec_version: 2` → full v2 parse path with widget-config blocks
- v1 specs valid for analyst workflow (Phase 0-6) but cannot be direct-deployed (no widget config)

---

## 2. Deployer Contract

Per-tool script: `scripts/deploy_to_{tool}.js` (Phase 2 Metabase: `deploy_from_design_spec.js`; renamed `deploy_to_metabase.js` when 2nd tool added)

### Signature

```typescript
deploy(designSpec: DesignSpec, options: {
  target: 'staging' | 'production'
  dryRun: boolean
  emitPortabilityReport: boolean
}) → DeployResult
```

### Deploy Steps (7)

1. Translate viz types via tool's VIZ_CATALOG (semantic term → tool display type + settings)
2. Translate color tokens → tool color values
3. Render `tab_standards` widgets in tool-native way:
   - Metabase: scalar with `strftime(current_date, ...)` SQL at row 0, full-width × 2
   - Evidence: `<DateRange/>` component
   - Superset: Markdown widget, Jinja date variable
   - Looker: `text:` element with dashboard parameter
4. Generate filter parameters + auto-wire by slug
5. Build position layout from grid coordinates (tool's `grid_cols` may differ from spec's `grid_base`)
6. Call tool API (create/update questions, cards, filters, tabs, layout)
7. Emit portability report if `emitPortabilityReport: true`

### Idempotency

Same as current `deploy_from_markdown.js` — match by name (tab + card name), update in-place. Safe to re-run.

### Portability Report (ADR-6)

Emitted when `--portability` flag passed:

```
Portability Report — sales_daily_operation (target: metabase)
✅ All 18 widgets native (100%)

Cross-tool projection (informational):
✅ Evidence: 17/18 native, 1 fallback (94%) — gauge → BigValue with conditional color
⚠️ Superset: 15/18 native, 3 fallback (83%)
❌ Looker: 11/18 native, gauge unsupported (Health Score breaks), 1-2 more fallbacks
```

Each viz catalog declares per-tool support level: `native` | `fallback` | `unsupported`. Spec author sees explicit warning when choosing non-universal viz type.

---

## 3. Validation Strategy

Multi-layer — file-level diff demoted to debugging aid (too brittle for correctness):

| Layer | When | What |
|-------|------|------|
| 1. JSON Schema | Every parse | Malformed YAML, missing required fields, invalid enum values. Fast feedback in editor (VSCode YAML ext) + CLI. |
| 2. Cross-reference | Parser | Widget IDs unique, row widths sum to `grid_base`, `metric_ref`s resolve, color tokens exist in catalog. |
| 3. Round-trip | Phase 1+ | Capture live dashboard → spec → deploy to staging → capture again → diff. Primary correctness signal. |
| 4. Property-based | Phase 2+ | For each viz type in vocabulary, generate small spec, convert, assert output contains required patterns. |
| 5. Behavioral | Phase 2+ | After deploy, query Metabase API, assert critical fields (display type, SQL, filter wiring, parameter mappings). |
| 6. Visual diff | Phase 3 migrations (manual) | Deploy old vs new to staging, screenshot, eyeball compare. |

### Schema Location

- `.skills/analytics-design/schemas/widget-config.schema.json` — JSON Schema 2020-12
- `.skills/analytics-design/WIDGET_CONFIG_SCHEMA.md` — human reference doc
- Schema published Phase 0; versioned alongside `spec_version`
- VSCode YAML extension auto-validates via schema reference in YAML header
