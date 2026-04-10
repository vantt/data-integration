# MISA AMIS Sales Detail Book — Data Source Description

**Source file:** `app_data/input_source/misa-amis/So_chi_tiet_ban_hang_{DD.MM.YYYY}-{DD.MM.YYYY}.xlsx`
**Origin:** MISA AMIS Kế toán → Bán hàng → **Sổ chi tiết bán hàng** export (accounting ledger report)
**Format:** Excel (.xlsx), **single sheet**, Vietnamese headers, 3-row report banner + 1 totals footer
**Cadence:** manual/periodic drop; filename encodes the reporting window (`DD.MM.YYYY-DD.MM.YYYY`)
**Grain of the file:** 1 row = 1 invoice line-item = `(voucher × product × promo-flag)` — **a sales line with both revenue and COGS already reconciled by MISA**

> **Why this source exists:** MISA is the company's book-of-record accounting system. This export is the **only reliable feed of landed cost-of-goods-sold (giá vốn)** per sales line. Sapo has order/line data but no COGS; Shopee has payout fees but no unit cost. MISA closes the margin loop.

---

## 1. File naming convention

```
So_chi_tiet_ban_hang . 01.01.2026 - 08.04.2026 . xlsx
         │                 │             │          │
         │                 │             │          └── extension
         │                 │             └── end date (inclusive)
         │                 └── start date (inclusive)
         └── report type: "Sổ chi tiết bán hàng" (Sales Detail Ledger)
```

- Filename dates use `DD.MM.YYYY` (European-style), **not** `YYYYMMDD` like Shopee.
- Printed banner in row 1–2 ("Từ ngày dd/mm/yyyy đến ngày dd/mm/yyyy") repeats the same range.
- **Do NOT parse the filename for business logic** — use row-level `posting_date` as the real temporal grain (same principle as Shopee: filename is lineage metadata only, drop window may overlap across drops).

**Proposed internal source key:** `misa_raw` (dataset/schema prefix)
**Proposed entity name:** `sales_lines` → table `misa_sales_lines`

---

## 2. Sheet inventory

| Sheet (original) | Rows × Cols | Grain | Proposed logical name | Priority |
|---|---|---|---|---|
| `SỔ CHI TIẾT BÁN HÀNG` | 476×25 | 1 row / invoice-line | **`misa_sales_lines`** | **P0** |

Only one sheet. Simpler than Shopee (no multi-grain split).

---

## 3. Physical layout (`SỔ CHI TIẾT BÁN HÀNG`)

| Row (0-indexed) | Role |
|---|---|
| 0 | report title banner: `SỔ CHI TIẾT BÁN HÀNG` (merged) — ignore |
| 1 | date-range banner: `Từ ngày 01/01/2026 đến ngày 09/04/2026` — ignore |
| 2 | blank spacer — ignore |
| **3** | **actual column headers (25 cols)** |
| 4 .. N-2 | data rows (472 rows in sample) |
| N-1 (row 475) | `Tổng cộng` totals footer — **MUST FILTER OUT** (all other cells `NaN`) |

**Parser rule:**
```python
df = pd.read_excel(path, sheet_name=0, header=3)
df = df[df["Số chứng từ"].notna()]  # drops the "Tổng cộng" footer
```

---

## 4. Column dictionary (25 columns)

Physical header (VN) → proposed logical name (snake_case, English-first for pipeline consistency).

### Group A — Temporal

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 1 | Ngày hạch toán | `posting_date` | DATE | Accounting posting date — **grain-defining date** |
| 2 | Ngày chứng từ | `voucher_date` | DATE | Voucher creation date (usually = posting_date) |
| 4 | Ngày hóa đơn | `invoice_date` | DATE | E-invoice issue date (usually = posting_date) |

In the audited sample all three dates are identical per row. Keep all three; downstream can drop two.

### Group B — Document identifiers

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 3 | Số chứng từ | `voucher_no` | VARCHAR | MISA voucher ID, **business key** (not unique alone) |
| 5 | Số hóa đơn | `invoice_no` | INT→VARCHAR | Serial # within the e-invoice series (loaded as float; cast to zero-padded string) |
| 6 | Diễn giải chung | `description` | VARCHAR | Free-text: `"{party} - {voucher_no} - {channel_hint}"` |

**Voucher number patterns observed (4 families):**

| Pattern | Example | Likely source |
|---|---|---|
| `SON07xxx` | `SON07125` | Sapo dealer sales order |
| `2YYMMDD{14 alphanum}` | `260101V2FWBW1J`, `260404U6X5W4WU` | **Shopee Order SN** — join with `fact_shopee_orders.order_code` |
| `58{11 digits}` | `58711000042994`, `58741000033346` | AEON retail receipt |
| `{14 digits}` | `58061000012297` | BigC/Co.op? (occasional) |

**Critical:** `voucher_no` is the bridge between MISA (COGS) and Sapo/Shopee (revenue/orders). P0 pipeline must preserve it verbatim for downstream joins.

### Group C — Product on document

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 7 | `Tên hàng trên chứng từ ` (trailing space) | `product_name_on_document` | VARCHAR | Name printed on the invoice — may differ from master |
| 10 | Mã hàng | `product_code` | VARCHAR | **Product natural key** — joins to product master |
| 11 | Tên hàng | `product_name` | VARCHAR | Name from MISA product master |
| 12 | Hàng khuyến mại | `is_promo_line` | BOOL | `"✓"` → `true`, blank → `false` |
| 13 | ĐVT | `unit_of_measure` | VARCHAR | `Hộp / Gói / Lọ / Chai / Bịch / Giờ / Tháng` |

**`is_promo_line` semantics (CRITICAL for margin):**
- 92 / 472 rows flagged
- `revenue = 0`, `discount = 0`, `cogs > 0` → products given away as promotions, booked to COGS expense account `64214` instead of `6321`
- Downstream margin calc **must include these rows** in cost side; else margin is overstated.

### Group D — Customer / counterparty

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 8 | Mã khách hàng | `customer_code` | VARCHAR | Tax code (e.g. `0317661471`) or fallback `0000000001` for "Người mua không lấy hóa đơn" |
| 9 | Tên khách hàng | `customer_name` | VARCHAR | Legal entity name |

### Group E — Quantity & pricing

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 14 | Tổng số lượng bán | `quantity` | BIGINT | Always integer in sample |
| 15 | Đơn giá | `unit_price` | DECIMAL(18,4) | VND; exact fractions present (e.g. `3055555.56`) |
| 16 | Doanh số bán | `revenue_gross` | BIGINT | VND, pre-discount line revenue |
| 20 | Chiết khấu | `discount_amount` | BIGINT | VND, always ≥ 0 |
| 21 | Tổng thanh toán | `total_payment` | BIGINT | VND, computed by MISA (≈ revenue − discount + VAT? — see § 7 Q1) |
| 23 | Giá vốn | `cogs_amount` | BIGINT | VND, **the key column** — landed unit cost × qty |

### Group F — Accounting accounts (Vietnamese chart of accounts — TT200)

| # | Header (VN) | Logical name | Type | Meaning |
|---|---|---|---|---|
| 17 | TK Nợ | `debit_account` | VARCHAR | `131` = A/R, `1111` = cash |
| 18 | TK Có | `credit_account` | VARCHAR | `51111`/`5113`/`51113` = revenue sub-accounts |
| 19 | TK chiết khấu | `discount_account` | VARCHAR | Same as credit (contra-revenue) |
| 22 | TK giá vốn | `cogs_account` | VARCHAR | `6321` = regular COGS, `6323` = service COGS, `64214` = **promo-expense** (promo lines) |

Store as VARCHAR (not numeric) to preserve leading-zero safety and because the account chart is a categorical dimension. Consider exposing as `ref_misa_coa` seed later.

### Group G — Sales agent & channel

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 24 | Tên nhân viên bán hàng | `salesperson_name` | VARCHAR | 2 nulls in sample |
| 25 | Mã thống kê | `channel_code` | VARCHAR | **`DAILY` / `ECOM` / `CS` / `KHAC`** (8 nulls) |

**`channel_code` values observed:**
- `DAILY` (186) — direct / dealer (đại lý, SON07xxx vouchers)
- `ECOM` (212) — e-commerce / marketplace (Shopee, etc.)
- `CS` (60) — customer service / B2B (?)
- `KHAC` (6) — other
- `NULL` (8) — unclassified (flag during ingest)

This is the **cleanest channel signal** in the dataset — use it as the primary dimension for channel-level P&L.

---

## 5. Natural key analysis

**Duplicate key test on 472 rows:**

| Candidate key | Unique rows | Collisions | Verdict |
|---|---|---|---|
| `(voucher_no)` | 345 | 127 | ❌ many lines per voucher |
| `(voucher_no, product_code)` | 438 | 34 | ❌ still collides — same product can appear twice on a voucher (one regular + one promo) |
| `(voucher_no, product_code, is_promo_line)` | ~472 (expected) | ~0 | ✅ likely full — needs confirmation |
| `(voucher_no, product_code, is_promo_line, unit_price)` | 472 | 0 | ✅ safest |

**Decision:** synthesize a monotonically-increasing `line_no` **per voucher** during ingestion, in original Excel row order:
```python
df["line_no"] = df.groupby("voucher_no").cumcount() + 1
```
Then **business key = `(voucher_no, line_no)`** — always unique, stable across re-exports as long as MISA preserves line order (it does; this is a ledger).

Dedup on re-ingest: `ROW_NUMBER() OVER (PARTITION BY voucher_no, line_no ORDER BY ingested_at DESC) = 1`.

---

## 6. Data quality & parsing hazards

| Hazard | Detail | Mitigation |
|---|---|---|
| Totals footer row | Last row is `"Tổng cộng"` with all other cells NaN | Filter `df[df.voucher_no.notna()]` post-load |
| Trailing space in header | `"Tên hàng trên chứng từ "` (col 7) | Strip whitespace on all column names: `df.columns = df.columns.str.strip()` |
| `invoice_no` as float | pandas loads `00000001` → `1.0` | Cast to zero-padded 8-char string: `df.invoice_no.apply(lambda x: f"{int(x):08d}")` |
| Dates as datetime objects | Some libs see naive datetime | Cast with `pd.to_datetime(...).dt.date`; store as `DATE` (no timezone — accounting date) |
| Accounting codes as float | `TK Nợ` etc. load as `131.0` | Cast `str(int(x))` to preserve `"131"`, `"51111"` etc. |
| Service UoM mixed in | `Giờ`, `Tháng` appear alongside physical UoM | Keep as-is; don't assume all lines are physical products |
| Promo lines with 0 revenue | Revenue = 0 but COGS > 0 | **Include in margin calc** — do NOT filter out |
| `salesperson_name`, `channel_code` nulls | 2 and 8 respectively | Allow null; coalesce to `'UNASSIGNED'` in stg_ for grouping |
| `Đơn giá` has fractions | e.g. `3055555.56` | Use `DECIMAL(18,4)`, not `BIGINT` |
| Filename locale DD.MM.YYYY | Opposite of Shopee's YYYYMMDD | Do NOT regex filename; trust `posting_date` |
| Windows-only Vietnamese filename | `So_chi_tiet_ban_hang_*.xlsx` is ASCII-safe but watch out for any MISA unicode exports | Use `pathlib.Path`, `encoding='utf-8'` |

---

## 7. Relationships & keys

### 7.1 Entity relationship (single-table dataset)

```
┌───────────────────────────────────────────────┐
│ misa_sales_lines                              │
│ grain: 1 row per (voucher, line)              │
│ business key: (voucher_no, line_no)           │
│                                               │
│   posting_date         DATE   ← temporal grain│
│   voucher_no           TEXT                   │
│   line_no              INT    ← synthesized   │
│   product_code         TEXT                   │
│   is_promo_line        BOOL                   │
│   quantity             BIGINT                 │
│   unit_price           DECIMAL                │
│   revenue_gross        BIGINT                 │
│   discount_amount      BIGINT                 │
│   cogs_amount          BIGINT   ← key column  │
│   channel_code         TEXT                   │
│   customer_code        TEXT                   │
│   ...                                         │
└───────────────────────────────────────────────┘
```

### 7.2 Cross-source joins (downstream / future)

| MISA column | Joins to | Join key | Purpose |
|---|---|---|---|
| `voucher_no` (pattern `SON07xxx`) | Sapo `fact_orders.order_code` | `voucher_no = order_code` | Attach COGS to Sapo dealer orders |
| `voucher_no` (pattern `2YYMMDD{...}`) | `fact_shopee_orders.order_code` | `voucher_no = order_code` | Attach COGS to Shopee marketplace orders |
| `product_code` | future `dim_product` | `product_code = sku_code` | Product-level margin |
| `customer_code` | Sapo `dim_customers.tax_code` | `customer_code = tax_code` | Dealer identity |
| `channel_code` | ref seed `ref_channels` | `channel_code → channel_name` | Channel dimension |

**P0 scope:** ingest MISA standalone, expose `int_misa_sales_lines` (intermediate enrichment — all orders exist in Sapo `fact_orders`; MISA adds COGS). **P1:** join into `fact_order_economics` for unified per-order P&L (Sapo + Shopee fees + MISA COGS).

### 7.3 Columns that look like keys but aren't

- **`Số hóa đơn`** — restarts per e-invoice series / fiscal period, not globally unique.
- **`Ngày hạch toán` + `Số chứng từ`** — date repeats; voucher_no alone already has the date implicit.
- **`customer_code`** — many rows share it; it's a dimension, not a key.

---

## 8. Proposed rename summary (quick reference)

| Original (VN) | Proposed logical key |
|---|---|
| `SỔ CHI TIẾT BÁN HÀNG` (sheet) | `misa_sales_lines` |
| `Ngày hạch toán` | `posting_date` *(grain-defining)* |
| `Ngày chứng từ` | `voucher_date` |
| `Ngày hóa đơn` | `invoice_date` |
| `Số chứng từ` | `voucher_no` *(cross-source join key)* |
| `Số hóa đơn` | `invoice_no` |
| `Diễn giải chung` | `description` |
| `Tên hàng trên chứng từ ` | `product_name_on_document` |
| `Mã khách hàng` | `customer_code` |
| `Tên khách hàng` | `customer_name` |
| `Mã hàng` | `product_code` |
| `Tên hàng` | `product_name` |
| `Hàng khuyến mại` | `is_promo_line` *(BOOL)* |
| `ĐVT` | `unit_of_measure` |
| `Tổng số lượng bán` | `quantity` |
| `Đơn giá` | `unit_price` |
| `Doanh số bán` | `revenue_gross` |
| `TK Nợ` | `debit_account` |
| `TK Có` | `credit_account` |
| `TK chiết khấu` | `discount_account` |
| `Chiết khấu` | `discount_amount` |
| `Tổng thanh toán` | `total_payment` |
| `TK giá vốn` | `cogs_account` |
| `Giá vốn` | `cogs_amount` *(key column)* |
| `Tên nhân viên bán hàng` | `salesperson_name` |
| `Mã thống kê` | `channel_code` |
| *(synthesized)* | `line_no` |

Proposed canonical **source key** in `sources.yml`: **`misa_raw`**; **entity**: **`sales_lines`**.

Also rename input folder *(optional cleanup)*: `app_data/input_source/misa-amis/` → keep as-is (already kebab-ish); the MISA docs placeholder file at `docs/misa-amis/README.md` (currently just 3 URLs) should be kept as `docs/misa-amis/api-reference-urls.md` later when MISA Open API path is explored.

---

## 9. Sample aggregates (audit baseline)

From the 2026-01-06 .. 2026-04-09 drop (472 lines):

| Metric | Value |
|---|---|
| Total lines | 472 |
| Distinct vouchers | 344 |
| Max lines per voucher | 4 |
| Promo lines | 92 (19.5%) |
| Non-promo revenue (sum `revenue_gross`) | **5,176,752,390 VND** |
| Non-promo COGS (sum `cogs_amount`) | **1,434,780,582 VND** |
| Promo COGS (sum `cogs_amount`) | **56,729,582 VND** |
| Implied gross margin (non-promo) | **72.3%** |
| Implied gross margin including promo-cost | **71.2%** |
| Channel split (lines) | ECOM 212 / DAILY 186 / CS 60 / KHAC 6 / NULL 8 |

> These numbers become the **reconciliation baseline** for Phase 6 verification of the pipeline.

---

## 10. Open questions

1. **Is `total_payment` = revenue − discount, or does it include VAT?** All accounts use `51111` etc. (revenue w/o VAT in TT200) → likely **net of VAT already**, but we have not seen a VAT column in the export. Confirm with accounting before building any "settled revenue" metric.
2. **What are `CS` and `KHAC` channel codes?** Need a seed mapping from MISA statistics codes → friendly channel names. `ECOM` clearly maps to Shopee/marketplace; `DAILY` to dealer; `CS` and `KHAC` unclear.
3. **Does the export always include ALL COGS accounts?** Sample shows `6321`, `6323`, `64214`. Are there others (`6322` merchandise COGS, etc.) that would appear in a larger drop?
4. **Re-export behavior:** if accounting closes a period and re-issues the report, do voucher IDs stay stable? (Expected yes — MISA vouchers are immutable once posted.)
5. **Multi-file drops with overlapping ranges:** same policy as Shopee — dedup via `ingested_at` on business key; confirm line_no is stable across re-exports.
6. **Service lines (`Giờ`, `Tháng` UoM):** are these real services (consulting, subscriptions) or mis-categorized products? May affect margin analysis.
7. **Cross-source join readiness:** how quickly must we deliver `fact_order_margin` (MISA × Sapo × Shopee)? Scopes timing of P1 design.
8. **Nullable `channel_code`:** 8 rows lack it. Policy — include as `UNKNOWN` in facts, or reject at ingest?
9. **MISA Open API alternative:** the existing `docs/misa-amis/README.md` lists MISA API URLs. Should file-drop be a stop-gap, or is it the long-term interface? (Affects whether we invest in API SDK work in a future phase.)
