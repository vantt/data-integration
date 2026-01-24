import duckdb
import os

target_id = '809888'
base_dir = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw'

print(f"Scanning {base_dir} for {target_id}...")

found = False

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".parquet"):
            full_path = os.path.join(root, file)
            # print(f"Checking {full_path}")
            try:
                con = duckdb.connect()
                # Check if payload contains the ID
                query = f"SELECT payload FROM '{full_path}' WHERE payload LIKE '%{target_id}%' LIMIT 1"
                result = con.execute(query).fetchall()
                if result:
                    print(f"\nFOUND in: {full_path}")
                    print("Values:")
                    payload = result[0][0]
                    import json
                    try:
                        p = json.loads(payload)
                        print(json.dumps(p, indent=2))
                    except:
                        print(payload)
                    found = True
                    break
            except Exception as e:
                pass
                # print(f"Error reading {file}: {e}")
    if found:
        break

if not found:
    print("Not found in any parquet file.")
