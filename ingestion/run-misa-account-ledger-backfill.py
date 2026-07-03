"""Backfill MISA 'Sổ chi tiết tài khoản' for a date range.

Downloads full chart of accounts for each month sequentially.
Saves to app_data/input_source/misa-account-ledger-backfill/ (staging — NOT auto-ingested).
Skips months where file already exists (safe to resume).

Usage:
  python ingestion/run-misa-account-ledger-backfill.py
  python ingestion/run-misa-account-ledger-backfill.py --from 2023-01 --to 2023-12
  python ingestion/run-misa-account-ledger-backfill.py --account 642
  python ingestion/run-misa-account-ledger-backfill.py --headed
  python ingestion/run-misa-account-ledger-backfill.py --delay 45
"""
import io
import os
import sys
import time
import argparse
import importlib.util
from pathlib import Path

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

MISA_USERNAME = os.environ.get("MISA_USERNAME", "oanh.ngo@fgorg.vn")
MISA_PASSWORD = os.environ.get("MISA_PASSWORD", "Oanh@1234")
COOKIE_DIR    = PROJECT_ROOT / "ingestion" / ".cookies"


def _months_range(from_ym: str, to_ym: str):
    """Yield 'YYYY-MM' strings inclusive."""
    fy, fm = map(int, from_ym.split("-"))
    ty, tm = map(int, to_ym.split("-"))
    y, m = fy, fm
    while (y, m) <= (ty, tm):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def run():
    ap = argparse.ArgumentParser(description="Backfill MISA account ledger by month")
    ap.add_argument("--from",    dest="from_ym", default="2022-01", metavar="YYYY-MM",
                    help="Start month (default: 2022-01)")
    ap.add_argument("--to",      dest="to_ym",   default="2025-12", metavar="YYYY-MM",
                    help="End month inclusive (default: 2025-12)")
    ap.add_argument("--account", default="",
                    help="Account prefix to filter (empty = full chart of accounts)")
    ap.add_argument("--headed",  action="store_true",
                    help="Show browser window (use if headless all-accounts fails)")
    ap.add_argument("--delay",   type=int, default=30,
                    help="Seconds between downloads to avoid overwhelming MISA (default 30)")
    ap.add_argument("--timeout", type=int, default=300,
                    help="Seconds to wait for each download (default 300)")
    ap.add_argument("--output-dir", default=None,
                    help="Staging output folder (default: misa-account-ledger-backfill/)")
    args = ap.parse_args()

    output_dir = Path(
        args.output_dir
        or PROJECT_ROOT / "app_data" / "input_source" / "misa-account-ledger-backfill"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    months = list(_months_range(args.from_ym, args.to_ym))
    account_label = args.account or "(full chart of accounts)"
    print("=" * 64)
    print(f"MISA account ledger backfill")
    print(f"  Range:   {args.from_ym} → {args.to_ym}  ({len(months)} months)")
    print(f"  Account: {account_label}")
    print(f"  Output:  {output_dir}")
    print(f"  Delay:   {args.delay}s between downloads")
    print(f"  Headed:  {args.headed}")
    print("=" * 64)
    print()

    done = skipped = failed = 0
    failed_months = []

    for i, ym in enumerate(months):
        yyyymm = ym.replace("-", "")

        # Skip if any xlsx for this month already exists in staging
        existing = list(output_dir.glob(f"*{yyyymm}*.xlsx"))
        if existing:
            print(f"[{i+1:2d}/{len(months)}] {ym}  SKIP — {existing[0].name}")
            skipped += 1
            continue

        print(f"[{i+1:2d}/{len(months)}] {ym}  downloading...")
        try:
            saved = downloader.download_account_ledger(
                output_dir      = output_dir,
                cookie_dir      = COOKIE_DIR,
                username        = MISA_USERNAME,
                password        = MISA_PASSWORD,
                headless        = not args.headed,
                period          = ym,
                timeout_seconds = args.timeout,
                account         = args.account,
            )
            print(f"           OK → {saved.name}")
            done += 1
        except Exception as e:
            print(f"           FAIL: {e}")
            failed += 1
            failed_months.append(ym)

        # Pause between downloads (skip after last)
        if i < len(months) - 1:
            print(f"           sleeping {args.delay}s...")
            time.sleep(args.delay)

    print()
    print("=" * 64)
    print(f"Result: {done} downloaded, {skipped} skipped, {failed} failed")
    if failed_months:
        print(f"Failed months: {', '.join(failed_months)}")
        print("Re-run with --from / --to targeting failed months to retry.")
    print(f"Staging: {output_dir}")
    print("Next step: inspect files, then use run-misa-account-ledger-file-drop.py")
    print("           to ingest each file (one at a time to avoid UPSERT wipe).")
    print("=" * 64)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run()
