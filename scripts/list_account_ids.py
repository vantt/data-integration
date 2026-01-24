import duckdb
import os
import json

base_dir = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw/orders'

print(f"Scanning {base_dir} for account_ids...")

ids = set()
samples = {}

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".parquet"):
            full_path = os.path.join(root, file)
            try:
                con = duckdb.connect()
                # Extract account_id
                query = f"SELECT distinct json_extract_string(payload, '$.account_id') as aid, payload FROM '{full_path}' WHERE json_extract_string(payload, '$.account_id') IS NOT NULL"
                result = con.execute(query).fetchall()
                for r in result:
                    aid = r[0]
                    payload_str = r[1]
                    if aid is not None:
                        ids.add(aid)
                        if aid not in samples:
                             # Store sample payload for this account_id to inspect account object
                             samples[aid] = payload_str
            except Exception as e:
                pass

print(f"Found {len(ids)} Account IDs.")
for i in list(ids)[:5]:
    print(f"ID: {i}")

if samples:
    print("\nInspecting Account Object for first ID:")
    first_id = list(samples.keys())[0]
    try:
        p = json.loads(samples[first_id])
        print(f"ID: {first_id}")
        print("Account Object:")
        print(json.dumps(p.get('account'), indent=2))
        print("User Name:")
        print(p.get('user_name'))
    except:
        pass

if not ids:
    print("No non-null account_ids found.")
