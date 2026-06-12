import sys
import os

# Add src to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sapo.products import sapo_products_source
from utils.pipeline_runner import run_pipeline
import argparse

def run(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--limit", type=int, default=100)
    args, _ = parser.parse_known_args(argv)

    source_args = {
        "max_pages": args.limit
    }

    return run_pipeline(
        pipeline_name="sapo_v2_products_batch",
        dataset_name="sapo_v2_raw",
        source_factory=sapo_products_source,
        source_args=source_args,
        argv=argv
    )

if __name__ == "__main__":
    run()
