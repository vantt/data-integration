"""Ingestion script for Team Configuration from Google Sheets.

Reads 2 tabs from the Team Config spreadsheet:
- teams: Team definitions with revenue_type and revenue_filter
- team_members: Staff membership with SCD2 (effective_from/to)

Writes to:
- sapo_raw/teams_raw/
- sapo_raw/team_members_raw/

Environment:
- DBT_DATA_LAKE_PATH: Path to data lake (required in Docker, auto-detected locally)
- SOURCES__SPREADSHEET_URL__TEAM_CONFIG: Google Sheet URL
"""
import sys
import os
import re
import pandas as pd
from datetime import datetime

# Load .env.local if exists (for local development)
def _load_dotenv_local():
    """Load environment variables from .env.local if it exists."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../.."))
    env_local = os.path.join(project_root, ".env.local")

    if os.path.exists(env_local):
        with open(env_local, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:  # Don't override existing
                        os.environ[key] = value

_load_dotenv_local()

# Configuration
DATA_LAKE_PATH = os.environ.get("DBT_DATA_LAKE_PATH")

if not DATA_LAKE_PATH:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up 2 levels from ingestion/src/ to project root, then into app_data/data_lake
    DATA_LAKE_PATH = os.path.abspath(os.path.join(current_dir, "../../app_data/data_lake"))
    print(f"Info: DBT_DATA_LAKE_PATH not set. Using local path: {DATA_LAKE_PATH}")

SHEET_URL = os.environ.get(
    "SOURCES__SPREADSHEET_URL__TEAM_CONFIG",
    "https://docs.google.com/spreadsheets/d/1bKZSbKX-ngkzum_OQXCaUbVzGFo3a-1B40EN_c2wN7Y/edit?usp=sharing"
)

# --- Validation rules ---
VALID_REVENUE_TYPES = {"member", "platform", "channel_name"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _get_xlsx_url(sheet_url):
    """Convert Google Sheets URL to XLSX export URL (all sheets)."""
    if "/edit" in sheet_url:
        base_url = sheet_url.split("/edit")[0]
        return f"{base_url}/export?format=xlsx"
    return sheet_url


def _fetch_sheets_from_xlsx(sheet_url):
    """Download XLSX and return dict of {sheet_name: DataFrame}.

    This is more reliable than CSV export with sheet= parameter,
    which doesn't work consistently with Google Sheets.
    """
    xlsx_url = _get_xlsx_url(sheet_url)
    print(f"Downloading XLSX from: {xlsx_url}")

    xlsx = pd.ExcelFile(xlsx_url)
    print(f"Found sheets: {xlsx.sheet_names}")

    sheets = {}
    for name in xlsx.sheet_names:
        sheets[name] = pd.read_excel(xlsx, sheet_name=name)

    return sheets


def _validate_teams(df):
    """Validate teams tab, return (valid_df, issues list)."""
    issues = []
    invalid_indices = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # Sheet row number (header=1, 0-indexed)

        # Required: team_code
        team_code = row.get("team_code")
        if pd.isna(team_code) or str(team_code).strip() == "":
            issues.append((row_num, "team_code", "Missing. Enter a unique team code (e.g. MKT, SOC)"))
            invalid_indices.add(idx)

        # Required: team_name
        team_name = row.get("team_name")
        if pd.isna(team_name) or str(team_name).strip() == "":
            issues.append((row_num, "team_name", "Missing. Enter team display name"))
            invalid_indices.add(idx)

        # Required: revenue_type
        revenue_type = row.get("revenue_type")
        if pd.isna(revenue_type) or str(revenue_type).strip() == "":
            issues.append((row_num, "revenue_type", "Missing. Use: member, platform, channel_name"))
            invalid_indices.add(idx)
        else:
            rt_clean = str(revenue_type).strip().lower()
            if rt_clean not in VALID_REVENUE_TYPES:
                issues.append((
                    row_num, "revenue_type",
                    f'"{revenue_type}" invalid. Use: {", ".join(sorted(VALID_REVENUE_TYPES))}'
                ))
                invalid_indices.add(idx)
            else:
                # If revenue_type is platform or channel_name, revenue_filter is required
                if rt_clean in ("platform", "channel_name"):
                    revenue_filter = row.get("revenue_filter")
                    if pd.isna(revenue_filter) or str(revenue_filter).strip() == "":
                        issues.append((
                            row_num, "revenue_filter",
                            f'Required when revenue_type={rt_clean}. Enter comma-separated values'
                        ))
                        invalid_indices.add(idx)

        # Optional: leader_email validation
        leader = row.get("leader_email")
        if not pd.isna(leader) and str(leader).strip() != "":
            leader_str = str(leader).strip()
            if not EMAIL_PATTERN.match(leader_str):
                issues.append((row_num, "leader_email", f'"{leader_str}" is not a valid email'))
                # Warning only

    valid_df = df.drop(index=invalid_indices)
    return valid_df, issues


def _validate_team_members(df, valid_team_codes):
    """Validate team_members tab, return (valid_df, issues list)."""
    issues = []
    invalid_indices = set()

    for idx, row in df.iterrows():
        row_num = idx + 2

        # Required: staff_email
        staff_email = row.get("staff_email")
        if pd.isna(staff_email) or str(staff_email).strip() == "":
            issues.append((row_num, "staff_email", "Missing. Enter staff email address"))
            invalid_indices.add(idx)
        else:
            email_str = str(staff_email).strip()
            if not EMAIL_PATTERN.match(email_str):
                issues.append((row_num, "staff_email", f'"{email_str}" is not a valid email'))
                invalid_indices.add(idx)

        # Required: team_code (must exist in teams tab)
        team_code = row.get("team_code")
        if pd.isna(team_code) or str(team_code).strip() == "":
            issues.append((row_num, "team_code", "Missing. Enter team code"))
            invalid_indices.add(idx)
        else:
            tc_clean = str(team_code).strip().upper()
            if tc_clean not in valid_team_codes:
                issues.append((
                    row_num, "team_code",
                    f'"{team_code}" not found in teams tab. Valid: {", ".join(sorted(valid_team_codes))}'
                ))
                invalid_indices.add(idx)

        # Required: effective_from
        eff_from = row.get("effective_from")
        if pd.isna(eff_from) or str(eff_from).strip() == "":
            issues.append((row_num, "effective_from", "Missing. Enter start date (e.g. 2025-01-01)"))
            invalid_indices.add(idx)
        else:
            try:
                pd.to_datetime(str(eff_from).strip())
            except (ValueError, TypeError):
                issues.append((row_num, "effective_from", f'Cannot parse "{eff_from}" as date'))
                invalid_indices.add(idx)

        # Optional: effective_to (if filled, must be >= effective_from)
        eff_to = row.get("effective_to")
        if not pd.isna(eff_to) and str(eff_to).strip() != "":
            try:
                to_date = pd.to_datetime(str(eff_to).strip())
                from_date = pd.to_datetime(str(eff_from).strip()) if not pd.isna(eff_from) else None
                if from_date and to_date < from_date:
                    issues.append((
                        row_num, "effective_to",
                        f'"{eff_to}" is before effective_from "{eff_from}"'
                    ))
                    invalid_indices.add(idx)
            except (ValueError, TypeError):
                issues.append((row_num, "effective_to", f'Cannot parse "{eff_to}" as date'))
                invalid_indices.add(idx)

    valid_df = df.drop(index=invalid_indices)
    return valid_df, issues


def _print_validation_report(tab_name, issues, total_rows, valid_count):
    """Print human-readable validation summary."""
    print(f"\n  [{tab_name}] Validation:")
    if not issues:
        print(f"    All {total_rows} rows passed validation.")
        return

    print(f"    {'Row':<5} {'Field':<18} {'Issue'}")
    print(f"    {'-'*5} {'-'*18} {'-'*50}")
    for row_num, field, message in issues:
        print(f"    {row_num:<5} {field:<18} {message}")

    skipped = total_rows - valid_count
    if skipped > 0:
        print(f"\n    {skipped} row(s) skipped due to errors.")
    print(f"    {valid_count} valid row(s) will be ingested.")


def _save_to_parquet(df, table_name, partition_col="year"):
    """Save DataFrame to parquet with year/month partitioning."""
    if partition_col not in df.columns:
        # Default partition: current year/month
        df["year"] = datetime.now().year
        df["month"] = datetime.now().month

    df["ingest_method"] = "google_sheet"

    # Handle empty dataframes - still write file with schema for dbt source
    if len(df) == 0:
        year = datetime.now().year
        month = datetime.now().month
        output_dir = os.path.join(
            DATA_LAKE_PATH, "sapo_raw", table_name,
            "ingest_method=google_sheet",
            f"year={year}",
            f"month={month}"
        )
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{table_name.replace('_raw', '')}.parquet")
        print(f"  Writing 0 rows (schema only) to {file_path}")
        df.to_parquet(file_path, index=False)
        return

    grouped = df.groupby(["year", "month"])

    for (year, month), group in grouped:
        output_dir = os.path.join(
            DATA_LAKE_PATH, "sapo_raw", table_name,
            "ingest_method=google_sheet",
            f"year={year}",
            f"month={month}"
        )
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, f"{table_name.replace('_raw', '')}.parquet")
        print(f"  Writing {len(group)} rows to {file_path}")
        group.to_parquet(file_path, index=False)


def fetch_and_save_team_config():
    """Main ingestion function for Team Config sheet."""
    print("Starting Team Config Ingestion (gsheet_team_config)...")

    # Expected sheet names (configurable via env vars)
    sheet_name_teams = os.environ.get("TEAM_CONFIG_SHEET_TEAMS", "teams")
    sheet_name_members = os.environ.get("TEAM_CONFIG_SHEET_MEMBERS", "team_members")

    try:
        # Download XLSX (all sheets) - more reliable than CSV with sheet= parameter
        sheets = _fetch_sheets_from_xlsx(SHEET_URL)

        # 1. Validate TEAMS tab
        if sheet_name_teams not in sheets:
            print(f"Error: Sheet '{sheet_name_teams}' not found. Available: {list(sheets.keys())}")
            return 1

        df_teams = sheets[sheet_name_teams]
        print(f"Processing {len(df_teams)} rows from '{sheet_name_teams}' tab.")

        # Normalize column names
        df_teams.columns = [c.strip().lower().replace(' ', '_') for c in df_teams.columns]

        valid_teams, teams_issues = _validate_teams(df_teams)
        _print_validation_report("teams", teams_issues, len(df_teams), len(valid_teams))

        if len(valid_teams) == 0:
            print("\nNo valid teams to ingest. Exiting.")
            return 1

        # Extract valid team codes for member validation
        valid_team_codes = set(valid_teams["team_code"].astype(str).str.strip().str.upper())

        # Clean teams data
        valid_teams["team_code"] = valid_teams["team_code"].astype(str).str.strip().str.upper()
        valid_teams["team_name"] = valid_teams["team_name"].astype(str).str.strip()
        valid_teams["revenue_type"] = valid_teams["revenue_type"].astype(str).str.strip().str.lower()

        # Ensure optional columns exist with defaults
        for col in ["revenue_filter", "leader_email", "description"]:
            if col not in valid_teams.columns:
                valid_teams[col] = ""
            else:
                valid_teams[col] = valid_teams[col].fillna("").astype(str).str.strip()

        # Add partition columns (use current date for config tables)
        valid_teams["year"] = datetime.now().year
        valid_teams["month"] = datetime.now().month

        # 2. Validate TEAM_MEMBERS tab
        if sheet_name_members not in sheets:
            print(f"\nWarning: Sheet '{sheet_name_members}' not found. Available: {list(sheets.keys())}")
            df_members = pd.DataFrame()
        else:
            df_members = sheets[sheet_name_members]
            print(f"\nProcessing {len(df_members)} rows from '{sheet_name_members}' tab.")

        valid_members = pd.DataFrame()
        members_issues = []

        if len(df_members) > 0:
            # Normalize column names
            df_members.columns = [c.strip().lower().replace(' ', '_') for c in df_members.columns]

            valid_members, members_issues = _validate_team_members(df_members, valid_team_codes)
            _print_validation_report("team_members", members_issues, len(df_members), len(valid_members))

        if len(valid_members) == 0:
            print("\nNo valid team members to ingest. Writing empty schema.")
            # Create empty dataframe with correct schema to prevent dbt source error
            valid_members = pd.DataFrame(columns=[
                "staff_email", "team_code", "effective_from", "effective_to",
                "year", "month", "ingest_method"
            ])
            valid_members["year"] = datetime.now().year
            valid_members["month"] = datetime.now().month
        else:
            # Clean members data
            valid_members["staff_email"] = valid_members["staff_email"].astype(str).str.strip().str.lower()
            valid_members["team_code"] = valid_members["team_code"].astype(str).str.strip().str.upper()

            # Parse dates
            valid_members["effective_from"] = pd.to_datetime(
                valid_members["effective_from"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")

            if "effective_to" in valid_members.columns:
                valid_members["effective_to"] = pd.to_datetime(
                    valid_members["effective_to"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
            else:
                valid_members["effective_to"] = None

            # Partition by current date (config tables are always "current snapshot")
            valid_members["year"] = datetime.now().year
            valid_members["month"] = datetime.now().month

        # 3. Save to Data Lake
        print("\nSaving to Data Lake...")
        _save_to_parquet(valid_teams, "teams_raw")
        _save_to_parquet(valid_members, "team_members_raw")

        print("\nIngestion Complete.")

        # Return non-zero if any rows were skipped
        if len(teams_issues) > 0 or len(members_issues) > 0:
            return 1
        return 0

    except Exception as e:
        print(f"Failed to ingest: {e}")
        raise e


def run(argv=None):
    return fetch_and_save_team_config()


if __name__ == "__main__":
    sys.exit(run() or 0)
