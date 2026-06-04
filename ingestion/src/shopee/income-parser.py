"""Shopee released-income Excel parser.

Parses 'Income.đã phát hành.vn.*.xlsx' files exported from Shopee Seller Center.
Outputs 4 DataFrames: order_revenue, order_revenue_items, order_service_fees, order_adjustments.

Canonical rename dict is the SINGLE SOURCE OF TRUTH for VN→snake_case mapping.
See docs/shopee-integration/data-source-description.md § 4.3 for full column dictionary.
"""

import os
import warnings
import pandas as pd
from datetime import datetime, timezone

# ── Canonical VN → snake_case rename dicts ──────────────────────────────────

# Sheet: Doanh thu (row 3 = actual headers, 53 columns)
DOANH_THU_RENAME = {
    "Mã giao dịch": "row_seq",
    "Đơn hàng / Sản phẩm": "row_grain",
    "Mã đơn hàng": "order_code",
    "Mã Số Thuế": "seller_tax_code",
    "Mã yêu cầu hoàn tiền": "refund_request_code",
    "Mã sản phẩm": "product_code",
    "Tên sản phẩm": "product_name",
    "Ngày đặt hàng": "order_placed_at",
    "Ngày hoàn thành thanh toán": "payout_released_at",
    "Phương thức thanh toán": "payment_method",
    "Loại đơn hàng": "order_type",
    "Sản Phẩm Bán Chạy": "is_bestseller_flag",
    "Tổng tiền đã thanh toán": "total_paid_amount",
    "Giá sản phẩm": "product_list_price",
    "Số tiền hoàn lại": "refund_amount",
    "Phí vận chuyển Người mua trả": "shipping_fee_paid_by_buyer",
    "Phí vận chuyển thực tế": "shipping_fee_actual",
    "Phí vận chuyển được trợ giá từ Shopee": "shipping_subsidy_from_shopee",
    "Phí vận chuyển trả hàng (đơn Trả hàng/hoàn tiền)": "shipping_fee_return_refund",
    "Phí vận chuyển được hoàn bởi PiShip": "shipping_refund_by_piship",
    "Phí vận chuyển trả hàng (đơn giao không thành công)": "shipping_fee_failed_delivery",
    "Sản phẩm được trợ giá từ Shopee": "product_subsidy_from_shopee",
    "Mã ưu đãi do Người Bán chịu": "seller_voucher_discount",
    "Mã ưu đãi Đồng Tài Trợ do Người Bán chịu": "seller_cofunded_voucher_discount",
    "Mã hoàn xu do Người Bán chịu": "seller_coin_cashback",
    "Mã hoàn xu Đồng Tài Trợ do Người Bán chịu": "seller_cofunded_coin_cashback",
    "Phí cố định": "fixed_fee",
    "Phí thanh toán": "payment_fee",
    "Phí xử lý giao dịch": "payment_fee",   # Shopee renamed this column in May 2026
    "Phí hoa hồng Tiếp thị liên kết": "affiliate_commission_fee",
    "Phí dịch vụ PiShip": "piship_service_fee",
    "Mức Nạp Tiền Tự Động (từ doanh thu đơn hàng)": "auto_topup_amount",
    "Thuế GTGT": "vat_tax",
    "Thuế TNCN": "personal_income_tax",
    "Phí lắp đặt người mua trả": "installation_fee_paid_by_buyer",
    "Phí lắp đặt thực tế": "installation_fee_actual",
    "Trade-in Bonus by Seller": "tradein_bonus_by_seller",
    "Người Mua": "buyer_username",
    "Amount Paid By Buyer": "amount_paid_by_buyer",
    "Transaction Fee Rate (%)": "transaction_fee_rate_pct",
    "Phương thức thanh toán của Người mua": "buyer_payment_method",
    "Buyer Payment Method Details_1": "buyer_payment_method_detail",
    "Installment Plan (if applicable)": "installment_plan",
    "Phí vận chuyển - Người bán hỗ trợ": "seller_shipping_support_fee",
    "Đơn vị vận chuyển": "carrier_name_local",
    "Courier Name": "courier_name_intl",
    "Mã voucher": "voucher_code",
    "Đền bù đơn mất hàng": "lost_order_compensation",
    "Giá sản phẩm (sau khuyến mãi)": "product_price_after_promo",
    "Shopee xu": "shopee_coin_used",
    "Shopee voucher": "shopee_voucher_used",
    "Ngân hàng khuyến mãi thanh toán trên Thẻ Tín Dụng": "bank_cc_promo",
    "Shopee khuyến mãi thanh toán trên Thẻ Tín Dụng": "shopee_cc_promo",
}

# Sheet: Service Fee Details (row 2 = headers, 4 columns)
SERVICE_FEE_RENAME = {
    "Mã giao dịch": "row_seq",
    "Mã đơn hàng": "order_code",
    "Phí Hạ Tầng": "infrastructure_fee",
    "Voucher Xtra": "voucher_xtra_fee",
}

# Sheet: Adjustment (section-based parsing, header row found dynamically)
ADJUSTMENT_RENAME = {
    "Mã giao dịch": "row_seq",
    "Ngày hoàn thành điều chỉnh đơn hàng": "adjustment_completed_at",
    "Loại điều chỉnh | Mô tả": "adjustment_type",
    "Lý do điều chỉnh": "adjustment_reason",
    "Số tiền điều chỉnh": "adjustment_amount",
    "Mã đơn hàng liên quan": "order_code",
    "Ngày hoàn thành thanh toán": "payout_released_at",
}

# Section marker to find the detail rows in Adjustment sheet
# (skip shop-level summary above this marker)
ADJUSTMENT_SECTION_MARKER = "Chi tiết danh sách giao dịch điều chỉnh"

# Required columns for Adjustment sheet validation
REQUIRED_ADJUSTMENT_HEADERS = {"Mã đơn hàng liên quan", "Số tiền điều chỉnh"}

# Columns that need string→int cleanup (may contain "-", "", or string numbers)
NUMERIC_CLEANUP_COLS = [
    "piship_service_fee", "amount_paid_by_buyer",
    "seller_shipping_support_fee", "lost_order_compensation",
    "product_price_after_promo", "shopee_coin_used",
    "shopee_voucher_used", "bank_cc_promo", "shopee_cc_promo",
]

# Required columns (fail loud if header drifts)
REQUIRED_DOANH_THU_HEADERS = {"Mã đơn hàng", "Đơn hàng / Sản phẩm", "Ngày hoàn thành thanh toán"}
REQUIRED_SFD_HEADERS = {"Mã đơn hàng", "Phí Hạ Tầng", "Voucher Xtra"}

# Fee/tax columns we DELIBERATELY do not map (so the drift guard doesn't cry wolf).
# "Phí Dịch Vụ" = D-sheet service-fee aggregate; dropped on purpose because it
# duplicates the F-sheet detail (infrastructure_fee + voucher_xtra_fee). See phase-07.
INTENTIONALLY_DROPPED_FEE_COLS = {"Phí Dịch Vụ"}


def _warn_schema_drift(df, rename_dict, sheet_name):
    """Surface unmapped fee/tax columns so Shopee header drift never silently drops a fee again."""
    unmapped = [c for c in df.columns if c not in rename_dict and c not in INTENTIONALLY_DROPPED_FEE_COLS]
    suspicious = [c for c in unmapped if ("Phí" in str(c)) or ("Thuế" in str(c))]
    if suspicious:
        msg = (
            f"[!] SCHEMA_DRIFT in '{sheet_name}': unmapped fee/tax column(s) {suspicious}"
            " — add to rename dict or a fee will be silently dropped!"
        )
        print(msg)
        warnings.warn(msg)


def to_int_vnd(series):
    """Clean string→Int64 for VND amount columns. Handles "-", "", numeric strings."""
    return (
        series.astype(str)
        .str.replace(r"[^\d\-]", "", regex=True)
        .replace({"": "0", "-": "0"})
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype("Int64")
    )


def parse_shopee_income(file_path):
    """Parse one Shopee income Excel file.

    Returns:
        (df_order_revenue, df_order_revenue_items, df_order_service_fees, df_order_adjustments)
        Each DataFrame has ingestion metadata columns: source_file, ingested_at, year, month.
        df_order_adjustments may be empty if no adjustment detail rows exist.
    """
    file_path = str(file_path)
    source_file = os.path.basename(file_path)
    ingested_at = datetime.now(timezone.utc)
    print(f"Parsing: {source_file}")

    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

    # ── Parse Doanh thu sheet ──────────────────────────────────────────────
    df_dt = pd.read_excel(file_path, sheet_name="Doanh thu", header=2, engine="openpyxl")
    df_dt.columns = df_dt.columns.str.strip()

    # Validate required headers
    missing = REQUIRED_DOANH_THU_HEADERS - set(df_dt.columns)
    if missing:
        raise ValueError(f"Doanh thu sheet missing required headers: {missing}")

    # Drift guard: warn on any unmapped fee/tax column BEFORE rename
    _warn_schema_drift(df_dt, DOANH_THU_RENAME, "Doanh thu")

    # Rename VN → snake_case (only rename columns that exist in the rename dict)
    rename_map = {k: v for k, v in DOANH_THU_RENAME.items() if k in df_dt.columns}
    df_dt = df_dt.rename(columns=rename_map)

    # Belt-and-suspenders: drop raw "Phí Dịch Vụ" if it survived the rename
    # (should never happen, but guards against future dict re-addition)
    if "Phí Dịch Vụ" in df_dt.columns:
        df_dt = df_dt.drop(columns=["Phí Dịch Vụ"])

    # Drop trailing all-NaN columns
    df_dt = df_dt.dropna(axis=1, how="all")

    # Filter out any blank/separator rows
    df_dt = df_dt[df_dt["order_code"].notna()].reset_index(drop=True)

    # Numeric cleanup for string→int columns
    for col in NUMERIC_CLEANUP_COLS:
        if col in df_dt.columns:
            df_dt[col] = to_int_vnd(df_dt[col])

    # Date parsing
    for date_col in ["order_placed_at", "payout_released_at"]:
        if date_col in df_dt.columns:
            df_dt[date_col] = pd.to_datetime(df_dt[date_col], errors="coerce").dt.date

    # transaction_fee_rate_pct → float
    if "transaction_fee_rate_pct" in df_dt.columns:
        df_dt["transaction_fee_rate_pct"] = pd.to_numeric(
            df_dt["transaction_fee_rate_pct"].astype(str).str.replace(r"[^\d.\-]", "", regex=True).replace({"": "0", "-": "0"}),
            errors="coerce",
        )

    # Drop row_seq (file row counter, not a business key)
    if "row_seq" in df_dt.columns:
        df_dt = df_dt.drop(columns=["row_seq"])

    # ── Split on row_grain: Order vs Sku ───────────────────────────────────
    df_order = df_dt[df_dt["row_grain"] == "Order"].copy()
    df_sku = df_dt[df_dt["row_grain"] == "Sku"].copy()

    # Drop row_grain after split (no longer needed)
    df_order = df_order.drop(columns=["row_grain"])
    df_sku = df_sku.drop(columns=["row_grain"])

    print(f"  Doanh thu: {len(df_order)} Order rows, {len(df_sku)} Sku rows")

    # ── Parse Service Fee Details sheet ────────────────────────────────────
    df_sfd = pd.read_excel(file_path, sheet_name="Service Fee Details", header=1, engine="openpyxl")
    df_sfd.columns = df_sfd.columns.str.strip()

    missing_sfd = REQUIRED_SFD_HEADERS - set(df_sfd.columns)
    if missing_sfd:
        raise ValueError(f"Service Fee Details sheet missing required headers: {missing_sfd}")

    # Drift guard: warn on any unmapped fee/tax column BEFORE rename
    _warn_schema_drift(df_sfd, SERVICE_FEE_RENAME, "Service Fee Details")

    rename_sfd = {k: v for k, v in SERVICE_FEE_RENAME.items() if k in df_sfd.columns}
    df_sfd = df_sfd.rename(columns=rename_sfd)

    # Filter blanks
    df_sfd = df_sfd[df_sfd["order_code"].notna()].reset_index(drop=True)

    # Numeric cleanup
    for col in ["infrastructure_fee", "voucher_xtra_fee"]:
        if col in df_sfd.columns:
            df_sfd[col] = to_int_vnd(df_sfd[col])

    # Drop row_seq
    if "row_seq" in df_sfd.columns:
        df_sfd = df_sfd.drop(columns=["row_seq"])

    print(f"  Service Fee Details: {len(df_sfd)} rows")

    # ── Parse Adjustment sheet (section-based) ───────────────────────────
    df_adj = _parse_adjustment_sheet(file_path)
    print(f"  Adjustment: {len(df_adj)} rows")

    # ── Inject ingestion metadata ──────────────────────────────────────────
    for df in [df_order, df_sku, df_sfd, df_adj]:
        df["ingest_method"] = "file_drop"
        df["source_file"] = source_file
        df["ingested_at"] = ingested_at

    # Partition keys from payout_released_at (order/sfd) or order's payout (sku via merge)
    _add_partition_keys(df_order, "payout_released_at")
    _add_partition_keys(df_sfd, "payout_released_at", fallback_df=df_order)
    _add_partition_keys(df_sku, "payout_released_at", fallback_df=df_order)
    _add_partition_keys(df_adj, "payout_released_at")

    return df_order, df_sku, df_sfd, df_adj


def _parse_adjustment_sheet(file_path):
    """Parse the Adjustment sheet using section-based detection.

    Scans column A for the section marker text to find where detail rows begin.
    Skips the shop-level summary section above the marker.
    Returns an empty DataFrame if no detail rows or sheet doesn't exist.
    """
    try:
        # Load entire sheet without header to scan for section marker
        df_raw = pd.read_excel(file_path, sheet_name="Adjustment", header=None, engine="openpyxl")
    except ValueError:
        # Sheet doesn't exist in this file
        return pd.DataFrame()

    # Find the section marker row: "Chi tiết danh sách giao dịch điều chỉnh"
    marker_row = None
    for idx, val in df_raw.iloc[:, 0].items():
        if isinstance(val, str) and ADJUSTMENT_SECTION_MARKER in val:
            marker_row = idx
            break

    if marker_row is None:
        return pd.DataFrame()

    # Header row = marker + 1, data starts at marker + 2
    header_row = marker_row + 1
    if header_row >= len(df_raw):
        return pd.DataFrame()

    # Re-read with correct header position
    df_adj = pd.read_excel(
        file_path, sheet_name="Adjustment",
        header=header_row, engine="openpyxl",
    )
    df_adj.columns = df_adj.columns.str.strip()

    # Validate required headers
    missing = REQUIRED_ADJUSTMENT_HEADERS - set(df_adj.columns)
    if missing:
        raise ValueError(f"Adjustment sheet missing required headers: {missing}")

    # Rename VN → snake_case
    rename_map = {k: v for k, v in ADJUSTMENT_RENAME.items() if k in df_adj.columns}
    df_adj = df_adj.rename(columns=rename_map)

    # Filter: keep only rows with order_code (drops blank rows + "Tổng cộng" summary)
    df_adj = df_adj[df_adj["order_code"].notna()].reset_index(drop=True)

    if df_adj.empty:
        return df_adj

    # Numeric cleanup — adjustment_amount may already be numeric from Excel,
    # so cast directly instead of to_int_vnd() which corrupts floats (strips '.')
    if "adjustment_amount" in df_adj.columns:
        df_adj["adjustment_amount"] = (
            pd.to_numeric(df_adj["adjustment_amount"], errors="coerce")
            .fillna(0)
            .round()
            .astype("Int64")
        )

    # Force adjustment_reason to string (avoids float64↔string type mismatch
    # across parquets when all values are null in some files but text in others)
    if "adjustment_reason" in df_adj.columns:
        df_adj["adjustment_reason"] = df_adj["adjustment_reason"].astype("string")

    # Date parsing
    for date_col in ["adjustment_completed_at", "payout_released_at"]:
        if date_col in df_adj.columns:
            df_adj[date_col] = pd.to_datetime(df_adj[date_col], errors="coerce").dt.date

    # Drop row_seq (file row counter)
    if "row_seq" in df_adj.columns:
        df_adj = df_adj.drop(columns=["row_seq"])

    return df_adj


def _add_partition_keys(df, date_col, fallback_df=None):
    """Add year/month partition keys from a date column.

    For DataFrames without their own date column (like sku or sfd),
    derive from fallback_df's date column via order_code join.
    """
    if date_col in df.columns and df[date_col].notna().any():
        dates = pd.to_datetime(df[date_col], errors="coerce")
    elif fallback_df is not None and date_col in fallback_df.columns:
        # Join to get date from parent (order) via order_code
        date_map = fallback_df.set_index("order_code")[date_col].to_dict()
        dates = pd.to_datetime(df["order_code"].map(date_map), errors="coerce")
    else:
        # Fallback to ingested_at month
        dates = pd.to_datetime(df["ingested_at"])

    df["year"] = dates.dt.year.fillna(1970).astype(int)
    df["month"] = dates.dt.month.fillna(1).astype(int)
