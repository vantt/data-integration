#!/usr/bin/env python3
"""Probe a source file before filing it as a research capture and recommend a
token-efficient reading strategy.

One cheap EXEC call answers, without the agent reading the file:
  - what is it (text / binary-needs-conversion), how big in estimated tokens
  - does it carry embedded base64 images (context bombs) and how heavy they are
  - what section structure exists (markdown headings, bold-line markers,
    chapter keywords) -> printed as a line-number map for sliced reading
  - which ingest strategy fits (read-whole / skeleton / multi-session / fan-out)

Pure stdlib. Usage:
    python ingest_probe.py <file> [--map-limit 60]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Rough chars-per-token for mixed Vietnamese/English prose (conservative).
CHARS_PER_TOKEN = 3.0

BINARY_CONVERT = {
    ".docx": "pandoc -f docx -t gfm --wrap=none <file> -o <file>.md   (or: markitdown <file>)",
    ".doc":  "libreoffice --headless --convert-to docx first, then pandoc / markitdown",
    ".pdf":  "pdftotext -layout <file> out.txt   (or: markitdown <file>; scanned PDF -> OCR needed)",
    ".pptx": "markitdown <file> > out.md   (or: python-pptx to walk slides/notes)",
    ".ppt":  "libreoffice --headless --convert-to pptx first, then markitdown",
    ".epub": "pandoc -f epub -t gfm <file> -o out.md",
    ".xlsx": "in-place python (openpyxl) or markitdown; usually better queried than ingested whole",
}

DATA_IMG_RE = re.compile(r"data:image/[a-zA-Z0-9.+-]+;base64,([A-Za-z0-9+/=]+)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.{1,120})", re.M)
BOLD_LINE_RE = re.compile(r"^\*\*([^*\n]{3,120})\*\*\s*$", re.M)
CHAPTER_RE = re.compile(
    r"^(?:\*\*)?((?:Chương|CHƯƠNG|Phần|PHẦN|Bài|BÀI|Kỹ thuật|KỸ THUẬT|Chapter|Part|Section|Lesson)\s+\d+[^\n]{0,100})",
    re.M,
)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def build_map(text: str):
    """Scan all marker families; return (all_candidates, chosen_family)."""
    candidates = []
    for label, rx, group in (("markdown headings", HEADING_RE, 2),
                             ("bold-line markers", BOLD_LINE_RE, 1),
                             ("chapter keywords", CHAPTER_RE, 1)):
        hits = [(line_of(text, m.start()), m.group(group).strip())
                for m in rx.finditer(text)]
        candidates.append((label, hits))
    # Prefer real headings when present in force; otherwise densest family.
    named = dict(candidates)
    if len(named["markdown headings"]) >= 5:
        chosen = ("markdown headings", named["markdown headings"])
    else:
        chosen = max(candidates, key=lambda c: len(c[1]))
    return candidates, chosen


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Probe a source file before filing as a research capture.")
    ap.add_argument("file")
    ap.add_argument("--map-limit", type=int, default=60,
                    help="max section-map entries to print (default 60)")
    args = ap.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2
    size = path.stat().st_size
    ext = path.suffix.lower()

    print(f"file : {path.name}")
    print(f"size : {size:,} bytes")

    if ext in BINARY_CONVERT:
        print(f"kind : binary ({ext}) — CONVERT FIRST, do not read directly")
        print(f"recipe: {BINARY_CONVERT[ext]}")
        print("then : re-run this probe on the converted markdown/text.")
        return 0

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("kind : undecodable as UTF-8 — treat as binary; convert or ask the user")
        return 0

    lines = text.count("\n") + 1
    blobs = DATA_IMG_RE.findall(text)
    blob_chars = sum(len(b) for b in blobs)
    prose_chars = len(text) - blob_chars
    est_tokens = int(prose_chars / CHARS_PER_TOKEN)

    print(f"kind : text/markdown, {lines:,} lines")
    print(f"est  : ~{est_tokens:,} prose tokens"
          + (f" (+{len(blobs)} base64 images, {blob_chars:,} chars of blob — a context bomb)"
             if blobs else ""))

    families, chosen = build_map(text)
    counts = " · ".join(f"{label}: {len(hits)}" for label, hits in families)
    print(f"markers : {counts}")

    # Strategy recommendation (in order of application).
    print("strategy:")
    if blobs:
        print("  1. STRIP IMAGES first: python strip_images.py <file>  (saves the blob tokens)")
    if est_tokens < 8_000:
        print("  - small file: read it whole in one pass; normal capture flow applies.")
    elif est_tokens < 50_000:
        print("  - medium file: SKELETON READ — use the section map below; read only the"
              " slices you need with READ offset/limit (or `sed -n 'A,Bp'`).")
    else:
        print("  - large file: SKELETON READ + MULTI-SESSION BOOKMARK — digest a group of"
              " sections per session; record progress in the raw frontmatter"
              " (`ingest_status: partial ...`) and log.md.")
        if est_tokens >= 100_000:
            print("  - very large: consider subagent fan-out (one section per subagent,"
                  " each returns a distillate; main context never reads the source).")

    label, hits = chosen
    if hits and len(hits) >= 3:
        shown = hits[: args.map_limit]
        print(f"section map ({label}, {len(hits)} total"
              + (f", first {len(shown)} shown" if len(hits) > len(shown) else "") + "):")
        for ln, title in shown:
            print(f"  L{ln:>5}  {title}")
    else:
        print("section map: no reliable markers found — fall back to reading in fixed"
              " windows (e.g. 300-line slices) and skimming each for structure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
