---
type: Command
title: /pkf query "<question>"
description: Answer a question by navigating the bundle index-first, without dumping full files.
tags: [pkf, command, read-only]
timestamp: 2026-07-05
---

This is the "before work" side of the skill's coordination role — run it (even informally, not
as a literal slash command) before starting substantial work through *any* tool on this project,
to avoid re-deriving what `pkf/` already knows.

# Schema

1. Start at `pkf/index.md`, follow only the links relevant to the question — frontmatter
   (`type`/`tags`/`description`) as the quick-query layer, bodies for detail.
2. Index navigation not reaching the answer → fall back to Grep: `tags` values, filename tokens
   (`issue-<id>-<type>-<slug>` filenames grep well by id, type, or subject).
3. Check `log.md` and open issues (see [status](status.md)) for "what's changing right now".
4. Answer, citing the concepts used by path. Don't dump whole files.
