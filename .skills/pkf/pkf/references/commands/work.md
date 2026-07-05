---
type: Command
title: /pkf work [issue-slug]
description: Pick an open issue (or take the given one), load its full context, verify it's ready, execute its Plan, verify the DoD line by line, draft the explain-back Resolution, cross the gate, sync docs and log.
tags: [pkf, command, issues, docs]
timestamp: 2026-07-05
---

Depends on [issue-lifecycle](../concepts/issue-lifecycle.md) and
[docs-topics](../concepts/docs-topics.md). Follows [issue](issue.md) and, if used,
[research](research.md).

# Schema

**Select & load context — no execution until the issue is understood.**

1. **Pick the issue.** Accept an id (`work 6`), a slug, or a filename. Nothing given → list the
   open issues from `issues/index.md` (id, type, one-line description, status) and ask the user
   which to work on (`AskUserQuestion`).
2. **Load the full context.** Read the issue end to end — every section, including `# Worklog`
   if present — then everything it references: the docs and issues in `# Related`, the relevant
   `docs/<topic>/` concepts. Skim `log.md` for anything that changed since the plan was written:
   the plan was approved against that day's reality, so verify it still holds.
3. **Readiness check.** The issue is workable only if: `# Plan` + DoD exist and the gate verdict
   is **recorded** as a `**Chốt:**` line in `# Discussion` ([issue](issue.md) step 5 — an
   unrecorded gate doesn't exist; important issues need the recorded approval); every issue id
   in frontmatter `blocked_by` is `resolved`; the plan still matches current code/docs. Anything missing → **don't start**: discuss with the user and route to the
   lifecycle flow that fits — no/unclear plan → the [issue](issue.md) clarify/plan steps;
   missing information → [research](research.md); a blocking dependency → `status: blocked`
   (note on what). Record the detour as a `# Discussion` entry (next `#n` in the issue's
   sequence).
4. **Start.** Only once context is sufficient and the request is clearly understood, set
   `status: in-progress` — this is the only place that transition happens. Resuming an issue
   already `in-progress` → continue from the last `# Worklog` entry instead of starting over.
5. Execute: write/edit code, and/or create-or-update the relevant `docs/<topic>/` concepts (new
   topic directory + `index.md` if none of the existing ones fit the subject matter). **Tick off
   each `# Plan` checklist item (`- [x]`) as it lands.** Discovered work that still serves the
   DoD → append a dated `- [ ] … (phát sinh YYYY-MM-DD)` line (scope changed materially →
   recross the gate); outside the DoD → file a new issue and **decide the relationship on the
   spot**: this issue can't reach its DoD without the new one → the new issue blocks it
   (`blocked_by` here / `blocks` there; if work must stop, `status: blocked` and surface the
   user), a mere follow-up → a plain `# Related` link and this work continues. Keep docs
   at the PM level (no code-detail regression) — see [docs-topics](../concepts/docs-topics.md).
   Updating an existing doc bumps its `updated` date and `version`; a new doc starts at
   `version: 1`, `created` = `updated` = today.
   If `# Research` exists, cite the `pkf/research/raw/` captures a claim came from; this is the
   only point where raw material may become a doc, and only with the human's go-ahead from
   [research](research.md) step 6.
6. **Verify the DoD line by line**, each by the method its line names (test run, manual check),
   plus the project's own tests/checks for anything code touched — an issue isn't done because
   a doc was written, it's done because every DoD line demonstrably holds.
7. Write `# Resolution`: **explain-back paragraph first** (plain language — what you understood
   and did), *then* the changelog (what changed, links to docs/code, date), *then* **the DoD
   checked off line by line with evidence** (which test ran, its result, what was manually
   verified — step 6's output goes here). Set `status: review`.
8. Apply the importance gate ([issue-lifecycle](../concepts/issue-lifecycle.md)): important →
   wait for the human to confirm or correct the explain-back, folding any correction into
   `# Resolution` verbatim — steps 9-10 do not run until that confirmation lands; not important →
   present it and set `status: resolved` in the same turn, then continue immediately to 9-10.
9. Once `status` is `resolved`: update the issue's row in the `issues/index.md` table — Status
   cell → `resolved`, drop any pending note from the Mô tả cell (the cell stays the frontmatter
   `description`; the Ngày tạo cell never changes; rows never move). **Release the dependents:** scan issues whose `blocked_by`
   contains this id — tell the user which are now unblocked, and clear their `status: blocked`
   (back to `open`) when this was their only blocker. Update `docs/index.md` (and the topic's own `index.md`) if
   a topic or concept was added; a topic added/removed/renamed also updates the topic names on
   the root `index.md` Docs line ([index-root template](../../assets/templates/index-root.md)).
10. Append `**Update**` (or `**Creation**`/`**Fix**` as fits) to `log.md`, linking the issue and
    the docs it touched. Validate `--strict`; fix; offer [viz](viz.md).

**Ending a session early:** whenever work stops before `review`/`resolved` — context running
out, the user pausing, a blocker — append a `# Worklog` entry first (next `#n` in the issue's
sequence: what was done, what's in flight, the next step). An interrupted session that leaves
no trace costs the next session its whole start.

If new information surfaces mid-work that invalidates the plan, don't push through — set
`status: blocked` or back to `open` (note why in `# Discussion`), and surface it to the human.

# Template

The `# Resolution` shape is part of the full issue skeleton:
[assets/templates/issue.md](../../assets/templates/issue.md). Doc concepts created/updated here
follow [assets/templates/doc.md](../../assets/templates/doc.md).
