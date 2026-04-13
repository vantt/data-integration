# Worked Example

Use this reference when you want a concrete anchor for what "good" looks like, not just rules.

## Gold Example

**File:** `docs/workflow-guides/workflow-content-creation-guide.md` (in the marketing-cockpit project).

This document is the current gold standard for a fgOS workflow guide. When rewriting or reviewing a workflow doc, compare your draft against it.

## What This Example Does Right

### Structure

- Opens with a 9-question "what this document answers" list (section 1) so readers can self-route.
- TL;DR in section 2 contains a single path string: `Brief -> Research -> Draft -> Review -> Revise loop nếu fail -> Brand gate -> Approve -> Publish -> Distribute`.
- Identity Card (2.1) and terminology table (2.2) before any diagrams.
- Overview diagram in 3.1 is intentionally simple. The full branching state machine is deferred to section 7.

### Three-Layer Thinking

Section 3.2 explicitly names three layers — **business flow**, **runtime flow**, **data flow** — and uses them as the organizing principle for the rest of the document:

- Section 6 = business flow (stage-by-stage)
- Section 8 = runtime flow (dispatch, hooks, state protocol)
- Section 10 = data flow (zones, artifacts, dry_run routing)

Readers who only care about one layer can skip the other two.

### Runtime Reality Section

Section 8 opens with: *"fgOS is not a workflow engine running in the background. It is workflow spec + agent spec + skill spec + conventions + runtime contract + adapter implementation."*

This single paragraph prevents the most common misreading: that the workflow file dispatches agents itself.

### Honest About Source Contradictions

Section 9.2 names the contradiction about `content.approved` emitter (workflow frontmatter says one thing, stage description says another, agent doc says a third) and gives a reading strategy instead of flattening. This is the "evidence model" in the skill applied correctly.

### Common Misunderstandings (section 12)

Four concrete pairs:

1. `rigor ≠ dry_run`
2. Review gate ≠ Brand gate
3. Spec-level signal ≠ runtime-level signal
4. Orchestrator ≠ Specialist

Each pair has an operational explanation, not just a definition.

### Quick Reading Checklist (section 13)

8-step ordered list for diagnosing a stuck run. Each step points at a concrete artifact:

- trigger type
- brief completeness
- draft version
- review status
- brand gate status
- nearest checkpoint
- dry_run flag
- output zone location

### Conclusion (section 16)

One quoted sentence:

> *"Workflow này tồn tại để biến một brief thành một content asset đã được kiểm soát về chất lượng, brand, và side effect trước khi đi ra ngoài."*

Nothing more.

## What This Example Could Improve

Not everything in the gold example is perfect. When writing a new guide, consider these gaps:

- Missing `rigor × dry_run` matrix as a 2D table
- Missing error decision diagram (only has a situation → behavior table)
- Missing concrete payload shapes for signals
- Missing "files to read when debugging" list with concrete paths
- Overview diagram does not use color/style to distinguish checkpoints, signals, gates, and escalation
- Per-stage subsections sometimes duplicate the summary table verbatim

A future v3 should add these without losing what v2 got right.

## How to Use This Reference

1. Before drafting a new workflow guide, read this file and skim the gold example.
2. After drafting, compare your draft section-by-section against the gold example.
3. Specifically check: TL;DR path string, three-layer split, runtime reality paragraph, common misunderstandings count, quick reading checklist concreteness, one-sentence conclusion.
4. If your draft is missing any of these, add them before calling the document finished.

## Why a Worked Example Matters

Rules in `SKILL.md` and `outline.md` describe shape. A worked example shows *judgment* — which details to keep, which to drop, how to phrase a contradiction, how to make a cheat sheet operationally useful. LLMs generating documentation without a concrete anchor tend to regress to generic structure even when they follow all stated rules.
