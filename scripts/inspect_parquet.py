import pandas as pd
import json

# Load parquet file
file_path = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw/orders/mock/2024/01/mock_order.parquet'

try:
    df = pd.read_parquet(file_path)
    print("Columns:", df.columns)
    
    if 'payload' in df.columns:
        # Get first row payload
        payload = df['payload'].iloc[0]
        
        # If payload is string (escaped json), parse it
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
                print("Payload Structure (First Row):")
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print("Payload is string but not valid JSON:", payload)
        else:
             print("Payload (First Row):", payload)
             
    else:
        print("Payload column not found.")

except Exception as e:
    print(f"Error reading parquet: {e}")
