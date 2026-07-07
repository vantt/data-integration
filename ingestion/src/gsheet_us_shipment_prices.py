"""Ingestion script for US Shipment Prices from Google Sheets.

Reads the US Shipment Price List tab (gid=304875363) and writes to:
  gsheet_raw/us_shipment_prices_raw/

The price list defines actual deal prices per SKU for US CrossBorder orders.
Sapo records US shipment prices as 0 (special deal); this sheet is the source of truth.

Snapshot pattern (like team_config): sheet maintains history via multiple rows per SKU
with different effective_from dates. Each ingest overwrites the parquet snapshot.

Environment:
  DBT_DATA_LAKE_PATH                          Path to data lake (required)
  SOURCES__SPREADSHEET_URL__US_SHIPMENT_PRICES Google Sheet URL (optional, has default)
"""
import sys
import os
import re
import shutil
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
    "1PWPQzzML_-i9yUrjGyhUcW0ABkrGEtXE2k49EaW4gwc/edit?gid=304875363"
)
SHEET_URL = os.environ.get(
    "SOURCES__SPREADSHEET_URL__US_SHIPMENT_PRICES",
    _DEFAULT_SHEET_URL,
)

# Tab identifier for the price list tab
_SHEET_GID = "304875363"

# Expected column name constants (after strip) — must match the Google Sheet exactly
_COL_SKU = "SKU"
_COL_PRODUCT_NAME = "Tên sản phẩm"
_COL_COST_PRICE = "Đơn giá mua (chưa bao gồm VAT)"
_COL_US_PRICE_EXCL = "Giá xuất US (mới)"
_COL_US_PRICE_INCL = "Giá xuất US (mới) (VAT 8%)"
_COL_RETAIL_PRICE = "Giá niêm yết"
_COL_FG_CARE = "Xuất FG Care"
_COL_MARGIN_PCT = "Tỷ lệ lợi nhuận"
_COL_EFFECTIVE_FROM = "effective_from"

def _parse_vnd(value) -> float | None:
    """Strip VND formatting (spaces, commas) and parse as float."""
    try:
        cleaned = str(value).replace(",", "").replace(" ", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_margin_pct(value) -> float | None:
    """Parse margin percentage string (e.g. '22.55%') to decimal (0.2255)."""
    try:
        cleaned = str(value).replace("%", "").strip()
        return float(cleaned) / 100.0
    except (ValueError, TypeError):
        return None


def _validate_columns(df: pd.DataFrame) -> list[str]:
    """Return list of missing required column names."""
    stripped = {str(c).strip() for c in df.columns}
    required = [_COL_SKU, _COL_US_PRICE_EXCL, _COL_US_PRICE_INCL, _COL_EFFECTIVE_FROM]
    return [c for c in required if c not in stripped]


def _validate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Validate each row. Return (valid_df, issues list of (row, field, message))."""
    issues = []
    invalid = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # spreadsheet row number (header=1)

        sku = row.get(_COL_SKU)
        if pd.isna(sku) or str(sku).strip() == "":
            issues.append((row_num, "SKU", "Missing SKU"))
            invalid.add(idx)
            continue  # Can't validate further without SKU

        price_raw = row.get(_COL_US_PRICE_EXCL)
        price = _parse_vnd(price_raw)
        if price is None or price <= 0:
            issues.append((row_num, "Giá xuất US (mới)", f'Cannot parse or invalid: "{price_raw}"'))
            invalid.add(idx)

        eff_raw = row.get(_COL_EFFECTIVE_FROM)
        if pd.isna(eff_raw) or str(eff_raw).strip() == "":
            issues.append((row_num, "effective_from", "Missing effective_from date"))
            invalid.add(idx)
        else:
            try:
                pd.to_datetime(str(eff_raw).strip())
            except (ValueError, TypeError):
                issues.append((row_num, "effective_from", f'Cannot parse date: "{eff_raw}"'))
                invalid.add(idx)

    return df.drop(index=invalid), issues


def _print_validation_report(issues: list, total: int, valid: int):
    if not issues:
        print(f"  All {total} rows passed validation.")
        return
    print(f"\n  Validation Issues:")
    print(f"  {'Row':<5} {'Field':<30} {'Issue'}")
    print(f"  {'-'*5} {'-'*30} {'-'*50}")
    for row_num, field, msg in issues:
        print(f"  {row_num:<5} {field:<30} {msg}")
    skipped = total - valid
    if skipped:
        print(f"\n  {skipped} row(s) skipped.")
    print(f"  {valid} valid row(s) will be ingested.")


def _save_to_parquet(df: pd.DataFrame):
    """Overwrite snapshot parquet. Sheet maintains history; each run = fresh snapshot."""
    base_dir = os.path.join(
        DATA_LAKE_PATH, "gsheet_raw", "us_shipment_prices_raw", "ingest_method=google_sheet"
    )

    # Remove legacy partition subdirs if any
    if os.path.exists(base_dir):
        for entry in os.listdir(base_dir):
            entry_path = os.path.join(base_dir, entry)
            if os.path.isdir(entry_path) and entry.startswith("year="):
                print(f"  Removing legacy partition dir: {entry_path}")
                shutil.rmtree(entry_path)

    snapshot_dir = os.path.join(base_dir, "snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)

    file_path = os.path.join(snapshot_dir, "us_shipment_prices.parquet")
    print(f"  Writing {len(df)} rows to {file_path}")
    df.to_parquet(file_path, index=False)


def fetch_and_save_us_shipment_prices():
    """Main ingestion function for US Shipment Prices sheet."""
    print("Starting US Shipment Prices Ingestion (gsheet_us_shipment_prices)...")

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

    # Drop fully empty rows (empty STT rows between sections)
    df = df.dropna(how="all")
    # Drop rows where SKU is empty (sub-header rows, total rows, etc.)
    df = df[df[_COL_SKU].notna() & (df[_COL_SKU].astype(str).str.strip() != "")]

    # Validate row data
    valid_df, issues = _validate_rows(df)
    _print_validation_report(issues, len(df), len(valid_df))

    if len(valid_df) == 0:
        print("\nNo valid rows to ingest. Exiting.")
        return 1

    # Clean and transform
    result = pd.DataFrame()
    result["sku"] = valid_df[_COL_SKU].astype(str).str.strip().str.upper()
    result["product_name"] = valid_df[_COL_PRODUCT_NAME].astype(str).str.strip() if _COL_PRODUCT_NAME in valid_df.columns else ""
    result["cost_price"] = valid_df[_COL_COST_PRICE].apply(_parse_vnd) if _COL_COST_PRICE in valid_df.columns else None
    result["us_price_excl_vat"] = valid_df[_COL_US_PRICE_EXCL].apply(_parse_vnd)
    result["us_price_incl_vat"] = valid_df[_COL_US_PRICE_INCL].apply(_parse_vnd) if _COL_US_PRICE_INCL in valid_df.columns else None
    result["retail_price"] = valid_df[_COL_RETAIL_PRICE].apply(_parse_vnd) if _COL_RETAIL_PRICE in valid_df.columns else None
    result["fg_care_price"] = valid_df[_COL_FG_CARE].apply(_parse_vnd) if _COL_FG_CARE in valid_df.columns else None
    result["margin_pct"] = valid_df[_COL_MARGIN_PCT].apply(_parse_margin_pct) if _COL_MARGIN_PCT in valid_df.columns else None
    result["effective_from"] = pd.to_datetime(
        valid_df[_COL_EFFECTIVE_FROM].astype(str).str.strip(), errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    result["ingest_method"] = "google_sheet"

    # Deduplicate: if same SKU+effective_from appears multiple times, keep first
    dupes = result.duplicated(subset=["sku", "effective_from"], keep=False)
    if dupes.any():
        dupe_skus = result.loc[dupes, "sku"].unique().tolist()
        print(f"\n  Warning: Duplicate (SKU, effective_from) rows detected: {dupe_skus}")
        print(f"  Keeping first occurrence of each duplicate.")
        result = result.drop_duplicates(subset=["sku", "effective_from"], keep="first")

    print(f"\nSaving {len(result)} rows to Data Lake...")
    _save_to_parquet(result)

    print("\nIngestion Complete.")
    return 1 if issues else 0


def run(argv=None):
    return fetch_and_save_us_shipment_prices()


if __name__ == "__main__":
    sys.exit(run() or 0)
