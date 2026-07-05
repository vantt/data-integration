"""Parse + validate + build rows for the ALLOCATION_POLICY tab (quarterly waterfall config)."""
from collections import defaultdict

import pandas as pd

from .fetch import ValidationError, _parse_vnd, _fmt_num

# --- ALLOCATION_POLICY column positions (0-indexed) — mirrors AP_COL ---
AP_COL_PRIORITY = 0
AP_COL_BUCKET = 1
AP_COL_RULE_TYPE = 2
AP_COL_VALUE = 3
AP_COL_EFFECTIVE_FROM = 4
AP_COL_EFFECTIVE_TO = 5
POLICY_HEADER_ROWS = 1     # row1 = column names only (verified against live sheet 2026-07-05)

VALID_RULE_TYPES = {"fill_to_target", "from_plan", "fixed", "pct_remaining", "remainder"}
RULE_TYPES_WITH_VALUE = {"fill_to_target", "fixed", "pct_remaining"}

SEED_POLICY_COLUMNS = [
    "priority", "bucket", "rule_type", "value", "effective_from", "effective_to", "notes",
]


def parse_policy_matrix(raw_df: pd.DataFrame):
    if raw_df.shape[0] < POLICY_HEADER_ROWS or raw_df.shape[1] < 6:
        raise ValidationError(
            "ALLOCATION_POLICY tab structure invalid: cần header row + 6 cột "
            "(Ưu Tiên|Bucket|Rule Type|Value|Effective From|Effective To)"
        )

    items = []
    warnings: list = []
    for i in range(POLICY_HEADER_ROWS, raw_df.shape[0]):
        sheet_row = i + 1
        row = raw_df.iloc[i]
        bucket = str(row[AP_COL_BUCKET]).strip()
        rule_type = str(row[AP_COL_RULE_TYPE]).strip()
        if not bucket and not rule_type:
            continue  # empty template row — silent skip

        items.append({
            "sheet_row": sheet_row,
            "priority_raw": str(row[AP_COL_PRIORITY]).strip(),
            "bucket": bucket,
            "rule_type": rule_type,
            "value_raw": str(row[AP_COL_VALUE]).strip(),
            "eff_from_raw": str(row[AP_COL_EFFECTIVE_FROM]).strip(),
            "eff_to_raw": str(row[AP_COL_EFFECTIVE_TO]).strip(),
        })

    return items, warnings


def _validate_policy_cross_rows(parsed: list) -> list:
    """Mirrors validatePolicyCrossRows() in validate-budget-sheet.gs."""
    errors = []

    active = [p for p in parsed if not p["eff_to"]]
    remainder_rows = [p for p in active if p["rule_type"] == "remainder"]
    if not remainder_rows:
        errors.append(
            "ALLOCATION_POLICY: thiếu dòng 'remainder' đang active (effective_to trống) "
            "— bắt buộc phải có 1 dòng remainder là priority cuối"
        )
    else:
        remainder_priority = min(p["priority"] for p in remainder_rows)
        after = [p for p in active if p["priority"] > remainder_priority]
        if after:
            names = ", ".join(f"{p['bucket']} (P{p['priority']})" for p in after)
            errors.append(f"ALLOCATION_POLICY: 'remainder' không phải priority cuối — có bucket sau nó: {names}")

    by_bucket = defaultdict(list)
    for p in parsed:
        by_bucket[p["bucket"]].append(p)

    for bucket, rows in by_bucket.items():
        if len(rows) < 2:
            continue
        rows_sorted = sorted(rows, key=lambda r: r["eff_from"])
        for a, b in zip(rows_sorted, rows_sorted[1:]):
            if not a["eff_to"]:
                errors.append(
                    f"ALLOCATION_POLICY bucket '{bucket}': dòng từ {a['eff_from'].date()} không có "
                    f"effective_to nhưng có dòng tiếp theo từ {b['eff_from'].date()}"
                )
                continue
            if b["eff_from"] < a["eff_to"]:
                errors.append(
                    f"ALLOCATION_POLICY bucket '{bucket}': OVERLAP giữa dòng từ {a['eff_from'].date()} "
                    f"và dòng từ {b['eff_from'].date()}"
                )
            elif b["eff_from"] > a["eff_to"] + pd.Timedelta(days=1):
                errors.append(
                    f"ALLOCATION_POLICY bucket '{bucket}': GAP từ {a['eff_to'].date()} đến {b['eff_from'].date()}"
                )

    return errors


def validate_and_build_policy_rows(items: list):
    errors = []
    parsed = []

    for it in items:
        row_no = it["sheet_row"]
        bucket = it["bucket"]
        rule_type = it["rule_type"]

        try:
            priority = int(float(it["priority_raw"]))
            if priority <= 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(f"ALLOCATION_POLICY row {row_no}: priority '{it['priority_raw']}' phải là số nguyên dương")
            continue

        if not bucket:
            errors.append(f"ALLOCATION_POLICY row {row_no}: bucket không được để trống")
            continue

        if rule_type not in VALID_RULE_TYPES:
            errors.append(
                f"ALLOCATION_POLICY row {row_no}: rule_type '{rule_type}' không hợp lệ "
                f"(phải là {sorted(VALID_RULE_TYPES)})"
            )
            continue

        value_raw = it["value_raw"]
        value_val = _parse_vnd(value_raw) if value_raw else None
        if rule_type in RULE_TYPES_WITH_VALUE:
            if value_val is None or value_val <= 0:
                errors.append(
                    f"ALLOCATION_POLICY row {row_no}: rule_type='{rule_type}' bắt buộc value dương, "
                    f"nhận '{value_raw}'"
                )
                continue
            if rule_type == "pct_remaining" and not (0 < value_val <= 100):
                errors.append(f"ALLOCATION_POLICY row {row_no}: pct_remaining value phải 0-100, nhận {value_val}")
                continue
        elif value_val is not None:
            errors.append(f"ALLOCATION_POLICY row {row_no}: rule_type='{rule_type}' không dùng value — để trống")
            continue

        eff_from_raw = it["eff_from_raw"]
        if not eff_from_raw:
            errors.append(f"ALLOCATION_POLICY row {row_no}: effective_from bắt buộc")
            continue
        try:
            eff_from_dt = pd.to_datetime(eff_from_raw)
        except Exception:
            errors.append(f"ALLOCATION_POLICY row {row_no}: effective_from '{eff_from_raw}' không phải ngày hợp lệ")
            continue

        eff_to_raw = it["eff_to_raw"]
        eff_to_dt = None
        if eff_to_raw:
            try:
                eff_to_dt = pd.to_datetime(eff_to_raw)
            except Exception:
                errors.append(f"ALLOCATION_POLICY row {row_no}: effective_to '{eff_to_raw}' không phải ngày hợp lệ")
                continue
            if eff_to_dt <= eff_from_dt:
                errors.append(f"ALLOCATION_POLICY row {row_no}: effective_to phải sau effective_from")
                continue

        parsed.append({
            "row_no": row_no,
            "priority": priority,
            "bucket": bucket,
            "rule_type": rule_type,
            "value": value_val,
            "eff_from": eff_from_dt,
            "eff_to": eff_to_dt,
        })

    if errors:
        return None, errors

    cross_errors = _validate_policy_cross_rows(parsed)
    if cross_errors:
        return None, cross_errors

    out_rows = [{
        "priority": p["priority"],
        "bucket": p["bucket"],
        "rule_type": p["rule_type"],
        "value": _fmt_num(p["value"]) if p["value"] is not None else "",
        "effective_from": p["eff_from"].strftime("%Y-%m-%d"),
        "effective_to": p["eff_to"].strftime("%Y-%m-%d") if p["eff_to"] is not None else "",
        "notes": "",
    } for p in parsed]

    df = pd.DataFrame(out_rows, columns=SEED_POLICY_COLUMNS)
    df = df.sort_values("priority").reset_index(drop=True)
    return df, []
