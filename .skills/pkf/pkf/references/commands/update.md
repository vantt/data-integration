---
type: Command
title: /pkf update [path]
description: Reconcile a named doc/code drift, or — with no specific target — auto-extract an insight or decision from the current conversation and file it.
tags: [pkf, command, docs, maintenance]
timestamp: 2026-07-05
---

Depends on [docs-topics](../concepts/docs-topics.md) and
[issue-lifecycle](../concepts/issue-lifecycle.md). See [issue](issue.md) for anything bigger
than a small reconciliation.

This is the "after work" side of the skill's coordination role: the way knowledge compounds
regardless of which tool did the actual work — a fix landed via another skill, a decision made
in plain conversation, a plan executed outside `pkf/issues/` entirely. `pkf/` doesn't need to
have run the work to learn from it.

# Schema

**Mode 1 — targeted** (a path, doc, or drift is named): reality (code) has drifted from `docs/`
without an issue driving it. Update the affected `docs/<topic>/` concept, bump its `updated` date
and `version`, log `**Fix**` in `log.md`. Validate `--strict`.

**Mode 2 — untargeted** (bare `/pkf update`, or "lưu lại", "ghi nhớ cái này", "save this" with no
specific file/path named): read back the current conversation and extract what's worth keeping.

1. Classify what happened:
   - **A decision** (real alternatives were weighed) → if there's an open issue this belongs to,
     append `# Decision` to it plus a `# Discussion` entry (next `#n` in the issue's sequence)
     with the `**Chốt:**` line (keep the minutes contiguous —
     [issue-lifecycle](../concepts/issue-lifecycle.md));
     otherwise create/update a `docs/<topic>/` concept with `type: Decision` (context, options,
     rejected/picked and why, who called it).
   - **An insight/fact** (new understanding, no alternatives weighed) → find the fitting
     `docs/<topic>/` concept and update it, or open a new topic if none fits (never force it into
     an unrelated one — see [docs-topics](../concepts/docs-topics.md)).
2. Apply the importance gate ([issue-lifecycle](../concepts/issue-lifecycle.md)): substantial
   (changes a prior decision, touches multiple topics, or you're unsure) → state what you're
   about to file and wait; small/uncontroversial → file it and say so in the same turn.
3. Update `docs/index.md` / the topic's `index.md` if a topic or concept was added; if a topic
   was added/removed/renamed, update the topic names on the root `index.md` Docs line
   ([index-root template](../../assets/templates/index-root.md)). Log
   `**Creation**`/`**Update**` in `log.md`. Validate `--strict`.

If the drift or insight is substantial enough to need discussion and a plan of its own, prefer
filing an issue instead ([issue](issue.md)) — `update` (either mode) is for reconciliation that
doesn't need the full issue lifecycle.
