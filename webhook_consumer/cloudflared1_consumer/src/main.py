import dlt
import os
import time
import json
from client import CloudflareWorkerClient

# Configuration
WORKER_URL = os.getenv("WORKER_URL", "http://localhost:8787")
POLL_LIMIT = int(os.getenv("POLL_LIMIT", "100"))
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", "5")) # Seconds to sleep if no data
SOURCE_SYSTEM = "sapo" # Optional: Filter by source

def run():
    client = CloudflareWorkerClient(WORKER_URL)
    
    # Configure dlt pipeline
    # We use a filesystem destination (parquet) for this example, or 'duckdb' as a local lakehouse.
    # The user request mentioned "save data into parquet".
    # We can use 'filesystem' destination or just local duckdb which stores as parquet/db.
    # Let's use 'filesystem' to store as parquet files if that's the explicit request, 
    # OR 'duckdb' and export? The user said "lưu dữ liệu vào parqute" (save data into parquet).
    # dlt with `destination='filesystem'` and `format='parquet'` is the direct way.
    
    # However, for simplicity in a standalone script without complex setup, 
    # we can also just use dlt to load to a local duckdb and it handles parquet under the hood if configured,
    # OR strictly filesystem.
    # Let's assume 'filesystem' destination to a local bucket/folder.
    # For this MVP, I will configure it to load to a local directory "data/webhooks".
    
    pipeline = dlt.pipeline(
        pipeline_name="cloudflared1_consumer",
        destination="filesystem",
        dataset_name="webhook_data"
    )

    print(f"Starting Consumer for {WORKER_URL}...")
    if SOURCE_SYSTEM:
        print(f"Filtering for source_system: {SOURCE_SYSTEM}")

    while True:
        try:
            print("Polling...")
            messages = client.poll_messages(source_system=SOURCE_SYSTEM, limit=POLL_LIMIT)
            
            if not messages:
                print(f"No messages. Sleeping {SLEEP_INTERVAL}s...")
                time.sleep(SLEEP_INTERVAL)
                continue

            print(f"Received {len(messages)} messages. Processing...")

            # Extract IDs for ACK later
            # Note: The 'payload' field in D1 is a JSON string. We should parse it or pass it as is?
            # dlt handles JSON extraction.
            # We want to load the *content* of the webhook.
            # The message structure from D1 is: { msg_id, payload (string), source_system, ... }
            
            # We can transform this list of dicts.
            # We want to keep msg_id for deduplication if needed, but definitely for ACK.
            
            data_to_load = []
            ids_to_ack = []
            
            for msg in messages:
                ids_to_ack.append(msg['msg_id'])
                
                # Try to parse the inner payload string to a dict if possible
                record = dict(msg)
                if isinstance(record.get('payload'), str):
                    try:
                        record['payload'] = json.loads(record['payload'])
                    except:
                        pass # Keep as string if redundant
                
                data_to_load.append(record)

            # Run dlt pipeline for this batch
            # We treat this as a separate load info
            load_info = pipeline.run(
                data_to_load, 
                table_name="webhooks", 
                loader_file_format="parquet"
            )
            
            print(load_info)

            # If load is successful (no exception thrown), we ACK
            # TODO: Inspect load_info for partial failures if necessary?
            # dlt raises exception on critical failure.
            
            print(f"Load successful. Acking {len(ids_to_ack)} messages...")
            client.batch_ack(ids_to_ack)
            
        except KeyboardInterrupt:
            print("Stopping consumer...")
            break
        except Exception as e:
            print(f"Pipeline error: {e}")
            time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    run()
