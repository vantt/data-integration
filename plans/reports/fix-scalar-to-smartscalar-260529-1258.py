"""Convert display:scalar→smartscalar for widgets that have scalar.comparisons.

Metabase v0.60: plain `scalar` viz does NOT render scalar.comparisons; only
SmartScalar (display="smartscalar", UI name "Trend") reads that setting.

This script:
- Walks every blueprint .md in docs/analytics-handbook/blueprints/
- Finds each ```json metabase-viz block
- Parses JSON; if display=="scalar" AND visualization_settings contains
  "scalar.comparisons" (with non-empty array), rewrites display="smartscalar"
- Leaves plain scalars (no comparisons) and other displays untouched
- Reports per-file counts

Run: python plans/reports/fix-scalar-to-smartscalar-260529-1258.py
"""
import json
import re
from pathlib import Path

BLUEPRINTS_DIR = Path("docs/analytics-handbook/blueprints")
VIZ_BLOCK_RE = re.compile(
    r"(```json metabase-viz\s*\n)(.*?)(\n```)",
    re.DOTALL,
)


def has_comparisons(viz: dict) -> bool:
    """True if viz has a non-empty scalar.comparisons array (top-level or under visualization_settings)."""
    direct = viz.get("scalar.comparisons")
    if isinstance(direct, list) and direct:
        return True
    nested = viz.get("visualization_settings", {})
    if isinstance(nested, dict):
        comparisons = nested.get("scalar.comparisons")
        if isinstance(comparisons, list) and comparisons:
            return True
    return False


def reformat_json(viz: dict, original_block: str) -> str:
    """Re-emit JSON preserving compact-ish style if original was single-line, otherwise multi-line."""
    is_compact = "\n" not in original_block.strip()
    if is_compact:
        return json.dumps(viz, ensure_ascii=False, separators=(", ", ": "))
    return json.dumps(viz, ensure_ascii=False, indent=2)


def process_file(path: Path) -> tuple[int, list[str]]:
    """Returns (conversions_count, list_of_brief_descriptions)."""
    text = path.read_text(encoding="utf-8")
    changes: list[str] = []

    def replace(match: re.Match) -> str:
        fence_open, body, fence_close = match.group(1), match.group(2), match.group(3)
        try:
            viz = json.loads(body)
        except json.JSONDecodeError:
            return match.group(0)  # malformed, skip
        if not isinstance(viz, dict):
            return match.group(0)
        if viz.get("display") != "scalar":
            return match.group(0)
        if not has_comparisons(viz):
            return match.group(0)
        viz["display"] = "smartscalar"
        # locate question title above the block for log line
        upto = text[: match.start()]
        title_match = re.findall(r"####\s+(?:❓\s+)?Question:\s*(.+)", upto)
        title = title_match[-1].strip() if title_match else "<unknown>"
        line_no = upto.count("\n") + 1
        changes.append(f"line {line_no}: {title}")
        return f"{fence_open}{reformat_json(viz, body)}{fence_close}"

    new_text = VIZ_BLOCK_RE.sub(replace, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return len(changes), changes


def main() -> None:
    files = sorted(BLUEPRINTS_DIR.glob("*.md"))
    total = 0
    touched_files: list[str] = []
    for f in files:
        count, changes = process_file(f)
        if count:
            total += count
            touched_files.append(f.name)
            print(f"\n=== {f.name}: {count} conversion(s) ===")
            for c in changes:
                print(f"  - {c}")
    print(f"\n{'=' * 60}")
    print(f"Total: {total} display:scalar→smartscalar conversions across {len(touched_files)} files.")
    print("Files touched:", ", ".join(touched_files) if touched_files else "(none)")


if __name__ == "__main__":
    main()
