# Phase 2 — `content:` model + renderer + S14 pilot

## Requirement
Optional `content:` key in the `ui-layout` fence describes typed elements per region; renderer draws real wireframe idioms. Fallback = `samples` line (all non-migrated surfaces unchanged).

## Schema (authored in layout-schema.mjs, docs in ui-layout-authoring.md)

```yaml
content:
  identity_bar:
    - row: [{h: "Hoàng Thức"}, {badge: GOLD}, {btn: "📞 Gọi", action: A-S14-006, primary: true}]
  talking_points:
    - checklist: ["Nhắc chu kỳ", "Ưu đãi", "Combo"]
  main_col:
    - table: {cols: [Tên, SĐT, Hạng], rows: 4}
    - list: {item: "{avatar} Tên khách · badge · 2 dòng", rows: 3}   # list uses item template + rows count
```

Primitives: `h text btn input select checklist chips badge tabs table list kpi divider slot row`.
Element opts: `action:` (action ID), `primary:` (btn), `placeholder` semantics via string value.

## Changes

1. **Renderer** — new client file `render-content.js` (keeps render-grid.js < 600 LOC):
   - `renderContentElements(surface, region, elements)` → HTML; each primitive → distinct idiom (btn shape, input outline, table/list skeleton with repeated rows, tabs bar, kpi big-number, slot = hatched grey placeholder)
   - `gridCellHtml` in render-grid.js: `layout.content?.[region]` → content path, else samples path
   - elements with `action:` get `data-action-id` → existing inspector hover/click works unchanged
   - styles: new chunk `styles-content.mjs` imported by styles.mjs
2. **ASCII** — `generate-ascii.mjs`: region line = `flattenContentLine(content[region])` when present, else `samples[region]`
3. **Validator** — content region keys join VR-LAYOUT-UNKNOWN check; new warns `VR-CONTENT-TYPE` (unknown primitive), `VR-CONTENT-ACTION` (action ref not an existing action id)
4. **chip-audit** — content surfaces: `btn`/`tabs` element without `action:` = unmapped entry; badge/chips/text types exempt (display-only by type)
5. **S14 pilot** — author `content:` for all S14 regions from existing samples + contract block; keep `samples` for ASCII? NO — content regions flatten for ASCII; trim S14 `samples` to regions without content (avoid dual-maintenance). `elements:` map entries covered by content `action:` are removed.
6. **Docs** — ui-layout-authoring.md: schema §2 + quick-ref §10 + new §content authoring; SKILL.md fence overview updated.
7. **Tests** — layout-schema.test.mjs (walk/flatten/type detection), generate-ascii.test extension (content flatten), extract-layout.test (new keys pass unknown-key warning check).

## Validation (Phase 3 rolled in)
- `node --test` green; `verify-runtime.mjs` green
- validate + build on crm/docs/ui-spec: 0 errors; S03/M01 byte-stable except timestamp
- Visual QA loop §11: screenshot S14 + S03 + M01, vision-check: element differentiation, repetition visible, proportions, no overflow, diacritics clean
