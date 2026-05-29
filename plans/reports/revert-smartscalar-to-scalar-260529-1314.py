"""Revert display:smartscalar → display:scalar; drop scalar.comparisons.

Background: SmartScalar requires time-series data with `insights` metadata
(query must GROUP BY a date column). Our native-SQL widgets return a single
row with (current, comparison) as separate columns — no insights → SmartScalar
throws "Group only by a time field to see how this has changed over time".

Resolution: revert to plain `display: scalar`. Plain scalar:
- Renders the first column as a big number.
- Ignores any extra columns (no error).
- Ignores `scalar.comparisons` setting (so we remove it for cleanliness).
- Still respects `column_settings` for currency / decimals / compact formatting.

This script:
- Finds every ```json metabase-viz block with display=="smartscalar"
- Rewrites display to "scalar"
- Removes `scalar.comparisons` from visualization_settings (top-level or nested)
- Leaves column_settings and other keys untouched
- Idempotent: re-running on a clean state does nothing
"""
import json
import re
from pathlib import Path

BLUEPRINTS_DIR = Path("docs/analytics-handbook/blueprints")
VIZ_BLOCK_RE = re.compile(
    r"(```json metabase-viz\s*\n)(.*?)(\n```)",
    re.DOTALL,
)


def reformat_json(viz: dict, original_block: str) -> str:
    is_compact = "\n" not in original_block.strip()
    if is_compact:
        return json.dumps(viz, ensure_ascii=False, separators=(", ", ": "))
    return json.dumps(viz, ensure_ascii=False, indent=2)


def process_file(path: Path) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8")
    changes: list[str] = []

    def replace(match: re.Match) -> str:
        fence_open, body, fence_close = match.group(1), match.group(2), match.group(3)
        try:
            viz = json.loads(body)
        except json.JSONDecodeError:
            return match.group(0)
        if not isinstance(viz, dict):
            return match.group(0)
        if viz.get("display") != "smartscalar":
            return match.group(0)

        viz["display"] = "scalar"
        # remove scalar.comparisons from both top-level and visualization_settings
        viz.pop("scalar.comparisons", None)
        nested = viz.get("visualization_settings")
        if isinstance(nested, dict):
            nested.pop("scalar.comparisons", None)

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
    touched: list[str] = []
    for f in files:
        count, changes = process_file(f)
        if count:
            total += count
            touched.append(f.name)
            print(f"\n=== {f.name}: {count} revert(s) ===")
            for c in changes:
                print(f"  - {c}")
    print("\n" + "=" * 60)
    print(f"Total reverted: {total} across {len(touched)} files.")


if __name__ == "__main__":
    main()
