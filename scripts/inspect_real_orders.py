import duckdb
import json
import os

file_path = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw/order/ingest_method=batch_sync/year=2026/month=1/part-00000-ceb575a9-fb60-4607-94f7-570f3184069d-c000.snappy.parquet'

print(f"Reading {file_path}")

try:
    con = duckdb.connect()
    # Select distinct payloads containing non-null account_id or assignee_id
    query = f"""
    SELECT payload 
    FROM '{file_path}' 
    WHERE json_extract_string(payload, '$.account_id') IS NOT NULL 
       OR json_extract_string(payload, '$.assignee_id') IS NOT NULL 
    LIMIT 2
    """
    result = con.execute(query).fetchall()
    
    if result:
        for idx, r in enumerate(result):
            print(f"\n--- Row {idx+1} ---")
            payload_str = r[0]
            try:
                p = json.loads(payload_str)
                print("IDs:")
                print(f"assignee_id: {p.get('assignee_id')}")
                print(f"account_id: {p.get('account_id')}")
                
                print("\nObjects:")
                print("Assignee:", json.dumps(p.get('assignee'), indent=2))
                print("Account:", json.dumps(p.get('account'), indent=2))
                
                # Check for other user-like fields
                print("\nOther User Fields:")
                for k in p.keys():
                    if 'user' in k or 'name' in k:
                        if k not in ['customer_data', 'billing_address', 'shipping_address', 'channel', 'source_name', 'payment_method_name', 'location_name']:
                             print(f"{k}: {p.get(k)}")

            except Exception as e:
                print(f"Error parsing JSON: {e}")
    else:
        print("No rows with account_id or assignee_id found.")

except Exception as e:
    print(f"Error: {e}")
