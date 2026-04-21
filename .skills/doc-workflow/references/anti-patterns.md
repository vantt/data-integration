# Workflow Documentation Anti-Patterns

Concrete mistakes that pass structural validation but produce low-value workflow docs. Avoid these when writing or rewriting a guide.

## 1. Opening with a Mega-Diagram

**Symptom:** Section 1 or 2 leads with a 9-stage flowchart containing every branch, checkpoint, signal and escalation path.

**Why it's bad:** First-time reader has no mental model to attach the diagram to. Overview diagrams must come after a 3–6 bullet TL;DR and a single-line path string.

**Fix:** TL;DR first. Path string second. Overview diagram third — and keep it simple. Save the full branching diagram for the stage-by-stage section.

## 2. Drawing an Abstract "Signal Bus" in Sequence Diagrams

**Symptom:** Sequence diagram has a participant named `SB` or `Signal Bus` or `Event Bus` with no corresponding runtime artifact in the project.

**Why it's bad:** Invents infrastructure. In most marketing/orchestration frameworks, signals are contract-level concepts emitted by agents and consumed by orchestrators — there is no bus process.

**Fix:** Use concrete participants: `Run State`, `Artifacts`, `FS`, or name the actual orchestrator. Let the reader see *where state is written*, not an imagined message broker.

## 3. Treating the Workflow File as the Engine

**Symptom:** Document describes the workflow file as if it dispatches agents, saves checkpoints, and emits signals.

**Why it's bad:** In fgOS and similar frameworks the workflow file is a *spec*. The adapter/runtime is what dispatches. Readers who believe the workflow file is the engine cannot debug a real run.

**Fix:** Add an explicit section distinguishing **spec** (what the workflow file says should happen) from **runtime** (adapter/hooks that actually execute). Use it to explain signals, checkpoints, and dispatch.

## 4. Flattening Source Contradictions

**Symptom:** Document picks one version of a disputed fact (e.g. signal emitter, gate ownership) and presents it as the canonical answer, without mentioning that the source material disagreed.

**Why it's bad:** Readers lose the ability to detect when source documents have drifted. Bugs that come from misalignment between workflow/agent/skill specs become invisible.

**Fix:** Name the conflict explicitly. State which sources disagree. Give an operational reading that works regardless of the disagreement.

## 5. Listing Payloads Without Consumers

**Symptom:** Signal table gives detailed payloads like `{content_id, version, word_count, draft_url}` but never says who consumes them.

**Why it's bad:** Payloads are useful only to downstream consumers. Without a consumer, the payload is decoration.

**Fix:** For every signal, document emitter *and* primary consumer(s). If the consumer is "orchestrator internal", say so. If it's a downstream workflow, name the workflow.

## 6. Conflating `rigor` with `dry_run`

**Symptom:** Matrix mixes review depth and side-effect control into a single dimension.

**Why it's bad:** `rigor` controls *how deeply* gates and reviews run. `dry_run` controls *whether side effects reach real systems*. A run can be `critical + dry_run=true` and that is a legitimate, useful combination.

**Fix:** Document them as orthogonal axes. A 2D table with rigor levels as rows and dry_run as columns is fine; merging them is not.

## 7. Treating Self-Check as an Official Gate

**Symptom:** The document calls a creator's self-review a "gate" and puts it in the gate table.

**Why it's bad:** Official gates block workflow progress. Self-checks help the creator ship cleaner output but cannot block. Mixing them makes the gate table lie about what actually stops a run.

**Fix:** Keep a separate column or note for self-checks. Official gates are only: blocking, owned by a non-creator agent, and have a documented fail path.

## 8. Missing the Unavailable-Adapter Path

**Symptom:** Document describes the mandatory gate but not what happens if the handler cannot be dispatched (service down, agent unavailable, adapter missing).

**Why it's bad:** This is where real runs get stuck. Without the unavailable path, operators resort to workarounds that bypass the gate.

**Fix:** Document explicitly: "If `brand-guardian` cannot dispatch → workflow BLOCKS with `NEEDS_CONTEXT`. Orchestrator MUST NOT impersonate the guardian." Same pattern for any mandatory external dependency.

## 9. Cheat Sheet That Restates the TL;DR

**Symptom:** Cheat sheet and TL;DR contain the same information at the same level of abstraction.

**Why it's bad:** Cheat sheet should help an operator diagnose a stuck run *right now*. TL;DR builds a mental model for a new reader. They serve different audiences.

**Fix:** Cheat sheet must point at concrete fields, file paths, commands, and artifact locations. Questions it answers: "Where is the checkpoint file?" "How do I resume?" "Which gate blocked my run?"

## 10. Conclusion That Summarizes Everything

**Symptom:** Conclusion section re-lists all major sections in 2–3 sentences each.

**Why it's bad:** Readers who reached the conclusion already read the document. They need a take-home message, not a recap.

**Fix:** One quoted sentence under 200 characters that captures why the workflow exists. Example: *"This workflow exists to turn a brief into a content asset whose quality, brand, and side effects are controlled before it reaches the outside world."*
