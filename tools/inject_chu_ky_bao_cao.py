#!/usr/bin/env python3
"""
inject_chu_ky_bao_cao.py
Inject "Chu kỳ báo cáo" period-display scalar card into Metabase blueprints
that are missing it. Inserts at row 0 of each tab and shifts all existing
row values in that tab by +2.
"""

import os
import re
import sys

BLUEPRINT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "docs",
    "analytics-handbook",
    "blueprints",
)

SKIP_FILES = {"us_crossborder_operations.md"}

# ---------------------------------------------------------------------------
# SQL templates by cadence
# ---------------------------------------------------------------------------
SQL_DAILY = (
    "SELECT '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y')"
    " || '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y') AS \" \""
)

SQL_WEEKLY = (
    "SELECT '📅 Tuần này: '"
    " || strftime(date_trunc('week', current_date), '%d/%m/%Y')"
    " || ' → ' || strftime(current_date, '%d/%m/%Y')"
    " || '  ·  Tuần trước: '"
    " || strftime(date_trunc('week', current_date) - INTERVAL '7 days', '%d/%m/%Y')"
    " || ' → '"
    " || strftime(date_trunc('week', current_date) - INTERVAL '1 day', '%d/%m/%Y')"
    ' AS " "'
)

SQL_MONTHLY = (
    "SELECT '📅 Tháng này: '"
    " || strftime(date_trunc('month', current_date), '%d/%m/%Y')"
    " || ' → ' || strftime(current_date, '%d/%m/%Y')"
    " || '  ·  Tháng trước: '"
    " || strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y')"
    " || ' → '"
    " || strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y')"
    ' AS " "'
)

# ---------------------------------------------------------------------------
# Cadence detection
# ---------------------------------------------------------------------------

def detect_file_cadence(filename: str) -> str:
    """Return 'daily', 'weekly', or 'monthly' from filename heuristics."""
    name = filename.lower()
    # Monthly indicators (specific filenames)
    monthly_patterns = [
        "monthly", "month", "economics", "profitability", "performance",
        "intelligence", "channel_pl", "recon", "accounting",
        "cost_ledger", "cost_margin", "return_impact",
        "summary", "roi", "promotion", "scorecard",
    ]
    # Weekly indicators
    weekly_patterns = [
        "weekly", "week", "pulse", "tracker", "review",
    ]
    # Daily indicators
    daily_patterns = [
        "daily", "yesterday", "today", "operational", "retention",
        "order_detail", "order_listing", "order_profitability",
        "product_profitability", "b2b", "logistics", "ingestion",
        "social_commerce", "finance_pl",
    ]

    for pat in monthly_patterns:
        if pat in name:
            return "monthly"
    for pat in weekly_patterns:
        if pat in name:
            return "weekly"
    for pat in daily_patterns:
        if pat in name:
            return "daily"
    return "daily"  # safe default


def detect_tab_cadence(tab_name: str, file_cadence: str) -> str:
    """Detect cadence from tab name; fall back to file_cadence."""
    lower = tab_name.lower()
    if any(k in lower for k in ("tuan", "week", "weekly")):
        return "weekly"
    if any(k in lower for k in ("thang", "month", "monthly")):
        return "monthly"
    # overview tabs use file-level cadence
    return file_cadence


def cadence_sql(cadence: str) -> str:
    if cadence == "weekly":
        return SQL_WEEKLY
    if cadence == "monthly":
        return SQL_MONTHLY
    return SQL_DAILY


def cadence_question_name(cadence: str, tab_name: str = "") -> str:
    """Return the question name for the period card."""
    tab_lower = tab_name.lower()
    if any(k in tab_lower for k in ("tuan", "week", "weekly")):
        return "Chu kỳ báo cáo (Weekly)"
    if any(k in tab_lower for k in ("thang", "month", "monthly")):
        return "Chu kỳ báo cáo (Monthly)"
    return "Chu kỳ báo cáo"


# ---------------------------------------------------------------------------
# Period card builder
# ---------------------------------------------------------------------------

CHU_KY_BLOCK_TEMPLATE = """\
#### ❓ Question: {name}

```sql
{sql}
```

```json metabase-viz
{{ "display": "scalar", "visualization_settings": {{ "card.title": "", "dashcard.background": false }} }}
```

```json metabase-pos
{{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }}
```

"""


def build_period_block(name: str, sql: str) -> str:
    return CHU_KY_BLOCK_TEMPLATE.format(name=name, sql=sql)


# ---------------------------------------------------------------------------
# Row shifting
# ---------------------------------------------------------------------------

def shift_rows_in_segment(text: str, shift: int = 2) -> str:
    """
    Increment all "row": N values in metabase-pos JSON blocks within text.
    Only modifies the row key inside ```json metabase-pos ... ``` blocks.
    """
    def replace_pos_block(m: re.Match) -> str:
        block = m.group(0)
        # Replace "row": N → "row": N+shift
        def inc_row(rm: re.Match) -> str:
            old_val = int(rm.group(1))
            return f'"row": {old_val + shift}'
        return re.sub(r'"row"\s*:\s*(\d+)', inc_row, block)

    # Match full ```json metabase-pos ... ``` blocks
    return re.sub(
        r'```json metabase-pos\s*\n.*?\n```',
        replace_pos_block,
        text,
        flags=re.DOTALL,
    )


# ---------------------------------------------------------------------------
# Core injection: per-tab strategy
# ---------------------------------------------------------------------------

# Pattern: tab header line  (### 📑 Tab: ... or ### Tab: ...)
TAB_HEADER_RE = re.compile(r'^(###\s+(?:📑\s+)?Tab:\s+.+)$', re.MULTILINE)


def inject_into_tabbed_blueprint(content: str, file_cadence: str) -> tuple[str, list[str]]:
    """
    Split content on tab headers, inject period card at start of each tab,
    shift existing rows in each tab segment.
    Returns (new_content, [tab_name, ...]) for reporting.
    """
    tab_headers = list(TAB_HEADER_RE.finditer(content))
    if not tab_headers:
        return content, []

    # Build (start, end, header_text) spans for each tab
    spans = []
    for i, m in enumerate(tab_headers):
        start = m.start()
        end = tab_headers[i + 1].start() if i + 1 < len(tab_headers) else len(content)
        spans.append((start, end, m.group(0)))

    # Prefix = everything before first tab
    prefix = content[: spans[0][0]]

    segments = []
    tab_names_processed = []

    for span_start, span_end, header_line in spans:
        seg = content[span_start:span_end]

        # Extract tab name from header
        tab_name_match = re.search(r'Tab:\s+(.+)$', header_line)
        tab_name = tab_name_match.group(1).strip() if tab_name_match else ""

        cadence = detect_tab_cadence(tab_name, file_cadence)
        q_name = cadence_question_name(cadence, tab_name)
        sql = cadence_sql(cadence)
        period_block = build_period_block(q_name, sql)

        # The segment starts with the header line, then newline(s), then content
        # Insert period card immediately after the header line
        header_end = seg.index('\n', 0) + 1  # position right after the header newline
        after_header = seg[header_end:]

        # Shift rows in the rest of the segment (after the header)
        shifted_after = shift_rows_in_segment(after_header)

        # Reassemble: header + newline + period_block + shifted_rest
        new_seg = seg[:header_end] + "\n" + period_block + shifted_after

        segments.append(new_seg)
        tab_names_processed.append(tab_name)

    new_content = prefix + "".join(segments)
    return new_content, tab_names_processed


def inject_into_single_tab_blueprint(content: str, file_cadence: str) -> tuple[str, str]:
    """
    For blueprints with no Tab: headers — single-tab dashboard.
    Insert period card after the first '---' separator that follows
    the Dashboard description line, before the first question/text block.
    Returns (new_content, cadence_used).
    """
    cadence = file_cadence
    q_name = cadence_question_name(cadence)
    sql = cadence_sql(cadence)
    period_block = build_period_block(q_name, sql)

    # Find the dashboard description block: after '### 🖥️ Dashboard:' or '### Dashboard:'
    # Look for the first content block after the filters/--- separators
    # Strategy: find the position of the first #### (question or text) that isn't a Filter
    # and insert period block before it, then shift the whole body.

    # Split at the dashboard header line
    dashboard_re = re.compile(r'^(###\s+(?:🖥️\s+)?Dashboard:.+)$', re.MULTILINE)
    dash_match = dashboard_re.search(content)
    if not dash_match:
        return content, cadence

    dash_start = dash_match.start()
    prefix = content[:dash_start]
    body_from_dash = content[dash_start:]

    # Find first #### Question or #### Text block (not a filter block)
    # After filters and --- separators
    first_card_re = re.compile(
        r'^(####\s+(?:❓\s+)?Question:|####\s+(?:📝\s+)?Text:)',
        re.MULTILINE,
    )
    m = first_card_re.search(body_from_dash)
    if not m:
        return content, cadence

    insert_pos = m.start()
    before_insert = body_from_dash[:insert_pos]
    after_insert = body_from_dash[insert_pos:]

    # Shift rows in the existing body (after_insert)
    shifted_after = shift_rows_in_segment(after_insert)

    new_body = before_insert + period_block + shifted_after
    new_content = prefix + new_body
    return new_content, cadence


# ---------------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------------

def process_file(filepath: str) -> dict:
    filename = os.path.basename(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    # Skip check
    if "Chu kỳ báo cáo" in original or "Chu ky bao cao" in original:
        return {
            "file": filename,
            "status": "skipped",
            "reason": "already has period card",
            "cadence": None,
            "tabs": [],
        }

    file_cadence = detect_file_cadence(filename)

    # Detect if blueprint has tab headers
    has_tabs = bool(TAB_HEADER_RE.search(original))

    if has_tabs:
        new_content, tabs_processed = inject_into_tabbed_blueprint(original, file_cadence)
        details = {"tabs": tabs_processed, "cadence": file_cadence}
    else:
        new_content, used_cadence = inject_into_single_tab_blueprint(original, file_cadence)
        details = {"tabs": ["(single-tab)"], "cadence": used_cadence}

    if new_content == original:
        return {
            "file": filename,
            "status": "no_change",
            "reason": "injection produced no diff",
            "cadence": file_cadence,
            "tabs": details["tabs"],
        }

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    return {
        "file": filename,
        "status": "modified",
        "cadence": details["cadence"],
        "tabs": details["tabs"],
        "reason": None,
    }


def main():
    bp_dir = os.path.abspath(BLUEPRINT_DIR)
    files = sorted(f for f in os.listdir(bp_dir) if f.endswith(".md"))

    results = []
    for fname in files:
        if fname in SKIP_FILES:
            results.append({
                "file": fname,
                "status": "skipped",
                "reason": "explicitly excluded",
                "cadence": None,
                "tabs": [],
            })
            continue
        fpath = os.path.join(bp_dir, fname)
        r = process_file(fpath)
        results.append(r)

    # Print summary
    import sys
    out = sys.stdout

    def pr(s=""):
        print(s.encode("ascii", "replace").decode("ascii"))

    pr()
    pr("=" * 70)
    pr("Chu ky bao cao injection summary")
    pr("=" * 70)

    modified = [r for r in results if r["status"] == "modified"]
    skipped = [r for r in results if r["status"] == "skipped"]
    no_change = [r for r in results if r["status"] == "no_change"]

    pr(f"\nModified ({len(modified)} files):")
    for r in modified:
        tabs_str = ", ".join(r["tabs"])
        pr(f"  + {r['file']}")
        pr(f"    cadence: {r['cadence']}  |  tabs: {tabs_str}")

    if skipped:
        pr(f"\nSkipped ({len(skipped)} files):")
        for r in skipped:
            pr(f"  - {r['file']} -- {r['reason']}")

    if no_change:
        pr(f"\nNo change ({len(no_change)} files):")
        for r in no_change:
            pr(f"  ~ {r['file']} -- {r['reason']}")

    pr()
    pr("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
