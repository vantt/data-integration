---
type: Concept
title: Research raw layer
description: pkf/research/raw/ holds immutable captured sources, separate from compiled docs/; only a human-approved compile step turns raw material into a doc.
tags: [pkf, research, raw]
timestamp: 2026-07-05
---

Referenced by [research](../commands/research.md) and [work](../commands/work.md).

# Schema

```
pkf/research/
  index.md
  raw/
    index.md
    <source-slug>.md   # type: Raw Source — immutable, never edited after filing
```

**Raw capture frontmatter:**
```yaml
---
type: Raw Source
title: <source title>
description: one sentence
source_url: https://example.com/article   # omit if not URL-based
ingested: 2026-07-04
issue: issues/issue-<id>-<type>-<slug>.md   # omit for standalone (docs-enrichment) research
confidence: high | medium | low
tags: [...]
---
```

- **Raw is immutable.** Never edit a capture after filing — corrections happen in the compiled
  `docs/<topic>/` concept, not here.
- **Confidence rubric:** `high` only when corroborated across multiple sources; `medium` for a
  single credible source or opinion-heavy content; `low` for anything unverified or >3 years old.
- **Compile is a separate, human-approved step** — the research *loop* only writes `raw/` and
  the issue's `# Research`; `docs/` is written only after the human's go-ahead, via
  [work](../commands/work.md) (issue-bound) or [research](../commands/research.md) step 6
  (standalone docs-enrichment). Enriching `docs/` is research's compounding goal — raw material
  that never compiles helps once; a compiled doc helps every session after.

# Examples

A large/binary/image-laden source is probed and cleaned before capture:
```bash
python <skill-dir>/scripts/ingest_probe.py <file>      # detect type/size/structure -> strategy
python <skill-dir>/scripts/strip_images.py <file.md>   # base64 blobs -> assets/ files
```
See [research-large-sources](../research-large-sources.md) for the full decision table.
