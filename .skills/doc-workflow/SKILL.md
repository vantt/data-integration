---
name: doc-workflow
description: "Write, rewrite, normalize, or review workflow documentation for any project. Use when Codex needs to explain how a workflow, process, pipeline, or orchestration path works end-to-end, including stages, triggers, owners, tools or skills, events or signals, checkpoints, runtime behavior, data flow, error handling, and diagrams. Trigger on requests like: 'document this workflow', 'make this process guide clearer', 'write a v2 workflow guide', 'explain this pipeline from brief to publish', or 'standardize workflow docs across projects'."
---

# Workflow Documentation

Create workflow documentation that is readable, operationally useful, and consistent across projects.

Read bundled resources as needed:

- Read [`references/outline.md`](references/outline.md) before drafting.
- Read [`references/worked-example.md`](references/worked-example.md) before drafting — concrete anchor for what "good" looks like.
- Read [`references/anti-patterns.md`](references/anti-patterns.md) before drafting — concrete mistakes to avoid.
- Read [`references/consistency-checklist.md`](references/consistency-checklist.md) before finalizing.
- Read [`references/diagram-patterns.md`](references/diagram-patterns.md) when choosing diagrams.
- Reuse [`assets/workflow-guide-template.md`](assets/workflow-guide-template.md) as the default scaffold unless the user asked for a different format.
- Run [`scripts/validate_workflow_doc.py`](scripts/validate_workflow_doc.py) on the final markdown when practical.

## Core Objective

Turn fragmented workflow source material into one document that answers:

1. What the workflow is for.
2. What triggers it.
3. Which stages it passes through.
4. Which actors own each stage.
5. Which tools, skills, or sub-processes are used and when.
6. Which events, signals, gates, checkpoints, or approvals exist.
7. How runtime execution actually works.
8. Where data and artifacts move.
9. How failure, retry, resume, and escalation behave.

## Source Reading Order

Read sources in this order unless the project structure demands a different order:

1. Existing workflow documentation if rewriting
2. Workflow spec or pipeline definition
3. Actor, agent, role, or service definitions referenced by the workflow
4. Skill, tool, or module definitions used in the workflow
5. Runtime, orchestration, hooks, state, or eventing docs
6. Test reports, dry-run reports, incident notes, or implementation reports
7. Representative artifacts from actual runs if available

## Evidence Model

Before drafting, build a compact internal model with three buckets:

- **Direct facts**: explicitly stated in source
- **Operational inferences**: strongly implied by multiple sources
- **Open questions**: contradictions, missing details, or unverified behavior

Reflect this model in the document:

- State direct facts cleanly.
- Mark inferences as interpretations when needed.
- Keep unresolved contradictions visible instead of silently flattening them.

## Output Contract

Default to a document with these sections unless the user wants a smaller format:

1. Title
2. TL;DR
3. Identity card or overview table
4. Workflow map or high-level flow
5. Trigger and input conditions
6. Actor and tool or skill map
7. Stage-by-stage breakdown
8. Runtime mechanics
9. Signals, gates, checkpoints
10. Data flow and storage zones
11. Failure, retry, and escalation paths
12. Common misunderstandings or reading notes
13. Quick reference or cheat sheet
14. Open questions when source material conflicts
15. Conclusion

Prefer tables for:

- stage summaries
- actor to tool/skill mapping
- signal summaries
- gate ownership
- checkpoint mapping
- error decision matrix

## Diagram Minimum

Include at least three Mermaid diagrams for a standard workflow guide:

1. A high-level flowchart of the main path
2. A sequence diagram or actor handoff diagram
3. A state, retry, decision, or data-flow diagram

If the workflow is complex, prefer four diagrams:

- overview flow
- sequence flow
- state or retry loop
- data or artifact flow

Do not add diagrams that only repeat tables with less clarity.

## Consistency Rules

Follow these rules strictly:

1. Separate **spec behavior** from **observed runtime behavior** when they differ.
2. Do not invent missing emitters, approvals, or fallback paths.
3. If workflow, actor, and tool docs conflict, name the conflict explicitly.
4. Keep `rigor` and `dry_run` separate. Do not treat review depth and side effects as the same concept.
5. Distinguish self-checks from official blocking gates.
6. Distinguish internal logs from external signals if the source is ambiguous.
7. If a stage depends on a required adapter, service, or tool, document the unavailable-path behavior.
8. If a checkpoint exists, say what it saves and what stage resume continues from.

## Rewrite Mode

When rewriting an existing workflow document:

1. Preserve useful concrete detail from the old document.
2. Improve scanability before adding more detail.
3. Remove repeated explanations that do not improve understanding.
4. Normalize terminology across sections.
5. Add a short change summary at the end or in the assistant response.

## Compression Rules

When the source is large, compress aggressively around these priorities:

- keep stage ownership
- keep gate behavior
- keep signal/checkpoint behavior
- keep failure paths
- keep diagrams

Drop low-value prose before dropping operational detail.

## Final Check

Before finishing:

- Ensure the document can be read top-down by a newcomer.
- Ensure a maintainer can use it to debug a stuck run.
- Ensure contradictions are visible.
- Ensure diagrams and tables tell the same story.
- Compare your draft against `references/worked-example.md` section-by-section.
- Verify you did not fall into any trap in `references/anti-patterns.md`.
- Run the validator script when practical.
