"""MISA AMIS Sales Detail Ledger Excel parser.

Parses 'So_chi_tiet_ban_hang_*.xlsx' files exported from MISA AMIS.
Outputs 1 DataFrame: sales_lines (1 row per invoice-line with COGS).

Canonical rename dict is the SINGLE SOURCE OF TRUTH for VN→snake_case mapping.
See docs/misa-amis/data-source-description.md § 4 for full column dictionary.
"""

import os
import warnings
import pandas as pd
from datetime import datetime, timezone

# ── Canonical VN → snake_case rename dict ────────────────────────────────────
# Header row is at index 3 (0-based) in the Excel sheet.
# Trailing space in "Tên hàng trên chứng từ " is stripped by column cleanup.

SALES_LEDGER_RENAME = {
    "Ngày hạch toán": "posting_date",
    "Ngày chứng từ": "voucher_date",
    "Số chứng từ": "voucher_no",
    "Ngày hóa đơn": "invoice_date",
    "Số hóa đơn": "invoice_no",
    "Diễn giải chung": "description",
    "Tên hàng trên chứng từ": "product_name_on_document",
    "Mã khách hàng": "customer_code",
    "Tên khách hàng": "customer_name",
    "Mã hàng": "product_code",
    "Tên hàng": "product_name",
    "Hàng khuyến mại": "is_promo_line",
    "ĐVT": "unit_of_measure",
    "Tổng số lượng bán": "quantity",
    "Đơn giá": "unit_price",
    "Doanh số bán": "revenue_gross",
    "TK Nợ": "debit_account",
    "TK Có": "credit_account",
    "TK chiết khấu": "discount_account",
    "Chiết khấu": "discount_amount",
    "Tổng thanh toán": "total_payment",
    "TK giá vốn": "cogs_account",
    "Giá vốn": "cogs_amount",
    "Tên nhân viên bán hàng": "salesperson_name",
    "Mã thống kê": "channel_code",
}

# Required headers to validate (fail loud on header drift)
REQUIRED_HEADERS = {"Số chứng từ", "Mã hàng", "Giá vốn", "Doanh số bán"}


def parse_misa_sales_ledger(file_path):
    """Parse one MISA sales ledger Excel file.

    Returns:
        (df_sales_lines, cogs_total_claimed)
        - df_sales_lines: DataFrame with renamed cols, line_no synthesized, metadata injected.
        - cogs_total_claimed: int or None — the "Tổng cộng" footer's COGS value for reconciliation.
    """
    file_path = str(file_path)
    source_file = os.path.basename(file_path)
    ingested_at = datetime.now(timezone.utc)
    print(f"Parsing: {source_file}")

    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

    # ── Load sheet ─────────────────────────────────────────────────────────
    # Single sheet; header at row index 3 (rows 0-2 are banner/spacer)
    df = pd.read_excel(file_path, sheet_name=0, header=3, engine="openpyxl")
    df.columns = df.columns.str.strip()  # kills trailing space in "Tên hàng trên chứng từ "

    # Validate required headers
    missing = REQUIRED_HEADERS - set(df.columns)
    if missing:
        raise ValueError(f"MISA sheet missing required headers: {missing}. "
                         f"Got: {list(df.columns)}")

    # ── Capture totals footer before filtering ─────────────────────────────
    # The last row is "Tổng cộng" — capture COGS total as reconciliation checksum
    cogs_total_claimed = None
    totals_mask = df.iloc[:, 0].astype(str).str.strip().str.lower() == "tổng cộng"
    if totals_mask.any():
        totals_row = df[totals_mask]
        try:
            cogs_total_claimed = int(totals_row["Giá vốn"].iloc[0])
            print(f"  Captured Tổng cộng COGS checksum: {cogs_total_claimed:,} VND")
        except (ValueError, TypeError, IndexError):
            pass

    # ── Filter out totals footer and blank rows ────────────────────────────
    df = df[df["Số chứng từ"].notna()].reset_index(drop=True)

    # ── Rename VN → snake_case ─────────────────────────────────────────────
    rename_map = {k: v for k, v in SALES_LEDGER_RENAME.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    print(f"  Data rows: {len(df)}")

    # ── Synthesize line_no per voucher ─────────────────────────────────────
    df["line_no"] = df.groupby("voucher_no").cumcount() + 1

    # ── Type coercion ──────────────────────────────────────────────────────

    # Dates
    for date_col in ["posting_date", "voucher_date", "invoice_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    # invoice_no: float → zero-padded 8-char string
    if "invoice_no" in df.columns:
        df["invoice_no"] = df["invoice_no"].apply(
            lambda x: f"{int(x):08d}" if pd.notna(x) else None
        )

    # Accounting codes: float → str (preserves "131", "51111", etc.)
    for acct_col in ["debit_account", "credit_account", "discount_account", "cogs_account"]:
        if acct_col in df.columns:
            df[acct_col] = df[acct_col].apply(
                lambda x: str(int(x)) if pd.notna(x) else None
            )

    # is_promo_line: "✓" → True, NaN → False
    if "is_promo_line" in df.columns:
        df["is_promo_line"] = df["is_promo_line"].notna()

    # Money columns → Int64
    for money_col in ["revenue_gross", "discount_amount", "total_payment", "cogs_amount", "quantity"]:
        if money_col in df.columns:
            df[money_col] = pd.to_numeric(df[money_col], errors="coerce").astype("Int64")

    # unit_price → float64
    if "unit_price" in df.columns:
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    # ── Inject ingestion metadata ──────────────────────────────────────────
    df["ingest_method"] = "file_drop"
    df["source_file"] = source_file
    df["ingested_at"] = ingested_at

    # Partition keys from posting_date
    dates = pd.to_datetime(df["posting_date"], errors="coerce")
    df["year"] = dates.dt.year.fillna(1970).astype(int)
    df["month"] = dates.dt.month.fillna(1).astype(int)

    return df, cogs_total_claimed
