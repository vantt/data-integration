import duckdb
import os
import glob
import re

# Configuration
# HOST PATHS
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_LAKE_DIR = os.path.join(PROJECT_ROOT, 'data_lake')
SERVING_DIR = os.path.join(DATA_LAKE_DIR, 'serving')
EXPORT_BASE_DIR = os.path.join(DATA_LAKE_DIR, 'export', 'marts')
SERVING_DB_PATH = os.path.join(SERVING_DIR, 'olap.duckdb')

# DOCKER / PORTABLE PATH
# This path must exist on BOTH Host (via Junction) and Docker (via Mount)
# Host: D:\data_lake (Junction to Project/data_lake)
# Docker: /data_lake (Mounted volume)
# We assume the junction is setup by run_pipeline.ps1
PORTABLE_ROOT = "/data_lake"

# Pattern: v_YYYYMMDD_HHMMSS
DIR_PATTERN = re.compile(r'^v_(\d{8}_\d{6})$')

def generate_serving_db():
    print(f"Generating Serving DB at: {SERVING_DB_PATH}")
    
    # 0. Reset DB (Remove stale views)
    if os.path.exists(SERVING_DB_PATH):
        try:
            os.remove(SERVING_DB_PATH)
            print("  [x] Removed existing serving database to clear stale views.")
        except Exception as e:
            print(f"  [!] Could not remove existing DB: {e}")

    os.makedirs(SERVING_DIR, exist_ok=True)
    
    # 1. Scan/Find Versions
    if not os.path.exists(EXPORT_BASE_DIR):
        print(f"Export dir {EXPORT_BASE_DIR} does not exist.")
        return

    subdirs = [d for d in os.listdir(EXPORT_BASE_DIR) if os.path.isdir(os.path.join(EXPORT_BASE_DIR, d))]
    versions = []
    
    for d in subdirs:
        match = DIR_PATTERN.match(d)
        if match:
            versions.append((match.group(1), os.path.join(EXPORT_BASE_DIR, d)))
            
    if not versions:
        print("No versioned directories found.")
        return
        
    # Sort
    versions.sort(key=lambda x: x[0], reverse=True)
    latest_batch, latest_path = versions[0]
    
    print(f"Detected Latest Version: {latest_batch}")
    
    # Connect
    con = duckdb.connect(SERVING_DB_PATH)
    
    # 2. Update Views from Latest Directory
    parquet_files = glob.glob(os.path.join(latest_path, "*.parquet"))
    
    print(f"Updating Views from {latest_path}...")
    
    parquet_files = glob.glob(os.path.join(latest_path, "*.parquet"))
    print(f"  Found {len(parquet_files)} parquet files.")
    for p in parquet_files:
        print(f"    - {os.path.basename(p)}")
        filename = os.path.basename(p)
        table_name = os.path.splitext(filename)[0]
        
        # Construct PORTABLE Path
        # /data_lake/export/marts/v_BATCH/filename
        # Force forward slashes
        portable_path = f"{PORTABLE_ROOT}/export/marts/v_{latest_batch}/{filename}"
        
        print(f"  [+] View: {table_name} -> {portable_path}")
        
        # Create View
        # On Windows: /data_lake resolves to CurrentDrive:\data_lake which matches the Junction D:\data_lake
        # On Linux: /data_lake resolves to Root /data_lake
        con.sql(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM '{portable_path}'")
        
    con.close()
    
    # 3. Cleanup
    KEEP_COUNT = 2
    if len(versions) > KEEP_COUNT:
        to_delete = versions[KEEP_COUNT:]
        for batch, path in to_delete:
            print(f"  [d] Cleanup old version: {batch}")
            try:
                import shutil
                shutil.rmtree(path)
            except Exception as e:
                print(f"    Error deleting {path}: {e}")

    print("Done.")

if __name__ == "__main__":
    generate_serving_db()
