# AGENTS.md - Retail Reactivation Plan Rules

## Scope

These instructions apply only inside `plans/260604-1125-retail-reactivation/`.

This folder is a structured working plan, not a loose notes directory. Preserve the 6-stage flow, source provenance, item lineage, and registry links when adding or editing content.

## Required Reading Order

Before changing files in this plan, read:

1. `00-start-here.md` - current truth, immediate reading route, and cross-cutting warnings.
2. `NAVIGATION.md` - human navigation map for go-through, move-back, and jump-forward reading.
3. `REGISTRY.md` - cross-stage item lineage index.
4. This `AGENTS.md` - contribution rules for AI agents.
5. The target stage `README.md`.
6. Any local template for the item type being created or edited.
7. Any source item named in `from`, `source`, `depends_on`, `spawned_by`, or `moves_to`.

Do not read `archive/` first. Archive is provenance only, not the current source of truth.

## Root Surfaces

| File | Role |
|---|---|
| `00-start-here.md` | Short entrypoint and latest critical truth. |
| `NAVIGATION.md` | Reader map across the whole system. Use this after start-here. |
| `REGISTRY.md` | Machine/human index of canonical items and lineage. |
| `AGENTS.md` | Rules for agents editing the plan. |
| `06-execute/operating-board.md` | Work management board after the reader understands the system. |

Do not recreate navigation content inside `operating-board.md`. The board is for active priorities, decisions, execution checks, and weekly operating rhythm.

## Core Structure

This plan uses a 6-stage workflow:

1. `01-perspectives` - perspectives and lenses that generate hypotheses.
2. `02-understand` - investigations, findings, open questions, current diagnosis.
3. `03-evaluate` - scoring, sequencing, blockers, decision register.
4. `04-opportunities` - candidate actions and data/GTM opportunities, not yet committed.
5. `05-action-plans` - committed plans with owner, timeline, KPI, and execution path.
6. `06-execute` - execution log, KPI tracking, dashboard readiness, learnings, operating board.

Canonical flow:

```text
01-perspectives -> 02-understand -> 03-evaluate -> 04-opportunities -> 05-action-plans -> 06-execute -> 02-understand
```

Do not add major workflow items outside this flow unless the user explicitly asks for a different structure.

## Vocabulary

- `Perspective` = stage-01 container/framing artifact. It groups related lenses.
- `Lens` = actionable thinking unit inside a perspective. A lens must generate hypotheses, investigations, findings, or opportunities.
- `Hypothesis` = testable belief created by a lens, finding, or operator observation.
- `Investigation` = stage-02 work item that tests a hypothesis or resolves an unknown.
- `Finding` = evidence-backed stage-02 conclusion.
- `Question` = unresolved issue tracked in stage 02 or 03.
- `Decision` = stage-03 choice that changes priority, sequencing, or scope.
- `Rubric` = stage-03 reusable scoring/evaluation method.
- `Opportunity` = stage-04 candidate action. It is not yet committed.
- `Action Plan` = stage-05 committed work with owner/timeline/KPI.
- `Execution Item` = stage-06 run/log/KPI/result/learning.
- `Companion` = supporting script/checklist/interview guide. It supports an item but does not replace the canonical item.

Use `Perspective` for the stage/file-level concept and `Lens` for the actionable sub-item.

## File Naming And IDs

Canonical workflow files must use a code-prefix in the filename and the main header.

| Prefix | Type | Stage |
|---|---|---|
| `PERS-###` | perspective artifact | 01 |
| `LENS-###` | lens item inside a perspective | 01 |
| `HYP-###` | hypothesis | 01/02 |
| `FIND-###` | evidence-backed finding | 02 |
| `INV-###` | investigation | 02 |
| `Q-###` | open question register | 02/03 |
| `COMP-###` | companion/checklist/script | any stage |
| `DEC-###` | decision register or decision item | 03 |
| `RUBRIC-###` | evaluation framework | 03 |
| `OPP-###` | opportunity | 04 |
| `PLAN-###` | committed action plan | 05 |
| `EXEC-###` | execution tracker/result/learning | 06 |
| `EXEC-BOARD` | operating board | 06 |

Keep IDs stable once referenced. Do not renumber existing IDs for aesthetics.

Archive and research files do not need code-prefix names unless they become current canonical workflow items.

## Source Of Truth By Content

| Content | Canonical location |
|---|---|
| Entry/current warning | `00-start-here.md` |
| Human navigation | `NAVIGATION.md` |
| Item lineage index | `REGISTRY.md` |
| Current diagnosis / what we currently believe | `02-understand/FIND-000-current-diagnosis.md` |
| Evidence-backed finding | `02-understand/FIND-*.md` |
| Active investigation | `02-understand/INV-*.md` |
| Open business/data question | `02-understand/Q-001-open-questions.md` |
| Strategic decision | `03-evaluate/DEC-001-decision-register.md` |
| Evaluation rubric | `03-evaluate/RUBRIC-001-evaluation-framework.md` |
| Candidate action | `04-opportunities/OPP-*.md` |
| Committed plan | `05-action-plans/PLAN-*.md` |
| KPI/result/execution learning | `06-execute/README.md` |
| Operating board | `06-execute/operating-board.md` |
| Provenance | `archive/`, `research/` |

Do not duplicate full content across stages. Link to the canonical source and summarize only what is needed for navigation.

## Registry Rules

`REGISTRY.md` is the cross-stage index for item lineage. Update it whenever adding, resolving, promoting, dropping, or materially changing a workflow item.

Minimum registry columns:

| ID | Type | Stage | Item | Status | From | Moves To | Canonical Link |
|---|---|---|---|---|---|---|---|

The registry is an index, not the full source of truth. The canonical item remains in its stage file.

Every canonical workflow item must be present in `REGISTRY.md` unless it is intentionally temporary and marked as such in its stage README.

## Registry Backlinks

Use two-way links between registry rows and canonical workflow items.

Every canonical workflow file must link back to its registry entry when that registry row exists:

```md
**Registry:** ITEM-ID -> ../REGISTRY.md#item-id
```

The registry row must link to the canonical item:

```md
| ITEM-ID | ... | canonical -> ./02-understand/example.md#item-id |
```

Backlink scope:

- Canonical workflow items need registry backlinks.
- Stage README files do not need registry backlinks unless they are themselves tracked as a workflow item.
- Companion files, scripts, raw scans, interview guides, checklists, and evidence-only sections do not need registry backlinks.
- Companions must link to their canonical parent item.
- If a section becomes important enough to need its own registry backlink, promote it to a canonical item with its own ID.

## Lineage Rules

Every new canonical workflow item must declare:

- `id`
- `type`
- `stage`
- `status`
- `from`
- `moves_to`
- `canonical_anchor`

Recommended optional fields:

- `depends_on`
- `blocks`
- `spawned_by`
- `spawns`
- `promoted_to`
- `dropped_by`
- `owner`
- `created`
- `updated`

If an item cannot name `from` and `moves_to`, treat it as a note or companion, not a canonical workflow item.

Do not invent lineage. If the source or next step is unclear, write `from: unknown` or `moves_to: pending` and add an explicit open question.

## Transition Semantics

Use these verbs consistently:

| Verb | Meaning |
|---|---|
| `spawns` | A perspective/lens/finding creates a new investigation or opportunity. |
| `informs` | A finding supplies evidence to a decision or scoring step. |
| `blocks` | An unresolved question prevents promotion or execution. |
| `promotes_to` | An opportunity becomes a committed action plan. |
| `executes_as` | A plan is run and tracked in stage 06. |
| `produces` | Execution creates a new finding or learning. |
| `updates` | A result changes diagnosis, decision, opportunity, or plan. |
| `drops` | Evaluation or evidence removes an item from active consideration. |

Default transitions:

```text
Perspective/Lens -> Investigation or Opportunity
Investigation -> Finding or Question
Finding -> Decision or Opportunity
Decision -> Opportunity or Action Plan
Opportunity -> Action Plan or Dropped
Action Plan -> Execution Item
Execution Item -> Finding / Decision update / Plan update
```

## Perspective And Lens Structure

A perspective file is a container. A lens is the actionable unit inside it.

Perspective files should include:

- frontmatter with `id`, `type: perspective`, `stage: 1`, `status`, `source`, and `contains`
- purpose
- when to use
- lens index
- lens sections or links to lens sections

Lens items should include:

- `Lens ID + title`
- `Status`
- `Core question`
- `Framing`
- `Hypotheses`
- `Evidence needed`
- `Spawned items`
- `Implications`
- `Links / moves_to`

Use explicit anchors for important lens sections:

```md
<a id="lens-result-trust"></a>

## LENS-001 - Niem tin vao ket qua
```

## Templates

Use local templates before creating new item formats:

- Stage 02 investigation: `02-understand/_TEMPLATE-INV-investigation.md`
- Stage 04 opportunity: `04-opportunities/_TEMPLATE-OPP-opportunity.md`

Templates are guardrails, not rigid forms. Preserve the minimum contract: identity, lineage, status, source, `from`, `moves_to`, `canonical_anchor`, and the core question/proposed move.

Do not force content to fit a template when the item needs a better shape. Add, remove, rename, or reorder optional sections when that makes the reasoning clearer.

Avoid fake completeness: do not add weak hypotheses, filler findings, or arbitrary three-step plans just because a template has placeholders.

Companion files such as interview scripts, checklists, or raw scans must link back to their canonical item. They do not need full lineage unless they become workflow items themselves.

## Markdown Anchors And Links

Use explicit HTML anchors for important sections that other files will reference:

```md
<a id="finding-retention-leak"></a>

## FIND-002 - Retention leak
```

Prefer links to explicit anchors over auto-generated heading anchors, especially for Vietnamese headings or headings with punctuation.

Good:

```md
[FIND-002 retention leak](./02-understand/FIND-002-retention-leak.md#finding-retention-leak)
```

Avoid relying on renderer-generated anchors for critical lineage links:

```md
[retention leak](./02-understand/FIND-002-retention-leak.md#23-cohort-retention-bang-chung-cua-xo-thung)
```

Relative links must be correct from the file where they appear.

## Status Rules

Use status consistently:

| Status | Meaning |
|---|---|
| `living` | Maintained reference/hub/framework. |
| `open` | Active unresolved investigation/question/decision. |
| `blocked` | Cannot progress without external input or missing data. |
| `mostly-resolved` | Direction is clear, but one small verification remains. |
| `resolved` | Evidence/decision is sufficient for downstream use. |
| `idea` | Candidate opportunity, not yet scored or committed. |
| `evaluating` | Being scored or compared in stage 03. |
| `promoted` | Selected to become or feed a stage-05 plan. |
| `committed` | Action plan is accepted for execution. |
| `tracking` | Being measured in stage 06. |
| `dropped` | Explicitly removed from active path. |

When changing status, update downstream links and registry references if they exist.

## Evidence Discipline

- Put conclusions before detail, but keep caveats visible.
- Separate direct facts, operational inference, and open questions.
- Do not silently flatten contradictions. Name them.
- Keep old wrong numbers only when they are provenance; clearly mark them as superseded.
- When data is soft, say why: missing payment table, stale snapshot, biased cohort, right-censoring, owner confirmation needed, etc.
- Do not promote an opportunity to an action plan if its blocker is still unresolved.

## Update Checklist

When adding or materially editing an item:

1. Confirm the stage and item type.
2. Use the local template if one exists.
3. Add or preserve explicit `id`, `from`, `moves_to`, and `canonical_anchor`.
4. Add an explicit anchor for the item or major section.
5. Link to source items and downstream targets.
6. Update the stage README index.
7. Update `REGISTRY.md`.
8. Update `NAVIGATION.md` only if the reading route changes.
9. Update `FIND-000`, `DEC-001`, `00-start-here.md`, or `06-execute/operating-board.md` if the item changes current truth, decisions, active priorities, or warnings.
10. Check local markdown links.

## Safety And Scope

- Do not move content between stages without preserving provenance links.
- Do not bulk-migrate old files to new lineage format unless explicitly asked.
- Do not treat `04-opportunities` as committed work.
- Do not treat `archive/` as current truth.
- Do not commit PII. Worklists with names/phone numbers stay outside git.
- Keep edits focused on this plan unless the user explicitly asks for cross-plan rules.
