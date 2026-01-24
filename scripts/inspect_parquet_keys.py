import duckdb
import json

# Load parquet file
file_path = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw/orders/mock/2024/01/mock_order.parquet'

try:
    con = duckdb.connect()
    # Select payload from parquet
    query = f"SELECT payload FROM '{file_path}' LIMIT 1"
    result = con.execute(query).fetchall()
    
    if result:
        payload_str = result[0][0]
        try:
            payload = json.loads(payload_str)
            print("--- KEYS ---")
            print(list(payload.keys()))
            
            print("\n--- ASSIGNEE ---")
            print(json.dumps(payload.get('assignee'), indent=2))
            
            print("\n--- ACCOUNT ---")
            print(json.dumps(payload.get('account'), indent=2))
            
            print("\n--- USER_NAME ---")
            print(payload.get('user_name'))
            
             # Check for other potential keys
            print("\n--- OTHER POTENTIALS ---")
            for key in ['staff', 'employee', 'salesperson', 'user']:
                if key in payload:
                    print(f"{key}: {payload[key]}")

        except json.JSONDecodeError:
            print("Payload is not valid JSON")
            print(payload_str[:500]) # Print start of string

    else:
        print("No rows found.")

except Exception as e:
    print(f"Error reading parquet with duckdb: {e}")
