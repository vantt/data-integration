import duckdb, json

con = duckdb.connect()

TEXT_GLOB = '/app/var/data_lake/sapo_raw/order/ingest_method=text/**/*.parquet'
BATCH_GLOB = '/app/var/data_lake/sapo_raw/order/ingest_method=batch_sync/**/*.parquet'

# Verify payload is a JSON string
print("=== text partition payload type ===")
r = con.execute(f"SELECT typeof(payload), payload[:50] FROM read_parquet('{TEXT_GLOB}') LIMIT 1").fetchone()
print(f"type={r[0]}  sample={r[1]}")

# Use json_extract_string for VARCHAR JSON columns
print()
print("=== text partition — source_id + channel by year ===")
r2 = con.execute(f"""
SELECT
    YEAR(CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMP)) AS yr,
    json_extract_string(payload, '$.source_id') AS source_id,
    json_extract_string(payload, '$.channel') AS channel,
    COUNT(*) AS cnt
FROM read_parquet('{TEXT_GLOB}')
WHERE payload IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1, 4 DESC
""").fetchall()
total = 0
for row in r2:
    print(f"  yr={row[0]}  source_id={row[1]}  channel={row[2]}  cnt={row[3]:,}")
    total += row[3]
print(f"TOTAL text partition rows: {total:,}")

# batch_sync by year + source_id
print()
print("=== batch_sync — source_id + channel by year ===")
r3 = con.execute(f"""
SELECT
    YEAR(CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMP)) AS yr,
    json_extract_string(payload, '$.source_id') AS source_id,
    json_extract_string(payload, '$.channel') AS channel,
    COUNT(*) AS cnt
FROM read_parquet('{BATCH_GLOB}')
WHERE payload IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1, 4 DESC
LIMIT 60
""").fetchall()
total2 = 0
for row in r3:
    print(f"  yr={row[0]}  source_id={row[1]}  channel={row[2]}  cnt={row[3]:,}")
    total2 += row[3]
print(f"TOTAL batch_sync rows: {total2:,}")

con.close()
print("Done")
