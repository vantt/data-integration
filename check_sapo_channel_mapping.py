import duckdb, glob, os

con = duckdb.connect()

# Find dim_channels parquet
print("=== Searching for dim_channels parquet ===")
for root, dirs, files in os.walk('/app/var/data_lake/export'):
    for f in files:
        if 'channel' in f.lower() and f.endswith('.parquet'):
            full = os.path.join(root, f)
            print(f"  {full}")

# Also check serving olap.duckdb for channels
print()
print("=== sapo_raw/channel files ===")
ch_files = glob.glob('/app/var/data_lake/sapo_raw/channel/**/*.parquet', recursive=True)
print(f"Files: {len(ch_files)}")
if ch_files:
    cols = [d[0] for d in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{ch_files[0]}') LIMIT 1").fetchall()]
    print(f"Columns: {cols}")
    r = con.execute(f"""
    SELECT json_extract_string(payload, '$.id') AS id,
           json_extract_string(payload, '$.name') AS name,
           json_extract_string(payload, '$.channel_type') AS channel_type
    FROM read_parquet('/app/var/data_lake/sapo_raw/channel/**/*.parquet')
    WHERE payload IS NOT NULL
    LIMIT 30
    """).fetchall()
    for row in r:
        print(f"  id={row[0]}  name={row[1]}  type={row[2]}")

# Check what source_ids 4164989 and 4110169 are in fact_orders via channel_key join
print()
print("=== fact_orders channel_key for 2024-2025 ===")
try:
    r2 = con.execute("""
    SELECT channel_key, COUNT(*) AS cnt
    FROM read_parquet('/app/var/data_lake/export/marts/rolling/fact_orders/*.parquet')
    WHERE YEAR(ordered_at) IN (2024, 2025)
    GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """).fetchall()
    for row in r2:
        print(f"  channel_key={row[0]}  cnt={row[1]}")
except Exception as e:
    print(f"error: {e}")

# Also check serving olap.duckdb - if not locked now
print()
print("=== dim_channels via olap.duckdb ===")
try:
    con2 = duckdb.connect('/app/var/data_lake/serving/olap.duckdb', read_only=True)
    r3 = con2.execute("SELECT * FROM dim_channels ORDER BY channel_key").fetchall()
    cols3 = [d[0] for d in con2.execute("DESCRIBE dim_channels").fetchall()]
    print(f"Columns: {cols3}")
    for row in r3:
        print(f"  {dict(zip(cols3, row))}")
    con2.close()
except Exception as e:
    print(f"olap.duckdb error: {e}")

con.close()
print("Done")
