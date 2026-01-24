import duckdb
import os

db_path = r"d:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2\data_integration2.duckdb"

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

con = duckdb.connect(db_path, read_only=True)

print("--- Schemas ---")
print(con.execute("SELECT schema_name FROM information_schema.schemata").fetchall())


print("\n--- Constraints Check ---")
try:
    constraints = con.execute("""
        SELECT *
        FROM information_schema.table_constraints
        WHERE table_schema = 'main' AND constraint_type = 'FOREIGN KEY'
    """).fetchall()
    
    if constraints:
        print("Found Foreign Keys:")
        for row in constraints:
            print(row)
    else:
        print("No physical Foreign Key constraints found in 'main' schema.")

    print("\n--- Table DDL (fact_orders) ---")
    try:
        # DuckDB method to get create table statement
        # First, get all tables and thei# Debugging: List all tables
        print("\n--- ALL TABLES ---")
        all_tables = con.execute("SELECT table_schema, table_name FROM information_schema.tables").fetchall()
        for t in all_tables:
            print(t)

        target_schema = 'main_marts' 
        # Just hardcode to check main_marts based on dbt logs
        print(f"\n--- Checking {target_schema}.fact_orders ---")
        try:
            constraints = con.execute(f"SELECT * FROM duckdb_constraints WHERE table_name='fact_orders' AND schema_name='{target_schema}'").fetchall()
            print("Constraints:", constraints)
        except Exception as e:
            print(f"Error checking constraints: {e}")
            
        try:
            # Use DuckDB specific function to generate DDL
            ddl = con.execute(f"SELECT sql FROM sqlite_master WHERE name='fact_orders'").fetchall() 
            # Note: sqlite_master in DuckDB often only shows main schema or attached. 
            # Let's try to infer from data_integration2.duckdb context.
            print("Sqlite Master DDL:", ddl)
        except Exception as e:
            print(f"Error checking sqlite_master: {e}")

        # Try to find the correct schema for fact_orders, prioritizing main_marts
        found_schema = None
        for schema, name in all_tables: # Use all_tables from above
            if name == 'fact_orders' and schema == 'main_marts':
                found_schema = schema
                break

        if not found_schema:
            for schema, name in all_tables: # Use all_tables from above
                if name == 'fact_orders':
                    found_schema = schema
                    break
                    
        print(f"DEBUG: Found tables: {[f'{s}.{n}' for s, n in all_tables if n == 'fact_orders']}")

        if found_schema:
            # Now fetch the DDL using the found schema and table name
            print(f"\n--- DDL Check for {found_schema}.fact_orders ---")
            try:
                # DuckDB's sqlite_master might not list main_marts depending on attachment
                # We can try describing the table
                desc = con.execute(f"DESCRIBE {found_schema}.fact_orders").fetchall()
                # print("Columns:", [r[0] for r in desc]) 
                
                # Check constraints specifically in the system table for this table
                print("\n--- DuckDB Constraints ---")
                constraints = con.execute(f"SELECT * FROM duckdb_constraints WHERE table_name='fact_orders' AND schema_name='{found_schema}'").fetchall()
                if constraints:
                    for row in constraints:
                        print(row)
                else:
                    print("No constraints found in duckdb_constraints.")

            except Exception as e:
                print(f"Error checking DDL: {e}")
        else:
            print("Could not find 'fact_orders' in any schema.")
            
    except Exception as e:
        print(f"Error checking DDL: {e}")
        
    print("\n--- DDL Check for dim_channels ---")
    try:
         # Assuming dim_channels is in the same schema
         dim_schema = found_schema or 'main_marts'
         desc = con.execute(f"DESCRIBE {dim_schema}.dim_channels").fetchall()
         
         constraints = con.execute(f"SELECT * FROM duckdb_constraints WHERE table_name='dim_channels' AND schema_name='{dim_schema}'").fetchall()
         if constraints:
                print(f"Constraints on {dim_schema}.dim_channels:")
                for row in constraints:
                    print(row)
         else:
                print(f"No constraints found on {dim_schema}.dim_channels.")
                
         ddl = con.execute(f"SELECT sql FROM sqlite_master WHERE tbl_name = 'dim_channels' AND type = 'table'").fetchone()
         if ddl:
             print(ddl[0])

    except Exception as e:
         print(f"Error checking dim_channels DDL: {e}")
         
    print("\n--- Channel Keys in dim_channels ---")
    # DuckDB doesn't standardly expose 'SHOW CREATE TABLE' in SQL easily via python without fetching specific col, 
    # but we can check if there is any reference.
    # Actually, let's just assume if table_constraints is empty, there are no FKs.
    
except Exception as e:
    print(f"Error checking constraints: {e}")

con.close()

