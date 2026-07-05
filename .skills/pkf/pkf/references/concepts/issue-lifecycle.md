---
type: Concept
title: Issue lifecycle
description: Issue frontmatter, body sections, the status state machine, and the importance gate shared by every command that touches issues/.
tags: [pkf, issues, workflow]
timestamp: 2026-07-05
---

Referenced by [issue](../commands/issue.md), [research](../commands/research.md),
[work](../commands/work.md), [update](../commands/update.md), and [status](../commands/status.md).
Copy-paste skeleton: [assets/templates/issue.md](../../assets/templates/issue.md).

# Schema

**Frontmatter** (`type`, `id`, `title`, `description`, `tags`, `created`, `updated` all required;
`created` set once, `updated` bumps on any new section or status change):
```yaml
---
type: Bug   # free string — see suggested vocabulary below
id: 7
title: ...
description: one sentence
status: open | in-progress | review | resolved | blocked | wontfix
tags: [...]
blocked_by: [2, 5]   # optional — ids of issues this one waits on; omit when none
blocks: [10]         # optional — ids of issues waiting on this one; omit when none
created: 2026-07-04
updated: 2026-07-04
---
```

**`blocked_by` / `blocks`** (optional, omit when empty) — dependency between issues, by `id`
(the one key that never changes). Machine-readable: [work](../commands/work.md)'s readiness
check refuses to start while any `blocked_by` id isn't `resolved`, and
[status](../commands/status.md) can surface chains. Keep the two sides consistent (A
`blocked_by: [B]` ⇒ B `blocks: [A]`), and mirror each id as a clickable link in `# Related`
for the human reader. An issue truly stuck on a dependency also sets `status: blocked`.

**`type`** is a free string, same policy as every OKF `type` — **suggested vocabulary, not a
fixed enum**; use these when they fit, add project-specific ones when they don't:

| Suggested `type` | Filename token | Typical use |
|---|---|---|
| `Bug` | `bug` | behavior broken vs. documented/expected |
| `Feature Request` | `feature` | new user-facing capability |
| `Enhancement` | `enhancement` | improve an existing behavior (UX, robustness) |
| `Docs Request` | `docs` | write/update documentation |
| `Chore` | `chore` | maintenance, tooling, process (no user-visible change) |
| `Security` | `security` | vulnerability or hardening |
| `Performance` | `perf` | speed/resource problem or target |
| `Question` | `question` | needs an answer/decision, not (yet) a change |

A new type defines its own short kebab token for the filename, kept consistent once chosen.

**`id`** is an integer, assigned once at creation and never changed: `max(existing issue ids in
pkf/issues/) + 1`, starting at 1 if `issues/` has none yet. It drives the filename —
`issues/issue-<id>-<type-token>-<slug>.md`, `<slug>` a short kebab of the title. Id, type, and
subject are all greppable from the filename alone
(e.g. `issue-6-bug-transcript-button-not-enabling.md`).

**`tags`** — as meaningful and specific as possible: the subsystem/topic touched, the surface
(ui, config, api…), the nature of the change. Tags are a retrieval signal, not decoration.

**Body sections are a toolkit, not a checklist.** Which ones appear, and how much each says,
tracks the issue's `type` and actual complexity — never include a section that wouldn't say
anything real. A fresh issue has just `# Request`. Per-type guidance (a `Bug` usually stays thin;
a `Feature Request` is more likely to use the full set; a `Docs Request`'s `# Plan` is often
just "write doc X"; a `Chore`'s center of gravity is usually `# Decision`) lives in
[assets/templates/issue.md](../../assets/templates/issue.md) — this section defines what each
one *means*, not how much of it any given issue needs:

1. `# Request` — the human's ask, verbatim, dated.
2. `# Discussion` — the working minutes (biên bản trao đổi), an **append-only thread** of
   numbered, dated entries:
   ```markdown
   ### #1 — 2026-07-05 09:15 — User
   > their words, verbatim, in a blockquote

   ### #2 — 2026-07-05 09:18 — AI
   Analysis / questions, neutral tone.

   **Chốt:** what both sides agreed in this exchange (bold — scannable).
   ```
   `#n` increments per issue, across **all** numbered entries (`# Discussion` and `# Worklog`
   share one sequence) — a number, once assigned, never changes, so `#3` stays a stable
   reference in later entries and in `# Resolution`. Time is local `HH:MM` from the session
   clock — never invented. One issue, one format for life: issues created before this
   convention keep their original unnumbered `### YYYY-MM-DD — Author` headers (no retrofit,
   new entries in them stay unnumbered too).
   **Quote the human's own words**; if you must summarize, label it `(paraphrased)`. Never edit
   an old entry — changing course means a *new* entry saying what changed and why (supersede,
   don't rewrite; same rule ADRs use).
3. `# Research` (optional) — filled by [research](../commands/research.md) when the issue needs
   external information: findings, new topic candidates, contradictions, open questions, links
   into `pkf/research/raw/`.
4. `# Decision` (optional) — only when the plan involved real alternatives, not a single obvious
   path: context, the options considered, which was rejected and why, which was picked and why,
   and who called it (human — product/business judgment; AI — technical judgment; note which).
   Durable, project-wide decisions also get their own `docs/<topic>/` concept with
   `type: Decision` (see [docs-topics](docs-topics.md)) — [update](../commands/update.md)'s
   untargeted mode is what promotes one there.
5. `# Plan` — the contract: a `- [ ]` checklist of concrete steps (what changes, where), closed
   by a bold `**DoD:**` list — acceptance criteria, each line naming **how it will be verified**
   (test to run, manual check). The AI drafts the DoD as advice; the human confirms it at the
   gate. Content flexes by type — a Bug's DoD is usually "old repro no longer reproduces +
   regression test"; a `Question` may have no DoD at all; one checklist line is a complete plan
   if that's genuinely all. Don't manufacture steps or criteria that aren't real.
   **Mid-execution discoveries:** work that still serves this DoD is *appended*, dated —
   `- [ ] <step> (phát sinh YYYY-MM-DD)` — never rewrite approved lines; if additions change
   scope materially, recross the importance gate. Work outside the DoD → file a new issue
   ([issue](../commands/issue.md)) and link it in `# Related`.
6. `# Worklog` (optional) — progress reports (báo cáo tiến độ) for an issue spanning more than
   one working session: numbered entries in the issue's shared sequence
   (`### #n — YYYY-MM-DD HH:MM`), a few past-tense lines each (did X, found Y, stuck on Z).
   A single-session issue skips this — `# Resolution` suffices.
7. `# Resolution` — the acceptance record (biên bản nghiệm thu): **opens with a plain-language
   restatement** of what was understood and done (the explain-back, scaled to the issue's size),
   then the changelog (links to docs/code touched, date), then **the DoD checked off line by
   line with evidence** (which test ran, its result, what was manually verified) — a resolution
   without evidence isn't a report. Written when `status` becomes `resolved` (or the closing
   note for `blocked`/`wontfix`).
8. `# Related` — **every related document must be referenced**: the docs whose topic this issue
   touches, prior issues on the same subject (including the resolved issue a regression re-files
   — see [issue](../commands/issue.md) step 1), and anything `# Plan` relied on. Every id in
   `blocked_by`/`blocks` appears here as a clickable link with its prefix —
   `- Blocked by: [issue-…](…)` / `- Blocks: [issue-…](…)` (frontmatter holds the
   machine-readable ids; this holds the human-readable links). Closes the file.

## State machine

```
open ──(importance gate)──> in-progress ──work done──> review ──(importance gate)──> resolved
  │
  └──────────────────────────────────────────────────────────────> blocked / wontfix
```

- **open** — filed; being clarified and/or planned (`# Discussion`, `# Research`, `# Plan` all
  happen here — none of them are separate statuses). An issue stays `open` even after its plan
  passes the gate — a filed-but-not-started issue must not read as "being worked on".
- **in-progress** — AI is executing the plan. Set by [work](../commands/work.md) when execution
  actually starts, never at filing time.
- **review** — execution done, `# Resolution` drafted; not yet confirmed.
- **resolved** — confirmed; docs synced.
- **blocked** — can't proceed (external dependency, missing access); note why and on what.
- **wontfix** — deliberately not doing it; note why.

Any status transition (including `blocked`/`wontfix`) also updates the issue's row in the
`issues/index.md` table — the Status cell and the pending note in the Mô tả cell — **in the
same edit that changes the frontmatter `status`**; the index is one flat table, and a
frontmatter status change without the matching index-cell update is a drift bug.

## The importance gate (used twice: `open → in-progress`, `review → resolved`)

Before crossing either gate, classify the issue:

- **Important — stop and wait for the human:** touches money/payment/auth, deletes or overwrites
  data, changes behavior a user can see, architecture-level restructuring, scope is genuinely
  ambiguous, or the human already flagged this issue as sensitive.
- **Not important — state it and cross in the same turn:** small well-scoped fixes, doc-only
  changes, anything already agreed in `# Discussion`. The human still sees the plan/resolution
  before it's final and can interrupt — this isn't silent, just non-blocking.

The human can always force the gate on an issue regardless of the AI's own read — say so when
filing the request, and the AI must honor it.

# Examples

Never delete an issue to "close" it — update `status` and add `# Resolution` instead. History
lives in the issue itself, not just in `log.md`.
