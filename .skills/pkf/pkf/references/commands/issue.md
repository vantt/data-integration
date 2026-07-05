---
type: Command
title: /pkf issue "<request>"
description: File a new issue from a human request (or AI observation) — search for duplicates, clarify until the problem is clear, plan with a DoD, gate it; the issue stays open, ready for work.
tags: [pkf, command, issues]
timestamp: 2026-07-05
---

Depends on [issue-lifecycle](../concepts/issue-lifecycle.md). Followed by [work](work.md).

# Schema

**Understand before filing — no issue file is created until the problem is clear.**

1. **Search first.** Scan `issues/index.md` + open issues for the same problem, and `docs/` for
   the topic the request touches. Route by what's found:
   - **Duplicate of an open issue** → don't create a new file; append the new information to
     that issue's `# Discussion` (quoted, dated) and continue there.
   - **Same problem on a resolved issue** (regression / re-request) → file a **new** issue and
     link the old one in `# Related` — never reopen or rewrite closed history.
   - Related-but-distinct issues and docs → collect for step 3's `# Related`.
2. **Clarify until the problem is actually understood.** Discuss with the human — `AskUserQuestion`
   for concrete choices, plain-text interview or a brainstorm pass for open-ended gaps — as many
   rounds as it takes. Only when the problem is clear, move to 3.
3. **Create the issue.** Compute the next `id` (max existing `id` in `pkf/issues/` + 1; start
   at 1 if none). Create `pkf/issues/issue-<id>-<type>-<slug>.md` (see
   [issue-lifecycle](../concepts/issue-lifecycle.md) for the filename rule), `status: open`,
   `# Request` = the request verbatim, dated (a request the AI itself raised from observation is
   labelled `filed by AI from observation` — never dressed up as the human's words),
   `# Discussion` = the clarifying Q&A from step 2, recorded as numbered, dated author entries
   (`### #n — YYYY-MM-DD HH:MM — User/AI`) with agreements bolded `**Chốt:**`
   (format: [issue-lifecycle](../concepts/issue-lifecycle.md)).
   `tags`: as meaningful and specific as possible. **Reference every related document found in
   step 1** — related issues and docs go in `# Related`. Dependencies go in frontmatter
   `blocked_by`/`blocks` (by id, both sides kept consistent) mirrored as `Blocked by:`/`Blocks:`
   links in `# Related` ([issue-lifecycle](../concepts/issue-lifecycle.md)).
4. **Plan against existing knowledge.** Write `# Plan` as a `- [ ]` checklist of concrete steps,
   closed by a `**DoD:**` list (acceptance criteria + how each is verified — the AI drafts it as
   advice, the human confirms at the gate). Stay consistent with the related docs — a plan that
   contradicts a documented `# Decision` must say so explicitly and route through the human.
   **This is where dependencies are decided at filing time:** if planning reveals this work
   waits on another issue, or the request is big enough to split into several issues, create and
   wire them now (`blocked_by`/`blocks` + `# Related` links, both sides) — the AI proposes the
   split and ordering; the gate in step 5 is where the human confirms it.
5. Apply the importance gate ([issue-lifecycle](../concepts/issue-lifecycle.md)) to the plan,
   **its DoD, and any dependency wiring from step 4**: important → wait for the human's
   approval; not important → proceed. **Record the verdict in the issue either way** — a bold
   line in `# Discussion`: `**Chốt:** gate: not important — proceed` or
   `**Chốt:** gate: important — approved by user, YYYY-MM-DD`. [work](work.md)'s readiness
   check relies on this recorded verdict; an unrecorded gate doesn't exist. **The issue stays
   `open`** — `in-progress` is set by [work](work.md) when execution actually starts, not at
   filing.
6. Add the issue as a new top row in the `issues/index.md` table (rows sorted by id descending;
   Mô tả cell = frontmatter `description`, plus a short pending note if any). Log
   `**Creation**`. Validate `--strict`.

# Template

Full skeleton (all sections, most optional): [assets/templates/issue.md](../../assets/templates/issue.md).
Section semantics and the state machine: [issue-lifecycle](../concepts/issue-lifecycle.md).
