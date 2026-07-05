---
type: PRD
title: pkf design PRD
description: The governing requirements for this skill — problem, goals, non-goals, and the 11 requirements every command/behavior must satisfy. Check against this before changing the skill.
tags: [pkf, philosophy, prd, design]
timestamp: 2026-07-04
---

**This is the skill's PRD, not a retrospective** — the document to check *before* adding or
changing a command, template, or behavior, not just an explanation written after the fact. If a
proposed change conflicts with a requirement below, that's a signal to either reject the change
or deliberately amend this PRD (via [update](commands/update.md), with the reasoning recorded) —
never let the skill's actual behavior silently drift away from what this file says it does. A PRD
that stops matching the system it governs is exactly the kind of dishonesty
[docs-topics](concepts/docs-topics.md) warns against.

# Problem

Before this design: AI-assisted project knowledge either evaporated between sessions (each
session re-derives context from scratch, RAG-style) or accumulated one-sidedly (the AI wrote
docs the AI would read back, with no real human authorship or correction loop). Neither compounds
into something a team — human and AI together — actually gets smarter from over time.

# Goals

- Project knowledge **compounds** across sessions and across which tool did the work.
- Knowledge creation is **bidirectional** — humans read, correct, and contribute, not just
  approve AI output.
- The system **coordinates** with existing skills/workflows instead of requiring everything to
  go through it.
- Oversight is **proportional** — real friction only where risk is real.
- Everything recorded is **honest and reversible** — no invented facts, no erased history.

# Non-goals

- **Not a replacement** for other skills, `plans/`, or project `docs/` — it complements them.
- **Not a mandatory front door** — `pkf/issues/` is optional structured scaffolding, not a gate
  every task must pass through.
- **Not a RAG index** — it doesn't re-derive answers each query; it accumulates durable concepts.
- **Not a rigid form** — templates are a toolkit; unused sections should not exist just to fill a
  shape.
- **Not an unbounded agent** — research and auto-capture work have hard stopping rules, never
  open-ended loops.

# Requirements

Every tenet below traces to a real decision made while building this skill, not invented after
the fact — and every future change to the skill should be checked against it.

**1. Compounding, not consuming.** pkf is a knowledge base that grows with use — every issue
resolved, every research pass, every decision becomes durable in `docs/` and `log.md` — unlike
RAG, which re-derives answers from scratch each time. `version`/`updated` on every doc concept
exist so "has this changed since I last read it" is a cheap check, not a re-read.

**2. Coordinate, don't gatekeep.** pkf never replaces another skill or workflow. It has exactly
two touchpoints regardless of which tool does the actual work: consult `docs/`/open `issues/`
*before* substantial work, fold learnings back via [update](commands/update.md) or a full
[issue](commands/issue.md) *after*. `pkf/issues/` is optional structured scaffolding for work
that benefits from discuss→plan→execute→review — not a mandatory front door for everything in
the project.

**3. Knowledge flows both ways.** The system was explicitly redesigned away from "AI writes docs
for AI to read." `# Discussion` quotes the human's own words rather than the AI's paraphrase
(labelling it when it must summarize); every `# Resolution` opens with an explain-back the human
can correct, not just a changelog to rubber-stamp.

**4. Judgment-gated, not rubber-stamped or bureaucratic.** The
[importance gate](concepts/issue-lifecycle.md) is crossed twice — before starting, before
closing — and draws a real line: money, data loss, user-visible behavior, architecture, or
ambiguous scope stops for a human; everything else proceeds visibly but without blocking. Gating
everything makes the system too slow to use; gating nothing makes oversight theater.

**5. Toolkit, not checklist.** Sections in the [issue template](../assets/templates/issue.md)
are a menu, not a mandatory form — a `Bug` can be three lines; a `Feature Request` can use the
full `Request → Discussion → Research → Decision → Plan → Worklog → Resolution → Related` arc. Depth
matches the issue's `type` and actual complexity, never habit.

**6. PM-level knowledge, not code detail.** [Docs](concepts/docs-topics.md) describe what/why and
point `sources` at the code — they never restate implementation. This keeps docs short enough to
actually get read, and stops them from breaking on every refactor the way a doc mirroring code
line-by-line would.

**7. Honesty over invention.** Never fabricate a `sources` entry, a date, a description, or a
decision's rationale. [Research](concepts/research.md) captures are immutable and kept in
`pkf/research/raw/`, separate from compiled `docs/` — a human approves before raw material
becomes doctrine.

**8. Bounded work is trustworthy work.** The research loop has a hard budget (max 3 rounds, max 5
URLs/round); exceeding it routes to "open questions," never to more rounds. A loop nobody can
predict the cost or stopping point of erodes trust before it produces anything.

**9. Format over platform.** Plain Markdown + YAML frontmatter, OKF v0.1 conformant,
git-versionable — no database, no proprietary schema, no lock-in. `validate.py`/`visualize.py`
are pure stdlib + PyYAML: auditable, not a black box.

**10. Progressive disclosure, always.** `SKILL.md` stays short; command flows live in
`references/commands/`, shared rules in `references/concepts/`, copy-paste skeletons in
`assets/templates/` — loaded only when the matching command actually runs. This mirrors the
[Agent Skills](https://agentskills.io/specification) three-tier loading model this skill itself
follows.

**11. Reversible history, not silent overwrites.** An issue is never deleted to "close" it — only
status-updated with a `# Resolution` appended. `log.md` is append-only, newest-first; historical
links may dangle and are exempt from the link check rather than force-rewritten.
[Decisions](concepts/issue-lifecycle.md) record what was rejected and why, not just what won —
losing that is losing half the knowledge.

# How this PRD governs changes

Before adding a command, changing a template, or altering a workflow in this skill:
1. Check the change against **Goals** and **Non-goals** above — does it still coordinate rather
   than gatekeep, still stay bounded, still keep the human as a real author?
2. Check it against the specific **Requirement** it touches most.
3. If it conflicts, either the change is wrong, or the requirement is outdated — in the latter
   case, update this file explicitly (with the reasoning, like a `# Decision`) rather than let
   the skill drift silently out of sync with its own PRD.

# Related

- [SKILL.md](../SKILL.md)
- [PHILOSOPHY.md](../PHILOSOPHY.md) — same content, plain language, for humans
- [concepts/issue-lifecycle](concepts/issue-lifecycle.md)
- [concepts/docs-topics](concepts/docs-topics.md)
- [concepts/research](concepts/research.md)
