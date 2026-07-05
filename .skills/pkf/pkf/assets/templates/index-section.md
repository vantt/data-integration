# Section index template

Copy for `pkf/issues/index.md`, `pkf/docs/index.md`, or `pkf/docs/<topic>/index.md` — no
frontmatter. **An index exists to route an AI (or human) to the right file from the question
they hold** — every entry gets a one-line description that says *what information lives behind
the link*, dense with the terms a query would use (behaviors, components, error cases, file
names). Distill from the concept's own frontmatter `description` — never invent. **No
statistics** (concept counts, file counts): they carry no retrieval signal.

**No intro prose.** Right under the heading, one backlink to the parent index
(`← [index gốc](../index.md)` / `← [docs](../index.md)`) — nothing else. Philosophy and
maintenance notes live in this skill's references, never in the bundle. List-style entries
(docs indexes) are each prefixed with their `(type)`.

`issues/index.md` — **one flat table**, rows sorted by `id` descending. Every cell mirrors the
issue's own frontmatter (`id`, `title`, `type`, `status`, `created`); the Mô tả cell is the
frontmatter `description` verbatim (one sentence — never a progress narrative; progress lives
in the issue), plus a short pending-state note on non-`resolved` rows (e.g. "chờ repro").
**Invariant: whenever an issue's frontmatter `status` changes, the Status cell of its index row
is updated in the same edit** — a frontmatter/index status mismatch is a drift bug. A status
transition edits the Status cell (and the pending note) in place — rows never move between
sections (see [issue-lifecycle](../../references/concepts/issue-lifecycle.md)):

```markdown
# Issues

← [index gốc](../index.md)

| ID | Tiêu đề | Type | Status | Ngày tạo | Mô tả |
|---|---|---|---|---|---|
| <id> | [<title>](issue-<id>-<type>-<slug>.md) | Bug | open | YYYY-MM-DD | <frontmatter description>; <pending note if any> |
```

`docs/index.md` — the topic map, the **only** place topics carry descriptions (the root index
just names them — see [index-root.md](index-root.md)). A topic's description **summarizes the
information inside it** — the union of its concepts' subjects, not a label ("mp4 → mp3") and
not a census ("2 concepts"):

```markdown
# Docs — topic map

← [index gốc](../index.md)

- [<topic>](<topic>/index.md) — <what's inside: key behaviors/components/decisions this topic covers>
```

`docs/<topic>/index.md` — concepts within the topic; add `##` groups only when more than one
kind of concept lives there (e.g. features vs test suites) — a 1–2 concept topic stays flat:

```markdown
# <Topic>

← [docs](../index.md)

- [<slug>](<slug>.md) — (<Type>) one-line description
```
