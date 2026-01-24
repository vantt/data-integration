import duckdb
import os
import json

base_dir = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw/orders'

print(f"Scanning {base_dir} for assignee_ids...")

ids = set()

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".parquet"):
            full_path = os.path.join(root, file)
            try:
                con = duckdb.connect()
                # Extract assignee_id
                query = f"SELECT distinct json_extract_string(payload, '$.assignee_id') FROM '{full_path}'"
                result = con.execute(query).fetchall()
                for r in result:
                    if r[0] is not None:
                        ids.add(r[0])
            except Exception as e:
                pass

print("Found Assignee IDs:")
for i in ids:
    print(i)

if not ids:
    print("No non-null assignee_ids found.")
