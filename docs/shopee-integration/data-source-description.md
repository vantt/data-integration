# Shopee Income Report — Data Source Description

**Source file:** `app_data/input_source/shopee/Income.đã phát hành.vn.{YYYYMMDD}_{YYYYMMDD}.xlsx`
**Origin:** Shopee Seller Center → Finance → Income → **Released (Đã phát hành)** export
**Format:** Excel (.xlsx), multi-sheet, Vietnamese headers, multi-row header blocks
**Cadence:** manual/periodic drop, covers a closed date range encoded in filename (`YYYYMMDD_YYYYMMDD`)
**Grain of the drop:** one file per export = one date window of **released payouts** (orders whose earnings have been credited to the seller wallet)

---

## 1. File naming convention

```
Income . đã phát hành . vn . 20260201_20260409 . xlsx
  │          │           │          │              │
  │          │           │          │              └── extension
  │          │           │          └── date range: start_end (inclusive)
  │          │           └── region (vn = Vietnam)
  │          └── payout status ("released" = wallet-credited)
  └── report type (Income / Doanh thu đã phát hành)
```

**Proposed internal source key:** `shopee_income_released` (category in data_lake partitioning)

---

## 2. Sheet inventory

| Sheet (original) | Rows × Cols | Grain | Proposed logical name | Priority |
|---|---|---|---|---|
| `Summary` | 101×4 | pivot/report | `shopee_income_summary` | later |
| `Service Fee Details` | 88×4 | 1 row / order | **`shopee_order_service_fees`** | **P0** |
| `Adjustment` | 17×7 | 1 row / adjustment | `shopee_income_adjustments` | later |
| `Doanh thu` | 183×53 | 2 rows / order (Order + Sku) | **`shopee_order_revenue`** | **P0** |

Focus of this document: the two P0 sheets.

---

## 3. Sheet: `Service Fee Details` → `shopee_order_service_fees`

### 3.1 Physical layout

| Row | Role |
|---|---|
| 1 | merged section title: `Phí Dịch Vụ` (Service Fee) — ignore |
| 2 | column headers |
| 3..N | data (N=88, so **86 order rows**) |

### 3.2 Columns (physical → logical)

| # | Header (VN) | Logical name (proposed) | Type | Notes |
|---|---|---|---|---|
| 1 | Mã giao dịch | `row_seq` | INT | 1..N file row index, **NOT a business key**, drop after load |
| 2 | Mã đơn hàng | `order_code` | VARCHAR | Shopee Order SN, **natural key** |
| 3 | Phí Hạ Tầng | `infrastructure_fee` | INT (VND) | Fixed fee, always negative (e.g. `-3000`) |
| 4 | Voucher Xtra | `voucher_xtra_fee` | INT (VND) | Shopee Xtra voucher cost borne by seller, always negative |

### 3.3 Quality observations

- All 86 rows have non-null `order_code`.
- `infrastructure_fee` constant at `-3000` in sample → low cardinality, still store as number.
- `voucher_xtra_fee` varies, always ≤ 0.
- No date column — this sheet is **not self-contained in time**; must enrich from `Doanh thu` via `order_code`.

### 3.4 Why this sheet exists separately

Shopee breaks fees across several UI sections. `Service Fee Details` captures fee types that do **not** appear in the main `Doanh thu` fee columns (specifically `Phí Hạ Tầng` and `Voucher Xtra`). These must be summed with `Doanh thu` fees for a complete per-order cost picture.

---

## 4. Sheet: `Doanh thu` → `shopee_order_revenue`

### 4.1 Physical layout (⚠ multi-row header)

| Row | Role |
|---|---|
| 1 | top section banners (merged): `Thông tin đơn hàng`, `Chi tiết doanh thu`, `Thông tin người mua`, `Thông tin tham chiếu` |
| 2 | mid section banners: `Doanh thu đơn hàng`, `Giảm giá và trợ giá`, `Phí giao dịch`, `Thuế`, `Vận chuyển`, `Khuyến mãi`, ... |
| 3 | **actual column headers** (53 columns) |
| 4..183 | data (180 rows) |

**Parser rule:** skip rows 1–2, use row 3 as header, load from row 4. Rows 1–2 are for human visual grouping only and **must not be fed to dlt/pandas as headers**.

### 4.2 Dual-grain via `Đơn hàng / Sản phẩm`

Each order appears twice:

| Value | Grain | What it carries |
|---|---|---|
| `Order` | 1 row / order | All revenue + fee breakdown (totals for the order) |
| `Sku` | 1..N rows / order | Product identity (`Mã sản phẩm`, `Tên sản phẩm`), money columns often `"-"` or duplicated |

In the audited sample: 90 unique orders × 2 → **180 rows = 90 Order + 90 Sku**. Sku count can exceed Order count when an order has multiple line items; parser must **not** assume 1:1.

**Split strategy on ingest:**

- **Order rows** → `shopee_order_revenue` (fact-shaped, one row per order)
- **Sku rows** → `shopee_order_revenue_items` (line-item shape, one row per order × product)

### 4.3 Column dictionary (row 3 headers, 53 cols)

Semantic groups + proposed logical names (snake_case, English-first for pipeline alignment):

#### Group A — Order identifiers

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 1 | Mã giao dịch | `row_seq` | INT | Row index, drop |
| 2 | Đơn hàng / Sản phẩm | `row_grain` | ENUM('Order','Sku') | **Splitter** |
| 3 | Mã đơn hàng | `order_code` | VARCHAR | **Natural key** |
| 4 | Mã Số Thuế | `seller_tax_code` | VARCHAR | Constant per seller |
| 5 | Mã yêu cầu hoàn tiền | `refund_request_code` | VARCHAR | `"-"` when none |
| 6 | Mã sản phẩm | `product_code` | VARCHAR | Sku rows only |
| 7 | Tên sản phẩm | `product_name` | VARCHAR | Sku rows only |

#### Group B — Temporal

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 8 | Ngày đặt hàng | `order_placed_at` | DATE | `YYYY-MM-DD` string, parse |
| 9 | Ngày hoàn thành thanh toán | `payout_released_at` | DATE | Date the payout was released — **this file's temporal grain** |

#### Group C — Order meta

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 10 | Phương thức thanh toán | `payment_method` | VARCHAR |
| 11 | Loại đơn hàng | `order_type` | VARCHAR (`Đơn thường`, ...) |
| 12 | Sản Phẩm Bán Chạy | `is_bestseller_flag` | VARCHAR(YES/NO) |

#### Group D — Revenue (Doanh thu đơn hàng)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 13 | Tổng tiền đã thanh toán | `total_paid_amount` | INT (VND) |
| 14 | Giá sản phẩm | `product_list_price` | INT (VND) |
| 15 | Số tiền hoàn lại | `refund_amount` | INT (VND) |

#### Group E — Shipping (Phí vận chuyển)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 16 | Phí vận chuyển Người mua trả | `shipping_fee_paid_by_buyer` | INT |
| 17 | Phí vận chuyển thực tế | `shipping_fee_actual` | INT (negative) |
| 18 | Phí vận chuyển được trợ giá từ Shopee | `shipping_subsidy_from_shopee` | INT |
| 19 | Phí vận chuyển trả hàng (đơn Trả hàng/hoàn tiền) | `shipping_fee_return_refund` | INT |
| 20 | Phí vận chuyển được hoàn bởi PiShip | `shipping_refund_by_piship` | INT |
| 21 | Phí vận chuyển trả hàng (đơn giao không thành công) | `shipping_fee_failed_delivery` | INT |

#### Group F — Discounts & subsidies (Giảm giá và trợ giá)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 22 | Sản phẩm được trợ giá từ Shopee | `product_subsidy_from_shopee` | INT |
| 23 | Mã ưu đãi do Người Bán chịu | `seller_voucher_discount` | INT (negative) |
| 24 | Mã ưu đãi Đồng Tài Trợ do Người Bán chịu | `seller_cofunded_voucher_discount` | INT |
| 25 | Mã hoàn xu do Người Bán chịu | `seller_coin_cashback` | INT |
| 26 | Mã hoàn xu Đồng Tài Trợ do Người Bán chịu | `seller_cofunded_coin_cashback` | INT |

#### Group G — Transaction & service fees (Phí giao dịch)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 27 | Phí cố định | `fixed_fee` | INT (negative) |
| 28 | Phí Dịch Vụ | `service_fee` | INT (negative) |
| 29 | Phí thanh toán | `payment_fee` | INT (negative) |
| 30 | Phí hoa hồng Tiếp thị liên kết | `affiliate_commission_fee` | INT |
| 31 | Phí dịch vụ PiShip | `piship_service_fee` | STR→INT | ⚠ stored as string (`"-1620"`, `"-"`) |
| 32 | Mức Nạp Tiền Tự Động (từ doanh thu đơn hàng) | `auto_topup_amount` | INT |

#### Group H — Taxes (Thuế)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 33 | Thuế GTGT | `vat_tax` | INT |
| 34 | Thuế TNCN | `personal_income_tax` | INT |

#### Group I — Value-added service subtotal (Tổng phụ dịch vụ giá trị gia tăng cho người mua)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 35 | Phí lắp đặt người mua trả | `installation_fee_paid_by_buyer` | INT |
| 36 | Phí lắp đặt thực tế | `installation_fee_actual` | INT |
| 37 | Trade-in Bonus by Seller | `tradein_bonus_by_seller` | INT |

#### Group J — Buyer info (Thông tin người mua)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 38 | Người Mua | `buyer_username` | VARCHAR |
| 39 | Amount Paid By Buyer | `amount_paid_by_buyer` | STR→INT |
| 40 | Transaction Fee Rate (%) | `transaction_fee_rate_pct` | STR→DECIMAL |
| 41 | Phương thức thanh toán của Người mua | `buyer_payment_method` | VARCHAR |
| 42 | Buyer Payment Method Details_1 | `buyer_payment_method_detail` | VARCHAR |
| 43 | Installment Plan (if applicable) | `installment_plan` | VARCHAR (`"2x"`, `""`) |

#### Group K — Shipping ref (Vận chuyển)

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 44 | Phí vận chuyển - Người bán hỗ trợ | `seller_shipping_support_fee` | STR→INT |
| 45 | Đơn vị vận chuyển | `carrier_name_local` | VARCHAR |
| 46 | Courier Name | `courier_name_intl` | VARCHAR |

#### Group L — Promotions, refunds, compensation

| # | Header (VN) | Logical name | Type |
|---|---|---|---|
| 47 | Mã voucher | `voucher_code` | VARCHAR |
| 48 | Đền bù đơn mất hàng | `lost_order_compensation` | STR→INT |
| 49 | Giá sản phẩm (sau khuyến mãi) | `product_price_after_promo` | STR→INT |
| 50 | Shopee xu | `shopee_coin_used` | STR→INT |
| 51 | Shopee voucher | `shopee_voucher_used` | STR→INT |
| 52 | Ngân hàng khuyến mãi thanh toán trên Thẻ Tín Dụng | `bank_cc_promo` | STR→INT |
| 53 | Shopee khuyến mãi thanh toán trên Thẻ Tín Dụng | `shopee_cc_promo` | STR→INT |

### 4.4 Quality & parsing hazards

| Hazard | Detail | Mitigation |
|---|---|---|
| Multi-row header | Rows 1–2 are banner-only, row 3 = real headers | Skip `[0,1]`, `header=2` in pandas |
| Mixed types in numeric cols | Cols 31, 39–53 stored as strings, with `"-"`, `""`, `"0"`, `"-1620"` | Clean: `replace("-","").replace("","0")` → `pd.to_numeric(errors="coerce").fillna(0)` |
| Dual grain | Order vs Sku rows share columns | Split on `row_grain` at ingest |
| No explicit currency | All amounts are **VND integers** | Enforce `DECIMAL(18,0)` or `BIGINT`, document assumption |
| Signed fees | Fee columns are negative, revenue positive | Preserve signs — downstream `SUM()` gives net directly |
| Date as text | `YYYY-MM-DD` string | `CAST AS DATE` in stg_ |
| Filename drives window | No in-sheet start/end dates | Capture `window_start`, `window_end` from filename as ingestion metadata |
| Partial coverage of SFD | 4 orders in Doanh thu are absent from Service Fee Details (86 vs 90) | Use **LEFT JOIN** from revenue → service_fees, default fee to 0 |

---

## 5. Relationships & keys

```
┌──────────────────────────────────┐       ┌───────────────────────────────┐
│ shopee_order_revenue             │       │ shopee_order_service_fees     │
│ grain: 1 row / order             │◄─────►│ grain: 1 row / order          │
│ PK: order_code                   │ 1:0/1 │ PK: order_code                │
│                                  │       │                               │
│ payout_released_at (DATE)        │       │ infrastructure_fee            │
│ order_placed_at (DATE)           │       │ voucher_xtra_fee              │
│ total_paid_amount, fees..., tax  │       │                               │
└───────────┬──────────────────────┘       └───────────────────────────────┘
            │ 1:N
            ▼
┌──────────────────────────────────┐
│ shopee_order_revenue_items       │
│ grain: 1 row / order × product   │
│ PK: (order_code, product_code)   │
│                                  │
│ product_name, (money cols mostly │
│ NULL — derive from parent row)   │
└──────────────────────────────────┘
```

**Join rules:**
- `shopee_order_revenue` **LEFT JOIN** `shopee_order_service_fees` ON `order_code` → complete order-level P&L
- `shopee_order_revenue_items` **INNER JOIN** `shopee_order_revenue` ON `order_code` → line-item view inheriting order totals
- Downstream (future): `shopee_order_revenue.order_code` ↔ Sapo `fact_orders.order_code` for reconciliation (Shopee side of omnichannel fact)

**Column marked as key but NOT a key:**
- `Mã giao dịch` (row_seq) in both sheets — it's a 1..N spreadsheet row counter, not a Shopee transaction ID. **Drop during ingest.**

---

## 6. Proposed rename summary (quick reference)

| Original | Proposed logical key |
|---|---|
| `Service Fee Details` (sheet) | `shopee_order_service_fees` |
| `Doanh thu` (sheet, Order rows) | `shopee_order_revenue` |
| `Doanh thu` (sheet, Sku rows) | `shopee_order_revenue_items` |
| `Mã đơn hàng` | `order_code` (natural key across both sheets) |
| `Mã giao dịch` | `row_seq` → **drop** |
| `Ngày hoàn thành thanh toán` | `payout_released_at` (grain-defining date) |
| `Phí Hạ Tầng` | `infrastructure_fee` |
| `Voucher Xtra` | `voucher_xtra_fee` |
| `Phí Dịch Vụ` | `service_fee` (Doanh thu) — distinct from SFD fees! |

> **Naming warning:** the sheet called "Service Fee Details" does **not** contain the column called "Phí Dịch Vụ". The column "Phí Dịch Vụ" lives in `Doanh thu`. The sheet's name refers to *additional* service-related fees (infrastructure, Xtra voucher) that sit **outside** the main fee section. Document this explicitly to prevent analyst confusion.

---

## 7. Open questions

1. **Full fee coverage:** Does `Doanh thu.Phí Dịch Vụ` + `Service Fee Details.Phí Hạ Tầng` + `Service Fee Details.Voucher Xtra` exhaust all Shopee-charged fees, or are there more hidden in `Adjustment` / `Summary`? Need confirmation before publishing net margin metrics.
2. **Multi-SKU orders:** sample has 1 SKU per order; real data may have N>1. Confirm by loading a multi-month file and asserting `COUNT(Sku rows) >= COUNT(Order rows)` never breaks.
3. **Shop identity:** file carries `seller_tax_code = 0317341714` but no `shop_id` / `shop_name`. If we onboard multiple Shopee shops, add `shop_code` partition from folder path (e.g. `input_source/shopee/{shop_code}/*.xlsx`).
4. **File overlap between drops:** if two drops cover overlapping date ranges, which wins? Recommended dedup key: `(order_code, payout_released_at)` with `ingested_at` tiebreaker.
5. **`Adjustment` sheet semantics:** does it add/subtract from `order_code`-level totals, or is it standalone (e.g. chargebacks, manual compensations)? Defer until P1.
6. **`Summary` sheet:** pivot/report for humans or a useful reconciliation anchor? Treat as out-of-scope for pipeline; use only for ingest-time checksum.
