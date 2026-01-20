import duckdb
import sys
import pandas as pd

def main():
    if len(sys.argv) < 2:
        print("Usage: python view_vertical.py \"<query>\"")
        print("Example: python view_vertical.py \"SELECT * FROM 'data/file.parquet' LIMIT 1\"")
        return

    query_str = sys.argv[1]
    
    try:
        conn = duckdb.connect()
        # Execute query and convert to pandas DF, then to dict records
        # This handles timestamps and complex types relatively well via pandas repr
        df = conn.sql(query_str).df()
        
        records = df.to_dict(orient='records')
        
        if not records:
            print("No results found.")
            return

        print(f"Executing query: {query_str}")
        print(f"Found {len(records)} record(s).\n")

        for i, row in enumerate(records):
            print(f"--- RECORD {i+1} ---")
            for col, val in row.items():
                # Format None/NaN nicely
                val_str = str(val)
                if pd.isna(val):
                    val_str = "NULL"
                print(f"{col:<35}: {val_str}")
            print("\n")

    except Exception as e:
        print(f"❌ Error executing query: {e}")

if __name__ == "__main__":
    main()
