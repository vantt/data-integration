import duckdb

con = duckdb.connect()

# Check text partition for orders
print("=== text partition order files ===")
import glob
text_files = glob.glob('/app/var/data_lake/sapo_raw/order/ingest_method=text/**/*.parquet', recursive=True)
print(f"Files: {len(text_files)}")
for f in text_files[:5]:
    import os
    print(f"  {f}  size={os.path.getsize(f):,}")

if text_files:
    cols = [d[0] for d in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{text_files[0]}') LIMIT 1").fetchall()]
    print(f"\nColumns: {cols}")

    r = con.execute(f"""
    SELECT MIN(created_on)::date, MAX(created_on)::date, COUNT(*) AS cnt
    FROM read_parquet('{text_files[0]}')
    WHERE created_on IS NOT NULL
    """).fetchone()
    print(f"Date range: {r[0]} → {r[1]}, rows={r[2]:,}")

    # source_id breakdown by year
    source_col = next((c for c in cols if 'source' in c.lower()), None)
    if source_col:
        r2 = con.execute(f"""
        SELECT YEAR(created_on) AS yr, {source_col}, COUNT(*) AS cnt
        FROM read_parquet('{text_files[0]}')
        WHERE YEAR(created_on) IN (2024, 2025) AND created_on IS NOT NULL
        GROUP BY 1,2 ORDER BY 1,3 DESC
        """).fetchall()
        print(f"\nSource breakdown 2024-2025 ({source_col}):")
        for row in r2:
            print(f"  {row[0]}  {source_col}={row[1]}  cnt={row[2]:,}")

# Also check batch_sync total count vs fact_orders
print()
print("=== batch_sync order count ===")
batch_files = glob.glob('/app/var/data_lake/sapo_raw/order/ingest_method=batch_sync/**/*.parquet', recursive=True)
print(f"batch_sync files: {len(batch_files)}")

con.close()
