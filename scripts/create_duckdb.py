import duckdb
import os

def create_duckdb():
    # Change working directory to data_lake so paths are relative to it
    if os.path.exists("data_lake"):
        os.chdir("data_lake")
        print("Changed working directory to 'data_lake'")
    
    # Database path (now relative to current CWD which is data_lake)
    db_path = "sapo.duckdb"
    
    # Connect (this will create the file if it doesn't exist)
    con = duckdb.connect(db_path)
    
    print(f"Connected to DuckDB at {db_path}")

    # Define paths to parquet files relative to data_lake
    # Using recursive glob pattern to catch all partitions with forward slashes
    orders_path = "sapo_raw/order/**/*.parquet"
    customers_path = "sapo_raw/customer/**/*.parquet"
    
    print(f"Reading orders from: {orders_path}")
    print(f"Reading customers from: {customers_path}")

    try:
        # Create View for Orders
        # hive_partitioning=1 explicitly enables checking for hive-style partitions (key=value) directories
        # union_by_name=True ensures that if schemas differ slightly (e.g. column order), they are matched by name
        con.execute(f"""
            CREATE OR REPLACE VIEW sapo_orders AS 
            SELECT * FROM read_parquet('{orders_path}', hive_partitioning=true, union_by_name=true)
        """)
        print("Successfully created view: sapo_orders")
        
        # Verify count
        count_orders = con.execute("SELECT COUNT(*) FROM sapo_orders").fetchone()[0]
        print(f"Total orders found: {count_orders}")

        # Create View for Customers
        con.execute(f"""
            CREATE OR REPLACE VIEW sapo_customers AS 
            SELECT * FROM read_parquet('{customers_path}', hive_partitioning=true, union_by_name=true)
        """)
        print("Successfully created view: sapo_customers")
        
        # Verify count
        count_customers = con.execute("SELECT COUNT(*) FROM sapo_customers").fetchone()[0]
        print(f"Total customers found: {count_customers}")

        # List all tables/views to confirm
        print("\nAll Tables/Views:")
        tables = con.execute("SHOW TABLES").fetchall()
        for table in tables:
            print(table)

    except Exception as e:
        print(f"Error creating DuckDB views: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    # Ensure we are running from the project root or at least where data_lake is accessible
    if not os.path.exists("data_lake"):
        print("Error: 'data_lake' directory not found. Please run this script from the project root.")
    else:
        create_duckdb()
