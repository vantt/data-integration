"""Shopee released-income Excel parser.

Parses 'Income.đã phát hành.vn.*.xlsx' files exported from Shopee Seller Center.
Outputs 3 DataFrames: order_revenue, order_revenue_items, order_service_fees.

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
    "Phí Dịch Vụ": "service_fee",
    "Phí thanh toán": "payment_fee",
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
        (df_order_revenue, df_order_revenue_items, df_order_service_fees)
        Each DataFrame has ingestion metadata columns: source_file, ingested_at, year, month.
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

    # Rename VN → snake_case (only rename columns that exist in the rename dict)
    rename_map = {k: v for k, v in DOANH_THU_RENAME.items() if k in df_dt.columns}
    df_dt = df_dt.rename(columns=rename_map)

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

    # ── Inject ingestion metadata ──────────────────────────────────────────
    for df in [df_order, df_sku, df_sfd]:
        df["ingest_method"] = "file_drop"
        df["source_file"] = source_file
        df["ingested_at"] = ingested_at

    # Partition keys from payout_released_at (order/sfd) or order's payout (sku via merge)
    _add_partition_keys(df_order, "payout_released_at")
    _add_partition_keys(df_sfd, "payout_released_at", fallback_df=df_order)
    _add_partition_keys(df_sku, "payout_released_at", fallback_df=df_order)

    return df_order, df_sku, df_sfd


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
