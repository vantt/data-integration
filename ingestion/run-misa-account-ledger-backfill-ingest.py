"""Ingest all staged MISA account-ledger backfill files into the data lake.

Processes each file via run-misa-account-ledger-file-drop.py --file <path>.
Reports row/entry counts per year at the end.

Usage:
  python ingestion/run-misa-account-ledger-backfill-ingest.py
  python ingestion/run-misa-account-ledger-backfill-ingest.py --staging-dir path/to/dir
  python ingestion/run-misa-account-ledger-backfill-ingest.py --from 2023-01 --to 2023-12
"""
import io
import re
import sys
import subprocess
import argparse
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FILE_DROP_SCRIPT = PROJECT_ROOT / "ingestion" / "run-misa-account-ledger-file-drop.py"


def _months_range(from_ym: str, to_ym: str):
    fy, fm = map(int, from_ym.split("-"))
    ty, tm = map(int, to_ym.split("-"))
    y, m = fy, fm
    while (y, m) <= (ty, tm):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def _extract_row_count(output: str) -> int:
    """Pull total rows written from file-drop output."""
    # Look for patterns like "Wrote 1234 rows" or "rows written: 1234"
    for pattern in [
        r"Wrote\s+(\d[\d,]*)\s+rows",
        r"rows written[:\s]+(\d[\d,]*)",
        r"(\d[\d,]*)\s+rows",
        r"Total entries[:\s]+(\d[\d,]*)",
    ]:
        m = re.search(pattern, output, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
    return -1  # unknown


def run():
    ap = argparse.ArgumentParser(description="Ingest MISA backfill files into data lake")
    ap.add_argument("--staging-dir", default=None,
                    help="Staging dir (default: misa-account-ledger-backfill/)")
    ap.add_argument("--from", dest="from_ym", default="2021-01", metavar="YYYY-MM")
    ap.add_argument("--to",   dest="to_ym",   default="2025-12", metavar="YYYY-MM")
    args = ap.parse_args()

    staging_dir = Path(
        args.staging_dir
        or PROJECT_ROOT / "app_data" / "input_source" / "misa-account-ledger-backfill"
    )

    months = list(_months_range(args.from_ym, args.to_ym))

    print("=" * 64)
    print(f"MISA account-ledger backfill INGEST")
    print(f"  Range:       {args.from_ym} → {args.to_ym}  ({len(months)} months)")
    print(f"  Staging dir: {staging_dir}")
    print("=" * 64)
    print()

    done = skipped = failed = 0
    year_rows: dict[int, int] = defaultdict(int)
    year_months: dict[int, int] = defaultdict(int)
    failed_months = []

    for i, ym in enumerate(months):
        yyyymm = ym.replace("-", "")
        year = int(ym[:4])

        candidates = list(staging_dir.glob(f"*{yyyymm}*.xlsx"))
        if not candidates:
            print(f"[{i+1:2d}/{len(months)}] {ym}  SKIP — no file in staging")
            skipped += 1
            continue

        xlsx = candidates[0]
        print(f"[{i+1:2d}/{len(months)}] {ym}  ingesting {xlsx.name} ...")

        env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [sys.executable, str(FILE_DROP_SCRIPT), "--file", str(xlsx)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(PROJECT_ROOT), env=env,
        )

        combined = result.stdout + result.stderr
        if result.returncode != 0:
            print(f"           FAIL (exit {result.returncode})")
            # Print last 10 lines of output for context
            lines = combined.strip().splitlines()
            for line in lines[-10:]:
                print(f"    {line}")
            failed += 1
            failed_months.append(ym)
        else:
            rows = _extract_row_count(combined)
            year_rows[year] += max(rows, 0)
            year_months[year] += 1
            row_label = f"{rows:,} rows" if rows >= 0 else "? rows"
            print(f"           OK  ({row_label})")
            # Show key reconciliation lines (MISMATCH warnings, totals)
            for line in combined.splitlines():
                if any(kw in line for kw in ["MISMATCH", "Total", "Wrote", "rows", "Error"]):
                    print(f"    {line}")
            done += 1

    print()
    print("=" * 64)
    print(f"Result: {done} ingested, {skipped} skipped, {failed} failed")
    print()
    print("Data volume per year:")
    for year in sorted(year_rows):
        months_done = year_months[year]
        rows = year_rows[year]
        if rows > 0:
            print(f"  {year}: {rows:>10,} rows  ({months_done} months)")
        else:
            print(f"  {year}: (row count not parsed)  ({months_done} months)")

    if failed_months:
        print()
        print(f"Failed: {', '.join(failed_months)}")
        print("Re-run with --from / --to to retry failed months.")
        sys.exit(1)


if __name__ == "__main__":
    run()
