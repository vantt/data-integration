"""MISA AMIS Account Ledger ('Sổ chi tiết các tài khoản') Excel parser.

Parses 'So_chi_tiet_6421 6422.xlsx' (or any account-ledger export) from MISA AMIS.
Outputs 1 DataFrame: account_ledger (1 row per journal line, section-based parse).

Format differs fundamentally from sales-ledger:
  - Sales ledger: 1 row/invoice-line, account in column 'cogs_account'
  - Account ledger: section-based — marker row sets current_account (forward-fill),
    detail rows carry the actual debit/credit amounts.

See docs/architecture/order-pl/overhead-account-ledger-ingestion-design.md §2 (parser),
§4 (idempotency), §5 (net rule) for authoritative design decisions.
"""

import os
import warnings
import pandas as pd
from datetime import datetime, timezone


# ── Constants ─────────────────────────────────────────────────────────────────

# Expected sheet name for defense-in-depth guard (misdropped file → loud error)
EXPECTED_SHEET_NAME = "SỔ CHI TIẾT CÁC TÀI KHOẢN"

# Sentinel string in col A that marks an account section header
ACCOUNT_MARKER_PREFIX = "Tài khoản:"

# Sentinel in col E (index 4) that marks a subtotal row → skip
SUBTOTAL_MARKER = "Cộng"

# Sentinels in col E marking the per-account opening/closing balance rows.
# These carry running balances (cols I/J) but no debit/credit movement.
OPENING_BALANCE_MARKER = "Số dư đầu kỳ"
CLOSING_BALANCE_MARKER = "Số dư cuối kỳ"

# Column indices (0-based) — real export has 10 cols: A=0…J=9
COL_POSTING_DATE = 0   # A — Ngày hạch toán
COL_VOUCHER_NO   = 1   # B — Số chứng từ
COL_INVOICE_DATE = 2   # C — Ngày hóa đơn
COL_INVOICE_NO   = 3   # D — Số hóa đơn
COL_DESCRIPTION  = 4   # E — Diễn giải
COL_OFFSET_ACCT  = 5   # F — TK đối ứng
COL_DEBIT        = 6   # G — Phát sinh Nợ
COL_CREDIT       = 7   # H — Phát sinh Có
COL_DEBIT_BAL    = 8   # I — Dư Nợ (running debit balance after this line)
COL_CREDIT_BAL   = 9   # J — Dư Có (running credit balance after this line)

# Kết chuyển cuối kỳ account — warn if present (see §5 net rule)
KET_CHUYEN_ACCOUNT = "911"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_int_vnd(value):
    """Convert a cell value to int VND; returns 0 on blank/dash/None.

    Mirrors the money-cleanup pattern in sales-ledger-parser.py.
    MISA cells can be: int, float, str with commas, "-", "", or NaN.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    s = str(value).strip().replace(",", "").replace(".", "")
    if s in ("", "-"):
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _to_date(value):
    """Coerce a cell value to datetime.date; returns None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    # pandas Timestamp
    if hasattr(value, "date"):
        try:
            return value.date()
        except Exception:
            pass
    try:
        parsed = pd.to_datetime(str(value), errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _is_datetime_like(value):
    """Return True if value looks like a posting date (datetime or Timestamp)."""
    if isinstance(value, datetime):
        return True
    if hasattr(value, "year") and hasattr(value, "month"):
        # pandas Timestamp / numpy datetime64
        return True
    return False


def _fmt_offset_account(value):
    """Format offset account code: numeric float → str; blank → None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        s = str(value).strip()
        return s if s else None


def _account_group(account_str):
    """Derive account_group from account string.

    Rule: starts with '6421' → '6421'; starts with '6422' → '6422'; else first 4 chars.
    Keeps roll-up flexibility while distinguishing the two overhead pools.
    """
    if account_str.startswith("6421"):
        return "6421"
    if account_str.startswith("6422"):
        return "6422"
    return account_str[:4] if len(account_str) >= 4 else account_str


def _add_partition_keys(df):
    """Inject year/month partition columns from posting_date (mirrors sales parser)."""
    dates = pd.to_datetime(df["posting_date"], errors="coerce")
    df["year"] = dates.dt.year.fillna(1970).astype(int)
    df["month"] = dates.dt.month.fillna(1).astype(int)
    return df


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_misa_account_ledger(file_path):
    """Parse one MISA 'Sổ chi tiết các tài khoản' Excel file.

    Args:
        file_path: str or Path to the .xlsx file.

    Returns:
        (df, recon)
        - df: DataFrame with ledger lines. Empty if no detail rows found.
        - recon: dict with reconciliation summary:
            {
              'total_debit': int,
              'per_account': {account: {'lines': int, 'marker': int, 'cong': int}},
              'mismatches': [account, ...],
              'ket_chuyen_911': bool,
            }

    Raises:
        ValueError: if file does not match expected account-ledger format.
    """
    file_path = str(file_path)
    source_file = os.path.basename(file_path)
    ingested_at = datetime.now(timezone.utc)
    print(f"Parsing: {source_file}")

    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

    # ── 1. Load sheet — header=None so we control row scanning ────────────────
    # Read all columns as raw values; header row is row 4 (index 3), but we
    # do NOT use pandas header= because section markers interleave with data.
    try:
        raw = pd.read_excel(
            file_path,
            sheet_name=0,      # always sheet 0; name validated below
            header=None,
            engine="openpyxl",
            dtype=object,      # preserve raw cell types — no coercion yet
        )
    except Exception as exc:
        raise ValueError(f"Cannot open Excel file '{source_file}': {exc}") from exc

    # ── 2. Sheet-title guard (defense-in-depth) ────────────────────────────────
    # Two checks: (a) sheet name, (b) cell A1 text. Both can differ independently.
    # This is the critical guard against a sales-ledger dropped in wrong folder.
    xl = pd.ExcelFile(file_path, engine="openpyxl")
    actual_sheet_name = xl.sheet_names[0] if xl.sheet_names else ""
    cell_a1 = str(raw.iloc[0, 0]).strip() if not raw.empty else ""

    sheet_name_ok = actual_sheet_name.strip() == EXPECTED_SHEET_NAME
    cell_a1_ok = EXPECTED_SHEET_NAME in cell_a1

    if not sheet_name_ok and not cell_a1_ok:
        raise ValueError(
            f"Not an account-ledger file (wrong sheet) — check folder.\n"
            f"  Expected sheet name: '{EXPECTED_SHEET_NAME}'\n"
            f"  Got sheet name:      '{actual_sheet_name}'\n"
            f"  Cell A1 text:        '{cell_a1}'\n"
            f"  Source: {source_file}"
        )

    print(f"  Sheet guard OK — sheet='{actual_sheet_name}', A1='{cell_a1[:60]}'")

    # ── 3. Section-based row scan (from row 5, index 4 onward) ────────────────
    # Rows 0-3: title, currency, blank, headers — all skipped.
    # From row 4 (0-based index 4 = Excel row 5):
    #   - ACCOUNT_MARKER row: col A string starts with "Tài khoản:" → set current_account
    #   - SUBTOTAL row: col E == "Cộng" → skip (capture cong total)
    #   - DETAIL row: col A is a datetime → emit ledger line

    rows = []           # accumulated detail rows
    current_account = None   # forward-filled from marker rows

    # Reconciliation accumulators per account
    marker_totals = {}  # account → int (period Nợ from marker row col G)
    cong_totals = {}    # account → int (subtotal from Cộng row col G)
    line_debits = {}    # account → int (sum of detail row debits)

    # Opening balance per account (signed: Dư Nợ − Dư Có) from "Số dư đầu kỳ" row.
    # Forward-filled onto every detail row of the account so cashflow/balance
    # models get the period-opening anchor without a second pass.
    opening_balances = {}  # account → int (signed opening balance)

    has_ket_chuyen_911 = False

    data_start = 4  # 0-based index of first data row (Excel row 5)
    n_rows = len(raw)

    for idx in range(data_start, n_rows):
        row = raw.iloc[idx]

        cell_a = row.iloc[COL_POSTING_DATE]  # col A
        cell_e = row.iloc[COL_DESCRIPTION]   # col E

        # ── Account marker row: col A is a string starting with "Tài khoản:" ──
        if isinstance(cell_a, str) and cell_a.strip().startswith(ACCOUNT_MARKER_PREFIX):
            account_raw = cell_a.strip()[len(ACCOUNT_MARKER_PREFIX):].strip()
            current_account = account_raw

            # col G = marker's period debit total (the account's Phát sinh Nợ header)
            marker_debit = _to_int_vnd(row.iloc[COL_DEBIT] if raw.shape[1] > COL_DEBIT else None)
            marker_totals[current_account] = marker_debit
            # Initialize accumulators for this account (may be re-set for sub-accounts)
            if current_account not in line_debits:
                line_debits[current_account] = 0
            print(f"  Account marker: {current_account} (marker Nợ = {marker_debit:,})")
            continue

        # ── Opening balance row: col E == "Số dư đầu kỳ" ──────────────────────
        # Carries the period-opening running balance in cols I/J (no movement).
        if isinstance(cell_e, str) and cell_e.strip() == OPENING_BALANCE_MARKER:
            if current_account is not None and raw.shape[1] > COL_CREDIT_BAL:
                open_dr = _to_int_vnd(row.iloc[COL_DEBIT_BAL])
                open_cr = _to_int_vnd(row.iloc[COL_CREDIT_BAL])
                opening_balances[current_account] = open_dr - open_cr
            continue

        # ── Closing balance row: col E == "Số dư cuối kỳ" → skip (running bal covers it) ──
        if isinstance(cell_e, str) and cell_e.strip() == CLOSING_BALANCE_MARKER:
            continue

        # ── Subtotal row: col E == "Cộng" ─────────────────────────────────────
        if isinstance(cell_e, str) and cell_e.strip() == SUBTOTAL_MARKER:
            if current_account is not None:
                cong_debit = _to_int_vnd(row.iloc[COL_DEBIT] if raw.shape[1] > COL_DEBIT else None)
                cong_totals[current_account] = cong_debit
            continue

        # ── Detail row: col A is a datetime (posting date) ────────────────────
        if _is_datetime_like(cell_a):
            if current_account is None:
                print(f"  WARNING: detail row at Excel row {idx+1} has no current_account — skipping")
                continue

            posting_date = _to_date(cell_a)
            voucher_no = str(row.iloc[COL_VOUCHER_NO]).strip() if pd.notna(row.iloc[COL_VOUCHER_NO]) else None
            invoice_date = _to_date(row.iloc[COL_INVOICE_DATE]) if raw.shape[1] > COL_INVOICE_DATE else None
            invoice_no = str(row.iloc[COL_INVOICE_NO]).strip() if pd.notna(row.iloc[COL_INVOICE_NO]) else None
            description = str(row.iloc[COL_DESCRIPTION]).strip() if pd.notna(row.iloc[COL_DESCRIPTION]) else None
            offset_account = _fmt_offset_account(row.iloc[COL_OFFSET_ACCT] if raw.shape[1] > COL_OFFSET_ACCT else None)
            debit = _to_int_vnd(row.iloc[COL_DEBIT] if raw.shape[1] > COL_DEBIT else None)
            credit = _to_int_vnd(row.iloc[COL_CREDIT] if raw.shape[1] > COL_CREDIT else None)
            # Running balance after this line (cols I/J); signed net for convenience.
            debit_balance = _to_int_vnd(row.iloc[COL_DEBIT_BAL] if raw.shape[1] > COL_DEBIT_BAL else None)
            credit_balance = _to_int_vnd(row.iloc[COL_CREDIT_BAL] if raw.shape[1] > COL_CREDIT_BAL else None)

            # ── 911 kết chuyển guard (§5) ──────────────────────────────────────
            if offset_account == KET_CHUYEN_ACCOUNT:
                has_ket_chuyen_911 = True
                print(
                    f"  [!] KET_CHUYEN_911 detected at Excel row {idx+1} "
                    f"(account={current_account}, credit={credit:,}) — "
                    f"net = Nợ − Có needs 911 exclusion, verify"
                )

            # Accumulate line-level debits for checksum
            line_debits[current_account] = line_debits.get(current_account, 0) + debit

            rows.append({
                "posting_date": posting_date,
                "voucher_no": voucher_no,
                "invoice_date": invoice_date,
                "invoice_no": invoice_no,
                "description": description,
                "offset_account": offset_account,
                "debit": debit,
                "credit": credit,
                "debit_balance": debit_balance,
                "credit_balance": credit_balance,
                "opening_balance": opening_balances.get(current_account, 0),
                "account": current_account,
                "account_group": _account_group(current_account),
            })
            continue

        # ── Other rows (blank lines, title, header row, currency row) → skip ──

    # ── 3b. Drop redundant PARENT accounts (rollups re-listed under leaves) ────
    # MISA lists each txn under BOTH the parent account (e.g. 64217) AND its leaf
    # sub-account (e.g. 642174) — same voucher/amount twice. Summing both
    # double-counts. Keep leaves; drop a parent X iff a longer account starts
    # with X AND X's line-sum == sum of its kept descendants (safety check that
    # X is a pure rollup, not an account with its own unique lines). Process
    # longest-first so multi-level hierarchies (6421→64217→642172) net correctly.
    accounts = set(line_debits.keys()) | set(marker_totals.keys())
    dropped_parents = set()
    for parent in sorted(accounts, key=len, reverse=True):
        descendants = [a for a in accounts
                       if a != parent and a.startswith(parent) and a not in dropped_parents]
        if not descendants:
            continue
        desc_sum = sum(line_debits.get(a, 0) for a in descendants)
        if line_debits.get(parent, 0) == desc_sum:
            dropped_parents.add(parent)
            print(f"  Parent rollup dropped: {parent} == Σ descendants "
                  f"{sorted(descendants)} ({desc_sum:,}) — keeping leaves only")
        else:
            print(f"  [!] {parent} looks like a parent but its line-sum "
                  f"{line_debits.get(parent, 0):,} != Σ descendants {desc_sum:,} "
                  f"— KEPT (has own lines), verify")
    if dropped_parents:
        rows = [r for r in rows if r["account"] not in dropped_parents]
        for p in dropped_parents:
            line_debits.pop(p, None)
            marker_totals.pop(p, None)
            cong_totals.pop(p, None)

    # ── 4. Build DataFrame ─────────────────────────────────────────────────────
    if not rows:
        print(f"  WARNING: no detail rows found in {source_file}")
        df = pd.DataFrame(columns=[
            "posting_date", "voucher_no", "invoice_date", "invoice_no",
            "description", "offset_account", "debit", "credit",
            "debit_balance", "credit_balance", "opening_balance",
            "account", "account_group",
            "ingest_method", "source_file", "ingested_at",
            "year", "month",
        ])
        recon = {"total_debit": 0, "per_account": {}, "mismatches": [], "ket_chuyen_911": False}
        return df, recon

    df = pd.DataFrame(rows)
    print(f"  Detail rows: {len(df)}")

    # Coerce money columns to Int64 (nullable integer — consistent with sales parser)
    df["debit"] = df["debit"].astype("Int64")
    df["credit"] = df["credit"].astype("Int64")
    df["debit_balance"] = df["debit_balance"].astype("Int64")
    df["credit_balance"] = df["credit_balance"].astype("Int64")
    df["opening_balance"] = df["opening_balance"].astype("Int64")

    # ── 5. Reconciliation checksum per account ─────────────────────────────────
    # Σ(detail debit) per account == marker col-G == Cộng col-G.
    # Mismatch → loud warn but do NOT raise (surface and continue).
    mismatches = []
    per_account_recon = {}

    all_accounts = set(list(marker_totals.keys()) + list(line_debits.keys()))
    for acct in all_accounts:
        lines_sum = line_debits.get(acct, 0)
        marker_val = marker_totals.get(acct, None)
        cong_val = cong_totals.get(acct, None)

        per_account_recon[acct] = {
            "lines": lines_sum,
            "marker": marker_val,
            "cong": cong_val,
        }

        # Check marker vs lines
        if marker_val is not None and lines_sum != marker_val:
            mismatches.append(acct)
            print(
                f"  [!] RECON_MISMATCH account={acct}: "
                f"lines={lines_sum:,} vs marker={marker_val:,}"
                + (f" vs cong={cong_val:,}" if cong_val is not None else "")
            )
        # Check cong vs lines (secondary check)
        elif cong_val is not None and lines_sum != cong_val:
            mismatches.append(acct)
            print(
                f"  [!] RECON_MISMATCH account={acct}: "
                f"lines={lines_sum:,} vs cong={cong_val:,}"
                + (f" (marker={marker_val:,})" if marker_val is not None else "")
            )

    total_debit = int(df["debit"].sum())
    print(f"  Total Nợ (all accounts): {total_debit:,}")
    if mismatches:
        print(f"  [!] RECON mismatches for accounts: {mismatches}")
    else:
        print(f"  Reconciliation: OK (all accounts match)")

    # ── 6. Inject ingestion metadata ───────────────────────────────────────────
    df["ingest_method"] = "file_drop"
    df["source_file"] = source_file
    df["ingested_at"] = ingested_at

    # ── 7. Partition keys from posting_date ────────────────────────────────────
    df = _add_partition_keys(df)

    recon = {
        "total_debit": total_debit,
        "per_account": per_account_recon,
        "mismatches": mismatches,
        "ket_chuyen_911": has_ket_chuyen_911,
    }

    return df, recon
