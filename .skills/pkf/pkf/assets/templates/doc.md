# Docs concept template

Copy this skeleton for `pkf/docs/<topic>/<slug>.md`. `type` is a free string — suggested
vocabulary and the topic model: [concepts/docs-topics.md](../../references/concepts/docs-topics.md).
Content describes what/why; point `sources` at the implementing code/material instead of
restating it.

Required: `type`, `title`, `description`, `tags`, `created`, `updated`. `created` is set once
and never changes; `updated` bumps on every meaningful change, together with `version`.

```markdown
---
type: Feature | Architecture Note | Design | Data Model | Guide | Decision
title: <name>
description: <one sentence>
tags: [...]
sources: [file://<path/to/code>, file://<path/to/other/relevant/file>]
version: 1
created: 2026-07-04
updated: 2026-07-04
---

← [<topic>](index.md)

<what this is, why it exists, key behavior or decisions — no function signatures, no
step-by-step pseudocode of the implementation>

# Related
- [other-topic/other-slug](../other-topic/other-slug.md)
```

`sources` is an array — a doc can point at more than one implementing file, or more than one
external reference, unlike the single-URI `resource` field OKF suggests by default.

For `type: Decision` specifically, the body follows the same shape as an issue's `# Decision`
section: context, options considered, rejected + why, picked + why, who decided.

`version` starts at 1 and increments by 1 on each meaningful update (same trigger as bumping
`updated`) — a cheap, git-independent signal of how much a doc has evolved and whether it's
changed since it was last read.

`# Related` closes every doc — link the other concepts (docs or issues) this one connects to.
An unlinked, unlinked-to doc is a smell (see the orphan lint in
[validate](../../references/commands/validate.md)).
