import sys
import os
import time
import argparse
import dlt

# Add src to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sapo.webhook_consumer import sapo_webhook_source
from utils.pipeline_runner import setup_dlt_env

def run(argv=None):
    # 1. Parse Args
    parser = argparse.ArgumentParser(description="Sapo Webhook Consumer")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for orchestration/Dagster)")
    parser.add_argument("--poll-limit", type=int, default=100, help="Number of messages to poll per cycle")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode")
    args = parser.parse_args(argv)

    # 2. Setup Env
    worker_url = os.getenv("WORKER_URL")
    if not worker_url:
        try:
             worker_url = dlt.secrets["sources.sapo_webhook_source.worker_url"]
        except:
             pass
    
    if not worker_url:
        print("❌ Error: WORKER_URL is missing. Please set it in .env or .dlt/secrets.toml")
        return

    dataset_name = "sapo_raw" + ("_dev" if args.dev else "")
    setup_dlt_env(dataset_name)

    # 3. Pipeline Init
    pipeline = dlt.pipeline(
        pipeline_name="sapo_v2_webhook_consumer",
        destination="filesystem",
        dataset_name=dataset_name
    )

    print(f"🚀 Starting Webhook Consumer Pipeline ({'ONCE' if args.once else 'LOOP'})")
    print(f"   Worker URL: {worker_url}")
    print(f"   Target Dataset: {dataset_name}")
    print(f"   Destination Bucket: {os.getenv('DESTINATION__FILESYSTEM__BUCKET_URL', 'Not Set')}")

    min_sleep = int(os.getenv("MIN_SLEEP_INTERVAL", "10"))
    max_sleep = int(os.getenv("MAX_SLEEP_INTERVAL", "60"))
    current_sleep = min_sleep

    # Loop Logic
    while True:
        try:
            source = sapo_webhook_source(worker_url=worker_url, poll_limit=args.poll_limit)
            info = pipeline.run(source, loader_file_format="parquet")
            
            if info:
                print(info)
                current_sleep = min_sleep
            else:
                print(f"💤 No new data. Sleeping {current_sleep}s..." if not args.once else "No new data.")
                if not args.once:
                    time.sleep(current_sleep)
                    current_sleep = min(current_sleep * 2, max_sleep)
            
            if args.once:
                # Return info for run_once callers (Dagster)
                return info
                
        except KeyboardInterrupt:
            print("🛑 Consumer stopped by user.")
            break
        except Exception as e:
            print(f"❌ Pipeline Error: {e}")
            if args.once:
                # In once mode, we want to fail hard so Dagster knows
                raise e
            time.sleep(current_sleep)

if __name__ == "__main__":
    run()
