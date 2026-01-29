import duckdb
import os

import os
data_lake_path = os.environ.get('DBT_DATA_LAKE_PATH', '/app/data_lake')
db_path = os.path.join(data_lake_path, 'sapo_warehouse.duckdb')
print(f"Connecting to {db_path}...")

try:
    con = duckdb.connect(db_path, read_only=True)
    row = con.execute("SELECT sql FROM sqlite_master WHERE name='dim_branch_location'").fetchone()
    if row:
        print("--- View Definition ---")
        print(row[0])
        print("-----------------------")
    else:
        print("View 'dim_branch_location' not found!")
except Exception as e:
    print(f"Error: {e}")
