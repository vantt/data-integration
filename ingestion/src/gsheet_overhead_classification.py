"""Ingestion script for Overhead Account Classification from Google Sheets.

Reads the overhead account classification tab (gid=0) and writes to:
  gsheet_raw/overhead_account_classification_raw/

The classification sheet is the source of truth for how each MISA overhead
sub-account (6421/6422 family) is treated in the P&L:
  - keep_* accounts: pooled and allocated to channels
  - drop_traceable: excluded from pool (direct-traceable costs)
  - drop_promo_count_once: promotion costs counted once, not per-channel

Snapshot pattern (like us_shipment_prices): each ingest overwrites the parquet
snapshot. The sheet is the live master — no incremental partitioning needed.

Environment:
  DBT_DATA_LAKE_PATH                                    Path to data lake (required)
  SOURCES__SPREADSHEET_URL__OVERHEAD_CLASSIFICATION     Google Sheet URL (optional, has default)
"""
import sys
import os
import pandas as pd
from datetime import datetime

import gsheet_auth


def _load_dotenv_local():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../.."))
    env_local = os.path.join(project_root, ".env.local")
    if os.path.exists(env_local):
        with open(env_local, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value


_load_dotenv_local()

DATA_LAKE_PATH = os.environ.get("DBT_DATA_LAKE_PATH")
if not DATA_LAKE_PATH:
    raise ValueError(
        "DBT_DATA_LAKE_PATH environment variable is not set. "
        "Set via .env.docker (container) or .env.local (host)."
    )

_DEFAULT_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1fwdyzIdyXRkFva7FHgxwCPiQOY8s3m4MDATMsGY0YKM/edit?gid=0"
)
SHEET_URL = os.environ.get(
    "SOURCES__SPREADSHEET_URL__OVERHEAD_CLASSIFICATION",
    _DEFAULT_SHEET_URL,
)

# Tab identifier for the classification tab
_SHEET_GID = "0"

# Expected column names (after strip) — must match the Google Sheet exactly
_COL_ACCOUNT = "account"
_COL_ACCOUNT_GROUP = "account_group"
_COL_TREATMENT = "treatment"
_COL_POOL_ID = "pool_id"
_COL_BASE_METRIC = "base_metric"
_COL_CHANNEL = "channel"
_COL_EFFECTIVE_FROM = "effective_from"
_COL_EFFECTIVE_TO = "effective_to"
_COL_NOTE = "note"

# Allowed enum values — must match dbt accepted_values test
_VALID_TREATMENTS = {
    "keep_admin",
    "keep_handling",
    "keep_marketing",
    "keep_selling",
    "drop_traceable",
    "drop_promo_count_once",
}

_VALID_BASE_METRICS = {"net_revenue", "order_count", "gross_profit"}


def _parse_date_str(value) -> str | None:
    """Parse a date value to YYYY-MM-DD string, or None if blank/unparseable."""
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return pd.to_datetime(str(value).strip()).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _validate_columns(df: pd.DataFrame) -> list[str]:
    """Return list of missing required column names."""
    stripped = {str(c).strip() for c in df.columns}
    required = [_COL_ACCOUNT, _COL_TREATMENT]
    return [c for c in required if c not in stripped]


def _validate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Validate each row. Return (valid_df, issues list of (row, field, message)).

    Skips rows with unknown treatment (warn). Warns (but keeps) keep_* rows
    missing pool_id or base_metric — these are data-quality warnings, not fatal.
    """
    issues = []
    invalid = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # spreadsheet row number (header=1)

        # account must be non-empty (already filtered, but guard here too)
        account = row.get(_COL_ACCOUNT)
        if pd.isna(account) or str(account).strip() == "":
            issues.append((row_num, "account", "Missing account code"))
            invalid.add(idx)
            continue

        # treatment must be in the allowed enum — skip row if unknown
        treatment = str(row.get(_COL_TREATMENT, "")).strip()
        if treatment not in _VALID_TREATMENTS:
            issues.append((
                row_num, "treatment",
                f'Unknown treatment "{treatment}" — row skipped'
            ))
            invalid.add(idx)
            continue

        # For keep_* rows: warn if pool_id or base_metric is blank
        if treatment.startswith("keep_"):
            pool_id = row.get(_COL_POOL_ID)
            if pd.isna(pool_id) or str(pool_id).strip() == "":
                issues.append((row_num, "pool_id", f"keep_* row missing pool_id (treatment={treatment})"))

            base_metric = str(row.get(_COL_BASE_METRIC, "")).strip()
            if not base_metric:
                issues.append((row_num, "base_metric", f"keep_* row missing base_metric (treatment={treatment})"))
            elif base_metric not in _VALID_BASE_METRICS:
                issues.append((
                    row_num, "base_metric",
                    f'Invalid base_metric "{base_metric}" — expected one of {sorted(_VALID_BASE_METRICS)}'
                ))

    return df.drop(index=invalid), issues


def _print_validation_report(issues: list, total: int, valid: int):
    if not issues:
        print(f"  All {total} rows passed validation.")
        return
    print(f"\n  Validation Issues:")
    print(f"  {'Row':<5} {'Field':<20} {'Issue'}")
    print(f"  {'-'*5} {'-'*20} {'-'*60}")
    for row_num, field, msg in issues:
        print(f"  {row_num:<5} {field:<20} {msg}")
    skipped = total - valid
    if skipped:
        print(f"\n  {skipped} row(s) skipped.")
    print(f"  {valid} valid row(s) will be ingested.")


def _save_to_parquet(df: pd.DataFrame):
    """Overwrite snapshot parquet. Classification is a full snapshot on every run."""
    snapshot_dir = os.path.join(
        DATA_LAKE_PATH,
        "gsheet_raw",
        "overhead_account_classification_raw",
        "ingest_method=google_sheet",
        "snapshot",
    )
    os.makedirs(snapshot_dir, exist_ok=True)

    file_path = os.path.join(snapshot_dir, "overhead_account_classification.parquet")
    print(f"  Writing {len(df)} rows to {file_path}")
    df.to_parquet(file_path, index=False)


def fetch_and_save_overhead_classification():
    """Main ingestion function for Overhead Account Classification sheet."""
    print("Starting Overhead Account Classification Ingestion (gsheet_overhead_classification)...")

    print(f"Fetching via Sheets API (gid={_SHEET_GID}): {SHEET_URL}")
    raw = gsheet_auth.fetch_tab_as_dataframe(SHEET_URL, gid=_SHEET_GID)
    raw.columns = raw.iloc[0]
    df = raw[1:].reset_index(drop=True)
    print(f"Downloaded {len(df)} rows.")

    # Strip column names (handles leading/trailing spaces from Google Sheets export)
    df.columns = [str(c).strip() for c in df.columns]

    # Validate required columns exist
    missing_cols = _validate_columns(df)
    if missing_cols:
        raise ValueError(
            f"Required columns missing from sheet: {missing_cols}\n"
            f"Found columns: {list(df.columns)}"
        )

    # Drop fully empty rows (blank rows between sections)
    df = df.dropna(how="all")
    # Drop rows where account is empty (header-like or blank rows)
    df = df[df[_COL_ACCOUNT].notna() & (df[_COL_ACCOUNT].astype(str).str.strip() != "")]

    # Validate row data (skips rows with unknown treatment)
    valid_df, issues = _validate_rows(df)
    _print_validation_report(issues, len(df), len(valid_df))

    if len(valid_df) == 0:
        print("\nNo valid rows to ingest. Exiting.")
        return 1

    # Build output — account stays VARCHAR (MISA codes like 64211 are not integers)
    def _str_or_none(series_val) -> str | None:
        v = str(series_val).strip() if not pd.isna(series_val) else None
        return v if v else None

    result = pd.DataFrame()
    result["account"] = valid_df[_COL_ACCOUNT].astype(str).str.strip()
    result["account_group"] = (
        valid_df[_COL_ACCOUNT_GROUP].astype(str).str.strip()
        if _COL_ACCOUNT_GROUP in valid_df.columns
        else None
    )
    result["treatment"] = valid_df[_COL_TREATMENT].astype(str).str.strip()
    result["pool_id"] = (
        valid_df[_COL_POOL_ID].apply(_str_or_none)
        if _COL_POOL_ID in valid_df.columns
        else None
    )
    result["base_metric"] = (
        valid_df[_COL_BASE_METRIC].apply(_str_or_none)
        if _COL_BASE_METRIC in valid_df.columns
        else None
    )
    result["channel"] = (
        valid_df[_COL_CHANNEL].apply(_str_or_none)
        if _COL_CHANNEL in valid_df.columns
        else None
    )
    result["effective_from"] = (
        valid_df[_COL_EFFECTIVE_FROM].apply(_parse_date_str)
        if _COL_EFFECTIVE_FROM in valid_df.columns
        else None
    )
    result["effective_to"] = (
        valid_df[_COL_EFFECTIVE_TO].apply(_parse_date_str)
        if _COL_EFFECTIVE_TO in valid_df.columns
        else None
    )
    result["note"] = (
        valid_df[_COL_NOTE].apply(_str_or_none)
        if _COL_NOTE in valid_df.columns
        else None
    )
    result["ingest_method"] = "google_sheet"

    print(f"\nSaving {len(result)} rows to Data Lake...")
    _save_to_parquet(result)

    print("\nIngestion Complete.")
    return 1 if issues else 0


def run(argv=None):
    return fetch_and_save_overhead_classification()


if __name__ == "__main__":
    sys.exit(run() or 0)
