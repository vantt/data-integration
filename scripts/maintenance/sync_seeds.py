import duckdb
import pandas as pd
import os
import re

# Configuration
# Environment Variables (Standardized)
DATA_LAKE_PATH = os.environ.get("DBT_DATA_LAKE_PATH", "../../data_lake")
PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "../../transformation")

DB_PATH = os.path.join(DATA_LAKE_PATH, "sapo_warehouse.duckdb")
SEEDS_DIR = os.path.join(PROJECT_DIR, "seeds")
RAW_SCHEMA = "sapo_raw"

# Allowlist regex for CSV-sourced IDs used in SQL NOT IN clauses
# Prevents self-reinforcing injection if a corrupted upstream value reaches the CSV
_ID_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')

def sync_seeds():
    print("Connecting to DuckDB...")
    con = duckdb.connect(DB_PATH)
    try:
        # 1. Sync Order Sources
        print("Syncing Order Sources...")
        existing_sources = pd.read_csv(f"{SEEDS_DIR}/ref_order_sources.csv")
        existing_ids = {i for i in existing_sources['id'].astype(str) if _ID_RE.match(i)}

        # Query Raw for new IDs
        # Note: Requires duckdb with sapo_raw attached or accessible
        try:
            new_sources_df = con.execute(f"""
                SELECT DISTINCT
                    json_extract_string(payload, '$.source_id') as id,
                    json_extract_string(payload, '$.source_name') as name
                FROM {RAW_SCHEMA}.order
                WHERE id NOT IN ({','.join(["'" + i + "'" for i in existing_ids])})
                AND id IS NOT NULL
            """).fetchdf()

            if not new_sources_df.empty:
                print(f"Found {len(new_sources_df)} new sources. Appending...")
                # Heuristic Classification
                def classify_platform_group(name):
                    n = str(name).lower()
                    if any(x in n for x in ['shopee', 'lazada', 'tiki', 'sendo', 'grab', 'tiktok']): return 'Ecom'
                    if any(x in n for x in ['facebook', 'fb', 'instagram', 'zalo', 'social']): return 'Social'
                    if any(x in n for x in ['pos', 'store', 'cửa hàng', 'showroom', 'tại quầy']): return 'Retail'
                    if any(x in n for x in ['web', 'online']): return 'Web'
                    return 'Other'

                def classify_platform(name):
                    n = str(name).lower()
                    if 'shopee' in n: return 'Shopee'
                    if 'lazada' in n: return 'Lazada'
                    if 'tiki' in n: return 'Tiki'
                    if 'tiktok' in n: return 'TikTok'
                    if 'facebook' in n or 'fb' in n: return 'Facebook'
                    if 'zalo' in n: return 'Zalo'
                    if 'web' in n: return 'Website'
                    if 'pos' in n or 'store' in n: return 'Retail'
                    return 'Other'

                new_sources_df['status'] = 'true'
                new_sources_df['platform_group'] = new_sources_df['name'].apply(classify_platform_group)
                new_sources_df['is_generic_source'] = new_sources_df['platform_group'].apply(
                    lambda x: 'true' if x == 'Retail' else 'false'
                )
                # Add New Columns matching CSV Schema
                new_sources_df['platform'] = new_sources_df['name'].apply(classify_platform)
                new_sources_df['mapping_tag'] = '' # Default empty for auto-synced sources

                # Ensure Column Order matches CSV: id,name,status,platform_group,is_generic_source,platform,mapping_tag
                new_sources_df = new_sources_df[[
                    'id', 'name', 'status', 'platform_group', 'is_generic_source', 'platform', 'mapping_tag'
                ]]

                # Append
                new_sources_df.to_csv(f"{SEEDS_DIR}/ref_order_sources.csv", mode='a', header=False, index=False)
            else:
                print("No new sources found.")

        except Exception as e:
            print(f"Error syncing sources: {e}")

        # 2. Sync Branch Locations
        print("Syncing Branch Locations...")
        existing_locs = pd.read_csv(f"{SEEDS_DIR}/ref_branch_locations.csv")
        existing_loc_ids = {i for i in existing_locs['id'].astype(str) if _ID_RE.match(i)}

        try:
            new_locs_df = con.execute(f"""
                SELECT DISTINCT
                    json_extract_string(payload, '$.location_id') as id,
                    'UNK' as code,
                    'Unknown Location ' || json_extract_string(payload, '$.location_id') as name
                FROM {RAW_SCHEMA}.order
                WHERE id NOT IN ({','.join(["'" + i + "'" for i in existing_loc_ids])})
                AND id IS NOT NULL
            """).fetchdf()

            if not new_locs_df.empty:
                print(f"Found {len(new_locs_df)} new locations. Appending...")
                new_locs_df.to_csv(f"{SEEDS_DIR}/ref_branch_locations.csv", mode='a', header=False, index=False)
            else:
                print("No new locations found.")

        except Exception as e:
            print(f"Error syncing locations: {e}")

    finally:
        con.close()

    print("Sync complete.")

if __name__ == "__main__":
    sync_seeds()
