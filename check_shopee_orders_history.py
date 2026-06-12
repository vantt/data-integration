import duckdb

# Check fact_orders - all channels 2024-2025, no scope filter
con = duckdb.connect('/app/var/data_lake/serving/olap.duckdb', read_only=True)

print("=== fact_orders: all channels 2024-2025 (no scope filter) ===")
r = con.execute("""
SELECT YEAR(o.ordered_at) AS yr,
       ch.channel_name,
       ch.channel_code,
       ch.is_sales_channel,
       COUNT(*) AS cnt
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE YEAR(o.ordered_at) IN (2024, 2025)
GROUP BY 1,2,3,4
ORDER BY 1, 5 DESC
""").fetchall()
for row in r:
    print(f"  {row[0]}  channel={row[1]}  code={row[2]}  is_sales={row[3]}  cnt={row[4]:,}")

con.close()

# Check raw warehouse for Shopee orders
print()
print("=== sapo_warehouse: source_id / channel data 2024-2025 ===")
try:
    wh = duckdb.connect('/app/var/data_lake/sapo_warehouse.duckdb', read_only=True)
    tables = [t[0] for t in wh.execute("SHOW TABLES").fetchall()]
    print(f"  Tables: {tables[:20]}")

    # Find orders table
    order_tables = [t for t in tables if 'order' in t.lower() and 'item' not in t.lower()]
    print(f"  Order tables: {order_tables}")

    for tbl in order_tables[:2]:
        try:
            cols = [d[0] for d in wh.execute(f"DESCRIBE {tbl}").fetchall()]
            source_col = next((c for c in cols if 'source' in c.lower() or 'channel' in c.lower()), None)
            date_col = next((c for c in cols if 'created' in c.lower() or 'ordered' in c.lower()), None)
            print(f"\n  [{tbl}] cols sample: {cols[:15]}")
            if source_col and date_col:
                r2 = wh.execute(f"""
                    SELECT YEAR({date_col}) AS yr, {source_col}, COUNT(*) AS cnt
                    FROM {tbl}
                    WHERE YEAR({date_col}) IN (2024, 2025)
                      AND {source_col} IS NOT NULL
                    GROUP BY 1,2 ORDER BY 1, 3 DESC
                    LIMIT 20
                """).fetchall()
                for row in r2:
                    print(f"    {row[0]}  {source_col}={row[1]}  cnt={row[2]:,}")
        except Exception as e:
            print(f"  [{tbl}] error: {e}")
    wh.close()
except Exception as e:
    print(f"  warehouse error: {e}")
