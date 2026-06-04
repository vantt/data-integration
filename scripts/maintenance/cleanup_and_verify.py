import duckdb
import re

# Allowlist for table identifiers sourced from information_schema
# Format: schema.table — both parts alphanumeric/underscore
_TABLE_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_.]*$')

def main():
    con = duckdb.connect('data_lake/sapo_warehouse.duckdb')
    try:
        print("=== 1. Current Tables in 'main_staging' & 'main_marts' ===")
        tables = con.sql("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('main_staging', 'main_marts', 'main')
            ORDER BY table_schema, table_name
        """).fetchall()

        legacy_tables = []
        for schema, table in tables:
            print(f"{schema}.{table}")
            # Identify legacy tables: start with stg_ or src_ but NOT stg_sapo_*_v2 or src_sapo_*_v2
            # Note: old non-_v2 src_sapo_*/stg_sapo_* tables are orphans after P4 rename — Step 4.7 drops them manually.
            if (table.startswith('stg_') and not table.startswith('stg_sapo_')) or \
               (table.startswith('src_') and not table.startswith('src_sapo_')) or \
               (table.startswith('stag_')): # specific mention by user
                legacy_tables.append(f"{schema}.{table}")

        print(f"\n=== 2. Found {len(legacy_tables)} Legacy Tables to Drop ===")
        for t in legacy_tables:
            if not _TABLE_RE.match(t):
                print(f"  [!] Skipping invalid table identifier: {t}")
                continue
            print(f"Dropping {t}...")
            con.sql(f"DROP VIEW IF EXISTS {t}")
            con.sql(f"DROP TABLE IF EXISTS {t}")

        print("\n=== 3. Verifying Data in HOP 6 (Marts) ===")
        # Fact Counts
        f_orders = 0
        f_sales = 0
        try:
            f_orders = con.sql("SELECT COUNT(*) FROM main_marts.fact_orders").fetchone()[0]
            f_sales = con.sql("SELECT COUNT(*) FROM main_marts.fact_sales").fetchone()[0]
            print(f"✅ fact_orders row count: {f_orders}")
            print(f"✅ fact_sales row count: {f_sales}")
        except Exception as e:
            print(f"❌ Error checking facts: {e}")

        # Check if 0 rows, warn user
        if f_orders == 0:
            print("⚠️ WARNING: fact_orders is empty. Has the upstream 'stg_sapo_orders_v2' been populated?")

        print("\n=== 4. Verifying Data in HOP 5 (Staging) ===")
        try:
            stg_orders = con.sql("SELECT COUNT(*) FROM main_staging.stg_sapo_orders_v2").fetchone()[0]
            print(f"✅ stg_sapo_orders_v2 row count: {stg_orders}")
        except Exception as e:
            print(f"❌ Error checking staging: {e}")

    finally:
        con.close()

if __name__ == "__main__":
    main()
