# Root index template

Copy for `pkf/index.md` — the only file besides directory indexes that's reserved, and the only
one allowed frontmatter (just `okf_version`). **An index is a pure chỉ mục**: the root points
down to its child indexes; every child index backlinks up (`← [index gốc](../index.md)` — see
[index-section.md](index-section.md)). Detailed per-topic descriptions live in `docs/index.md`
only — never duplicated here.

```markdown
---
okf_version: "0.1"
---

# <Project> — Project Knowledge Base

<2–3 lines: what the project is and its main capabilities, readable by someone who has never
opened the code. What/why only — no code detail.>

- [Issues](issues/index.md) — bug, feature request, docs request (open/resolved)
- [Docs](docs/index.md) — tri thức app theo topic: <topic-1>, <topic-2>, …
- [Log](log.md) — lịch sử thay đổi, mới nhất trước
```

Rules:

- The Docs line **names the topics** (names only — retrieval scent without duplicating
  `docs/index.md` descriptions). When a topic is added/removed/renamed, update this line.
- No per-issue lines, counts, or per-topic description blocks here — those live in the child
  indexes. The root only changes when the project description or the topic list changes.
