import duckdb
import pandas as pd

file_path = r'd:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2\app_data\data_lake\sapo_raw\customers\mock\2024\01\mock_customer.parquet'

print(f"Inspecting file: {file_path}")

try:
    # Connect to DuckDB
    con = duckdb.connect()
    
    # Read the file
    query = f"SELECT * FROM read_parquet('{file_path}') LIMIT 1"
    df = con.execute(query).df()
    
    # Print Columns
    print("\nColumns:")
    print(df.columns.tolist())
    
    # Check payload if it exists
    if 'payload' in df.columns:
        print("\nPayload Sample (Raw):")
        payload = df['payload'].iloc[0]
        print(payload)
        
        # Try to parse JSON and show keys
        import json
        try:
            data = json.loads(payload)
            print("\nPayload Keys:")
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"\nError parsing JSON payload: {e}")

except Exception as e:
    print(f"Error inspecting parquet: {e}")
