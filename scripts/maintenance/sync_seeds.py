import duckdb
import pandas as pd
import os

# Configuration
# Environment Variables (Standardized)
DATA_LAKE_PATH = os.environ.get("DBT_DATA_LAKE_PATH", "../../data_lake")
PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "../../transformation")

DB_PATH = os.path.join(DATA_LAKE_PATH, "sapo_warehouse.duckdb")
SEEDS_DIR = os.path.join(PROJECT_DIR, "seeds")
RAW_SCHEMA = "sapo_raw"

def sync_seeds():
    print("Connecting to DuckDB...")
    con = duckdb.connect(DB_PATH)
    
    # 1. Sync Order Sources
    print("Syncing Order Sources...")
    # Get existing IDs
    existing_sources = pd.read_csv(f"{SEEDS_DIR}/ref_order_sources.csv")
    existing_ids = set(existing_sources['id'].astype(str))
    
    # Query Raw for new IDs
    # Note: Requires duckdb with sapo_raw attached or accessible
    try:
        new_sources_df = con.execute(f"""
            SELECT DISTINCT 
                json_extract_string(payload, '$.source_id') as id,
                json_extract_string(payload, '$.source_name') as name
            FROM {RAW_SCHEMA}.order
            WHERE id NOT IN ({','.join(["'" + str(i) + "'" for i in existing_ids])})
            AND id IS NOT NULL
        """).fetchdf()
        
        if not new_sources_df.empty:
            print(f"Found {len(new_sources_df)} new sources. Appending...")
            # Heuristic Classification
            def classify_platform(name):
                n = str(name).lower()
                if any(x in n for x in ['shopee', 'lazada', 'tiki', 'sendo', 'grab', 'tiktok']): return 'Ecom'
                if any(x in n for x in ['facebook', 'fb', 'instagram', 'zalo', 'social']): return 'Social'
                if any(x in n for x in ['pos', 'store', 'cửa hàng', 'showroom', 'tại quầy']): return 'Retail'
                if any(x in n for x in ['web', 'online']): return 'Web'
                return 'Other'

            new_sources_df['status'] = 'true'
            new_sources_df['platform_group'] = new_sources_df['name'].apply(classify_platform)
            # Retail/POS implies Generic Source (needs location split)
            new_sources_df['is_generic_source'] = new_sources_df['platform_group'].apply(
                lambda x: 'true' if x == 'Retail' else 'false'
            )
            
            # Append
            new_sources_df.to_csv(f"{SEEDS_DIR}/ref_order_sources.csv", mode='a', header=False, index=False)
        else:
            print("No new sources found.")
            
    except Exception as e:
        print(f"Error syncing sources: {e}")

    # 2. Sync Branch Locations
    print("Syncing Branch Locations...")
    existing_locs = pd.read_csv(f"{SEEDS_DIR}/ref_branch_locations.csv")
    existing_loc_ids = set(existing_locs['id'].astype(str))
    
    try:
        new_locs_df = con.execute(f"""
            SELECT DISTINCT 
                json_extract_string(payload, '$.location_id') as id,
                'UNK' as code,
                'Unknown Location ' || json_extract_string(payload, '$.location_id') as name
            FROM {RAW_SCHEMA}.order
            WHERE id NOT IN ({','.join(["'" + str(i) + "'" for i in existing_loc_ids])})
            AND id IS NOT NULL
        """).fetchdf()
        
        if not new_locs_df.empty:
            print(f"Found {len(new_locs_df)} new locations. Appending...")
            new_locs_df.to_csv(f"{SEEDS_DIR}/ref_branch_locations.csv", mode='a', header=False, index=False)
        else:
            print("No new locations found.")
            
    except Exception as e:
        print(f"Error syncing locations: {e}")
        
    con.close()
    print("Sync complete.")

if __name__ == "__main__":
    sync_seeds()
