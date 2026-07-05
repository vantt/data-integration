#!/usr/bin/env python3
"""Extract embedded base64 images from a markdown file into asset files.

Embedded `data:image/...;base64,...` blobs are context bombs: thousands of
tokens the LLM cannot see anyway. This script moves each blob to a real image
file and rewrites the markdown to link it, shrinking the file to its prose.

Handles both markup shapes:
  1. Reference definitions (Google Docs export style):
       ![][image1]           ...
       [image1]: <data:image/png;base64,AAAA...>
  2. Inline data URIs:
       ![alt](data:image/png;base64,AAAA...)

Pure stdlib. Usage:
    python strip_images.py <file.md> [--assets-dir DIR] [--output PATH | --in-place] [--dry-run]

Defaults: assets to `<file_dir>/assets/`, output to `<stem>.noimg.md`
(the original is left untouched unless --in-place).
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path, PurePosixPath

REF_DEF_RE = re.compile(
    r"^\[([^\]\n]+)\]:\s*<data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+?)>[ \t]*$",
    re.M,
)
INLINE_RE = re.compile(
    r"!\[([^\]\n]*)\]\(\s*data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)\s*\)"
)

EXT_FIX = {"jpeg": "jpg", "svg+xml": "svg"}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Move base64 images out of a markdown file.")
    ap.add_argument("file")
    ap.add_argument("--assets-dir", default=None,
                    help="where to write image files (default: <file_dir>/assets)")
    ap.add_argument("--output", default=None,
                    help="output markdown path (default: <stem>.noimg.md)")
    ap.add_argument("--in-place", action="store_true",
                    help="rewrite the input file itself")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be extracted; write nothing")
    args = ap.parse_args(argv)

    src = Path(args.file)
    if not src.is_file():
        print(f"error: not a file: {src}", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")

    out_path = src if args.in_place else Path(args.output or src.with_suffix(".noimg.md"))
    assets_dir = Path(args.assets_dir) if args.assets_dir else src.parent / "assets"
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", src.stem)[:60].strip("-") or "img"

    counter = 0
    saved_chars = 0
    failures = 0

    def rel_href(asset: Path) -> str:
        try:
            rel = asset.resolve().relative_to(out_path.parent.resolve())
            return str(PurePosixPath(rel))
        except ValueError:  # assets dir outside the output's tree
            return asset.resolve().as_posix()

    def extract(fmt: str, blob: str):
        """Decode + write one image; return its href or None on failure."""
        nonlocal counter, saved_chars, failures
        counter += 1
        clean = re.sub(r"\s+", "", blob)
        ext = EXT_FIX.get(fmt.lower(), fmt.lower())
        asset = assets_dir / f"{stem}-img{counter:02d}.{ext}"
        try:
            data = base64.b64decode(clean, validate=True)
        except Exception:
            failures += 1
            print(f"warn: image {counter} failed base64 decode — left in place")
            return None
        saved_chars += len(blob)
        if not args.dry_run:
            assets_dir.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(data)
        return rel_href(asset)

    def sub_ref(m: re.Match) -> str:
        href = extract(m.group(2), m.group(3))
        return m.group(0) if href is None else f"[{m.group(1)}]: {href}"

    def sub_inline(m: re.Match) -> str:
        href = extract(m.group(2), m.group(3))
        return m.group(0) if href is None else f"![{m.group(1)}]({href})"

    new_text = REF_DEF_RE.sub(sub_ref, text)
    new_text = INLINE_RE.sub(sub_inline, new_text)

    extracted = counter - failures
    if extracted == 0:
        print("no embedded base64 images found — nothing to do")
        return 0

    if not args.dry_run:
        out_path.write_text(new_text, encoding="utf-8")

    action = "would extract" if args.dry_run else "extracted"
    print(f"{action} {extracted} image(s) -> {assets_dir}"
          + (f" ({failures} undecodable, kept inline)" if failures else ""))
    print(f"markdown: {len(text):,} -> {len(new_text):,} chars "
          f"(saved ~{saved_chars // 3:,} tokens)")
    if not args.dry_run:
        print(f"output  : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
