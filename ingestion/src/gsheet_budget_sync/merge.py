"""Historical merge (budget seed only — policy sheet is append-only by convention) +
atomic CSV write shared by both seeds.

Historical merge: rows for period_month < current month are kept as-is from the
existing seed; only current-month-and-future rows are replaced by the fresh pull.
This survives finance deleting old month columns from the sheet.
"""
import os

import pandas as pd

from .budget_transform import SEED_BUDGET_COLUMNS


def merge_historical_budget(existing_path: str, new_df: pd.DataFrame, current_month_start: str) -> pd.DataFrame:
    """Keep rows for period_month < current_month_start from the existing seed as-is;
    replace current-month-and-future rows with the fresh pull (new_df).
    """
    if os.path.exists(existing_path):
        old_df = pd.read_csv(existing_path, dtype=str, keep_default_na=False, na_filter=False)
    else:
        old_df = pd.DataFrame(columns=SEED_BUDGET_COLUMNS)

    old_kept = old_df[old_df["period_month"] < current_month_start] if len(old_df) else old_df
    new_kept = new_df[new_df["period_month"] >= current_month_start] if len(new_df) else new_df

    merged = pd.concat([old_kept, new_kept], ignore_index=True)
    if len(merged):
        merged = merged.sort_values(["period_month", "cashflow_line", "direction"]).reset_index(drop=True)
    return merged[SEED_BUDGET_COLUMNS] if len(merged) else pd.DataFrame(columns=SEED_BUDGET_COLUMNS)


def _write_csv_atomic(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)
