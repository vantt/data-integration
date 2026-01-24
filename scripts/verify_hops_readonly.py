import duckdb
import os

db_path = 'data_integration2.duckdb'
if not os.path.exists(db_path):
    # Try parent directory
    db_path = '../data_integration2.duckdb'

if not os.path.exists(db_path):
    print(f"❌ Error: Database file not found at '{db_path}' or in current dir.")
    exit(1)

try:
    # Connect in READ_ONLY mode
    con = duckdb.connect(db_path, read_only=True)
    print(f"✅ Connected to {db_path} (Read-Only)")
except Exception as e:
    print(f"❌ Failed to connect (even Read-Only): {e}")
    exit(1)

print("\n=== VERIFICATION: HOP 4, 5, 6 ===")

def check_table(schema, table, hop_name):
    try:
        count = con.sql(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()[0]
        status = "✅ Has Data" if count > 0 else "⚠️  EMPTY"
        print(f"{hop_name:<10} | {schema}.{table:<25} | Rows: {count:<6} | {status}")
        return count
    except Exception as e:
        print(f"{hop_name:<10} | {schema}.{table:<25} | ❌ Error: {e}")
        return 0

# HOP 4: Raw Data is Parquet, but 'src_sapo_orders' reads it.
# We check src_sapo_orders to verify Hop 4 -> 5 interface.
check_table("main_staging", "src_sapo_orders", "HOP 4 (Src)")

# HOP 5: Staging (Cleaned)
check_table("main_staging", "stg_sapo_orders", "HOP 5 (Stg)")
check_table("main_staging", "stg_sapo_customers", "HOP 5 (Stg)")

# HOP 6: Marts (OLAP)
orders_count = check_table("main_marts", "fact_orders", "HOP 6 (Fct)")
sales_count = check_table("main_marts", "fact_sales", "HOP 6 (Fct)")
check_table("main_marts", "dim_customers", "HOP 6 (Dim)")
check_table("main_marts", "dim_products", "HOP 6 (Dim)")

con.close()
