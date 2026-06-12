import duckdb, json

con = duckdb.connect()

HLOG_GLOB = '/app/var/data_lake/sapo_raw/order/ingest_method=history_log/**/*.parquet'

# Check history_log partition date range and source_id breakdown
print("=== history_log partition files ===")
import glob, os
files = glob.glob('/app/var/data_lake/sapo_raw/order/ingest_method=history_log/**/*.parquet', recursive=True)
print(f"Files: {len(files)}")
for f in sorted(files):
    sz = os.path.getsize(f)
    print(f"  {f}  ({sz:,} bytes)")

print()
print("=== history_log — source_id + channel by year ===")
r = con.execute(f"""
SELECT
    YEAR(CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMP)) AS yr,
    json_extract_string(payload, '$.source_id') AS source_id,
    json_extract_string(payload, '$.channel') AS channel,
    COUNT(*) AS cnt
FROM read_parquet('{HLOG_GLOB}')
WHERE payload IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1, 4 DESC
""").fetchall()
total = 0
for row in r:
    print(f"  yr={row[0]}  source_id={row[1]}  channel={row[2]}  cnt={row[3]:,}")
    total += row[3]
print(f"TOTAL history_log rows: {total:,}")

# Specifically look for source_id=3988158 (Shopee) in 2024-2025 across ALL partitions
print()
print("=== ALL partitions — Shopee source_id=3988158 by year ===")
ALL_GLOB = '/app/var/data_lake/sapo_raw/order/**/*.parquet'
r2 = con.execute(f"""
SELECT
    YEAR(CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMP)) AS yr,
    json_extract_string(payload, '$.source_id') AS source_id,
    json_extract_string(payload, '$.channel') AS channel,
    COUNT(*) AS cnt
FROM read_parquet('{ALL_GLOB}')
WHERE payload IS NOT NULL
  AND json_extract_string(payload, '$.source_id') = '3988158'
GROUP BY 1, 2, 3
ORDER BY 1
""").fetchall()
for row in r2:
    print(f"  yr={row[0]}  source_id={row[1]}  channel={row[2]}  cnt={row[3]:,}")

# Check what channels exist in dim_channels (via serving layer)
print()
print("=== dim_channels in serving (to map source_id → name) ===")
try:
    r3 = con.execute("""
    SELECT channel_key, channel_name, source_id, is_sales_channel
    FROM read_parquet('/app/var/data_lake/export/marts/core/dim_channels/*.parquet')
    ORDER BY channel_key
    """).fetchall()
    for row in r3:
        print(f"  key={row[0]}  name={row[1]}  source_id={row[2]}  is_sales={row[3]}")
except Exception as e:
    print(f"dim_channels error: {e}")

con.close()
print("Done")
