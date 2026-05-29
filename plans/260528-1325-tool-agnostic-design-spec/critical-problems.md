---
title: "Critical Problems & Open Questions"
status: active
created: 2026-05-28
updated: 2026-05-28
---

# Critical Problems & Open Questions

Research backing: see [reference/research-foundation.md](reference/research-foundation.md)

**Review updates (2026-05-28 1745)**: 2 adversarial reviews completed (see [reports/](reports/)). Reclassifications + new items below.

---

## Section 1: Critical (C) — Phase 0 blockers

Must resolve before or during Phase 0 spike (except C6 = Phase 4 blocker, C7 = Phase 0 hard block).

**HARD BLOCK Phase 0 day 1**: C2 must decide BEFORE schema code written. C7 makes this explicit.

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

**Status**: 🔵 DOWNGRADED to M (per review 2026-05-28 1745 — not Phase 0 blocker)
**Problem**: When parser/deployer fails, analyst sees raw JS stack traces — no `file:line` context, no suggested fix.
**Proposal**: Phase 2 deliverable: structured errors with file+line references, context sentence, suggested fix. Schema validator errors carry location info.
**Phase**: Phase 2 (deployer build)
**Source**: risks-and-open-questions § §E.4

---

## C5: Test Fixture Location

**Status**: 🔵 DOWNGRADED to M (per review 2026-05-28 1745 — obvious answer: Option A)
**Problem**: Schema validation + parser unit tests need fixture specs. No test infra exists yet.
**Resolution (review)**: Option A — `.skills/analytics-design/__tests__/fixtures/` alongside skill. Standard convention, no special analysis needed.
**Phase**: Phase 0 picks; tests introduced Phase 2+
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

## C7: Schema Design Coupled to C2 (Phase 0 Ordering) — NEW from review

**Status**: 🔴 open (Phase 0 HARD BLOCK day 1)
**Problem**: D7 JSON Schema implementation cannot begin until C2 (monolith vs companion) decided. Schema for "single .md file" vs "two-file split (`spec.md` + `spec.widgets.yaml`)" is structurally different. Starting Phase 0 schema work without C2 = rework guaranteed.
**Proposal**:
- A. Decide C2 on day 1 (30-min review of 1 sample spec, NOT a multi-day spike)
- B. Build schema for both modes, decide later (wasteful)
**Phase**: Phase 0 day 1 — first activity before any other work
**Source**: review-problems-260528-1745.md (new finding)

---

## C8 (was M4): Markdown Table Parsing — ESCALATED from M4

**Status**: 🔴 open (per review: assumed-mitigated but NOT tested)
**Problem**: Pipes in cells, Vietnamese chars, multi-line cells (`<br>`), whitespace — break naive parsers. Mitigation "use markdown-it" not verified against real composition tables in 26 production specs.
**Proposal**: Phase 0 test markdown-it parser against ALL 26 v1 specs in `docs/analytics-handbook/designs/`. If failures > 0, evaluate alternatives (regex preprocessor, custom parser).
**Phase**: Phase 0 (verify before Phase 2 parser build)
**Source**: review-problems-260528-1745.md (escalation); originally M4 / risks §C.5

---

## C9 (was M5): Migration Safety for 30 Production Dashboards — ESCALATED from M5

**Status**: 🔴 open (per review: needs concrete plan, not generic principles)
**Problem**: Current mitigation = "staging first, blueprint rollback, gradual" = principles, not plan. No defined: how many days per dashboard? Who reviews? What if visual diff <95% but functionally identical? Rollback procedure step-by-step?
**Proposal**: Phase 3 deliverable: written runbook with per-dashboard checklist (capture → review → staging diff → behavioral test → commit → promote), defined acceptance gates, named owner.
**Phase**: Phase 3 entry — runbook must exist before first migration commits
**Source**: review-problems-260528-1745.md (escalation); originally M5 / risks §D.2

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

## M4: Markdown Table Parsing Fragility → ESCALATED

**Status**: 🔴 ESCALATED to [C8](#c8-was-m4-markdown-table-parsing--escalated-from-m4) per review 2026-05-28 1745. See C8 for active tracking.

---

## M5: Migration Safety for 30 Production Dashboards → ESCALATED

**Status**: 🔴 ESCALATED to [C9](#c9-was-m5-migration-safety-for-30-production-dashboards--escalated-from-m5) per review 2026-05-28 1745. See C9 for active tracking.

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

## M16: Viz Catalog Maintenance Owner Undefined — NEW from review

**Status**: 🟡 needs-owner
**Problem**: METABASE_VIZ_CATALOG.md (and future SUPERSET/EVIDENCE catalogs) require updates when BI tool releases new viz types or changes settings. No named owner → stale within 6 months → misleading portability reports.
**Mitigation**: Phase 0 assign owner (likely whoever owns the deployer). Add catalog freshness check to D6 portability badge — flag if catalog last-updated > 6 months.
**Phase**: Phase 0 (assign), Phase 2 (implement freshness check)
**Source**: review-problems-260528-1745.md (new)

---

## M17: Auto-Captured SQL — Generated vs Authored Accountability Gap — NEW from review

**Status**: 🟡 needs-policy
**Problem**: After Phase 3 capture-first, widget-config blocks contain SQL generated by `capture_dashboard.js`. Git history shows commit author = whoever ran the script. No clear marker distinguishing "machine-extracted SQL (trust capture)" vs "human-authored SQL (analyst reviewed/edited)". Debug + accountability gap.
**Mitigation**: Convention: auto-captured specs have `status: draft-from-capture`; manual edits MUST set `status: reviewed` or `status: final` with author note. Possibly: machine-generated SQL gets a `# AUTO-CAPTURED <timestamp>` header comment.
**Phase**: Phase 1 (define convention), Phase 3 (enforce on migration)
**Source**: review-problems-260528-1745.md (new)

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
- ✅ **Answered (review 2026-05-28 1745)**: `analytics-design` skill owner (per D8). `/design-dashboard` skill workflow update happens when C3 resolved in Phase 0.

**Q4**: H.4 — User hasn't adopted dbt Semantic Layer / MetricFlow. If Phase 4 custom engine grows complex, what is the exit criterion for switching to MetricFlow? Define before Phase 4 starts.

**Q5**: Phase 0 entry check — Are ADR-1, ADR-2, ADR-3 confirmed by user? (Recorded as done 2026-05-28 per origin file; verify before Phase 0 kick-off.)
- ✅ **Answered**: ADR-1 (D1), ADR-2 (D2), ADR-3 (D3) all user-confirmed 2026-05-28. Verified in commit `d7168f7`.

**Q6**: Phase 0 entry check — Is plan dir checked into git and Phase 0 implementer has read `decisions.md` + `reference/architecture.md`?
- ✅ **Answered**: Plan dir committed `d7168f7` 2026-05-28. Phase 0 kickoff checklist must verify implementer read both files (operational, not blocker).

**Q7**: NEW from review — What is the acceptance bar for auto-captured SQL correctness? Who signs off? Visual diff alone is insufficient (timezone-corrupted SQL can pass visual but be ~15% wrong). Needs: numerical sample check (e.g., compare aggregate values old vs new on 7-day window), named reviewer, sign-off marker in spec.
- **Blocks**: Phase 1 acceptance criteria, Phase 3 migration runbook
- **Source**: review-problems-260528-1745.md stress scenario #2

---

## Section 5: Proposed Decisions (await user confirm) — from review 2026-05-28

Two new decisions surfaced by reviews. NOT yet locked. Once user confirms, migrate to `decisions.md` as D9/D10.

### D9 (proposed): Parser Ownership at `analytics-design/lib/`

**Choice**: Place parser at `.skills/analytics-design/lib/design-spec-parser.js` from day 1, NOT at `.skills/metabase-automation/lib/` with deferred relocation.
**Rationale**: Parser has ZERO Metabase-specific logic by contract. Schema at `analytics-design` + parser enforcement at `metabase-automation` = friction every schema change. Cost of deferred move = guaranteed Phase 6 rework. Cost of moving now = nothing (no code exists yet).
**Source**: review-decisions-260528-1745.md (top 3 concerns, #3)
**Blocks**: Phase 2 location decision (must answer before parser code written)

### D10 (proposed): SQL Authoring Ownership in widget-config

**Choice**: TBD. Options:
- A. Analyst-only (matches D8 analyst-owns-spec, but analysts may not write SQL)
- B. Engineer-only (matches blueprint legacy where engineers authored SQL)
- C. Auto-captured only (no hand-authoring; if SQL exists in spec, it came from `capture_dashboard.js`; manual SQL = use blueprint legacy path)
**Rationale**: Hybrid spec collapses analyst/engineer boundary. Without explicit ownership rule, authoring workflow has unresolved handoff. Affects: who gets blocked on Phase 2, D3 risk profile, M17 accountability convention.
**Source**: review-decisions-260528-1745.md (top concerns, missing decisions)
**Blocks**: Phase 1 capture script behavior, Phase 2 deployer validation rules

**Pending decisions awaiting user input:**
1. D9 — confirm parser location (recommend: approve as proposed)
2. D10 — choose option A / B / C (recommend: C, auto-captured only)
3. D2 forcing function — does `status: final` require `metric_ref` post-Phase 4, or allow inline SQL forever?
4. D3 pilot gate — Phase 3 schedule contingent on Phase 1 3-dashboard capture quality pilot?
