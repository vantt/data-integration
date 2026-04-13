# Consistency Checklist

Use this before finalizing a workflow document.

## Fact Discipline

- [ ] Every major claim is traceable to a source file or multiple consistent sources
- [ ] Inferences are not presented as guaranteed facts
- [ ] Contradictions are named explicitly
- [ ] Spec behavior and observed runtime behavior are separated when needed

## Workflow Structure

- [ ] Trigger path is documented
- [ ] Stage order is clear
- [ ] Stage owner is named for every stage
- [ ] Inputs and outputs are documented for every important stage
- [ ] Loop conditions and exit conditions are visible

## Control Surface

- [ ] Blocking gates are called out explicitly
- [ ] Self-checks are not mislabeled as official gates
- [ ] Signals are distinguished from internal logs
- [ ] Checkpoints include save point and resume point
- [ ] Approval boundaries are clear

## Runtime Reality

- [ ] Runtime, adapters, or hooks are explained if they materially affect execution
- [ ] Unavailable dependency paths are documented when relevant
- [ ] `dry_run` behavior is separate from `rigor`
- [ ] Real side effects vs. test behavior are clear

## Readability

- [ ] Document starts with a short mental model
- [ ] TL;DR contains a single-line path string using `->`
- [ ] Tables are used where scanning is better than prose
- [ ] At least three useful diagrams are included for a standard guide
- [ ] Repetition is trimmed
- [ ] Terms are used consistently

## Layer Separation

- [ ] Document separates **business flow** from **runtime flow** (and from **data flow**) when the project has an adapter layer
- [ ] Reader can tell which parts of the document describe the workflow spec vs the runtime that executes it
- [ ] At least one sequence diagram has a participant representing run state / artifacts / filesystem, not only actors
- [ ] Spec-level signals are distinguished from runtime-level signals when the source is ambiguous

## Common Misunderstandings Section

- [ ] Contains at least 3 entries
- [ ] Each entry is a pair of concepts that are commonly conflated
- [ ] Each entry explains the operational consequence of confusing them

## Quick Reading Checklist Section

- [ ] Contains an ordered list (5–10 steps) for diagnosing a stuck run
- [ ] Points at concrete files, fields, or artifacts (not theory)

## Conclusion

- [ ] Ends with a single quoted sentence capturing the workflow's purpose
- [ ] The sentence is under 200 characters
- [ ] Does not re-summarize all sections
