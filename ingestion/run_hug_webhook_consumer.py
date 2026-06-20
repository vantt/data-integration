"""
Hug Webhook Consumer runner.

Polls Cloudflare D1 for source_system='hug' events and lands them into:
  hug_raw/scan/         → hug_scan parquet
  hug_raw/optin_event/  → hug_optin_event parquet

Mirrors run_sapo_v2_webhook_consumer.py. Called by Dagster asset
ingest_hug_webhook_consumer_asset via argv=["--once"].
"""

import sys
import os
import time
import argparse
import dlt

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from hug.hug_webhook_consumer import hug_webhook_source
from utils.pipeline_runner import setup_dlt_env


def run(argv=None):
    parser = argparse.ArgumentParser(description="Hug Webhook Consumer")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for Dagster orchestration)",
    )
    parser.add_argument(
        "--poll-limit",
        type=int,
        default=100,
        help="Number of messages to poll per cycle",
    )
    parser.add_argument("--dev", action="store_true", help="Append _dev to dataset name")
    args = parser.parse_args(argv)

    worker_url = os.getenv("WORKER_URL")
    if not worker_url:
        try:
            worker_url = dlt.secrets["sources.hug_webhook_source.worker_url"]
        except Exception:
            pass

    if not worker_url:
        print("Error: WORKER_URL is missing. Set it in .env or .dlt/secrets.toml")
        return

    # Land into hug_raw, not sapo_v2_raw, so parquet paths don't collide.
    dataset_name = "hug_raw" + ("_dev" if args.dev else "")
    setup_dlt_env(dataset_name)

    pipeline = dlt.pipeline(
        pipeline_name="hug_webhook_consumer",
        destination="filesystem",
        dataset_name=dataset_name,
    )

    print(f"Starting Hug Webhook Consumer ({'ONCE' if args.once else 'LOOP'})")
    print(f"  Worker URL: {worker_url}")
    print(f"  Target Dataset: {dataset_name}")
    print(f"  Bucket: {os.getenv('DESTINATION__FILESYSTEM__BUCKET_URL', 'Not Set')}")

    min_sleep = int(os.getenv("MIN_SLEEP_INTERVAL", "10"))
    max_sleep = int(os.getenv("MAX_SLEEP_INTERVAL", "60"))
    current_sleep = min_sleep

    while True:
        try:
            source = hug_webhook_source(
                worker_url=worker_url, poll_limit=args.poll_limit
            )
            info = pipeline.run(source, loader_file_format="parquet")

            if info:
                print(info)
                current_sleep = min_sleep
            else:
                msg = f"No new Hug data. Sleeping {current_sleep}s..." if not args.once else "No new Hug data."
                print(msg)
                if not args.once:
                    time.sleep(current_sleep)
                    current_sleep = min(current_sleep * 2, max_sleep)

            if args.once:
                return info

        except KeyboardInterrupt:
            print("Hug consumer stopped by user.")
            break
        except Exception as e:
            print(f"Hug pipeline error: {e}")
            if args.once:
                raise
            time.sleep(current_sleep)


if __name__ == "__main__":
    run()
