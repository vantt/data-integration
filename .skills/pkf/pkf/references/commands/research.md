---
type: Command
title: /pkf research [issue] "<topic>"
description: Bounded web-research loop with two ends — unblock the work at hand and enrich docs/; findings compile into docs only with the human's go-ahead.
tags: [pkf, command, research, docs]
timestamp: 2026-07-05
---

Depends on [research](../concepts/research.md) and [issue-lifecycle](../concepts/issue-lifecycle.md).

# Schema

**Research serves two ends at once: unblocking the work at hand, and enriching `docs/` — the
second is what compounds.** Two modes, by whether an issue is involved:

- **Issue-bound** — `/pkf research <issue> "<topic>"` (accept id/slug/filename, same as
  [work](work.md)): findings land in the issue's `# Research`; compiling them into `docs/`
  happens in [work](work.md) with the human's go-ahead.
- **Standalone** — `/pkf research "<topic>"`, no issue: the target *is* `docs/` — findings
  compile into new or updated `docs/<topic>/` concepts (human-approved, step 6), no issue
  required.

**Budget (hard stop, not a suggestion, both modes):** max 3 rounds, max 5 fetched URLs per round.

1. **Scope.** Issue-bound: restate the topic in one sentence against the issue's `# Request`.
   Standalone: restate the topic and name the `docs/` topic(s) it should enrich.
2. **Scan what's known.** Read `docs/index.md` and the target topic's `index.md` + concepts if
   they exist. Write down: what's already covered, and the gaps this research must fill —
   researching what `docs/` already knows is waste.
3. **Research rounds:**
   - **Round 1 — broad:** 3-5 angles/keywords → web search each → pick the best 3-5 URLs by
     relevance/authority/recency → fetch.
   - **Round 2 — gap-fill:** what's still missing or contradictory → ≤5 targeted searches →
     fetch the best 1-3 URLs.
   - **Round 3 — verify (only if sources materially contradict):** one search on the contested
     claim.
   - Budget exhausted with questions unanswered → they go to `# Research`'s Open Questions, not
     extra rounds.
4. **Capture.** For each source worth keeping, file it to `pkf/research/raw/<source-slug>.md`
   per [research](../concepts/research.md)'s frontmatter — never edit a capture after filing.
   **Keep captures reachable:** add each to `research/raw/index.md`; the first research ever
   also creates `research/index.md` + `raw/index.md` and adds a Research line to the root
   `index.md` (an unindexed capture is an orphan the validator flags).
   Large/binary/image-heavy sources: see
   [research-large-sources](../research-large-sources.md) first.
5. **Record findings.**
   - Issue-bound: write `# Research` in the issue (create the section if absent; shape in
     [assets/templates/issue.md](../../assets/templates/issue.md)): key findings each with
     source + confidence, new topic candidates, contradictions, open questions, sources
     captured. `status` stays `open` — research is part of clarifying, not a status of its own.
   - Standalone: draft a **compile proposal** — which `docs/<topic>/` concepts to create or
     update, with which claims, each claim carrying its source + confidence.
6. **Present and wait.** Show rounds run, sources captured, top findings. Then:
   - Issue-bound: offer to compile into `docs/` now (hands off to [work](work.md)) or stop here
     (material stays in `raw/`).
   - Standalone: present the compile proposal; on the human's explicit go-ahead, write/update
     the `docs/<topic>/` concepts — `sources` cites the raw captures and original URLs, an
     updated doc bumps `updated` + `version`, a new topic/concept is wired into its indexes per
     [docs-topics](../concepts/docs-topics.md).
   **Never compile without an explicit go-ahead** — unapproved material stays in `raw/`, raw
   never becomes doctrine on its own.
7. **Log and validate** — research is a mutating flow like any other: bump the issue's
   `updated` (issue-bound), append `**Update**` to `log.md` (topic, sources captured, docs
   compiled if any), validate `--strict` ([validate](validate.md)).

# Examples

Claims without a fetched source don't enter `# Research` — search-result snippets are not
evidence, only fetched content counts.
