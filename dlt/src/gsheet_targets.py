import sys
import os
import pandas as pd
from datetime import datetime
import requests
import io

# Configuration
DATA_LAKE_PATH = "d:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZHt2iAD88OGgSRopVOkqEgusja-JpP4XqtiH4anhax4/edit?usp=sharing"

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
        # Use pandas to read directly
        df = pd.read_csv(csv_url)
        print(f"Downloaded {len(df)} rows.")
        
        # 2. Clean and Standardize
        # Ensure 'setup_date' is datetime
        if 'setup_date' in df.columns:
            df['setup_date'] = pd.to_datetime(df['setup_date'], errors='coerce')
            
            # Create Partition Columns
            df['year'] = df['setup_date'].dt.year.fillna(datetime.now().year).astype(int)
            df['month'] = df['setup_date'].dt.month.fillna(datetime.now().month).astype(int)
            
            # Format Date Key
            df['setup_date'] = df['setup_date'].dt.strftime('%Y-%m-%d')
        else:
            print("WARNING: 'setup_date' column missing. Using current date.")
            now = datetime.now()
            df['year'] = now.year
            df['month'] = now.month
            
        # Update ingest_method to user preference
        df['ingest_method'] = 'google_sheet'
        
        # 3. Write to Data Lake (Parquet)
        grouped = df.groupby(['year', 'month'])
        
        for (year, month), group in grouped:
            # Construct Path
            output_dir = os.path.join(DATA_LAKE_PATH, "sapo_raw", "targets_raw", 
                                      f"ingest_method=google_sheet", 
                                      f"year={year}", 
                                      f"month={month}")
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, "targets.parquet")
            
            print(f"Writing {len(group)} rows to {file_path}")
            group.to_parquet(file_path, index=False)
            
        print("Ingestion Complete.")
        
    except Exception as e:
        print(f"Failed to ingest: {e}")
        raise e

def run(argv=None):
    # argv is accepted for compatibility with other dlt scripts but not used here yet
    fetch_and_save_targets()

if __name__ == "__main__":
    run()
