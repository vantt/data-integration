"""Entry point: MISA AMIS sales ledger auto-download.

Downloads 'So chi tiet ban hang' Excel from MISA AMIS web for the previous week
(Tuan Truoc), then drops the file into the misa-sales-ledger input directory so
the existing file-drop pipeline (run-misa-sales-file-drop.py) can pick it up.

Usage:
  python ingestion/run-misa-sales-download.py
  python ingestion/run-misa-sales-download.py --headed       # show browser window
  python ingestion/run-misa-sales-download.py --clear-cookies
"""
import io
import os
import sys
import argparse
from pathlib import Path
import importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ingestion"))


def _import(name, rel_path):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / "ingestion" / rel_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


downloader = _import("misa_sales_web_downloader",
                     "src/misa_amis/misa_sales_web_downloader.py")

# ── Config ─────────────────────────────────────────────────────────────────────

MISA_USERNAME = os.environ.get("MISA_USERNAME", "oanh.ngo@fgorg.vn")
MISA_PASSWORD = os.environ.get("MISA_PASSWORD", "Oanh@1234")

# Cookie file lives alongside other source cookies
COOKIE_DIR = PROJECT_ROOT / "ingestion" / ".cookies"

# Drop file here so the Dagster sensor + run-misa-sales-file-drop pick it up
_DEFAULT_OUTPUT_DIR = os.environ.get(
    "MISA_INPUT_DIR",
    str(PROJECT_ROOT / "app_data" / "input_source" / "misa-sales-ledger"),
)
OUTPUT_DIR = (
    _DEFAULT_OUTPUT_DIR
    if os.path.isdir(_DEFAULT_OUTPUT_DIR)
    else "/app/var/input_source/misa-sales-ledger"
)

# Always download previous week (Mon-Sun)
PERIOD = "tuan_truoc"


def run(argv=None):
    arg_parser = argparse.ArgumentParser(description="MISA AMIS sales ledger auto-download")
    arg_parser.add_argument("--headed",        action="store_true",
                            help="Show browser window (useful for debugging)")
    arg_parser.add_argument("--clear-cookies", action="store_true",
                            help="Delete saved cookies and force re-login")
    arg_parser.add_argument("--timeout",       type=int, default=300,
                            help="Seconds to wait for download (default 300)")
    args = arg_parser.parse_args(argv)

    # Optionally clear cookies
    if args.clear_cookies:
        cookie_file = COOKIE_DIR / "misa_amis_cookies.json"
        if cookie_file.exists():
            cookie_file.unlink()
            print("Cleared MISA cookies — will re-login on next run.")
        else:
            print("No cookie file found.")
        return

    headless = not args.headed
    output   = Path(OUTPUT_DIR)
    start_d, end_d = downloader.period_date_range(PERIOD)
    print(f"MISA download: period={PERIOD}  {start_d} → {end_d}")
    print(f"Output dir:    {output}")
    print(f"Headless:      {headless}")

    saved_path = downloader.download_sales_ledger(
        output_dir      = output,
        cookie_dir      = COOKIE_DIR,
        username        = MISA_USERNAME,
        password        = MISA_PASSWORD,
        headless        = headless,
        period          = PERIOD,
        timeout_seconds = args.timeout,
    )

    print(f"\nDownload complete: {saved_path}")
    print("File is ready for run-misa-sales-file-drop to process.")


if __name__ == "__main__":
    run()
