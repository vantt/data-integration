---
type: Command
title: /pkf status
description: Read-only dashboard of issues grouped by status — waiting states, dependency chains, and stale in-progress work.
tags: [pkf, command, issues, read-only]
timestamp: 2026-07-05
---

Depends on [issue-lifecycle](../concepts/issue-lifecycle.md).

# Schema

**This is the no-argument default** — bare `/pkf` lands here. If the bundle directory doesn't
exist yet, report that and propose [init](init.md) instead of erroring.

Read `issues/index.md` (or scan `issues/*.md` frontmatter if the index is stale) and report
issues grouped by `status`. Beyond the raw grouping, surface what needs whose attention:

- **Waiting on the human:** `review` issues (explain-back to confirm), and open issues whose
  recorded gate verdict is `important — awaiting approval` (the `**Chốt:** gate:` line in
  `# Discussion`, [issue](issue.md) step 5).
- **Ready to work:** open issues with `# Plan` + a recorded `gate: not important — proceed`
  (or recorded approval) — just run [work](work.md).
- **Dependency chains:** for each issue with `blocked_by`, show blockers and their statuses —
  `#9 blocked by #2 (open), #5 (resolved)` — so the actual bottleneck is visible.
- **Staleness:** for `in-progress` issues, show `updated` and the last `# Worklog` date — long
  silence on an in-progress issue is a signal to resume, unblock, or send it back to `open`.

This is read-only — no writes, no validation run needed.
