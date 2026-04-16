
import duckdb
import sys

try:
    import os
    data_lake_path = os.environ.get('DBT_DATA_LAKE_PATH', '/app/var/data_lake')
    db_path = os.path.join(data_lake_path, 'serving', 'olap.duckdb')
    conn = duckdb.connect(db_path)
    views = ['dim_channels', 'fact_sales']
    
    for view_name in views:
        res = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='view' AND name='{view_name}'").fetchall()
        print(f"--- View: {view_name} ---")
        if res:
            print(res[0][0])
        else:
            print("NOT FOUND")
        print("-----------------------")
except Exception as e:
    print(f"Error: {e}")
