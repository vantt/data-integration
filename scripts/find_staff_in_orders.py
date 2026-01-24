import duckdb
import os
import json

target_id = '809888'
base_dir = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw/orders'

print(f"Scanning {base_dir} for {target_id}...")

found = False

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".parquet"):
            full_path = os.path.join(root, file)
            try:
                con = duckdb.connect()
                # Check if payload contains the ID
                query = f"SELECT payload FROM '{full_path}' WHERE payload LIKE '%{target_id}%' LIMIT 1"
                result = con.execute(query).fetchall()
                if result:
                    print(f"\nFOUND in: {full_path}")
                    payload_str = result[0][0]
                    try:
                        payload = json.loads(payload_str)
                        print("Keys related to staff:")
                        print(f"assignee_id: {payload.get('assignee_id')}")
                        print(f"account_id: {payload.get('account_id')}")
                        print(f"user_id: {payload.get('user_id')}")
                        
                        print("\nAssignee Object:")
                        print(json.dumps(payload.get('assignee'), indent=2))
                        
                        print("\nAccount Object:")
                        print(json.dumps(payload.get('account'), indent=2))
                        
                    except Exception as e:
                        print(f"JSON Parse Error: {e}")
                        print(payload_str[:500])
                    found = True
                    break
            except Exception as e:
                pass
    if found:
        break

if not found:
    print("Not found in any parquet file in orders directory.")
