---
type: Concept
title: Docs topic model
description: docs/ is organized into dynamically-created topics, not a fixed category list; type describes the kind of doc, not its topic.
tags: [pkf, docs, taxonomy]
timestamp: 2026-07-04
---

Referenced by [init](../commands/init.md), [work](../commands/work.md),
[update](../commands/update.md), and [issue-lifecycle](issue-lifecycle.md).
Copy-paste skeleton: [assets/templates/doc.md](../../assets/templates/doc.md).

# Schema

`docs/` is **not** carved into a fixed set of folders — directory layout is producer-defined and
`type` values aren't centrally registered (per the OKF spec, see Citations).

```
docs/
  index.md          # topic map — one line per topic directory
  <topic>/           # e.g. transcription/, ui/, packaging/ — created when a topic first needs one
    index.md         # concepts within this topic
    <slug>.md
```

A **topic** is a subject area that emerged from real work, not a predefined bucket — don't force a
new doc into an existing topic just because a similar one exists; open a new topic directory when
none fits. `docs/index.md` and every `docs/<topic>/index.md` must stay current when topics or
concepts are added/removed/renamed — and the root `pkf/index.md` names the topics on its Docs
line, so a topic add/remove/rename updates that line too (see
[assets/templates/index-root.md](../../assets/templates/index-root.md)).

`docs/` describes **what and why**, not **how the code does it line-by-line**. No function
signatures, no constant tables, no step-by-step pseudocode of an implementation — that's what the
source file is for. A doc's job is to be readable by a human who has never opened the code, while
still pointing precisely at the code (or other material) that realizes it via `sources`.

**Required frontmatter:** `type`, `title`, `description`, `tags`, `created`, `updated` (plus
`version` and, where relevant, `sources`). `created` is set once and never changes; `updated`
bumps on any content change worth noting, together with `version` (integer, starts at 1) — a
cheap, git-independent signal of how much a doc has evolved.

`sources` is an **array**, not a single URI — a doc can point at more than one implementing file
or reference (`sources: [file://path/one, file://path/two]`), unlike OKF's suggested single
`resource` field.

Every doc closes with a **`# Related`** section linking the other concepts (docs or issues) it
connects to — an unlinked, unlinked-to doc is an orphan (see
[validate](../commands/validate.md)).

`type` describes the *kind* of document, not its topic — it's a free string per spec (not
centrally registered; unknown values must be tolerated). Suggested vocabulary, extend freely as
new kinds of knowledge show up:

| Suggested `type` | Describes |
|---|---|
| `Feature` | One user-facing capability: what it does, behavior, edge cases, link to the code file(s) implementing it |
| `Architecture Note` | System structure, component boundaries, data/control flow between parts |
| `Design` | UI/UX layout, visual decisions, interaction states |
| `Data Model` | Data storage shape/schema (files, tables, config formats) |
| `Guide` | End-user how-to, parallel to a README but AI-maintained and OKF-linked |
| `Decision` | A design/technical decision and its rationale (when the *why* matters more than a living doc) — filed via an issue's `# Decision` section or [update](../commands/update.md)'s untargeted mode, never invented ahead of an actual decision |

# Examples

**Which topic does a doc go in?** Whichever topic the *subject matter* belongs to (e.g. a
`Feature` doc about audio transcription goes in `docs/transcription/`, not a generic
`docs/features/`). A `Bug` issue usually doesn't spawn a new doc — fix the code, update the
existing doc in that topic only if documented behavior changed. A `Feature Request`/`Docs Request`
may need a brand-new topic; open one rather than force-fitting into an unrelated existing
directory.

# Citations

1. Directory structure and `type` registration policy — [Open Knowledge Format
   spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/pkf/SPEC.md).
