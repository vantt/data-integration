---
type: Reference
title: Ingesting large or binary research sources
description: Decision table and scripts for probing and cleaning a research source before it's filed as a raw capture.
tags: [pkf, research, reference]
timestamp: 2026-07-04
---

Load from [research](commands/research.md) step 3 when a fetched source is binary
(docx/pdf/pptx/epub...), larger than ~50 KB, or carries embedded base64 images.

## Step 0 — probe, don't read

```bash
python <skill-dir>/scripts/ingest_probe.py <file> [--map-limit 60]
```

Trust the recommendation. Never open a binary file with Read; never read a file with base64
blobs before stripping.

## Decision table

| Source | Technique |
|---|---|
| `.md` / `.txt` | Probe directly → strategy by size (below) |
| `.docx` | `pandoc -f docx -t gfm --wrap=none f.docx -o f.md` (or `markitdown`) → re-probe |
| `.pdf` (text layer) | `pdftotext -layout` or `markitdown` → re-probe |
| `.pdf` (scanned) | Needs OCR — tell the user; don't guess content |
| `.pptx` | `markitdown` (slides + notes) → re-probe |
| `.epub` | `pandoc -f epub -t gfm` → re-probe |
| Embedded base64 images | `python <skill-dir>/scripts/strip_images.py <f.md>` → images become files in `assets/`, markdown shrinks to prose |

## Strategy by prose size (probe's `est` figure)

- **< ~8K tokens** — read whole, normal capture flow.
- **~8K–50K** — skeleton read: use the probe's section map, read only the slices needed.
- **> ~50K** — skeleton + multi-session bookmark: digest sections per session, record
  `ingest_status: "partial — sections 01-10 done"` in the raw frontmatter and in `log.md`.
- **> ~100K** — consider subagent fan-out: one section per subagent, each returns a distillate.

## Filing the capture

1. Strip/convert first, then file the cleaned markdown into `pkf/research/raw/` (extracted
   images go to `raw/assets/`, linked relatively).
2. Every claim in the issue's `# Research` section must trace to a slice actually read this
   session, not the skeleton alone. Numbers/quotes copied verbatim, with a provenance marker on
   synthesized paragraphs.
