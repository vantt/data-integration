import duckdb, glob

con = duckdb.connect()

# Check date range in rolling fact_orders parquet
files = sorted(glob.glob('/app/var/data_lake/export/marts/rolling/fact_orders/*.parquet'))
print(f"fact_orders parquet files: {len(files)}")
for f in files[-1:]:  # just latest
    r = con.execute(f"SELECT MIN(ordered_at)::date, MAX(ordered_at)::date, COUNT(*) FROM read_parquet('{f}')").fetchone()
    print(f"  {f.split('/')[-1]}: {r[0]} → {r[1]}, rows={r[2]:,}")

# Check if there are historical/full parquet exports
print()
import os
for root, dirs, fs in os.walk('/app/var/data_lake'):
    for f in fs:
        if f.endswith('.parquet') and 'fact_orders' in f and 'rolling' not in root:
            full = os.path.join(root, f)
            print(f"  non-rolling: {full}")

# Check ingestion source - stg_orders in sapo partition
print()
print("=== stg or raw order data ===")
for root, dirs, fs in os.walk('/app/var/data_lake'):
    for f in fs:
        if f.endswith('.parquet') and 'order' in f.lower() and 'sapo' in root.lower():
            full = os.path.join(root, f)
            size = os.path.getsize(full)
            print(f"  {full}  size={size:,}")
            break  # just show structure

con.close()
