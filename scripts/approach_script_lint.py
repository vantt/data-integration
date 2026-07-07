"""approach_script_lint.py — Guardrail linter cho approach-script JSON.

Chặn script hỏng/vi phạm guardrail TRƯỚC khi vào CRM, dù nguồn là dán tay
hay codex auto-gen. Chỉ check những gì máy check được; chất lượng lời thoại
vẫn do người duyệt.

API:
  lint_script(data: dict) -> list[str]   # rỗng = pass
  lint_file(path) -> list[str]           # parse + lint

CLI (lint cả thư mục hoặc từng file):
  python scripts/approach_script_lint.py <dir-or-file> [...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_TOP_KEYS = ("profile_read", "value_assessment", "opportunity", "risk",
                     "approach", "confidence", "data_gaps")
PRIMARY_CHANNELS = {"phone", "zalo", "sms", "in_store"}
FALLBACK_CHANNELS = PRIMARY_CHANNELS | {"none"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}

# Số thập phân dài thô (vd 0.7526163537…) — template cấm in ra (RÀNG BUỘC #7)
_RAW_DECIMAL_RE = re.compile(r"\d\.\d{4,}")
# Từ khóa khuyến mãi — cấm khi khách margin âm (quy tắc nghiệp vụ template)
_PROMO_RE = re.compile(r"giảm giá|khuyến mãi|ưu đãi|discount|sale off", re.IGNORECASE)


def _walk_strings(obj, path=""):
    """Yield (json_path, string_value) cho mọi string trong cây JSON."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_strings(v, f"{path}[{i}]")


def _lint_branching(data: dict) -> list[str]:
    """Check cây nhánh v3 (chỉ khi có key `nodes`)."""
    errors: list[str] = []
    nodes = data.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        return ["nodes phải là dict non-empty"]
    entry = data.get("entry_node")
    if entry not in nodes:
        errors.append(f"entry_node '{entry}' không tồn tại trong nodes")
    has_terminal = False
    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            errors.append(f"nodes[{node_id}] không phải object")
            continue
        if not node.get("say"):
            errors.append(f"nodes[{node_id}].say trống")
        options = node.get("options")
        if not isinstance(options, list) or not options:
            errors.append(f"nodes[{node_id}].options trống")
            continue
        for i, opt in enumerate(options):
            nxt = opt.get("next")
            if nxt is None:
                has_terminal = True
            elif nxt not in nodes:
                errors.append(f"nodes[{node_id}].options[{i}].next '{nxt}' không tồn tại")
            if not opt.get("outcome"):
                errors.append(f"nodes[{node_id}].options[{i}].outcome trống")
    if not has_terminal:
        errors.append("cây nhánh không có đường terminal nào (next=null)")
    return errors


def lint_script(data) -> list[str]:
    """Trả list lỗi guardrail; rỗng = pass."""
    if not isinstance(data, dict):
        return ["root không phải JSON object"]
    errors: list[str] = []

    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"thiếu key bắt buộc: {key}")

    approach = data.get("approach")
    if isinstance(approach, dict):
        rec = approach.get("recommended")
        if not isinstance(rec, bool):
            errors.append("approach.recommended phải là bool")
        elif rec is False and not approach.get("reason_if_not_recommended"):
            errors.append("recommended=false nhưng reason_if_not_recommended trống")
        pc = approach.get("primary_channel")
        if pc is not None and pc not in PRIMARY_CHANNELS:
            errors.append(f"primary_channel '{pc}' ngoài enum {sorted(PRIMARY_CHANNELS)}")
        fc = approach.get("fallback_channel")
        if fc is not None and fc not in FALLBACK_CHANNELS:
            errors.append(f"fallback_channel '{fc}' ngoài enum {sorted(FALLBACK_CHANNELS)}")
    elif "approach" in data:
        errors.append("approach không phải object")

    conf = data.get("confidence")
    if conf is not None and conf not in CONFIDENCE_LEVELS:
        errors.append(f"confidence '{conf}' ngoài enum {sorted(CONFIDENCE_LEVELS)}")

    # Chống lộ số thô — bỏ qua meta (dữ liệu nội bộ, không render cho sale)
    visible = {k: v for k, v in data.items() if k != "meta"}
    for jpath, text in _walk_strings(visible):
        if _RAW_DECIMAL_RE.search(text):
            errors.append(f"số thập phân thô tại {jpath}: ...{_RAW_DECIMAL_RE.search(text).group(0)}...")

    # Guardrail margin âm — chỉ check được khi generator nhúng meta.customer
    customer = (data.get("meta") or {}).get("customer") or {}
    if customer.get("is_margin_negative") is True and isinstance(approach, dict):
        promo_fields = {
            "opening_message": approach.get("opening_message") or "",
            "fallback_message": approach.get("fallback_message") or "",
            "talking_points": " ".join(approach.get("talking_points") or []),
            "cross_sell": " ".join(approach.get("cross_sell") or []),
        }
        for field, text in promo_fields.items():
            if isinstance(text, str) and _PROMO_RE.search(text):
                errors.append(f"khách margin âm nhưng approach.{field} chứa từ khóa khuyến mãi"
                              f" ('{_PROMO_RE.search(text).group(0)}')")

    if "nodes" in data:
        errors.extend(_lint_branching(data))

    return errors


def lint_file(path: str | Path) -> list[str]:
    """Parse file JSON rồi lint; lỗi parse cũng trả dạng list lỗi."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"không parse được JSON: {exc}"]
    return lint_script(data)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console
    except Exception:
        pass
    targets: list[Path] = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        targets.extend(sorted(p.glob("*.json")) if p.is_dir() else [p])
    if not targets:
        sys.exit("Usage: python scripts/approach_script_lint.py <dir-or-file> [...]")
    failed = 0
    for path in targets:
        errors = lint_file(path)
        if errors:
            failed += 1
            print(f"FAIL {path.name}")
            for e in errors:
                print(f"     - {e}")
        else:
            print(f"OK   {path.name}")
    print(f"\n{len(targets) - failed}/{len(targets)} pass")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
