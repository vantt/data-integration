import duckdb
import os

# Find latest version folder
base = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/export/marts'
try:
    versions = [v for v in os.listdir(base) if v.startswith('v_')]
    versions.sort()
    latest = versions[-1]
    file_path = os.path.join(base, latest, 'dim_staff.parquet')
    
    print(f"Reading: {file_path}")
    
    con = duckdb.connect()
    result = con.execute(f"SELECT * FROM '{file_path}' LIMIT 5").fetchall()
    
    print("Columns:", [d[0] for d in con.description])
    print("Rows:")
    for row in result:
        print(row)

except Exception as e:
    print(f"Error: {e}")
