import duckdb
import sys
import os

def query_lake(query=None):
    # Default query if none provided
    if query is None:
        query = "SELECT * FROM 'data_lake/sapo_data/orders/**/*.parquet' LIMIT 20"

    print(f"Executing query: {query}")
    con = None
    try:
        con = duckdb.connect()

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
    finally:
        if con:
            con.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Allow passing query as argument
        # e.g. python query_lake.py "SELECT distinct year, month FROM ..."
        user_query = sys.argv[1]
        query_lake(user_query)
    else:
        query_lake()
