import duckdb
import sys
import os

def query_lake(query=None):
    # Default query if none provided
    if query is None:
        query = "SELECT * FROM 'data_lake/sapo_data/orders/**/*.parquet' LIMIT 20"

    print(f"Executing query: {query}")
    try:
        con = duckdb.connect()
        
        # Check if files exist first to avoid confusing duckdb error if empty
        # But duckdb globbing handles it reasonably well usually. 
        # Let's just try running a count first to confirm data presence.
        
        try:
            count_query = "SELECT COUNT(*) FROM 'data_lake/sapo_data/orders/**/*.parquet'"
            count = con.execute(count_query).fetchone()[0]
            print(f"Total rows in 'data_lake/sapo_data/orders': {count}")
        except Exception as e:
            print(f"Error accessing data files: {e}")
            print("Ensure you are in the correct directory 'data-integration2/dlt' and data exists in 'data_lake/sapo_data/orders'.")
            return

        if count == 0:
            print("No data found.")
            return

        # Execute the main query
        print("\nQuery Results:")
        try:
            # Try to use pandas for pretty printing if available
            df = con.execute(query).df()
            print(df)
            print("\nColumns:")
            print(df.columns.tolist())
        except (ImportError, ModuleNotFoundError) as e:
            # Fallback if pandas/numpy is not installed
            print(f"Pandas/Numpy not found ({e}), falling back to raw output.")
            result = con.execute(query)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            
            print(f"Columns: {columns}")
            for row in rows:
                print(row)

    except Exception as e:
        print(f"Error executing query: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Allow passing query as argument
        # e.g. python query_lake.py "SELECT distinct year, month FROM ..."
        user_query = sys.argv[1]
        query_lake(user_query)
    else:
        query_lake()
