---
title: Adversarial Review - Decisions D1-D8
type: review
date: 2026-05-28
reviewer: sonnet brainstormer agent
status: complete
---

# Adversarial Review - Decisions D1-D8

## TL;DR

- **Solid**: D4, D7
- **Questionable**: D1, D2, D3, D5, D6, D8
- **Flawed**: none outright, but D2 and D3 carry the most hidden load
- **Missing decisions proposed**: D9 (parser location lock-in), D10 (inline SQL authorship responsibility)
- **Top 3 concerns before Phase 0**:
  1. D3 capture quality unknown -- if SQL extraction from Metabase is lossy, capture-first collapses; Phase 1 estimate wrong by 2-3x
  2. D2 hybrid spec has no forcing function toward metric_ref; stepping stone becomes permanent SQL state
  3. D8 schema in analytics-design + parser in metabase-automation = split contract; cracks under maintenance pressure

---

## Per-Decision Review

### D1: Skip Blueprint File (Direct Deploy)

**Verdict**: QUESTIONABLE

**Steelman**: Blueprint as intermediate artifact is pure overhead -- duplicates info already in the Design Spec, creates drift risk, adds a manual authoring step. Eliminating it gives a single source of truth.

**Devil's advocate**: Blueprint was a human-readable rollback artifact. When a production dashboard breaks at 2am, ops could read it without running scripts. That safety net disappears. Also: deploy_from_markdown.js legacy runs in parallel through Phase 3 -- two paths with different artifact conventions is the confusion D1 aimed to solve.

**Hidden cost**: Idempotency logic now runs entirely against live API state. API downtime during deploy = no fallback artifact to diff against. Blueprint implicitly served as a deploy manifest -- losing it means no fast answer to what the last deploy looked like without an API call.

**Falsification test**: First time a production deploy partially succeeds (network cut mid-deploy) and the team cannot determine which cards were created vs failed without hitting the API -- D1 is wrong.

**Recommendation**: Revise -- emit an optional lightweight deploy manifest (JSON: card IDs, names, SQL hashes, positions) as a side-effect of deploy. Not a full blueprint. A 20-line JSON manifest enables forensic diffs without API calls. D1 is 90% right; the audit trail gap is the 10% that matters under failure conditions.

---

### D2: Endgame = Semantic Layer (Hybrid Spec)

**Verdict**: QUESTIONABLE

**Steelman**: Hybrid is the only pragmatic path. SQL-in-spec is deployable today; metric_ref requires an aggregation engine that does not exist. Hybrid schema from day 1 means Phase 4 is additive (no schema break). Mirrors dbt evolution (SQL models then semantic layer) -- a proven incremental pattern.

**Devil's advocate**: Hybrid embeds two incompatible world-views in the same YAML block. Inline SQL is imperative (how to compute); metric_ref is declarative (what to compute). Parser must handle two execution paths with no guarantee they produce identical numbers. All 30 migrated dashboards start in inline SQL with no forcing function to migrate to metric_ref. Research already shows net_revenue SQL duplicated across 8 dashboards -- hybrid spec legitimizes that duplication by providing a sanctioned inline SQL path. Stepping stone silently becomes permanent.

**Hidden cost**: 30 dashboards x 15 widgets = 450 inline SQL blocks requiring manual metric_ref migration in Phase 4. Without a named owner and deadline, this migration never happens. The tool-agnostic DRY goal gets buried behind SQL duplication that is now officially supported by the format.

**Falsification test**: 12 months post-Phase 2, >80% of widget-configs still use inline SQL and no Phase 4 is scheduled -- stepping stone assumption was wrong. Simpler: if net_revenue filter logic changes and requires updating SQL in 8+ widget-configs across multiple specs -- D2 failed at its most fundamental goal.

**Recommendation**: Revise -- add a forcing function before Phase 0 schema design: (a) define what status:final requires -- can a spec be permanently final with inline SQL? (b) add status:sql-legacy flag to distinguish intentionally-SQL-only specs from in-progress migrations. Without this, hybrid is honest about the stepping stone but dishonest about whether a path to the destination exists.

---

### D3: Capture-First Migration Strategy

**Verdict**: QUESTIONABLE (highest hidden risk in the entire decision set)

**Steelman**: Capture-first stress-tests the schema against real data diversity before the parser hardens. Manual migration 2-4h per dashboard = 60-120h; automated capture = 1-2h if it works. Round-trip validation (capture then spec then deploy then compare) is the most honest correctness test possible.

**Devil's advocate**: Assumes capture_dashboard.js can extract SQL and viz config with high fidelity. Non-trivial: Metabase has GUI-built native questions (no SQL to capture), complex template tags, saved question references. The sales_daily_operation blueprint is 1451 lines; Health Score is a 5-CTE query 80+ lines. If capture produces partial SQL or misses visualization_settings mappings, draft-from-capture specs require correction approaching manual authoring cost -- but now with the risk that auto-generated drafts contain subtly wrong SQL that passes lint but computes wrong numbers.

**Hidden cost**: draft-from-capture requires human review with no stated acceptance criteria. If 30 dashboards x 3-4h verification = 90-120h anyway, capture-first saved nothing and introduced a new risk class: plausible-looking but incorrect SQL that a reviewer might miss. Captured spec creates false confidence where skepticism is warranted.

**Falsification test**: Capture the 3 most complex dashboards. If reviewer time per dashboard exceeds 2 hours, or if >20% of widgets need SQL correction -- capture-first is not faster than manual migration. This test costs 1 day and should be an explicit Phase 1 go/no-go gate.

**Recommendation**: Revise -- add explicit Phase 1 pilot gate: capture 3 representative dashboards (1 simple, 1 medium, 1 complex like sales_daily_operation), measure review time and error rate, decide Phase 3 approach from results. Phase 3 schedule must NOT be locked before Phase 1 pilot data is available. Define promotion criteria: SQL output matches baseline, visual diff <5%, filter wiring confirmed via behavioral test.

---

### D4: Spec Versioning (spec_version Field)

**Verdict**: SOLID

**Steelman**: 30 dashboards on an evolving schema without versioning = silent breakage at scale. spec_version frontmatter enables parser branching, migration script targeting, progressive rollout. Standard practice. Zero authoring overhead.

**Devil's advocate**: Version field only useful if enforced. Silent fallback from missing spec_version to v1 on a v2 spec (9-column table, widget-config blocks) means data loss with no error -- exactly the silent breakage versioning was meant to prevent.

**Hidden cost**: Two parse paths (v1 + v2) = two surfaces to maintain. Adding v3 means three. Without explicit v1 deprecation timeline, legacy path accumulates indefinitely.

**Falsification test**: A v2 spec accidentally missing spec_version gets silently parsed as v1 with no warning -- implementation failure the implementation note must prevent.

**Recommendation**: Reaffirm -- add to implementation notes: v2 spec missing spec_version should emit ERROR not silent v1 fallback. v2 specs have 9-column composition tables that v1 parser misreads. Only specs with no spec_version AND 8-column table should fall to v1 legacy path.

---

### D5: Per-Tool Deployer Pattern

**Verdict**: QUESTIONABLE

**Steelman**: Each BI tool has irreconcilably different APIs, grid systems, viz parameters. A single converter-to-neutral-format pushes complexity into the converter without eliminating it. Per-tool deployer isolates tool-specific logic and makes it independently testable. Proven pattern (Terraform providers, language SDKs).

**Devil's advocate**: Keeps abstraction cost low is asserted, not demonstrated. Each deployer still translates: viz types via catalog, color tokens, grid coordinates, filter wiring, tab standards, size tokens. If shared lib/deploy-core.js grows to contain most translation logic, it is a converter embedded in the deployer -- same complexity, less transparency. The abstraction line will shift under implementation pressure with no principled boundary to stop it.

**Hidden cost**: Tool-agnostic schema must be rich enough to serve ALL future tools from day one. If designed Metabase-first (the only tool for Phase 2-5), adding an Evidence deployer in Phase 6 may require DesignSpec interface changes -- potentially breaking 30 existing specs. The tool-agnostic promise is unfalsifiable until a second deployer is actually built.

**Falsification test**: When a second deployer is added, if it requires changes to the DesignSpec interface OR widget-config.schema.json -- the schema was Metabase-biased, not tool-agnostic.

**Recommendation**: Revise -- before Phase 0 schema design, run a 2-hour paper exercise: mock-translate 5 representative widgets (gauge, single-value-with-trend, multi-line-chart, data-table, text-annotation) to Evidence format using only the proposed DesignSpec interface. Any widget requiring information not in the interface reveals a schema gap. Low-cost insurance that validates the D5 promise before committing to the schema.

---

### D6: Portability Badge (Honest Reporting)

**Verdict**: QUESTIONABLE (real risk of compliance theater)

**Steelman**: 7/25 viz types non-universal including the most popular (gauge, progress-toward-goal, single-value-with-trend). Silent fallback means analysts discover broken dashboards post-deploy to a new tool. Portability report forces honest conversation about viz choices at authoring time, not migration time. Genuinely useful once multiple tools are in use.

**Devil's advocate**: Portability report is meaningful only when a second tool is targeted. For the next 12-18 months (Metabase only), every widget is native by definition -- report emits 100% native every time. Analysts have zero incentive to choose more portable viz types because there is no current cost to non-portability. The badge is wallpaper. When a second tool is added, 12-18 months of non-portable choices are already locked in.

**Hidden cost**: Maintaining native/fallback/unsupported for 6 tools x 25 viz types requires updating catalogs every time any BI tool releases new features. No named owner specified. Research data stale within 6 months. A wrong catalog entry is actively misleading -- worse than no entry.

**Falsification test**: 6 months post-implementation, if no spec author has changed a viz choice based on a portability warning (Metabase-only, every viz native) -- D6 is compliance theater. Also: if any catalog entry for a non-deployed tool is incorrect because that tool updated, the portability report misleads.

**Recommendation**: Revise -- defer cross-tool portability catalog to Phase 6 (when second deployer is added and immediately actionable). Phase 0-5: emit portability warnings ONLY for viz types with metabase:unsupported or fallback -- catches real errors now without speculative multi-tool data.

---

### D7: JSON Schema from Day 1

**Verdict**: SOLID

**Steelman**: YAML-in-markdown without schema validation at 30+ dashboards is a maintenance disaster. Schema-first enables VSCode autocompletion, catches typos at edit time, documents the format as an executable contract. Largest DX lever available at near-zero ongoing cost once written. Non-negotiable at this scale.

**Devil's advocate**: JSON Schema 2020-12 is complex to author and has behavioral differences from Draft-07 (which most tooling supports better). If VSCode YAML extension does not fully support 2020-12 constructs, validation silently fails -- authors believe they are protected when they are not.

**Hidden cost**: Schema must evolve with the spec format through Phase 0-6. Every widget-config change requires schema update, re-validation of 30+ specs, potentially a spec_version bump. Without clear ownership, schema drift degrades the validation guarantee silently over time.

**Falsification test**: A widget-config typo makes it to production 3 months after Phase 0 despite schema being in place -- D7 implementation failed (schema not enforced at deploy, or extension misconfigured or not installed on the authoring machine).

**Recommendation**: Reaffirm -- with two caveats: (1) target JSON Schema Draft-07 or 2019-09 instead of 2020-12 for broader tooling support; verify VSCode YAML extension compatibility before committing; (2) schema validation must be mandatory pre-deploy step in the deployer, not optional editor-only validation. Editor validation is DX; deploy-time validation is correctness. Both required.

---

### D8: Spec Schema Location (analytics-design)

**Verdict**: QUESTIONABLE (boundary confusion will cause real maintenance friction)

**Steelman**: Separating what to measure (analytics-design) from how to deploy (tool-specific skills) is architecturally clean and correct long-term. Analysts author specs without Metabase knowledge. Schema in analytics-design prevents tool implementation details from leaking into the spec format. Correct boundary -- question is only when to enforce it.

**Devil's advocate**: The parser that ENFORCES the schema lives in metabase-automation/lib/design-spec-parser.js. Schema is owned by analytics-design. Parser is owned by metabase-automation. A bug where schema says field X is optional but Metabase deployer requires it crosses both skill boundaries -- unclear who owns the fix. Under pressure, parser will accept fields not in schema (or vice versa) because the feedback loop across directories is slow. In a single-developer context, this means mental context-switching across two directories for every schema-parser sync issue.

**Hidden cost**: Architecture defers parser relocation to analytics-design until 2nd tool added -- scheduled rework with certain cost and uncertain timing. A developer adding a 3rd or 4th tool will discover the parser in a tool-specific directory and logically copy it rather than import it -- temporary location becomes permanent through cargo-culting.

**Falsification test**: Count how many times a spec authoring change (schema in analytics-design) requires a corresponding parser change (in metabase-automation) in the same commit. If >50% of schema changes require touching both directories -- the boundary creates friction, not clarity.

**Recommendation**: Revise -- move parser to analytics-design/lib/design-spec-parser.js from day one. Parser returns tool-agnostic DesignSpec and has zero Metabase-specific logic by contract. Metabase deployer imports it as a cross-skill dependency. This eliminates the Phase 6 relocation, co-locates schema and its enforcer, and makes the correct dependency direction explicit (tool skills depend on analytics-design, not reverse). Counter-argument YAGNI until 2nd tool is rejected: parser has NO Metabase-specific logic, so correct placement is analytics-design regardless of tool count.

---

## Cross-Decision Analysis

### Inconsistencies / Tensions

**D1 vs D3**: D1 eliminates blueprint as audit artifact. D3 round-trip validation requires a before-baseline to compare against. Without a blueprint, the baseline is live API state -- which is the thing being replaced by the deploy. Round-trip comparison requires snapshotting API state before each deploy -- a different kind of artifact D1 does not account for. D1 and D3 together leave the audit baseline undefined.

**D2 vs D3**: D2 says all captured/migrated specs use inline SQL. D3 auto-migrates 30 dashboards. Result: 30 x 15 widgets = 450 inline SQL blocks. If Phase 4 metric_ref migration never happens (D2 risk), the captured-and-reviewed specs are technical debt from day one -- not a stepping stone but a final state dishonest about being final. Two decisions together create a large SQL-laden spec body with no forcing function toward the tool-agnostic endgame.

**D5 vs D8**: D5 says per-tool deployer reads shared parser. D8 says parser lives in metabase-automation until Phase 6. Together: an Evidence deployer (Phase 6) must import metabase-automation/lib/ -- tool A depends on tool B directory. This is a known architectural smell; treating it as deferrable creates the conditions for it to never be relocated.

**D6 vs D5**: D6 requires viz catalogs to declare native/fallback/unsupported per tool. D5 says non-Metabase deployers are on-demand. Until those deployers exist, catalog entries for Evidence/Superset/Looker are educated guesses from research -- not tested against real API behavior. Portability report emits unverified portability claims for tools with no working deployer.

**D7 vs C2 (open)**: D7 says JSON Schema from day 1. C2 (monolith vs companion file) is unresolved. If Phase 0 spike selects companion file (spec.md + spec.widgets.yaml), the schema structure changes significantly -- YAML file is now the primary machine-readable surface, not embedded fenced blocks in markdown. D7 schema implementation must not begin until C2 is resolved.

### Order Issues

- **C2 must resolve as first Phase 0 output, before D7 implementation**: File format determines where widget-config YAML lives and how the schema references it. Starting schema design before this decision risks significant rework.

- **D5 paper exercise must precede D7 schema publication**: Tool-agnostic schema must be validated against at least one non-Metabase tool before publication. Publishing Metabase-biased schema as tool-agnostic and needing to break it in Phase 6 is worse than delaying publication by 2 hours.

- **D3 Phase 1 pilot results must gate Phase 3 schedule**: Phase 3 must not be committed before Phase 1 pilot quality data is available. Currently there is no explicit stopping point if capture quality is insufficient.

### Missing Decisions

**D9 proposed**: Parser ownership and location from day one.

Why needed: Architecture says parser lives in metabase-automation/lib/ until 2nd tool added. D8 says analytics-design owns the schema. Two different skill directories own different halves of the same contract. Phase 2 implementation requires making this concrete, and the path-of-least-resistance choice (keep in metabase-automation) is the wrong long-term choice.

Suggested choice: Move parser to analytics-design/lib/design-spec-parser.js from day one. Parser has zero Metabase-specific logic by contract. Metabase deployer takes a cross-skill dependency. Eliminates Phase 6 relocation as scheduled rework.

**D10 proposed**: Who authors and owns inline SQL in widget-config blocks.

Why needed: D3 assumes auto-capture generates SQL. D2 provides sanctioned inline SQL path. But the Design Spec is the ANALYST document -- analysts are not expected to write or verify complex multi-CTE SQL (Health Score is a 5-CTE query). Current blueprint was the ENGINEER document. Hybrid spec collapses that separation without deciding who inherits SQL responsibility. This determines the authoring workflow, who gets blocked on Phase 2, and the risk profile of D3.

Suggested choice: Define explicit section ownership. Composition table + brief + constraints = analyst-owned. Widget-config SQL + viz config = engineer-authored, analyst-reviewed. Alternative: SQL in widget-config is always auto-captured (never hand-authored), concentrating D3 risk into a single dependency but keeping the spec clean for analysts.

---

## Recommendations Summary

- **Reaffirm**: D4, D7 (both solid; implementation caveats noted above)
- **Revise**:
  - D1 -- add lightweight deploy manifest (JSON, not full blueprint) as optional audit artifact
  - D2 -- add forcing function: define status:final requirements re inline SQL vs metric_ref; add status:sql-legacy flag
  - D3 -- add explicit Phase 1 pilot gate (3 dashboards) with go/no-go criteria before committing Phase 3 schedule
  - D5 -- run 2h paper exercise (Evidence mock-translation) before schema is published in Phase 0
  - D6 -- defer cross-tool catalog to Phase 6; Phase 0-5 portability covers Metabase native/fallback/unsupported only
  - D8 -- move parser to analytics-design/lib/ from day one; eliminate deferred relocation
- **Add**:
  - D9 -- Parser location: analytics-design/lib/ from day one
  - D10 -- Inline SQL authorship boundary: analyst vs engineer section ownership
- **Block Phase 0 start until**:
  1. C2 (monolith vs companion file) is decided -- D7 schema structure depends on it
  2. D5 paper exercise complete -- schema must be validated as tool-agnostic before publication
  3. D10 is decided -- analyst/engineer ownership boundary determines template design and SKILL.md scope

---

## Unresolved questions for user

1. **D2 forcing function**: Is inline SQL acceptable at status:final indefinitely, or should Phase 4+ require metric_ref for final status? Without this, hybrid = SQL forever and the DRY goal is never reached.
2. **D3 pilot gate**: Will Phase 3 schedule be held contingent on Phase 1 capture quality results? If capture quality is insufficient after the pilot, what is the fallback plan?
3. **D8 / D9**: Any objection to moving the parser to analytics-design/lib/ now? The deferred Phase 6 move is scheduled rework with certain cost. Parser has zero Metabase-specific logic -- correct home is analytics-design regardless of tool count.
4. **D10**: Who authors SQL in widget-config blocks -- analyst, engineer, or auto-captured only? Determines authoring workflow, who gets blocked on Phase 2, and D3 risk profile.
5. **C2 vs D7 ordering**: Can C2 (monolith vs companion) be the first output of Phase 0 spike, before schema implementation begins? A 30-minute decision that prevents hours of schema rework.
6. **D6 catalog maintenance**: Who owns keeping viz catalogs current as BI tools release updates? Without a named owner, portability report degrades silently within 6 months.
