import duckdb
import os
import glob
import re
import shutil
import time

# Configuration
# HOST PATHS
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_LAKE_DIR = os.path.join(PROJECT_ROOT, 'data_lake')
SERVING_DIR = os.path.join(DATA_LAKE_DIR, 'serving')
# Point to Stable Rolling Directory
ROLLING_DIR = os.path.join(DATA_LAKE_DIR, 'export', 'marts', 'rolling')
SERVING_DB_PATH = os.path.join(SERVING_DIR, 'olap.duckdb')

# DOCKER / PORTABLE PATH
PORTABLE_ROOT = "/data_lake"

def garbage_collect(folder_path, latest_file):
    """
    Deletes all files in folder_path EXCEPT the latest_file.
    Silently ignores PermissionError (Windows Locking).
    """
    files = glob.glob(os.path.join(folder_path, "*.parquet"))
    for f in files:
        if os.path.basename(f) == latest_file:
            continue
            
        try:
            os.remove(f)
            print(f"    [GC] Deleted old file: {os.path.basename(f)}")
        except PermissionError:
            print(f"    [GC] SKIP Locked file (In Use): {os.path.basename(f)}")
        except Exception as e:
            print(f"    [GC] Error deleting {os.path.basename(f)}: {e}")

def get_latest_file(folder_path):
    """Finds the lexically latest parquet file in a folder."""
    files = glob.glob(os.path.join(folder_path, "*.parquet"))
    if not files:
        return None
    files.sort()
    return os.path.basename(files[-1])

def generate_serving_db():
    print(f"Updating Serving DB at: {SERVING_DB_PATH}")
    print(f"Scanning Rolling Directory: {ROLLING_DIR}")

    os.makedirs(SERVING_DIR, exist_ok=True)
    
    if not os.path.exists(ROLLING_DIR):
        print(f"Rolling dir {ROLLING_DIR} does not exist. Pipeline might not have run yet.")
        return

    # 1. Try to Connect to DB for View Updates (Best Effort)
    con = None
    db_locked = False
    try:
        con = duckdb.connect(SERVING_DB_PATH)
    except Exception as e:
        print(f"  [!] WARNING: Could not connect to DuckDB ({e}).")
        print(f"      Assuming DB is locked by a reader. Skipping View Definition updates.")
        print(f"      This is SAFE if Smart Views were already created previously.")
        db_locked = True

    # 2. Iterate through Table Folders
    subdirs = [d for d in os.listdir(ROLLING_DIR) if os.path.isdir(os.path.join(ROLLING_DIR, d))]
    
    if not subdirs:
        print("No table directories found in rolling/.")
        if con: con.close()
        return

    for table_name in subdirs:
        table_dir = os.path.join(ROLLING_DIR, table_name)
        
        # A. Find Latest File (Filesystem check)
        latest_filename = get_latest_file(table_dir)
        if not latest_filename:
            print(f"  [!] Empty folder: {table_name}")
            continue
            
        print(f"  [+] Table: {table_name}")
        print(f"      Latest: {latest_filename}")
        
        # B. Create Smart View (If DB available)
        if not db_locked and con:
            # Construct PORTABLE Pattern for Smart View
            # We use a glob pattern matching ALL parquet files in the folder
            # /data_lake/export/marts/rolling/table_name/*.parquet
            portable_glob = f"{PORTABLE_ROOT}/export/marts/rolling/{table_name}/*.parquet"
            
            # SMART VIEW LOGIC:
            # Select max(filename) from the glob scan, then filter by that filename.
            # This makes the view "Auto-Updating" as long as the latest file exists and is max string.
            sql = f"""
            CREATE OR REPLACE VIEW {table_name} AS 
            WITH source_files AS (
                SELECT *, filename FROM read_parquet('{portable_glob}', filename=true, hive_partitioning=0)
            ),
            latest AS (
                SELECT max(filename) as max_fn FROM source_files
            )
            SELECT * EXCLUDE (filename) 
            FROM source_files 
            WHERE filename = (SELECT max_fn FROM latest)
            """
            
            try:
                con.sql(sql)
                # print(f"      [View] Smart View Updated.")
            except Exception as e:
                print(f"      [!] Failed to update view: {e}")
        
        # C. Garbage Collection (Always run)
        garbage_collect(table_dir, latest_filename)
        
    if con:
        con.close()
        
    print("Serving Update & GC Completed.")

if __name__ == "__main__":
    generate_serving_db()
