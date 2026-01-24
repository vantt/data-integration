import duckdb

# Load parquet file
file_path = r'd:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw/orders/mock/2024/01/mock_order.parquet'

try:
    con = duckdb.connect()
    # Select payload from parquet
    query = f"SELECT payload FROM '{file_path}' LIMIT 1"
    result = con.execute(query).fetchall()
    
    if result:
        payload = result[0][0]
        print("Payload (First Row):")
        print(payload)
    else:
        print("No rows found.")

except Exception as e:
    print(f"Error reading parquet with duckdb: {e}")
