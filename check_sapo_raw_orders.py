import duckdb, os, glob

con = duckdb.connect()

# Check raw sapo parquet files structure
print("=== Data lake raw/ingestion paths ===")
for root, dirs, files in os.walk('/app/var/data_lake'):
    dirs[:] = [d for d in dirs if 'backup' not in d.lower()]
    for f in files:
        if f.endswith('.parquet'):
            full = os.path.join(root, f)
            print(f"  {full}")
    if 'export' in root:
        dirs[:] = []  # skip export subdirs (already checked)

print()

# Check stg_orders source_id / channel breakdown via sapo text partition
text_orders = glob.glob('/app/var/data_lake/**/orders*.parquet', recursive=True)
text_orders += glob.glob('/app/var/data_lake/**/stg_orders*.parquet', recursive=True)
print(f"stg/raw order parquet: {text_orders[:5]}")

# Try reading raw orders from sapo ingestion
sapo_paths = glob.glob('/app/var/**/*.parquet', recursive=True)
sapo_paths = [p for p in sapo_paths if 'order' in p.lower() and 'export' not in p and 'backup' not in p]
print(f"Non-export order parquets: {sapo_paths[:10]}")

con.close()
