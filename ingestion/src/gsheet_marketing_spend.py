import sys
import os
import pandas as pd
from datetime import datetime
import requests
import io

# Configuration
# Environment Variables (Standardized)
DATA_LAKE_PATH = os.environ.get("DBT_DATA_LAKE_PATH")

if not DATA_LAKE_PATH:
    # Fallback for local testing
    current_dir = os.path.dirname(os.path.abspath(__file__))
    DATA_LAKE_PATH = os.path.abspath(os.path.join(current_dir, "../../../app_data/data_lake"))
    print(f"Warning: DBT_DATA_LAKE_PATH not set. Using calculated path: {DATA_LAKE_PATH}")

# Replace with actual Marketing Spend Sheet URL
# Should be set in .dlt/secrets.toml or .env.local as SOURCES__SPREADSHEET_URL__MARKETING_SPEND
SHEET_URL = os.environ.get("SOURCES__SPREADSHEET_URL__MARKETING_SPEND", "https://docs.google.com/spreadsheets/d/1wQpT4lCZWrPE7fnbRNTKiNDRFzVT2u_WhN-9uY9u3lc/edit?usp=sharing") 

def fetch_and_save_marketing_spend():
    print(f"Starting Marketing Spend Ingestion...")
    
    # 1. Fetch CSV
    # Mocking URL transformation for export
    if "/edit" in SHEET_URL:
        # Note: Ideally query parameters should be handled more robustly
        csv_url = SHEET_URL.replace("/edit", "/export?format=csv")
    else:
        csv_url = SHEET_URL
        
    print(f"Downloading from: {csv_url}")
    try:
        # df = pd.read_csv(csv_url) # Uncomment when real URL is ready
        
        # MOCK DATA FOR DEVELOPMENT (Until User provides real Sheet)date
        data = {
            'date': ['2026-01-01', '2026-01-01', '2026-01-02'],
            'spend_code': ['fb_main', 'google_sa', 'fb_main'],
            'campaign_id': ['CMP_001', 'CMP_002', 'CMP_001'],
            'spend_amount': [1000000, 500000, 1200000],
            'clicks': [100, 50, 110],
            'impressions': [5000, 2000, 5500]
        }
        df = pd.DataFrame(data)
        print(f"Generated {len(df)} rows (Mock Data).")
        
        # 2. Clean and Standardize
        df['date'] = pd.to_datetime(df['date'])
        
        # Partition Columns
        df['year'] = df['date'].dt.year.astype(int)
        df['month'] = df['date'].dt.month.astype(int)
        
        # Format Date for Storage
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        df['ingest_method'] = 'google_sheet'
        
        # 3. Write to Data Lake (Parquet)
        # Target Path: sapo_raw/marketing_spend_raw
        grouped = df.groupby(['year', 'month'])
        
        for (year, month), group in grouped:
            output_dir = os.path.join(DATA_LAKE_PATH, "sapo_raw", "marketing_spend_raw", 
                                      f"ingest_method=google_sheet", 
                                      f"year={year}", 
                                      f"month={month}")
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, "marketing_spend.parquet")
            
            print(f"Writing {len(group)} rows to {file_path}")
            group.to_parquet(file_path, index=False)
            
        print("Ingestion Complete.")
        
    except Exception as e:
        print(f"Failed to ingest: {e}")
        raise e

def run(argv=None):
    fetch_and_save_marketing_spend()

if __name__ == "__main__":
    run()
