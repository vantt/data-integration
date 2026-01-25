import duckdb
import pandas as pd

# Connect to the persistent DuckDB file
# Note: Ensure no other process (like dbt or dagster) is currently writing to it to avoid lock issues
con = duckdb.connect('data_lake/sapo_warehouse.duckdb', read_only=True)

print("=== 1. Checking Tables in Marts Schema ===")
tables = con.sql("SHOW TABLES").fetchall()
print(tables)

print("\n=== 2. OLAP Query: Revenue by Product Category ===")
query_1 = """
SELECT 
    c.category_name,
    COUNT(s.order_id) as total_orders,
    SUM(s.revenue) as total_revenue
FROM main_marts.fact_sales s
JOIN main_marts.dim_product_category c ON s.category_key = c.category_key
GROUP BY 1
ORDER BY 3 DESC
LIMIT 5;
"""
print(con.sql(query_1).df())

print("\n=== 3. OLAP Query: Orders by Status ===")
query_2 = """
SELECT 
    d.status_code,
    COUNT(f.order_id) as order_count,
    SUM(f.gmv) as total_gmv
FROM main_marts.fact_orders f
JOIN main_marts.dim_order_status d ON f.status_key = d.status_key
GROUP BY 1
ORDER BY 2 DESC;
"""
print(con.sql(query_2).df())
