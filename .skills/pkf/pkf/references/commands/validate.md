---
type: Command
title: /pkf validate [path]
description: Run OKF conformance checks and producer lints against a bundle.
resource: file://../../scripts/validate.py
tags: [pkf, command, validation]
timestamp: 2026-07-05
---

# Schema

Run `python <skill-dir>/scripts/validate.py <bundle> --strict`.

**Conformance errors** (spec violations, always fixed): parseable YAML frontmatter on every
concept, non-empty `type` on every concept, reserved files (`index.md`/`log.md`) carry no `type`.

**Producer lints** (`--strict` warnings, fix but not blocking): broken intra-bundle links, links
missing `.md`, orphan concepts unreachable from any `index.md`, missing `title`/`description`.
Consumers must tolerate lint warnings — they are never grounds to reject a bundle.

Every mutating command ([issue](issue.md), [work](work.md), [research](research.md),
[update](update.md), [init](init.md)) ends by running this and fixing every error.
