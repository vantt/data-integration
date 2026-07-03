"""Entry point: MISA AMIS account-ledger auto-download.

Downloads 'Sổ chi tiết tài khoản' Excel (accounts 6421 + 6422) from MISA AMIS
web for the previous month, then drops the file into the account-ledger input
directory so the existing file-drop pipeline picks it up.

Usage:
  python ingestion/run-misa-account-ledger-download.py
  python ingestion/run-misa-account-ledger-download.py --headed
  python ingestion/run-misa-account-ledger-download.py --clear-cookies
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


downloader = _import(
    "misa_account_ledger_web_downloader",
    "src/misa_amis/misa_account_ledger_web_downloader.py",
)

# ── Config ─────────────────────────────────────────────────────────────────────

MISA_USERNAME = os.environ.get("MISA_USERNAME", "oanh.ngo@fgorg.vn")
MISA_PASSWORD = os.environ.get("MISA_PASSWORD", "Oanh@1234")

COOKIE_DIR = PROJECT_ROOT / "ingestion" / ".cookies"

_DEFAULT_OUTPUT_DIR = os.environ.get(
    "MISA_ACCOUNT_LEDGER_INPUT_DIR",
    str(PROJECT_ROOT / "app_data" / "input_source" / "misa-account-ledger"),
)
OUTPUT_DIR = (
    _DEFAULT_OUTPUT_DIR
    if os.path.isdir(_DEFAULT_OUTPUT_DIR)
    else "/app/var/input_source/misa-account-ledger"
)

PERIOD = "thang_truoc"


def run(argv=None):
    arg_parser = argparse.ArgumentParser(description="MISA AMIS account-ledger auto-download")
    arg_parser.add_argument("--headed",        action="store_true",
                            help="Show browser window")
    arg_parser.add_argument("--clear-cookies", action="store_true",
                            help="Delete saved cookies and force re-login")
    arg_parser.add_argument("--timeout",       type=int, default=300,
                            help="Seconds to wait for download (default 300)")
    arg_parser.add_argument("--account",       type=str,
                            default=downloader.DEFAULT_ACCOUNT,
                            help="Account prefix to download (default: 642 → all 6421*/6422*)")
    arg_parser.add_argument("--all-accounts",   action="store_true",
                            help="Download the FULL chart of accounts (overrides --account)")
    arg_parser.add_argument("--month",          type=str, default=None,
                            help="Specific month 'YYYY-MM' to download (default: previous month). "
                                 "Used for backfill.")
    args = arg_parser.parse_args(argv)

    if args.all_accounts:
        args.account = ""  # empty prefix → select all accounts

    period = args.month if args.month else PERIOD

    if args.clear_cookies:
        cookie_file = COOKIE_DIR / "misa_amis_cookies.json"
        if cookie_file.exists():
            cookie_file.unlink()
            print("Cleared MISA cookies.")
        else:
            print("No cookie file found.")
        return

    headless = not args.headed
    output   = Path(OUTPUT_DIR)
    start_d, end_d = downloader.period_date_range(period)
    print(f"MISA account-ledger download: period={period}  {start_d} → {end_d}")
    print(f"Account prefix: {args.account}")
    print(f"Output dir: {output}")
    print(f"Headless:   {headless}")

    saved_path = downloader.download_account_ledger(
        output_dir      = output,
        cookie_dir      = COOKIE_DIR,
        username        = MISA_USERNAME,
        password        = MISA_PASSWORD,
        headless        = headless,
        period          = period,
        timeout_seconds = args.timeout,
        account         = args.account,
    )

    print(f"\nDownload complete: {saved_path}")
    print("File is ready for run-misa-account-ledger-file-drop to process.")


if __name__ == "__main__":
    run()
