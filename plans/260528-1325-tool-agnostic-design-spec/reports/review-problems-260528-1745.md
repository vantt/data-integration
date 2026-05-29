---
title: "Adversarial Review — Critical Problems & Open Questions"
type: review
date: 2026-05-28
reviewer: sonnet general-purpose (resumed after brainstormer session limit)
status: complete
---

# Adversarial Review — Critical Problems & Open Questions

## TL;DR
- C verdict: keep 4 / reframe 1 / reclassify 1 (C4 → M)
- M escalations to C: M4, M5
- Q answerable now: Q3, Q5, Q6
- New issues surfaced: C7, M16, M17, Q7
- Top 5 for Phase 0 focus: C2 (monolith vs companion), C3 (source of truth), C1 (threshold DRY), M4-escalated (markdown fragility), C7 (schema coupling to file format)

---

## Part 1 — Critical Review (C1-C6)

### C1: DRY Thresholds / Comparisons Duplicated
- Framing: OK — 3-4 duplication points correctly identified
- Options: Mostly exhaustive. Missing option D: thresholds live in domain metric defs (playbook layer), widgets reference via `metric_ref` once semantic layer exists — eliminates problem entirely at Phase 4. Worth noting.
- Priority: keep C — authoring pain from day 1; wrong choice in Phase 0 → migrate 30 specs later
- Action: keep, add option D note for completeness

### C2: Monolith Spec vs Companion File
- Framing: OK — 1000-line projection accurate, buried-composition-table concern real
- Options: Exhaustive (A/B/C). Decisions review confirms C2 must resolve before D7 schema implementation — correct dependency already noted
- Priority: keep C — determines schema structure (where YAML lives); must be FIRST Phase 0 output before any code
- Action: keep, flag as Phase 0 day-1 decision (30 min decision, not a multi-day spike)

### C3: Composition Table vs Widget Details — Source of Truth
- Framing: OK — overlap real, sync risk understated. Lint check tells you they diverged AFTER the fact, not which is correct
- Options: Option B (auto-derive composition table) implies parser renders human-readable table from YAML — non-trivial, not flagged. Option C understated: if composition table is primary, widget YAML = pure tech config, analyst never touches it — cleaner separation worth steelmanning
- Priority: keep C — wrong choice locks authoring workflow; changing later = re-authoring 30+ specs
- Action: keep, strengthen option C framing (analyst owns table, engineer owns YAML)

### C4: Error Reporting Quality
- Framing: OK problem description, but Phase placement wrong. NOT a Phase 0 blocker
- Options: No real options presented — it is a "must do" NFR, not a decision
- Priority: downgrade to M — important Phase 2 build quality requirement, not blocking schema design
- Action: reclassify C → M (Phase 2 NFR)

### C5: Test Fixture Location
- Framing: OK but trivially resolvable in 5 min — should not occupy a Critical slot
- Options: All three viable; option A clearly correct given project structure
- Priority: downgrade to M — answer is obvious; only blocked if test infra policy uncertain
- Action: reclassify C → M; default answer: use `.skills/analytics-design/__tests__/fixtures/`

### C6: Cross-Skill Boundary — Aggregation Engine Location
- Framing: Correct — Phase 4 blocker, correctly deferred
- Options: Exhaustive. Option A (semantic-resolver) clearly correct; B and C are straw-men
- Priority: keep C (Phase 4 blocker) — label explicitly "not Phase 0 relevant"
- Action: keep; add note that Phase 0-3 unblocked regardless of this choice

---

## Part 2 — Open Questions (Q1-Q6)

### Q1: Monolith pain → companion preferred or collapsible?
- Answerable now: partially
- Answer: Collapsible sections (option C) is lowest-friction — one file, clean git diff. Companion file wins only if parser simplicity matters more than authoring simplicity. Default to collapsible unless Phase 0 spike shows >50 lines of YAML-in-markdown unworkable in practice. Recommend: decide on Phase 0 day 1, not after spike.

### Q2: Minimum aggregation engine scope for Phase 4?
- Answerable now: yes (partially)
- Answer: Minimum = simple aggregations (SUM/COUNT/AVG/DISTINCT) + time-grain (day/week/month) + comparison periods (wow/mom/yoy). Comparison periods are the most common widget type needing metric_ref (all trend widgets). Without them, metric_ref covers <30% of widgets — Phase 4 not worth building. Estimate stays 3-5d for MVP at that scope.

### Q3: If composition table auto-derived, does /design-dashboard skill need update? Who owns?
- Answerable now: yes
- Answer: Yes, skill needs update — analyst workflow changes from "fill composition table" to "fill widget YAML; table generates". Owner = analytics-design skill maintainer (same person writing Phase 0 schema). Not a separate ownership problem; it is part of Phase 0-2 scope already.

### Q4: Exit criterion for switching MetricFlow?
- Answerable now: yes (define now, not at Phase 4)
- Answer: Switch if custom engine requires any of: multi-hop joins, fiscal calendar offsets, fan-out metric dependencies, or >3 person-weeks engine maintenance per quarter. If none trigger by Phase 5 end, stay custom. Write this in decisions.md before Phase 4 starts.

### Q5: ADR-1/2/3 confirmed by user?
- Answerable now: yes
- Answer: Per critical-problems.md source "Recorded as done 2026-05-28". Treat as confirmed. Add sign-off checkpoint to Phase 0 kickoff, not a current blocker.

### Q6: Plan dir in git + Phase 0 implementer read decisions.md + architecture.md?
- Answerable now: yes (procedural check, not design question)
- Answer: Confirming git tracking and reader sign-off is a kickoff checklist item. Remove from open questions; add to Phase 0 kickoff checklist.

---

## Part 3 — Medium Escalations

**M4 (Markdown Table Parsing Fragility) → escalate (Phase 0 must test)**
Reason: "Mitigation: Use markdown-it" stated but not proven. Vietnamese chars + `<br>` in cells exist in current production specs. If markdown-it fails on actual specs during Phase 0 spike, C2/C3 decisions are invalidated. Not mitigated — assumed. Phase 0 spike MUST test parser against actual existing specs (incl. multi-byte chars) before committing to markdown tables as format.

**M5 (Migration Safety) → escalate (staging env unconfirmed)**
Reason: "Staging Metabase first" mitigation assumes staging exists and is configured. Not confirmed. D3 review found capture quality unknown. M5 mitigation depends on BOTH a working capture AND a staging env. If both fail together, 30 production dashboards at risk with no tested rollback. Confirm staging env existence as Phase 0 prerequisite (15-min check).

**M10 (Documentation Generation) → drop**
Pure YAGNI. No user demand. No architecture relevance.

**M14 (Parser Performance) → drop**
Author already says "not a concern / sub-second". Non-problem occupying a catalog slot.

---

## Part 4 — Missing Problems

### C7 (proposed): Schema Design Coupled to Unresolved C2 File Format Decision
- Why critical: D7 (JSON Schema from day 1) cannot be implemented until C2 resolved. Schema structure differs fundamentally: monolith = fenced YAML block in markdown, companion = standalone `.widgets.yaml`. If schema built for monolith and Phase 0 picks companion, schema must be rewritten. This is mentioned in decisions review cross-reference but absent from problems catalog. It is a Phase 0 ordering constraint, not a preference.
- Phase: Phase 0, day 1. Prerequisite ordering: C2 decided → D7 schema design → all else.

### M16 (proposed): No Named Owner for Ongoing Viz Catalog Maintenance
- Portability catalog (native/fallback/unsupported per tool) goes stale as BI tools update. No named owner. Stale catalog = misleading portability report. Decisions review flagged for D6. Low risk now (Phase 6 deferred correctly) but Phase 6 plan must include catalog ownership assignment.
- Phase: Phase 6 planning item; note now.

### M17 (proposed): Git History Pollution from Large Auto-Captured Spec Files
- 30 dashboards x ~1000 lines = 30,000-line addition in Phase 3. `git blame` / `git log` noise for `docs/analytics-handbook/designs/`. Mitigable by single migration commit per dashboard (already in M5) but also requires policy: is auto-captured SQL treated as generated (low blame value) or authored (analyst-accountable)? No current policy.
- Phase: Phase 3 concern; note now.

### Q7 (proposed): Who Reviews Auto-Captured SQL and What is the Acceptance Bar?
- D3 review flagged "plausible-looking but incorrect SQL" risk from auto-capture. Neither C nor M currently names an acceptance bar (% correctness, review checklist, sign-off requirement). Without this, capture-first produces unreviewed SQL in production specs. Question: does captured SQL require engineer sign-off before spec tagged `status:reviewed`? Define before Phase 1 pilot.

---

## Part 5 — Stress Scenarios (3 months out)

1. **DuckDB column rename cascades across 15 migrated specs**. A mart column is renamed (standard refactor). 8 widget-configs across 5 specs contain inline SQL referencing the old name. Deploy fails on those 8 widgets with cryptic binder errors (known production pattern per MEMORY.md). No automated cross-spec SQL reference check exists. Team must grep 30 specs manually.
   Mitigation: M11 (CI lint) should become Phase 3 prerequisite, not optional Phase 2+. Specifically: `validate-sql-references.js` extracts column refs from inline SQL blocks, diffs against mart schema. One-day build prevents hours of grep at 30-dashboard scale.

2. **Auto-captured SQL produces numerically wrong output that passes visual diff**. Health Score capture drops a timezone join condition (ICT/UTC mismatch — known footgun in MEMORY.md). Spec passes schema validation, round-trip deploy succeeds, visual diff looks similar. Wrong KPI numbers ship. Discovered 2 weeks later.
   Mitigation: Phase 1 pilot MUST include numerical correctness check — compare 5 key KPI outputs per captured dashboard against baseline SQL results. D3 pilot gate must add "numerical correctness" criterion, not just "reviewer time <2h" and visual diff.

3. **Mid-Phase-3 format switch after schema already committed**. Phase 0 picks monolith format. Phase 2 deploys 5 dashboards. Phase 3 capture of a 1300-line complex spec becomes unworkable. Team decides to switch to companion file format mid-stream. All 5 Phase 2 specs must be reformatted; parser must support both simultaneously; schema splits. 3-day unplanned rework stops migration.
   Mitigation: C2 must be decided Phase 0 day 1 (30-min decision on one sample enhanced spec, not a multi-day spike). Do NOT start D7 schema implementation until C2 locked. Format choice is not cheaply reversible after 5+ deployed dashboards.

---

## Recommendations

- Phase 0 must add to scope: (1) test markdown-it parser against actual existing specs with Vietnamese chars before committing to markdown tables; (2) confirm staging Metabase environment exists; (3) decide C2 as first day-1 output before schema design begins
- Reclassifications: C4 → M (Phase 2 NFR); C5 → M with default answer (option A); M4 → escalate (spike must test); M5 → escalate (staging env confirmation required); drop M10, M14
- New catalog items: C7 (schema-format ordering constraint), M16 (catalog owner), M17 (git history policy), Q7 (SQL acceptance bar)
- Block Phase 0 until: C2 decided (30 min, day 1) — gates D7 schema design and everything else. No other hard blocks.

---

## Unresolved Questions for User

1. **C2 fast-track**: Can C2 be decided in 30 min by reviewing one existing spec enhanced to ~1000 lines — on Phase 0 day 1, before writing any code?
2. **Staging Metabase**: Does a staging Metabase instance exist and is it configured? M5 migration safety depends on it. If not, Phase 3 requires provisioning one or accepting higher production risk.
3. **SQL acceptance bar (Q7)**: Does auto-captured SQL require engineer sign-off + numerical correctness check before spec tagged `status:reviewed`? Must define before Phase 1 pilot starts.
4. **C4/C5 reclassification**: Agree to drop C4 and C5 from Critical list? Clears Phase 0 scope confusion.
5. **M11 CI lint timing**: Should `validate-sql-references.js` (column name cross-check against mart schema) be built before Phase 3 starts? At 15+ dashboards, column rename grep is the most predictable failure mode.

---

Status: complete
