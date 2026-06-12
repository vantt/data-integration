import duckdb
con = duckdb.connect()

print("=== history_log: source_id by year ===")
r = con.execute("""
SELECT
    YEAR(CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMP)) AS yr,
    json_extract_string(payload, '$.source_id') AS source_id,
    json_extract_string(payload, '$.channel') AS ch,
    COUNT(*) AS cnt
FROM read_parquet('/app/var/data_lake/sapo_raw/order/ingest_method=history_log/**/*.parquet')
WHERE payload IS NOT NULL
GROUP BY 1,2,3 ORDER BY 1,4 DESC LIMIT 40
""").fetchall()
for row in r:
    print(f"  yr={row[0]} src={row[1]} ch={row[2]} cnt={row[3]}")

print()
print("=== dim_channels ===")
try:
    r2 = con.execute("""
    SELECT channel_key, channel_name, source_id, is_sales_channel
    FROM read_parquet('/app/var/data_lake/export/marts/core/dim_channels/*.parquet')
    ORDER BY channel_key
    """).fetchall()
    for row in r2:
        print(f"  key={row[0]} name={row[1]} src={row[2]} is_sales={row[3]}")
except Exception as e:
    print(f"error: {e}")

print()
print("=== fact_orders: Shopee orders by year (scope_retail=False filter) ===")
try:
    r3 = con.execute("""
    SELECT
        YEAR(ordered_at) AS yr,
        channel_name,
        scope_retail,
        COUNT(*) AS cnt
    FROM read_parquet('/app/var/data_lake/export/marts/rolling/fact_orders/*.parquet')
    WHERE channel_name ILIKE '%shopee%'
    GROUP BY 1,2,3 ORDER BY 1
    """).fetchall()
    for row in r3:
        print(f"  yr={row[0]} ch={row[1]} scope_retail={row[2]} cnt={row[3]}")
except Exception as e:
    print(f"error: {e}")

con.close()
print("Done")
