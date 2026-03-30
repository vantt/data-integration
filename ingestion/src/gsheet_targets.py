import sys
import os
import re
import pandas as pd
from datetime import datetime

# Configuration
DATA_LAKE_PATH = os.environ.get("DBT_DATA_LAKE_PATH")

if not DATA_LAKE_PATH:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    DATA_LAKE_PATH = os.path.abspath(os.path.join(current_dir, "../../../app_data/data_lake"))
    print(f"Warning: DBT_DATA_LAKE_PATH not set. Using calculated path: {DATA_LAKE_PATH}")

SHEET_URL = os.environ.get(
    "SOURCES__SPREADSHEET_URL__TARGETS",
    "https://docs.google.com/spreadsheets/d/1ZHt2iAD88OGgSRopVOkqEgusja-JpP4XqtiH4anhax4/edit?usp=sharing"
)

# --- Validation rules ---
VALID_CYCLE_TYPES = {"daily", "weekly", "monthly", "quarterly", "yearly"}
VALID_METRIC_CODES = {"gmv", "orders", "net_revenue", "profit"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _parse_target_value(raw):
    """Strip currency formatting ($, commas) and parse as float."""
    try:
        cleaned = str(raw).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _validate_rows(df):
    """Validate each row, return (valid_df, issues list).

    Issues format: list of (row_number, field, message) tuples.
    Valid rows are returned for ingestion; invalid rows are skipped.
    """
    issues = []
    invalid_indices = set()

    for idx, row in df.iterrows():
        # Sheet row number = idx + 2 (header=1, 0-indexed data)
        row_num = idx + 2

        # Required: cycle_start_date
        date_col = "cycle_start_date" if "cycle_start_date" in df.columns else "setup_date"
        date_val = row.get(date_col)
        if pd.isna(date_val) or str(date_val).strip() == "":
            issues.append((row_num, date_col, "Missing. Enter the first day of the cycle (e.g. 2026-03-01)"))
            invalid_indices.add(idx)

        # Required: metric_code
        metric = row.get("metric_code")
        if pd.isna(metric) or str(metric).strip() == "":
            issues.append((row_num, "metric_code", "Missing. Enter a metric code (e.g. gmv, orders, profit)"))
            invalid_indices.add(idx)
        else:
            metric_clean = str(metric).strip().lower()
            if metric_clean not in VALID_METRIC_CODES:
                issues.append((
                    row_num, "metric_code",
                    f'"{metric}" not recognized. Valid: {", ".join(sorted(VALID_METRIC_CODES))}'
                ))
                # Warning only — don't skip, new metric codes may be intentional

        # Required: target_value must be a parseable positive number
        raw_val = row.get("target_value")
        parsed = _parse_target_value(raw_val)
        if parsed is None:
            issues.append((
                row_num, "target_value",
                f'Cannot parse "{raw_val}". Enter a number (currency formatting like $100,000 is OK)'
            ))
            invalid_indices.add(idx)
        elif parsed <= 0:
            issues.append((row_num, "target_value", f'Value is {parsed}. Must be greater than 0'))
            invalid_indices.add(idx)

        # Required: cycle_type
        cycle_type = row.get("cycle_type")
        if pd.isna(cycle_type) or str(cycle_type).strip() == "":
            issues.append((row_num, "cycle_type", "Missing. Use: daily, weekly, monthly, quarterly, yearly"))
            invalid_indices.add(idx)
        else:
            ct_clean = str(cycle_type).strip().lower()
            if ct_clean not in VALID_CYCLE_TYPES:
                issues.append((
                    row_num, "cycle_type",
                    f'"{cycle_type}" invalid. Use: {", ".join(sorted(VALID_CYCLE_TYPES))}'
                ))
                invalid_indices.add(idx)

        # Optional: repeat_until — if filled, must be a valid date >= cycle_start_date
        repeat_val = row.get("repeat_until")
        if not pd.isna(repeat_val) and str(repeat_val).strip() != "":
            try:
                repeat_date = pd.to_datetime(str(repeat_val).strip())
                start_date = pd.to_datetime(str(date_val).strip()) if not pd.isna(date_val) else None
                if start_date and repeat_date < start_date:
                    issues.append((
                        row_num, "repeat_until",
                        f'"{repeat_val}" is before cycle_start_date "{date_val}". Must be equal or later'
                    ))
                    invalid_indices.add(idx)
            except (ValueError, TypeError):
                issues.append((
                    row_num, "repeat_until",
                    f'Cannot parse "{repeat_val}" as a date. Use format: 2026-12-31'
                ))
                invalid_indices.add(idx)

        # Optional: staff_email — if filled, must look like an email
        staff = row.get("staff_email")
        if not pd.isna(staff) and str(staff).strip() != "":
            staff_str = str(staff).strip()
            if not EMAIL_PATTERN.match(staff_str):
                issues.append((
                    row_num, "staff_email",
                    f'"{staff_str}" is not a valid email. Use format: name@company.com'
                ))
                # Warning only — don't skip

    valid_df = df.drop(index=invalid_indices)
    return valid_df, issues


def _print_validation_report(issues, total_rows, valid_count):
    """Print human-readable validation summary."""
    if not issues:
        print(f"\n  All {total_rows} rows passed validation.")
        return

    # Separate errors (rows skipped) from warnings (rows kept)
    print(f"\n  Validation Issues:")
    print(f"  {'Row':<5} {'Field':<18} {'Issue'}")
    print(f"  {'-'*5} {'-'*18} {'-'*50}")
    for row_num, field, message in issues:
        print(f"  {row_num:<5} {field:<18} {message}")

    skipped = total_rows - valid_count
    if skipped > 0:
        print(f"\n  {skipped} row(s) skipped due to errors.")
    print(f"  {valid_count} valid row(s) will be ingested.")


def fetch_and_save_targets():
    print(f"Starting Target Ingestion (gsheet_targets)...")

    # 1. Fetch CSV
    if "/edit" in SHEET_URL:
        csv_url = SHEET_URL.replace("/edit?usp=sharing", "/export?format=csv")
        csv_url = csv_url.replace("/edit", "/export?format=csv")
    else:
        csv_url = SHEET_URL

    print(f"Downloading from: {csv_url}")
    try:
        df = pd.read_csv(csv_url)
        print(f"Downloaded {len(df)} rows.")

        # 2. Validate raw data before any transformation
        valid_df, issues = _validate_rows(df)
        _print_validation_report(issues, len(df), len(valid_df))

        if len(valid_df) == 0:
            print("\nNo valid rows to ingest. Exiting.")
            return

        df = valid_df

        # 3. Clean and Standardize
        date_col = "cycle_start_date" if "cycle_start_date" in df.columns else "setup_date"
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        # Partition columns
        df["year"] = df[date_col].dt.year.fillna(datetime.now().year).astype(int)
        df["month"] = df[date_col].dt.month.fillna(datetime.now().month).astype(int)

        # Format date
        df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")

        # Clean target_value: strip currency formatting
        df["target_value"] = df["target_value"].apply(_parse_target_value)

        # Normalize metric_code to lowercase
        df["metric_code"] = df["metric_code"].astype(str).str.strip().str.lower()

        # Normalize cycle_type to lowercase
        if "cycle_type" in df.columns:
            df["cycle_type"] = df["cycle_type"].astype(str).str.strip().str.lower()

        # Clean repeat_until: parse as date string, ensure column always exists
        if "repeat_until" not in df.columns:
            df["repeat_until"] = pd.NaT
        df["repeat_until"] = pd.to_datetime(df["repeat_until"], errors="coerce").dt.strftime("%Y-%m-%d")

        df["ingest_method"] = "google_sheet"

        # 4. Write to Data Lake (Parquet)
        grouped = df.groupby(["year", "month"])

        for (year, month), group in grouped:
            output_dir = os.path.join(
                DATA_LAKE_PATH, "sapo_raw", "targets_raw",
                "ingest_method=google_sheet",
                f"year={year}",
                f"month={month}"
            )
            os.makedirs(output_dir, exist_ok=True)

            file_path = os.path.join(output_dir, "targets.parquet")

            print(f"Writing {len(group)} rows to {file_path}")
            group.to_parquet(file_path, index=False)

        print("Ingestion Complete.")

        # Return non-zero if any rows were skipped
        if len(issues) > 0 and len(valid_df) < len(df) + len(issues):
            return 1
        return 0

    except Exception as e:
        print(f"Failed to ingest: {e}")
        raise e


def run(argv=None):
    fetch_and_save_targets()


if __name__ == "__main__":
    run()
