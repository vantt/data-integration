#!/usr/bin/env python3
"""Rewrite blueprints/order_listing.md with unified 3-tab layout.

Changes applied:
  1. NEW Row A per tab: Reconciliation Checklist (15x2) + Data Freshness (3x2)
  2. Harmonize: all 3 tabs get 4 section headings (imperative voice) + footer
  3. Preserve 12 existing question SQL/viz blocks verbatim per tab
  4. Shift question positions: old row 0 -> row 3, row 4 -> row 7, row 8 -> row 12,
     row 14 -> row 19, row 19 -> row 25; positions col/size unchanged
  5. Rewrite section heading text (imperative + Sapo-reconciliation hints)
  6. Standardize footer across all tabs (fix the "Updated daily" lie)

Tab-specific content that MUST be preserved per-tab:
  - Today: uses `current_date` in SQL
  - Yesterday: uses `current_date - INTERVAL '1 day'` (and '2 days' for prev)
  - By Date: uses `{{date}}` template var + Filter: Date block

This script reads the current blueprint, extracts each tab's 12 Question blocks
(name + SQL + viz + pos), then generates a fresh blueprint with the new layout.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path("D:/Vantt/app/data-integration")
SRC = ROOT / "docs/analytics-handbook/blueprints/order_listing.md"
OUT = SRC  # in-place overwrite

# --- New layout: absolute row numbers per section ---
ROW_MAP = {
    # old_row -> new_row (questions only; text cards are rewritten entirely)
    0: 3,    # KPIs row C (Total Orders, Net Revenue, Total Collected, Gross Revenue)
    4: 7,    # KPIs row D (Total Discount, Cancelled, Returns)
    8: 12,   # Breakdowns row F (Status donut, Payment donut, Channel bar)
    14: 19,  # Flagged Orders row H (table)
    19: 25,  # Order Detail List row J (table)
}

# Section heading text (imperative voice, reconciliation-focused)
SECTION_HEADINGS = [
    ("row_2", "▸ Tổng quan đơn hàng — số cần đối soát với Sapo", 2),
    ("row_11", "▸ Phân bổ theo chiều — phát hiện lệch trạng thái, thanh toán, kênh", 11),
    ("row_18", "▸ Đơn bất thường — cần mở Sapo xác minh từng dòng", 18),
    ("row_24", "▸ Chi tiết đơn hàng — search order code trên Sapo nếu lệch", 24),
]

FOOTER_TEXT = (
    "Source: `fact_orders` · dbt updates every 10 min via Dagster incremental job · "
    "Filter: `status NOT IN ('CANCELLED', 'Voided')` for revenue KPIs · "
    "Playbook: [orders_list_reconciliation](../playbooks/orders_list_reconciliation.md) · "
    "For help: #data-team"
)

# Row A: Reconciliation Checklist (15 cols) + Data Freshness (3 cols) at rows 0-1
CHECKLIST_MD = """## 🔍 Đối chiếu BI ↔ Sapo — 5 bước

1. **So Total Orders** với Sapo Admin > Đơn hàng cùng ngày (bao gồm cả CANCELLED).
2. **So Net Revenue** và **Total Collected** với cùng bộ lọc.
3. **Kiểm tra DoD arrow** — đỏ/bất thường → cần điều tra ngay.
4. **Quét Flagged Orders** — bất kỳ dòng nào cũng cần xác minh Sapo.
5. **Lệch > 1 đơn?** Mở Order Detail List, search order code trên Sapo → báo Data Team nếu là ingestion gap."""

# Data Freshness SQL: uses fact_orders updated_at (DuckDB DATE_DIFF returns int)
FRESHNESS_SQL_TEMPLATE = """SELECT
    CAST(date_diff('minute', MAX(updated_at), now()) AS INTEGER) AS "Phút kể từ lần cập nhật cuối"
FROM fact_orders"""

FRESHNESS_VIZ = """{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Phút kể từ lần cập nhật cuối"
  }
}"""


def extract_tab_questions(content: str, tab_name: str) -> list[dict]:
    """Extract ordered list of Question blocks for a given tab.

    Returns list of dicts with keys: name, sql, viz, pos_json, raw_block.
    """
    # Find the tab section
    tab_pattern = re.compile(
        rf"^### Tab: {re.escape(tab_name)}\s*$(.*?)(?=^### Tab: |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = tab_pattern.search(content)
    if not m:
        raise RuntimeError(f"Tab '{tab_name}' not found")
    tab_body = m.group(1)

    # Split into question blocks
    # A question starts with "#### Question: " and continues until the next "#### " or end
    q_pattern = re.compile(
        r"^####\s+Question:\s+(.+?)$(.*?)(?=^####\s+|^---|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    questions = []
    for qm in q_pattern.finditer(tab_body):
        name = qm.group(1).strip()
        block = qm.group(2).strip()
        # Extract sql, viz, pos
        sql_m = re.search(r"```sql\s*\n(.*?)```", block, re.DOTALL)
        viz_m = re.search(r"```json metabase-viz\s*\n(.*?)```", block, re.DOTALL)
        pos_m = re.search(r"```json metabase-pos\s*\n(.*?)```", block, re.DOTALL)
        if not (sql_m and viz_m and pos_m):
            raise RuntimeError(f"Question '{name}' in tab '{tab_name}' missing sql/viz/pos block")
        questions.append({
            "name": name,
            "sql": sql_m.group(1).strip(),
            "viz": viz_m.group(1).strip(),
            "pos": pos_m.group(1).strip(),
            # Preserve any description text between question heading and first code block
            "description": "",
        })
    return questions


def shift_pos(pos_json: str) -> str:
    """Shift row in pos JSON per ROW_MAP. col and sizes unchanged."""
    m = re.search(r'"row"\s*:\s*(\d+)', pos_json)
    if not m:
        return pos_json
    old = int(m.group(1))
    new = ROW_MAP.get(old)
    if new is None:
        raise RuntimeError(f"Unmapped row {old} in pos: {pos_json}")
    return re.sub(r'"row"\s*:\s*\d+', f'"row": {new}', pos_json)


def render_text_card(heading: str, text_body: str, row: int, col: int = 0,
                     size_x: int = 18, size_y: int = 1) -> str:
    return f"""#### 📝 Text: {heading}

{text_body}

```json metabase-pos
{{ "row": {row}, "col": {col}, "size_x": {size_x}, "size_y": {size_y} }}
```
"""


def render_freshness_card() -> str:
    return f"""#### Question: Data Freshness

Tuổi của dữ liệu — xanh nếu < 120 phút, cam 120-360 phút, đỏ > 360 phút. Nếu > 120 phút, dừng reconciliation và kiểm tra Dagster trước.

```sql
{FRESHNESS_SQL_TEMPLATE}
```

```json metabase-viz
{FRESHNESS_VIZ}
```

```json metabase-pos
{{ "row": 0, "col": 15, "size_x": 3, "size_y": 2 }}
```
"""


def render_checklist_card() -> str:
    return f"""#### 📝 Text: Reconciliation Checklist

{CHECKLIST_MD}

```json metabase-pos
{{ "row": 0, "col": 0, "size_x": 15, "size_y": 2 }}
```
"""


def render_question(q: dict) -> str:
    new_pos = shift_pos(q["pos"])
    return f"""#### Question: {q['name']}

```sql
{q['sql']}
```

```json metabase-viz
{q['viz']}
```

```json metabase-pos
{new_pos}
```
"""


def render_tab(tab_name: str, questions: list[dict], include_filter: bool = False) -> str:
    """Render one tab with harmonized layout."""
    lines = [f"### Tab: {tab_name}", ""]

    if include_filter:
        lines.append("""#### Filter: Date

```json metabase-filter
{
  "name": "Date",
  "slug": "date",
  "type": "date/single",
  "default": "today"
}
```
""")

    # Row A: Reconciliation Checklist + Data Freshness
    lines.append(render_checklist_card())
    lines.append(render_freshness_card())
    lines.append("---\n")

    # Row 2: Section 1 heading
    lines.append(render_text_card("Section 1 — Tổng quan", SECTION_HEADINGS[0][1], 2))

    # Rows 3-10: KPIs (in order from extracted questions)
    kpi_names = ["Total Orders", "Net Revenue", "Total Collected", "Gross Revenue",
                 "Total Discount", "Cancelled Orders", "Returns"]
    for name in kpi_names:
        q = next((x for x in questions if x["name"] == name), None)
        if q is None:
            raise RuntimeError(f"Question '{name}' missing in tab '{tab_name}'")
        lines.append(render_question(q))

    lines.append("---\n")
    # Row 11: Section 2 heading
    lines.append(render_text_card("Section 2 — Phân bổ", SECTION_HEADINGS[1][1], 11))

    # Rows 12-17: Breakdowns
    breakdown_names = ["Orders by Status", "Orders by Payment Status", "Orders by Channel"]
    for name in breakdown_names:
        q = next((x for x in questions if x["name"] == name), None)
        if q is None:
            raise RuntimeError(f"Question '{name}' missing in tab '{tab_name}'")
        lines.append(render_question(q))

    lines.append("---\n")
    # Row 18: Section 3 heading
    lines.append(render_text_card("Section 3 — Cảnh báo", SECTION_HEADINGS[2][1], 18))

    # Row 19: Flagged Orders
    q = next((x for x in questions if x["name"] == "Flagged Orders"), None)
    lines.append(render_question(q))

    lines.append("---\n")
    # Row 24: Section 4 heading
    lines.append(render_text_card("Section 4 — Chi tiết", SECTION_HEADINGS[3][1], 24))

    # Row 25: Order Detail List
    q = next((x for x in questions if x["name"] == "Order Detail List"), None)
    lines.append(render_question(q))

    lines.append("---\n")
    # Row 35: Footer
    lines.append(render_text_card("Footer — Source & Escalation", FOOTER_TEXT, 35))

    return "\n".join(lines)


def main():
    content = SRC.read_text(encoding="utf-8")

    # Extract all 3 tabs' questions
    today_qs = extract_tab_questions(content, "Today")
    yesterday_qs = extract_tab_questions(content, "Yesterday")
    bydate_qs = extract_tab_questions(content, "By Date")

    print(f"Extracted: Today={len(today_qs)} Yesterday={len(yesterday_qs)} ByDate={len(bydate_qs)}", file=sys.stderr)

    # Header (preserve frontmatter and collection/dashboard sections)
    header = """# Blueprint: Order Listing

**Design Spec**: [Order Listing](../designs/order_listing.md)
**Playbook**: [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

> **Target Collection:** `Operations` > `Daily Monitoring`
> **Role:** Sales Ops, Store Manager, Data Team
> **Archetype:** Operational Cockpit

## 📂 Collection: Operations > Daily Monitoring

Dashboard đối soát đơn hàng — xác minh tính đúng đắn và đầy đủ của dữ liệu BI so với Sapo.

---

### 🖥️ Dashboard: Order Listing

**Description**: Công cụ đối soát đơn hàng — Reconciliation Checklist + Data Freshness + KPI DoD + phân bổ (donut/bar) + cảnh báo bất thường + chi tiết đơn. 3 tabs (Today / Yesterday / By Date) đồng bộ hoàn toàn — chỉ khác date predicate.

---

"""

    body = (
        render_tab("Today", today_qs, include_filter=False) + "\n\n---\n\n"
        + render_tab("Yesterday", yesterday_qs, include_filter=False) + "\n\n---\n\n"
        + render_tab("By Date", bydate_qs, include_filter=True) + "\n"
    )

    new_content = header + body
    OUT.write_text(new_content, encoding="utf-8")
    print(f"Wrote {OUT} ({len(new_content)} chars, {new_content.count(chr(10))} lines)", file=sys.stderr)


if __name__ == "__main__":
    main()
