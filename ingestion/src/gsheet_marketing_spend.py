import sys
import os
import pandas as pd
from datetime import datetime
import requests
import io


def _load_dotenv_local():
    """Load environment variables from .env.local if it exists (for local dev)."""
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

# Configuration
# Environment Variables (Standardized)
DATA_LAKE_PATH = os.environ.get("DBT_DATA_LAKE_PATH")

if not DATA_LAKE_PATH:
    raise ValueError(
        "DBT_DATA_LAKE_PATH environment variable is not set. "
        "Set via .env.docker (container) or .env.local (host)."
    )

# Replace with actual Marketing Spend Sheet URL
# Should be set in .dlt/secrets.toml or .env.local as SOURCES__SPREADSHEET_URL__MARKETING_SPEND
SHEET_URL = os.environ.get("SOURCES__SPREADSHEET_URL__MARKETING_SPEND", "https://docs.google.com/spreadsheets/d/1wQpT4lCZWrPE7fnbRNTKiNDRFzVT2u_WhN-9uY9u3lc/edit?usp=sharing") 

def fetch_and_save_marketing_spend():
    print(f"Starting Marketing Spend Ingestion...")
    
    # 1. Fetch CSV
    # Transform URL to export format
    if "/edit" in SHEET_URL:
        # Strip everything after /edit (including query params) and append export format
        base_url = SHEET_URL.split("/edit")[0]
        csv_url = f"{base_url}/export?format=csv"
    else:
        csv_url = SHEET_URL
        
    print(f"Downloading from: {csv_url}")
    
    # --- MAPPING LOGIC START ---
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    seeds_dir = os.path.join(base_dir, 'transformation', 'seeds')

    def load_csv_as_df(filename):
        return pd.read_csv(os.path.join(seeds_dir, filename))

    # 1. Load Reference Data
    try:
        df_spend_cat = load_csv_as_df('ref_spend_category.csv')
        df_sources = load_csv_as_df('ref_order_sources.csv')
        df_locations = load_csv_as_df('ref_branch_locations.csv')
    except Exception as e:
        print(f"Error loading reference seeds: {e}")
        raise e

    # 2. Build Dictionaries for Lookup
    
    # Map 1: Spend Category Name -> Spend Category Code
    # Key: 'Media Facebook', Value: 'media_facebook'
    spend_map = dict(zip(df_spend_cat['spend_category_name'], df_spend_cat['spend_category_code']))

    # Map 2: Target Channel Name -> (Source ID, Location ID)
    # This must match EXACTLY the logic in generate_dropdown.py
    channel_map = {}
    
    # 2a. Specific Sources
    specific = df_sources[df_sources['is_generic_source'] == False]
    for _, row in specific.iterrows():
        channel_map[row['name']] = (str(row['id']), None)

    # 2b. Generic Sources (Cross Join with Locations)
    generic = df_sources[df_sources['is_generic_source'] == True]
    for _, source_row in generic.iterrows():
        source_name = source_row['name']
        for _, loc_row in df_locations.iterrows():
            loc_name = loc_row['name']
            
            # Combination Name: "{Source Name} - {Location Name}"
            display_name = f"{source_name} - {loc_name}"
            channel_map[display_name] = (str(source_row['id']), str(loc_row['id']))
            
            # Special Case: POS shortcut
            if source_name == "Pos":
                channel_map[loc_name] = (str(source_row['id']), str(loc_row['id']))

    print(f"Loaded {len(spend_map)} Spend Categories and {len(channel_map)} Channels for mapping.")

    # --- MAPPING LOGIC END ---

    try:
        df = pd.read_csv(csv_url)
        print(f"Fetched {len(df)} rows from Google Sheet.")
        
        # 2. Clean and Standardize Columns
        # Expected: Date, Spend Category, Target Channel, Campaign ID, Spend Amount, Clicks, Impressions
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        
        # Validate Required Columns
        required_cols = ['date', 'spend_category', 'target_channel', 'spend_amount']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in Google Sheet: {missing_cols}")
        
        # 3. Apply Mapping
        def get_spend_code(name):
            return spend_map.get(name)

        def get_source_id(name):
            val = channel_map.get(name)
            return val[0] if val else None

        def get_location_id(name):
            val = channel_map.get(name)
            return val[1] if val else None

        df['spend_code'] = df['spend_category'].apply(get_spend_code)
        df['source_id'] = df['target_channel'].apply(get_source_id)
        df['location_id'] = df['target_channel'].apply(get_location_id)

        # Validation Report
        missing_spend = df[df['spend_code'].isna()]['spend_category'].unique()
        if len(missing_spend) > 0:
            print(f"WARNING: Unknown Spend Categories found (Check Spelling or Update Seeds): {missing_spend}")
            
        missing_channel = df[df['source_id'].isna()]['target_channel'].unique()
        if len(missing_channel) > 0:
            print(f"WARNING: Unknown Target Channels found (Check Spelling or Update Seeds): {missing_channel}")

        # 2. Clean and Standardize
        def clean_date(val):
            val = str(val).strip()
            # Handle MM/DD or DD/MM (e.g. "12/25") by appending Year
            # Heuristic: if length is short (e.g. 5 chars "12/25") and has /
            if len(val) <= 5 and '/' in val:
                return f"{val}/{datetime.now().year}"
            return val
            
        df['date'] = df['date'].apply(clean_date)
        # Using dayfirst=True for Vietnam context (DD/MM/YYYY)
        # errors='coerce' to safely handle bad data, but we hope clean_date fixes common issues
        df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
        
        # Check for NaT (failed parsing)
        if df['date'].isna().any():
            print(f"WARNING: {df['date'].isna().sum()} rows have invalid dates and will be dropped or ignored.")
            # Optional: drop them
            df = df.dropna(subset=['date'])
        
        # Partition Columns
        df['year'] = df['date'].dt.year.astype(int)

        # Clean Numeric Columns
        # Remove all non-digit characters (handling both comma and dot as thousand separators)
        # This assumes values are integers (e.g. 5,000,000 or 5.000.000 -> 5000000)
        for col in ['spend_amount', 'clicks', 'impressions']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)

        df['month'] = df['date'].dt.month.astype(int)
        
        # Format Date for Storage
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        # Keep source_id as None (NaN) where mapping failed — casting to str turns NaN into "nan" corrupting FK joins
        df['source_id'] = df['source_id'].where(df['source_id'].notna())
        df['ingest_method'] = 'google_sheet'
        
        # Target Path: gsheet_raw/marketing_spend_raw
        grouped = df.groupby(['year', 'month'])
        
        for (year, month), group in grouped:
            output_dir = os.path.join(DATA_LAKE_PATH, "gsheet_raw", "marketing_spend_raw",
                                      f"ingest_method=google_sheet", 
                                      f"year={year}", 
                                      f"month={month}")
            os.makedirs(output_dir, exist_ok=True)
            
            # Select only necessary columns to save
            # We keep the raw names for debugging/audit if needed, but for now let's stick to schema
            cols_to_save = ['date', 'spend_code', 'source_id', 'location_id', 'campaign_id', 'spend_amount', 'clicks', 'impressions', 'ingest_method', 'year', 'month']
            # Filter to columns that exist — campaign_id is optional in the sheet
            cols_to_save = [c for c in cols_to_save if c in group.columns]

            file_path = os.path.join(output_dir, "marketing_spend.parquet")

            print(f"Writing {len(group)} rows to {file_path}")
            group[cols_to_save].to_parquet(file_path, index=False)
            
        print("Ingestion Complete.")
        
    except Exception as e:
        print(f"Failed to ingest: {e}")
        raise e

def run(argv=None):
    fetch_and_save_marketing_spend()

if __name__ == "__main__":
    run()
