# Standard Workflow Guide Outline

Use this outline as the default structure for workflow documentation.

## Full Version

1. `# Title`
2. `## 1. Purpose` or `## 1. Muc tieu`
3. `## 2. TL;DR`
4. `## 3. Identity Card` or overview table
5. `## 4. Workflow Map`
6. `## 5. Trigger and Inputs`
7. `## 6. Actors and Tools/Skills`
8. `## 7. Stage-by-Stage`
9. `## 8. Runtime Mechanics`
10. `## 9. Signals, Gates, Checkpoints`
11. `## 10. Data Flow`
12. `## 11. Failure, Retry, Escalation`
13. `## 12. Common Misunderstandings`
14. `## 13. Quick Reading Checklist`
15. `## 14. Cheat Sheet`
16. `## 15. Open Questions`
17. `## 16. Conclusion`

## Minimal Version

Use this only when the workflow is small:

1. TL;DR
2. High-level flow
3. Stage table
4. Runtime and data notes
5. Failure paths

## Section Intent

| Section | Why it exists |
|---|---|
| TL;DR | Give the shortest accurate mental model |
| Identity Card | Expose type, trigger, retries, rollback, rigor, dry-run |
| Workflow Map | Show the main path before details |
| Actors and Tools/Skills | Show who does what |
| Stage-by-Stage | Operational detail |
| Runtime Mechanics | Explain how execution really happens |
| Signals/Gates/Checkpoints | Show control boundaries |
| Data Flow | Show file, artifact, and storage movement |
| Failure/Retry/Escalation | Show recovery behavior |
| Common Misunderstandings | Prevent bad readings |
| Cheat Sheet | Help future operators debug faster |

## Ordering Rule

Put overview before detail and business flow before runtime detail.

## Hard Rules for Specific Sections

These rules are not optional. Validator enforces what it can; the rest depends on author discipline.

### TL;DR (section 2)

- Must contain a single-line path string using `->` (e.g. `Trigger -> Draft -> Review -> Gate -> Publish`).
- Must fit within ~10 bullets. No mega-diagrams here.

### Workflow Map (section 4)

- Must be preceded by a short explicit statement separating **business flow** from **runtime flow** when the project has an adapter/runtime layer.
- Reader should not leave this section thinking the workflow file is the engine.

### Stage-by-Stage (section 7)

- Must have a single summary table covering: Stage, Owner, Skill, Input, Output, Gate, Checkpoint, Signal, Transition.
- Per-stage subsections are optional but must not duplicate the summary table verbatim — add operational detail only.

### Runtime Mechanics (section 8)

- Must state plainly what the workflow file IS vs what the runtime/adapter IS, if they are separate artifacts.
- Must include at least one diagram or paragraph showing the dispatch → hook → checkpoint → signal cycle.

### Signals, Gates, Checkpoints (section 9)

- Must separate **spec-level signals** (defined in workflow contract) from **runtime-level signals** (actually persisted/consumed) if the source shows ambiguity.
- Must include a path where a mandatory gate has no available handler (unavailable-adapter path).

### Common Misunderstandings (section 12)

- Must have at least 3 entries.
- Each entry must be a pair of concepts that look similar but are not (e.g. `rigor ≠ dry_run`, `review gate ≠ brand gate`, `self-check ≠ official gate`).
- Explain why confusing them causes real operational harm.

### Quick Reading Checklist (section 13)

- Must be an ordered list (5–10 steps) that a human can follow to diagnose a stuck run top-down.
- Not a theory section. Must point at concrete artifacts, fields, or files.

### Conclusion (section 16)

- Must end with a single quoted sentence that captures the workflow's reason to exist.
- No new information. No summary of all sections. One sentence, under 200 characters.
