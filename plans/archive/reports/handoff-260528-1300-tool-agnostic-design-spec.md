# Handoff Prompt — Tool-Agnostic Design Spec Implementation

**Date**: 2026-05-28
**Status**: Research complete, ready to implement Phase 1
**Branch**: `main`
**Previous session**: Research + format design + quality assessment

---

## Copy this prompt into the new chat

```
Tôi cần tiếp tục công việc "Tool-Agnostic Design Spec Format" cho data-integration project.
Session trước đã làm xong RESEARCH + FORMAT DESIGN. Giờ cần BUILD CONVERTER.

═══════════════════════════════════════════════════════════════════
PROJECT CONTEXT
═══════════════════════════════════════════════════════════════════

Project: D:\Vantt\app\data-integration (Sapo/Shopee data warehouse, DuckDB + Metabase)

Hiện có 2 skills tách biệt:
- `.skills/analytics-design/` — Analyst brain (Phase 0-6): tạo domain, playbook, design spec.
  Tool-agnostic, dùng semantic vocabulary (25 viz types, color/size tokens).
- `.skills/metabase-automation/` — Engineer brain (Phase 7-10): tạo blueprint, deploy.
  Metabase-specific: SQL + metabase-viz JSON + metabase-pos JSON.

VẤN ĐỀ: Blueprint 100% phụ thuộc Metabase. Đổi BI tool = rewrite toàn bộ.
Hiện tại có ~30 blueprints trong docs/analytics-handbook/blueprints/, mỗi cái 500-1500 dòng
Metabase-specific JSON. Design Spec tồn tại nhưng quá thin — chỉ có composition table,
thiếu SQL, viz config chi tiết, formatting, comparisons, conditional formatting.

═══════════════════════════════════════════════════════════════════
WHAT WAS DECIDED (READ THIS BEFORE STARTING)
═══════════════════════════════════════════════════════════════════

Đọc đầy đủ research report trước:
👉 plans/reports/research-260527-2300-tool-agnostic-design-spec.md

3 sub-reports (research data, đọc nếu cần verify):
👉 plans/reports/researcher-260527-2300-bi-dashboard-formats.md
👉 plans/reports/researcher-260527-2348-dashboard-json-formats.md
👉 plans/reports/researcher-260527-2348-dashboard-definition-formats.md
👉 plans/reports/researcher-260527-visualization-type-mapping.md

QUALITY SCORE: 8/10 (industry-leading — không có open standard nào > 5/10 cho dashboard-level spec).
FEASIBILITY: Cao. Không có algorithm phức tạp. Toàn bộ là parsing + lookup + templating.

KEY DECISIONS (DON'T REVISIT — ALREADY DEBATED):

1. Hybrid markdown format: composition table (overview) + widget detail sections (SQL + YAML).
   KHÔNG dùng pure YAML/JSON — phải human-readable trong markdown editor.

2. Widget IDs dùng stable slug: `W:net-revenue` (NOT sequential `W5`).
   Lý do: reorder widgets không cascade renumber.

3. Blueprint trở thành GENERATED artifact:
   - Design Spec = source of truth (hand-authored)
   - Blueprint = auto-generated bởi converter (KHÔNG sửa tay)
   - Cả 2 commit vào git để audit
   - Deploy script (deploy_from_markdown.js) unchanged — vẫn đọc blueprint

4. SQL stays database-specific (DuckDB), declare `sql_dialect: duckdb` trong frontmatter.
   Đổi DB ≠ đổi BI tool — SQL phải rewrite regardless.

5. Per-tool escape hatch: section `overrides:` cho settings không fit generic schema.
   Acknowledge 100% portability là impossible.

6. Adapter pattern cho multi-tool: 1 shared parser + 1 converter per target tool.
   Mỗi tool có file VIZ_CATALOG riêng (METABASE_VIZ_CATALOG.md đã có).

7. Roadmap PHASED (YAGNI — don't build all upfront):
   - Phase 1: Metabase converter (2-3 ngày) — PRIMARY
   - Phase 2: Migrate 3-5 dashboards quan trọng nhất
   - Phase 3: Evidence.dev converter (1-2 ngày) — preview/second target
   - Phase 4: Superset converter (3-5 ngày) — CHỈ khi thực sự cần migrate
   - KHÔNG build Looker/Power BI converter (paradigm gap — LookML/DAX không SQL-compat)

═══════════════════════════════════════════════════════════════════
PROPOSED FORMAT (FINAL — v2)
═══════════════════════════════════════════════════════════════════

Enhanced Design Spec structure:

---
title: [Dashboard Title]
archetype: Executive Pulse | Operational Cockpit | Exploratory Tool
status: final | draft | draft-from-capture
last_modified: YYYY-MM-DD
domain_refs: [domains/sales.md]
sql_dialect: duckdb              ← NEW
grid_base: 18                     ← NEW (default 18-col)
---

## Design Spec: [Title]

### Brief                          (unchanged)
### Constraints & Filters          (enhanced — structured filter YAML block)
### Views                          (unchanged)
### Composition                    (unchanged — overview table)
### Action Map                     (unchanged)

### Widget Details                 ← NEW SECTION (the meat)
#### W:{stable-slug}               ← per-widget section

  (SQL fenced block — DuckDB)

  ```yaml widget-config
  comparison: ...
  format: ...
  chart: ...        # for chart types
  gauge: ...        # for gauge types
  table: ...        # for table types
  conditional_format: ...
  fallback: ...     # if viz type not universal
  overrides:        # per-tool escape hatch
    metabase: ...
    superset: ...
  ```

### Tab Standards                  ← NEW (declare Chu kỳ báo cáo + Source & Freshness)
### Dashboard Finish Checklist     (unchanged)

WIDGET-CONFIG YAML SCHEMA (full reference trong research report section 3.4).

Example scalar KPI:
```yaml widget-config
comparison:
  type: another-column
  column: "Hôm qua"
  label: "vs hôm qua"
  positive_direction: up
format:
  "Net Revenue":
    style: currency
    currency: VND
    decimals: 0
    compact: true
```

Example gauge:
```yaml widget-config
gauge:
  segments:
    - range: [0, 49]
      color: negative
      label: "Báo động"
    - range: [49, 74]
      color: warning
      label: "Chú ý"
    - range: [74, 100]
      color: positive
      label: "Khỏe mạnh"
fallback:
  if_unsupported: single-value
  notes: "Looker has no gauge; display as number with conditional color"
```

═══════════════════════════════════════════════════════════════════
ARCHITECTURE (PHASE 1)
═══════════════════════════════════════════════════════════════════

NEW files cần build:

1. .skills/metabase-automation/lib/design-spec-parser.js
   - Input: enhanced Design Spec markdown
   - Output: DesignSpec object {frontmatter, brief, filters, views, widgets, tabStandards}
   - Parses: frontmatter (YAML), composition table (markdown), widget details (SQL + YAML)

2. .skills/metabase-automation/scripts/convert_design_to_blueprint.js
   - Input: Design Spec file
   - Output: Blueprint markdown (same format as existing blueprints)
   - Uses: design-spec-parser + METABASE_VIZ_CATALOG.md + size-to-grid algo
   - Applies: overrides.metabase per widget

3. .skills/metabase-automation/lib/size-to-grid.js
   - Width tokens (18-col):
     full-width: 18, two-thirds: 12, half: 9, one-third: 6, one-quarter: 4, one-sixth: 3
   - Height tokens: minimal: 1, short: 3, medium: 6, tall: 8
   - Algo: group widgets by Row letter (A, B, C...), accumulate col left-to-right,
     accumulate row by max height of preceding rows
   - Validate: total width per row = grid_base (18)

EXISTING files (DON'T modify behavior — read for reference):

- .skills/metabase-automation/scripts/deploy_from_markdown.js
  Already deploys blueprints to Metabase. UNCHANGED — just consumes generated blueprint.

- .skills/metabase-automation/METABASE_VIZ_CATALOG.md
  Translation table: standard viz term → Metabase display + settings notes.
  Color token → hex mapping. Already complete.

- .skills/metabase-automation/lib/markdown_parser.js
  Existing blueprint parser. Reference for parsing patterns, but our parser is separate
  (different input format).

═══════════════════════════════════════════════════════════════════
VALIDATION STRATEGY
═══════════════════════════════════════════════════════════════════

Validation target: `sales_daily_operation` (most complex dashboard, ~1450 lines blueprint,
4 tabs, 30+ widgets, has all viz types: scalar, gauge, table-formatted, line-chart, bar,
pie, conditional formatting, KPIs with DoD comparison).

Validation flow:
1. Read existing design spec: docs/analytics-handbook/designs/sales_daily_operation.md
2. Add Widget Details section to it (transcribe SQL + widget-config YAML from blueprint)
3. Run new converter: node convert_design_to_blueprint.js designs/sales_daily_operation.md
4. Compare output vs existing blueprints/sales_daily_operation.md (semantic diff —
   ignore whitespace/ordering)
5. Deploy generated blueprint to staging Metabase, visual diff vs existing
6. If 95%+ match → Phase 1 done

═══════════════════════════════════════════════════════════════════
KEY FILES TO READ FIRST (IN THIS ORDER)
═══════════════════════════════════════════════════════════════════

1. plans/reports/research-260527-2300-tool-agnostic-design-spec.md
   (THE definitive spec — read fully, ~600 lines)

2. .skills/analytics-design/SKILL.md
   (Understand Phase 0-6 + artifact ownership)

3. .skills/analytics-design/templates/design_spec_template.md
   (Current Design Spec format — what we're extending)

4. .skills/analytics-design/VISUALIZATION_VOCABULARY.md
   (25 standard viz terms + Metabase support column)

5. .skills/analytics-design/VISUAL_LANGUAGE.md (Section 1 — Color & Size tokens)
   (Semantic tokens already defined)

6. .skills/metabase-automation/STRATEGY.md
   (2-skill collaboration model)

7. .skills/metabase-automation/METABASE_VIZ_CATALOG.md
   (Translation layer for viz/color)

8. .skills/metabase-automation/templates/blueprint_template.md
   (Current blueprint format — what we're auto-generating)

9. docs/analytics-handbook/designs/sales_daily_operation.md
   (Current Design Spec for validation target)

10. docs/analytics-handbook/blueprints/sales_daily_operation.md
    (Current blueprint — target output of converter)

11. .skills/metabase-automation/scripts/deploy_from_markdown.js
    (How blueprints are parsed for deploy — reference for parsing patterns)

12. .skills/metabase-automation/lib/markdown_parser.js
    (Existing parser implementation — reference style)

═══════════════════════════════════════════════════════════════════
UNRESOLVED QUESTIONS (FROM RESEARCH)
═══════════════════════════════════════════════════════════════════

1. SQL dialect portability: Maintain dialect variants per DB (DuckDB/Postgres) hay rely
   on dbt compilation? Recommendation: declare dialect, không multi-variant.

2. Capture → Design Spec reverse flow: Should capture_dashboard.js generate enhanced
   Design Spec directly? Or keep generating blueprint and let user promote manually?
   Recommendation: defer to Phase 2+; capture flow chưa break.

3. Partial deploys: Support deploying single widget change? Or always full regenerate?
   Recommendation: always full regenerate (simpler, deploy script đã handle diff).

4. Semantic layer integration (dbt metrics): Reference dbt metrics in model_ref?
   Recommendation: defer — không có user need hiện tại.

5. Comparison config portability: `single-value-with-trend` native ở 3/5 tools.
   Define universal fallback (e.g., 2 side-by-side scalars)?
   Recommendation: dùng `fallback` field per widget khi cần.

═══════════════════════════════════════════════════════════════════
WHAT I NEED YOU TO DO (RECOMMENDED FIRST ACTIONS)
═══════════════════════════════════════════════════════════════════

OPTION A: Implement Phase 1 directly
1. Đọc 12 key files trên (ưu tiên #1, #2, #7, #8, #9, #10)
2. Build design-spec-parser.js (start với frontmatter + composition table)
3. Build size-to-grid.js (pure function, dễ test)
4. Build convert_design_to_blueprint.js (orchestrate parser + grid + viz catalog)
5. Validate với sales_daily_operation
6. Report kết quả + diff

OPTION B: Tạo detailed implementation plan trước (planner agent)
1. Đọc research report đầy đủ
2. Delegate `planner` agent: tạo phase-by-phase plan trong
   plans/260528-{HHMM}-tool-agnostic-spec-converter/
3. Reviewer xác nhận plan rồi mới code

OPTION C: Migrate 1 dashboard trước, build converter sau
1. Manually viết enhanced Design Spec cho `sales_daily_operation` (transcribe từ blueprint)
2. Verify format compliance với schema trong research report
3. Sau đó build converter để verify nó sinh ra output matching

My recommendation: OPTION A nếu bạn confident, OPTION B nếu muốn safety net.
Đừng làm OPTION C trước — sẽ phải redo nếu schema cần adjust khi code.

═══════════════════════════════════════════════════════════════════
CONSTRAINTS & CONVENTIONS
═══════════════════════════════════════════════════════════════════

- File naming: kebab-case cho JS files (design-spec-parser.js, NOT designSpecParser.js)
- Code style: existing .skills/metabase-automation/* code dùng CommonJS (require), không ESM
- Test: tạo unit tests cho size-to-grid (pure function) và parser (fixture-based)
- DOM dependencies: KHÔNG add new npm packages trừ khi thực sự cần (YAGNI)
  Đã có: js-yaml, markdown-it có sẵn trong dependency tree
- Commit style: conventional commits, KHÔNG dùng "chore" hay "docs" cho .claude/ files
- DO NOT modify behavior of deploy_from_markdown.js — chỉ consume generated blueprint
- DO NOT modify existing blueprints — chỉ generate new ones from enhanced Design Specs

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERIA (PHASE 1)
═══════════════════════════════════════════════════════════════════

✅ design-spec-parser.js parse được enhanced Design Spec → structured object
✅ size-to-grid.js convert size tokens → row/col/size_x/size_y (unit tested)
✅ convert_design_to_blueprint.js sinh ra blueprint markdown deploy-able
✅ Generated blueprint cho sales_daily_operation match existing 95%+ (semantic diff)
✅ Deploy generated blueprint → Metabase staging → visual match existing dashboard
✅ Documentation: update .skills/metabase-automation/STRATEGY.md với new flow

Báo cáo kết quả ở: plans/reports/implementation-{date}-design-spec-converter.md

═══════════════════════════════════════════════════════════════════
ADDITIONAL CONTEXT (NICE TO KNOW)
═══════════════════════════════════════════════════════════════════

- User là CTO/CEO của 1 retail/ecommerce business ở VN. Đã tự code, không phải junior.
  Pragmatic, YAGNI-focused, ghét over-engineering.

- Previous related work in repo:
  - Recent commit `24c1434`: Tab structure standards (Chu kỳ báo cáo + Source & Freshness)
    đã rollout sang ~30 blueprints. Mọi enhanced Design Spec mới phải support 2 widgets này.
  - Recent commit `8cdbd5d`: Collection restructure by audience (ADR-009).
    Mọi dashboard mới phải có scope suffix [Retail]/[B2B]/[All]/...

- Memory system: ~\.claude\projects\D--Vantt-app-data-integration\memory\
  Check MEMORY.md cho feedback memories liên quan (Metabase quirks, DuckDB constraints,
  TIMESTAMPTZ rules, etc.)

- Hooks: PreToolUse hook warns về file naming convention. Tuân thủ kebab-case cho code files.

═══════════════════════════════════════════════════════════════════
START WHEN READY
═══════════════════════════════════════════════════════════════════

Bắt đầu bằng việc đọc research report đầy đủ:
plans/reports/research-260527-2300-tool-agnostic-design-spec.md

Sau đó báo lại bạn chọn Option A/B/C và proceed.
```

---

## File này dùng để làm gì?

- Đây là handoff prompt để paste vào chat mới.
- Content trong code block ở trên là **prompt nguyên văn** — copy paste y nguyên vào new chat.
- File này chỉ là backup để reference, không phải design doc.

## Khi nào revisit handoff này?

- Nếu chat mới hỏi thêm context không có trong prompt → quay lại research report.
- Nếu Phase 1 hoàn thành → mark file này archived, tạo handoff mới cho Phase 2.
- Nếu schema thay đổi sau khi code → update prompt này trước khi handoff lần 2.
