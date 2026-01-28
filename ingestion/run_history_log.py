import sys
import os

# Add src to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sapo.history_log import sapo_history_log_source
from utils.pipeline_runner import run_pipeline
import argparse

def run(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None) # Optional limit
    parser.add_argument("--debug", action="store_true", default=True)
    args, _ = parser.parse_known_args(argv)

    # Configure source arguments
    source_args = {
        "page_size": args.page_size,
        "min_overlap_items": 500,
        "limit": args.limit,
        "debug": args.debug
    }

    run_pipeline(
        pipeline_name="sapo_history_log_pipeline",
        dataset_name="sapo_raw",
        source_factory=sapo_history_log_source,
        source_args=source_args,
        argv=argv
    )

if __name__ == "__main__":
    run()
