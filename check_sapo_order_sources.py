import duckdb, json

con = duckdb.connect()

# See actual structure of raw order parquet
print("=== Sample raw order parquet ===")
r = con.execute("""
SELECT * FROM read_parquet('/app/var/data_lake/sapo_raw/order/ingest_method=batch_sync/**/*.parquet')
LIMIT 2
""").fetchall()
cols = [d[0] for d in con.execute("""
DESCRIBE SELECT * FROM read_parquet('/app/var/data_lake/sapo_raw/order/ingest_method=batch_sync/**/*.parquet') LIMIT 1
""").fetchall()]
print(f"Columns: {cols}")
for row in r:
    for col, val in zip(cols, row):
        if isinstance(val, str) and len(val) > 200:
            val = val[:200] + '...'
        print(f"  {col}: {val}")
    print()

# Check if there's a text partition with full order data
print("=== text partition orders ===")
try:
    r2 = con.execute("""
    SELECT * FROM read_parquet('/app/var/data_lake/sapo_raw/order/ingest_method=text/**/*.parquet')
    LIMIT 1
    """).fetchall()
    cols2 = [d[0] for d in con.execute("""
    DESCRIBE SELECT * FROM read_parquet('/app/var/data_lake/sapo_raw/order/ingest_method=text/**/*.parquet') LIMIT 1
    """).fetchall()]
    print(f"Columns: {cols2}")
except Exception as e:
    print(f"text partition: {e}")

# Check sapo_warehouse tables directly via a temp connection
# The warehouse is locked, so use the stg_ models output if available
print()
print("=== stg_orders export ===")
import glob as g
stg_files = g.glob('/app/var/data_lake/export/**/*stg*order*.parquet', recursive=True)
stg_files += g.glob('/app/var/data_lake/export/**/*order*stg*.parquet', recursive=True)
print(f"stg order files: {stg_files[:5]}")

con.close()
