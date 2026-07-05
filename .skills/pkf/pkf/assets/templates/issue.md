# Issue template

Sections below are a **toolkit, not a checklist** — which ones appear, and how much each says,
should track the issue's `type` and actual complexity. Never include a section that wouldn't say
anything real. Section semantics and the state machine:
[concepts/issue-lifecycle.md](../../references/concepts/issue-lifecycle.md).

Required frontmatter: `type`, `id`, `title`, `description`, `status`, `tags`, `created`, `updated`.
`id` is an integer assigned once at creation (next = highest existing issue `id` in `pkf/issues/`
+ 1, starting at 1 if none exist) and never changes; it drives the filename:
`issues/issue-<id>-<type>-<slug>.md` (`<type>` token: `bug`/`feature`/`docs`/`chore`). `tags`
are a retrieval signal — as meaningful and specific as possible. `created` is set once and never
changes; `updated` bumps whenever the issue gains a new section or its status changes. Every
issue starts with just this + `# Request`:

```markdown
---
type: <Bug | Feature Request | Enhancement | Docs Request | Chore | Security | Performance | Question | project-specific>
id: <n>
title: <short title>
description: <one sentence>
status: open
tags: [...]
blocked_by: [<id>, …]   # optional — omit when none; mirror as links in # Related
blocks: [<id>, …]       # optional — omit when none; mirror as links in # Related
created: 2026-07-04
updated: 2026-07-04
---

← [issues](index.md)

# Request

<human's ask, verbatim, dated — or labelled `filed by AI from observation` when the AI raised it>
```

Filename: `issues/issue-<n>-<type>-<slug>.md` (e.g. `id: 7`, Feature Request, slug
`auto-fill-mp3-path` → `issues/issue-7-feature-auto-fill-mp3-path.md`). The slug is a short
kebab of the title — the type token already carries the kind, don't repeat it in the slug.

## How much of the rest to use, by type

- **Bug** — usually thin: short `# Discussion` (repro details) → one-line `# Plan` ("fix X in
  `file.py`") → short `# Resolution`. Skip `# Research`/`# Decision` unless the fix genuinely
  involves a real trade-off or something that needed looking up.
- **Feature Request** — the fuller toolkit is more likely to earn its keep: `# Discussion` to
  scope it, `# Research` if it needs outside information, `# Decision` if there were real
  alternatives, a substantive `# Plan`, a `# Resolution` with a real explain-back.
- **Docs Request** — `# Plan` is often just "write/update `docs/<topic>/<slug>.md`" — don't pad
  it into steps that don't exist. `# Resolution` just confirms the doc landed and links it.
- **Chore** (refactor, cleanup, maintenance) — `# Decision` is frequently the section that
  matters most here (why restructure this way and not that way); `# Discussion` can be thin if
  the human's ask was already precise.

If none of these fit, use judgment — the point is matching the issue, not matching a category.

## Section reference

Full semantics live in [issue-lifecycle](../../references/concepts/issue-lifecycle.md); shapes:

- `# Discussion` — append-only numbered entries (`#n` per issue, shared sequence with
  `# Worklog`; local HH:MM); quote the human verbatim, close agreements with a bold `**Chốt:**`
  line; never edit old entries — supersede with a new one:
  ```markdown
  ### #1 — 2026-07-05 09:15 — User
  > nguyên văn lời user

  ### #2 — 2026-07-05 09:18 — AI
  Phân tích / câu hỏi.

  **Chốt:** điều đã thống nhất.
  ```
- `# Research` — only when [research](../../references/commands/research.md) actually ran:
  key findings, new topic candidates, contradictions, open questions, sources captured.
- `# Decision` — only when real alternatives were weighed: context, options considered,
  rejected + why, picked + why, who decided (human or AI).
- `# Plan` — checklist + DoD; append discoveries dated, never rewrite approved lines:
  ```markdown
  - [ ] concrete step (file, expected behavior)
  - [ ] step discovered mid-work (phát sinh 2026-07-05)

  **DoD:**
  - [ ] acceptance criterion (verify: which test / manual check)
  ```
- `# Worklog` — only for multi-session issues: `### #n — YYYY-MM-DD HH:MM` (same sequence as
  `# Discussion`) + a few past-tense lines per session.
- `# Resolution` — explain-back first (plain language: what was understood and done, and why),
  then the changelog, then the DoD checked off with evidence:
  ```markdown
  Touched:
  - [docs/<topic>/<slug>](../docs/<topic>/<slug>.md)
  - `<code file>`

  **DoD:**
  - [x] criterion — evidence (pytest 32/32 pass; manual check …)
  ```
  Scale the explain-back to the issue's size — a one-line fix doesn't need a paragraph restating
  the obvious.
- `# Related` — every related issue/doc referenced; dependencies with semantic prefixes
  `- Blocked by: […]` / `- Blocks: […]`. Omit only if there's truly nothing.
