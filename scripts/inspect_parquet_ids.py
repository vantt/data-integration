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
            print(f"assignee_id: {payload.get('assignee_id')}")
            print(f"account_id: {payload.get('account_id')}")
            print(f"user_id: {payload.get('user_id')}")
            
            # Print all keys that end with _id
            print("\nKeys ending with _id:")
            for k in payload.keys():
                if k.endswith('_id'):
                    print(f"{k}: {payload[k]}")

        except json.JSONDecodeError:
            print("Payload is not valid JSON")

    else:
        print("No rows found.")

except Exception as e:
    print(f"Error reading parquet with duckdb: {e}")
