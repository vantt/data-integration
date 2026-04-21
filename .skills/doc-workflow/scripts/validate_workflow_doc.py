#!/usr/bin/env python
"""Validate a workflow documentation markdown file.

Checks both structural requirements (sections, diagrams) and quality heuristics
(path string in TL;DR, common misunderstandings pairs, concise conclusion).
"""
import re
import sys
from pathlib import Path


REQUIRED_SECTION_PATTERNS = {
    "tl_dr": [r"^##\s+.*TL;DR"],
    "stage_by_stage": [
        r"^##\s+.*stage-by-stage",
        r"^##\s+.*Stage-by-Stage",
        r"^##\s+.*Bảng stage-by-stage",
        r"^##\s+.*Chi tiết từng stage",
        r"^##\s+.*Chi tiết các stage",
    ],
    "runtime": [
        r"^##\s+.*Runtime",
        r"^##\s+.*Thực thi",
        r"^##\s+.*runtime thực thi",
    ],
    "signals_gates_checkpoints": [
        r"^##\s+.*Signals,\s*gates,\s*checkpoints",
        r"^##\s+.*Signals,\s*Gates,\s*Checkpoints",
        r"^##\s+.*Signals.*Gates.*Checkpoints",
        r"^##\s+.*Tín hiệu.*Gate.*Checkpoint",
    ],
    "data_flow": [
        r"^##\s+.*Dữ liệu",
        r"^##\s+.*Data Flow",
        r"^##\s+.*artifact",
    ],
    "failure": [r"^##\s+.*Failure", r"^##\s+.*retry", r"^##\s+.*escalation"],
    "common_misunderstandings": [
        r"^##\s+.*Common Misunderstandings",
        r"^##\s+.*dễ nhầm",
        r"^##\s+.*dễ hiểu lầm",
        r"^##\s+.*Misreadings",
    ],
    "quick_reading_checklist": [
        r"^##\s+.*Quick Reading",
        r"^##\s+.*Checklist đọc nhanh",
        r"^##\s+.*Reading Checklist",
    ],
}

RECOMMENDED_SECTION_PATTERNS = {
    "identity_or_overview": [r"Identity", r"Tổng quan", r"Overview"],
    "cheat_sheet": [r"Cheat Sheet", r"Quick reference", r"Quick Reference"],
    "open_questions": [r"Open questions", r"Unresolved questions", r"Open Questions"],
    "conclusion": [r"^##\s+.*Conclusion", r"^##\s+.*Kết luận"],
}


def has_any_pattern(text, patterns):
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def extract_section(text, heading_patterns):
    """Return the body text of the first section whose heading matches any pattern."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if any(re.search(p, line, flags=re.IGNORECASE) for p in heading_patterns):
            start = i + 1
            break
    if start is None:
        return ""
    # End at next h2
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^##\s+", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def check_tldr_path_string(text):
    """TL;DR must contain a path string with -> arrows."""
    tldr = extract_section(text, [r"^##\s+.*TL;DR"])
    if not tldr:
        return False
    # Look for at least 2 arrows on one line (A -> B -> C)
    for line in tldr.splitlines():
        if line.count("->") >= 2:
            return True
    return False


def check_misunderstandings_count(text):
    """Common misunderstandings section must have at least 3 entries."""
    section = extract_section(
        text,
        [
            r"^##\s+.*Common Misunderstandings",
            r"^##\s+.*dễ nhầm",
            r"^##\s+.*dễ hiểu lầm",
        ],
    )
    if not section:
        return 0
    # Count h3 subsections or bullet pairs with "not", "≠", "khác", "vs"
    h3_count = len(re.findall(r"^###\s+", section, flags=re.MULTILINE))
    if h3_count >= 3:
        return h3_count
    # Fallback: count bullets containing contrast markers
    bullet_pairs = len(
        re.findall(r"^[-*].*(?:≠|vs\.?|không phải|not the same)", section, flags=re.MULTILINE | re.IGNORECASE)
    )
    return max(h3_count, bullet_pairs)


def check_conclusion_concise(text):
    """Conclusion should contain a short quoted sentence under 200 chars."""
    section = extract_section(text, [r"^##\s+.*Conclusion", r"^##\s+.*Kết luận"])
    if not section:
        return None  # no conclusion section at all
    # Look for a blockquote line
    quotes = re.findall(r"^>\s+(.+)$", section, flags=re.MULTILINE)
    if not quotes:
        return False
    # At least one quote should be under 200 chars
    return any(len(q.strip()) < 200 for q in quotes)


def check_state_participant(text):
    """At least one sequence diagram should have a state/artifacts participant."""
    sequence_blocks = re.findall(
        r"```mermaid\s*\n(.*?sequenceDiagram.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not sequence_blocks:
        return None  # no sequence diagrams at all
    state_markers = [
        r"participant.*(?:state|artifacts?|FS|run\s*state|filesystem|storage)",
    ]
    for block in sequence_blocks:
        for marker in state_markers:
            if re.search(marker, block, flags=re.IGNORECASE):
                return True
    return False


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_workflow_doc.py <markdown-file>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"FAIL: file not found: {path}")
        return 2

    text = path.read_text(encoding="utf-8", errors="replace")

    failures = []
    warnings = []

    # Structural requirements
    for label, patterns in REQUIRED_SECTION_PATTERNS.items():
        if not has_any_pattern(text, patterns):
            failures.append(f"Missing required section category: {label}")

    mermaid_count = len(re.findall(r"```mermaid", text, flags=re.IGNORECASE))
    if mermaid_count < 3:
        failures.append(f"Expected at least 3 Mermaid diagrams, found {mermaid_count}")

    table_rows = len(re.findall(r"^\|.+\|$", text, flags=re.MULTILINE))
    if table_rows < 8:
        warnings.append(f"Low markdown table coverage: found {table_rows} table rows")

    if "dry_run" not in text or "rigor" not in text:
        warnings.append("Expected both `dry_run` and `rigor` to be documented explicitly")

    if "checkpoint" not in text.lower():
        failures.append("Expected checkpoint behavior to be documented")

    if "signal" not in text.lower():
        failures.append("Expected signal behavior to be documented")

    if "gate" not in text.lower():
        failures.append("Expected gate behavior to be documented")

    # Quality heuristics
    if not check_tldr_path_string(text):
        failures.append("TL;DR missing a path string (expected a line with at least 2 `->` arrows)")

    misunderstandings = check_misunderstandings_count(text)
    if misunderstandings < 3:
        failures.append(
            f"Common misunderstandings section needs at least 3 entries (found {misunderstandings})"
        )

    conclusion_ok = check_conclusion_concise(text)
    if conclusion_ok is None:
        warnings.append("No conclusion section found — expected a one-sentence closing")
    elif conclusion_ok is False:
        warnings.append(
            "Conclusion should end with a short quoted sentence (blockquote) under 200 characters"
        )

    state_participant = check_state_participant(text)
    if state_participant is None:
        warnings.append("No sequence diagram found — consider adding one with actor handoffs")
    elif state_participant is False:
        warnings.append(
            "Sequence diagrams should include a state/artifacts/FS participant to show where state is written"
        )

    for label, patterns in RECOMMENDED_SECTION_PATTERNS.items():
        if not has_any_pattern(text, patterns):
            warnings.append(f"Missing recommended section category: {label}")

    if failures:
        print("FAIL")
        for item in failures:
            print(f"- {item}")
        if warnings:
            print("WARN")
            for item in warnings:
                print(f"- {item}")
        return 1

    print("PASS")
    print(f"- Mermaid diagrams: {mermaid_count}")
    print(f"- Misunderstandings entries: {misunderstandings}")
    if warnings:
        print("WARN")
        for item in warnings:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
