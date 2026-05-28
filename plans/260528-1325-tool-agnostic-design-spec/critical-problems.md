---
title: "Critical Problems & Open Questions"
status: active
created: 2026-05-28
updated: 2026-05-28
---

# Critical Problems & Open Questions

Research backing: see [reference/research-foundation.md](reference/research-foundation.md)

---

## Section 1: Critical (C) — Phase 0 blockers

Must resolve before or during Phase 0 spike (except C6 = Phase 4 blocker).

---

## C1: DRY Thresholds / Comparisons Duplicated

**Status**: 🔴 open
**Problem**: Gauge thresholds (e.g., Health Score 0-49/49-74/74-100) appear in 3-4 places: Playbook Action Triggers, Design Spec composition table "color zones", widget-config gauge.segments YAML, possibly domain metric thresholds. Same value, multiple sources = sync risk.
**Proposal**:
- A. Frontmatter `defaults:` block; widgets use `inherit_from: defaults`
- B. Single source = widget-config; composition table auto-derived (less duplication, loses readability)
- C. Accept duplication + CI lint to catch divergence
**Phase**: Phase 0 spike decides based on authoring experience
**Source**: risks-and-open-questions § §C.1; also ADR-9 deferred item #3

---

## C2: Monolith Spec vs Companion File

**Status**: 🔴 open
**Problem**: Enhanced spec for `sales_daily_operation` projected ~1000-1200 lines (vs current 161). Composition table — highest analyst value — gets buried under YAML/SQL blocks.
**Proposal**:
- A. Monolith: single `.md` file (handoff plan)
- B. Companion: `spec.md` (composition + brief) + `spec.widgets.yaml` (technical)
- C. Collapsible markdown sections (one file, visual split)
**Phase**: Phase 0 spike answers: does authoring 1000-line spec feel painful?
**Source**: risks-and-open-questions § §C.3; also ADR-9 deferred item #1

---

## C3: Composition Table vs Widget Details — Source of Truth

**Status**: 🔴 open
**Problem**: Both composition table and widget-details YAML contain overlapping info (card name, viz type, role, size). If both hand-authored, sync risk.
**Proposal**:
- A. Hand-author both + lint check warns on mismatch
- B. Hand-author widget details only; composition table auto-derived on parse
- C. Hand-author composition table only; widget-details = technical config only (handoff implication)
**Phase**: Phase 0 decides based on which feels natural to author
**Source**: risks-and-open-questions § §C.6; also ADR-9 deferred item #2

---

## C4: Error Reporting Quality

**Status**: 🔴 open
**Problem**: When parser/deployer fails, analyst sees raw JS stack traces — no `file:line` context, no suggested fix.
**Proposal**: Phase 2 deliverable: structured errors with file+line references, context sentence, suggested fix. Schema validator errors carry location info.
**Phase**: Phase 2 (deployer build)
**Source**: risks-and-open-questions § §E.4

---

## C5: Test Fixture Location

**Status**: 🔴 open
**Problem**: Schema validation + parser unit tests need fixture specs. No test infra exists yet.
**Proposal**:
- A. `.skills/analytics-design/__tests__/fixtures/` (alongside skill)
- B. `plans/260528-.../fixtures/` (in plan dir during dev)
- C. `tests/fixtures/` (project root)
**Phase**: Phase 0 picks based on existing test infra; tests introduced Phase 2+
**Source**: risks-and-open-questions § §G.3

---

## C6: Cross-Skill Boundary — Aggregation Engine Location

**Status**: 🔴 open (Phase 4 blocker)
**Problem**: When metric defs become executable (semantic layer), aggregation engine needs a home. analytics-design = analyst brain (no execution). Tool deployers = tool-specific. Neither fits well.
**Proposal**:
- A. New `.skills/semantic-resolver/` folder
- B. Absorb into `analytics-design` (breaks "no execution" principle)
- C. Each tool deployer handles its own resolution (duplication)
**Phase**: Phase 4 decision. Phase 0-3 unblocked (inline SQL, no engine needed).
**Source**: risks-and-open-questions § §B.3

---

## Section 2: Medium (M) — track, not blocking

---

## M1: Multi-Tool ROI Weak Short-Term

**Status**: 🟡 mitigated
**Problem**: User on Metabase only; per-tool deployer infra may sit unused.
**Mitigation**: Phase 2 = Metabase only. Phase 6 = on-demand. Adapter pattern cost ~1 day schema discipline, not weeks of speculative code.
**Source**: risks-and-open-questions § §A.2

---

## M2: Fallback Semantics for Non-Universal Viz Types

**Status**: 🟡 mitigated
**Problem**: 7/25 viz types non-universal; most popular (gauge, progress-toward-goal, single-value-with-trend) included. Silent fallback = degraded output.
**Mitigation**: D6 portability badge. Each catalog declares `native|fallback|unsupported`. `fallback:` field in widget-config. Ongoing: validate fallback chains when adding new BI tool.
**Source**: risks-and-open-questions § §C.2

---

## M3: Composition Table Format Change Breaks v1 Parsers

**Status**: 🟡 mitigated
**Problem**: Adding Widget ID column changes column count 8→9; existing v1 specs have 8-col tables.
**Mitigation**: Parser auto-detects column count; 8-col → Widget ID derived from card name slugification; 9-col → explicit Widget ID.
**Source**: risks-and-open-questions § §C.4

---

## M4: Markdown Table Parsing Fragility

**Status**: 🟡 mitigated
**Problem**: Pipes in cells, Vietnamese chars, multi-line cells (`<br>`), whitespace — break naive parsers.
**Mitigation**: Use markdown-it (established lib). If composition table parse fails, parser falls back to widget-details as source of truth.
**Source**: risks-and-open-questions § §C.5

---

## M5: Migration Safety for 30 Production Dashboards

**Status**: 🟡 mitigated
**Problem**: Wrong migration = users see broken dashboards.
**Mitigation**: Phase 3 → staging Metabase first. Blueprint kept as rollback. Each dashboard = separate git commit. Visual + behavioral diff before promoting. Low-risk dashboards first.
**Source**: risks-and-open-questions § §D.2

---

## M6: Semantic Layer Iteration Footgun

**Status**: ⚪ deferred (Phase 4+)
**Problem**: Changing a metric def in domain files affects ALL dashboards using it. Refactor `net_revenue` → 15 dashboards rebuild.
**Mitigation**: Phase 4 deliverable: `which-dashboards-use <metric>` tool. Possible: metric versioning + deprecation flags.
**Source**: risks-and-open-questions § §D.4

---

## M7: File Diff as Validation — Fragile

**Status**: 🟡 mitigated
**Problem**: Semantic diff undefined; JSON key order/whitespace creates noise. File diff ≠ behavioral correctness.
**Mitigation**: 6-layer validation strategy (JSON Schema → cross-ref → round-trip → property-based → behavioral → visual diff). File diff = debug aid only.
**Source**: risks-and-open-questions § §E.1

---

## M8: Schema Lock-In

**Status**: 🟡 mitigated
**Problem**: 30 dashboards depend on schema correctness; schema change → mass migration.
**Mitigation**: D4 `spec_version` field. JSON Schema versioned. Parser supports v1+v2. Migration scripts on bumps.
**Source**: risks-and-open-questions § §E.2

---

## M9: Aggregation Engine — Build vs Adopt dbt MetricFlow

**Status**: ⚪ deferred (Phase 4 decision)
**Problem**: Custom engine = full control, heavy build. dbt MetricFlow = industry standard but requires dbt Cloud / self-host; DuckDB compat questionable.
**Mitigation**: Re-evaluate Phase 4 start. Build minimal custom first; adopt MetricFlow if complexity explodes.
**Source**: risks-and-open-questions § §F.1

---

## M10: Documentation Generation from Spec

**Status**: ⚪ deferred
**Problem**: Spec could auto-generate stakeholder docs (PDF/HTML). YAGNI risk if no user demand.
**Mitigation**: Revisit if Phase 3+ users request.
**Source**: risks-and-open-questions § §F.3

---

## M11: CI Integration (Lint on PR)

**Status**: ⚪ deferred
**Problem**: Could lint Design Specs in CI: schema validation, row width sums, broken metric_refs.
**Mitigation**: Phase 2+ optional. Manual `node validate.js` first; CI hookup later.
**Source**: risks-and-open-questions § §F.4

---

## M12: Slug Uniqueness for Shared Widget Library

**Status**: ⚪ deferred (YAGNI)
**Problem**: If shared widgets reused across dashboards, slugs need global namespace. Not planned.
**Mitigation**: Add namespace prefix if/when shared library emerges.
**Source**: risks-and-open-questions § §F.5

---

## M13: Bilingual Content Handling

**Status**: 🟡 mitigated
**Problem**: Vietnamese (Đ, ô, ơ, ư) in card titles/annotations; ASCII-only in slugs/file names.
**Mitigation**: YAML/JSON UTF-8 throughout. Slug regex: `^W:[a-z0-9-]+$`. File names: `^[a-z0-9_-]+\.md$`. Documented in JSON Schema.
**Source**: risks-and-open-questions § §G.1

---

## M14: Parser Performance

**Status**: 🟡 mitigated (not a concern)
**Problem**: Parsing 30 specs (~1000 lines each) at deploy time.
**Mitigation**: Should be sub-second. markdown-it + js-yaml are fast. No optimization needed.
**Source**: risks-and-open-questions § §G.2

---

## M15: Backward Compat for 25 Existing v1 Design Specs

**Status**: 🟡 mitigated
**Problem**: `docs/analytics-handbook/designs/*.md` has 25 thin specs (current format). Enhancing format must not break them.
**Mitigation**: v1 (no `spec_version`) → legacy parse path. v1 specs usable for analyst workflow only (no direct deploy). Phase 3 capture-first migrates to v2.
**Source**: risks-and-open-questions § §G.4

---

## Section 3: Deferred Decisions (from ADR-9)

Items intentionally not decided — Phase 0 spike informs. Cross-linked to Critical section above.

| # | Item | Phase | Cross-link |
|---|------|-------|------------|
| 1 | Monolith vs companion file | Phase 0 | [C2](#c2-monolith-spec-vs-companion-file) |
| 2 | Composition table vs widget details as source-of-truth | Phase 0 | [C3](#c3-composition-table-vs-widget-details--source-of-truth) |
| 3 | Threshold/comparison DRY model (inherit_from, single source, lint) | Phase 0 | [C1](#c1-dry-thresholds--comparisons-duplicated) |
| 4 | Aggregation engine: custom build vs dbt MetricFlow | Phase 4 | [M9](#m9-aggregation-engine--build-vs-adopt-dbt-metricflow) |

**Source**: decisions § §ADR-9

---

## Section 4: Open Questions

Issues not yet fitting C/M categories; require answer before or during relevant phase.

**Q1**: H.1 — If Phase 0 spike shows monolith 1000-line spec IS painful, is companion file (`spec.md` + `spec.widgets.yaml`) the preferred split, or collapsible sections? Decision owner: Phase 0 implementer.

**Q2**: H.2 — What is minimum aggregation engine scope to unblock Phase 4? (simple aggregations only, or must include comparison periods from day 1?) Impacts Phase 4 estimate (3-5d vs longer).

**Q3**: H.3 — Composition table is currently hand-authored (primary analyst value). If we move to auto-derived table (option B in C3), does `/design-dashboard` skill workflow need update? Who owns that change?

**Q4**: H.4 — User hasn't adopted dbt Semantic Layer / MetricFlow. If Phase 4 custom engine grows complex, what is the exit criterion for switching to MetricFlow? Define before Phase 4 starts.

**Q5**: Phase 0 entry check — Are ADR-1, ADR-2, ADR-3 confirmed by user? (Recorded as done 2026-05-28 per origin file; verify before Phase 0 kick-off.)

**Q6**: Phase 0 entry check — Is plan dir checked into git and Phase 0 implementer has read `decisions.md` + `reference/architecture.md`?
