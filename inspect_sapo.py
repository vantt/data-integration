
import pandas as pd
import json
import os

# Path to the parquet file
file_path = r"d:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2\app_data\data_lake\sapo_raw\order\ingest_method=batch_sync\year=2024\month=12\part-00000-41abeb11-4c3a-4c70-bc95-93d1691d2c39-c000.snappy.parquet"

try:
    print(f"Reading file: {file_path}")
    df = pd.read_parquet(file_path)
    
    print("Columns in Parquet:", df.columns.tolist())
    
    if 'payload' in df.columns:
        print("\nAnalyzing 'payload' column...")
        
        # Get a sample of non-null payloads
        sample_payloads = df['payload'].dropna().head(5)
        
        all_keys = set()
        
        for i, payload_str in enumerate(sample_payloads):
            try:
                data = json.loads(payload_str)
                
                # Function to recursively find keys
                def exploring_keys(d, prefix=''):
                    keys = set()
                    if isinstance(d, dict):
                        for k, v in d.items():
                            full_key = f"{prefix}.{k}" if prefix else k
                            keys.add(full_key)
                            keys.update(exploring_keys(v, full_key))
                    elif isinstance(d, list) and len(d) > 0:
                         # Check first item if it's a dict
                        if isinstance(d[0], dict):
                             keys.update(exploring_keys(d[0], f"{prefix}[]"))
                    return keys

                keys = exploring_keys(data)
                all_keys.update(keys)
                
                if i == 0:
                    print("\nFirst record structure:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000] + "...") # Print first 2000 chars

            except json.JSONDecodeError:
                print(f"Error decoding JSON for row {i}")
        
        print("\n--- Potential Sales/Staff Fields ---")
        keywords = ['assignee', 'sales', 'staff', 'employee', 'user', 'account', 'seller', 'person', 'referral', 'source']
        
        found_fields = sorted([k for k in all_keys if any(keyword in k.lower() for keyword in keywords)])
        
        for field in found_fields:
            print(field)
            
    else:
        print("Column 'payload' not found.")

except Exception as e:
    print(f"An error occurred: {e}")
