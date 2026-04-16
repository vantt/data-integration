# Phase: Adjustment Sheet Integration

**Added:** 2026-04-16 (promoted from P1 → P0 per Q5 answer)
**Depends on:** Phase 1 ingestion framework already built

## Context

Sheet `Adjustment` trong file Income chứa các khoản điều chỉnh (bù trừ, hoàn tiền, phí marketing...) liên quan đến đơn hàng cụ thể. Mỗi dòng có `order_code` → join được vào `int_shopee_order_fees`.

### Cấu trúc thực tế (từ file mẫu)

```
Row  1-6:  Metadata (ghi chú, seller, date range, currency) → BỎ QUA
Row  7-9:  Tóm tắt shop-level (tổng theo loại điều chỉnh) → BỎ QUA
Row 10-11: Blank
Row 12:    Section header "Chi tiết danh sách giao dịch điều chỉnh" → BỎ QUA
Row 13:    Column headers → DÙNG LÀM HEADER
Row 14+:   Data rows → PARSE
Row cuối:  "Tổng cộng" summary row → BỎ QUA
```

### Columns (Row 13)

| # | Header (VN) | Logical name | Type | Notes |
|---|---|---|---|---|
| 1 | Mã giao dịch | `row_seq` | INT | Row counter → **drop** |
| 2 | Ngày hoàn thành điều chỉnh đơn hàng | `adjustment_completed_at` | DATE | Ngày điều chỉnh hoàn tất |
| 3 | Loại điều chỉnh \| Mô tả | `adjustment_type` | VARCHAR | Ví dụ: "Chương trình Marketing" |
| 4 | Lý do điều chỉnh | `adjustment_reason` | VARCHAR | Nullable |
| 5 | Số tiền điều chỉnh | `adjustment_amount` | INT (VND) | Luôn negative trong mẫu (-54724) |
| 6 | Mã đơn hàng liên quan | `order_code` | VARCHAR | **Join key** → `int_shopee_order_fees` |
| 7 | Ngày hoàn thành thanh toán | `payout_released_at` | DATE | Ngày payout released (cùng grain với Doanh thu) |

### Data mẫu (1 row)

```
row_seq=1, adjustment_completed_at=2026-02-10, adjustment_type="Chương trình Marketing",
adjustment_reason=NULL, adjustment_amount=-54724, order_code="2602098R4NA7MV",
payout_released_at=2026-02-09
```

## Design decisions

### 1. Grain: 1 row per adjustment per order

Một order có thể có N adjustments (nhiều loại điều chỉnh khác nhau). Business key = `(order_code, adjustment_completed_at, adjustment_type)` — không dùng `row_seq`.

### 2. Bảng riêng, KHÔNG join vào `int_shopee_order_fees`

**Lý do:**
- `int_shopee_order_fees` grain = 1 row/order. Adjustment grain = N rows/order → join trực tiếp sẽ fan-out hoặc cần aggregate trước
- Adjustment là khoản riêng biệt (marketing fee, compensation...), không thuộc cùng payout cycle với revenue/fees
- Tách bảng giữ model đơn giản, analyst có thể query riêng hoặc join khi cần

**Model:** `int_shopee_order_adjustments` — bảng riêng với rolling location (giống `int_shopee_order_fees`)

### 3. Tổng điều chỉnh per order (convenience)

Thêm 1 cột `total_adjustment_amount` vào `int_shopee_order_fees` qua LEFT JOIN aggregate:

```sql
COALESCE(adj.total_adjustment_amount, 0) AS total_adjustment_amount
```

Và cập nhật `net_settlement` thành `net_settlement_with_adjustments`:

```sql
net_settlement + COALESCE(adj.total_adjustment_amount, 0) AS net_settlement_adjusted
```

Giữ cả `net_settlement` (gốc, không adjustment) và `net_settlement_adjusted` (có adjustment) để analyst so sánh.

## Implementation steps

### Step 1: Parser — thêm parse Adjustment sheet

**File:** `ingestion/src/shopee/income-parser.py`

1. Thêm rename dict cho Adjustment sheet:
```python
ADJUSTMENT_RENAME = {
    "Mã giao dịch": "row_seq",
    "Ngày hoàn thành điều chỉnh đơn hàng": "adjustment_completed_at",
    "Loại điều chỉnh | Mô tả": "adjustment_type",
    "Lý do điều chỉnh": "adjustment_reason",
    "Số tiền điều chỉnh": "adjustment_amount",
    "Mã đơn hàng liên quan": "order_code",
    "Ngày hoàn thành thanh toán": "payout_released_at",
}
```

2. Parse logic (**section-based, KHÔNG hardcode row number**):
   - Load toàn bộ sheet không header: `pd.read_excel(sheet_name="Adjustment", header=None)`
   - Scan column A tìm section marker: row chứa text `"Chi tiết danh sách giao dịch điều chỉnh"`
   - Header row = marker row + 1 (dòng ngay sau section title)
   - Data rows = header row + 1 trở đi, cho đến khi gặp row "Tổng cộng" hoặc all-NaN
   - **Tại sao không hardcode row 12:** Phần tóm tắt shop-level (rows 7–9 trong mẫu) có thể dài/ngắn tùy số loại adjustment trong file → row number của section "Chi tiết" không cố định
   - Rename VN → snake_case
   - `to_int_vnd()` cho `adjustment_amount`
   - Date parse cho `adjustment_completed_at`, `payout_released_at`
   - Drop `row_seq`
   - Nếu không tìm thấy section marker hoặc data rỗng → skip (file không có adjustment)
   - Inject metadata: `source_file`, `ingested_at`, `ingest_method`, `year`, `month` (from `payout_released_at`)

3. Write parquet:
```
{DBT_DATA_LAKE_PATH}/shopee_raw/order_adjustments/ingest_method=file_drop/year={YYYY}/month={MM}/shopee_income_{YYYY}-{MM}_{ingested_at_ts}.parquet
```

### Step 2: dbt source registration

**File:** `transformation/models/sources.yml` — thêm entity vào `shopee_raw`:

```yaml
- name: order_adjustments
  description: "Shopee order-level adjustments (marketing fees, compensations, etc.)"
```

### Step 3: dbt src_ model

**File:** `transformation/models/staging/src_shopee_order_adjustments.sql`

- Materialize: `view`
- Business key: `(order_code, adjustment_completed_at, adjustment_type)`
- Dedup: `ROW_NUMBER() OVER (PARTITION BY order_code, adjustment_completed_at, adjustment_type ORDER BY ingested_at DESC) = 1`
- Tag: `['src', 'shopee']`

### Step 4: dbt stg_ model

**File:** `transformation/models/staging/stg_shopee_order_adjustments.sql`

- Materialize: `view` over `src_shopee_order_adjustments`
- Cast: `adjustment_amount` → BIGINT, dates → DATE
- Pass-through: `adjustment_type`, `adjustment_reason`, `order_code`

### Step 5: dbt int_ model

**File:** `transformation/models/intermediate/shopee/int_shopee_order_adjustments.sql`

```sql
{{ config(
    tags=['int', 'shopee'],
    materialized='table',
    location="{{ get_rolling_location() }}"
) }}

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'order_code', 'adjustment_completed_at', 'adjustment_type'
    ]) }} AS shopee_order_adjustment_sk,
    order_code,
    adjustment_completed_at,
    adjustment_type,
    adjustment_reason,
    adjustment_amount,
    payout_released_at,
    source_file,
    ingested_at
FROM {{ ref('stg_shopee_order_adjustments') }}
```

### Step 6: Update `int_shopee_order_fees` — add adjustment total

Thêm CTE aggregate adjustment + LEFT JOIN:

```sql
adj AS (
    SELECT
        order_code,
        SUM(adjustment_amount) AS total_adjustment_amount
    FROM {{ ref('int_shopee_order_adjustments') }}
    GROUP BY order_code
)
...
LEFT JOIN adj USING (order_code)
...
-- thêm columns:
COALESCE(adj.total_adjustment_amount, 0) AS total_adjustment_amount,
net_settlement + COALESCE(adj.total_adjustment_amount, 0) AS net_settlement_adjusted,
```

### Step 7: dbt tests

**File:** `transformation/models/intermediate/shopee/schema.yml` — thêm:

```yaml
- name: int_shopee_order_adjustments
  columns:
    - name: shopee_order_adjustment_sk
      tests: [unique, not_null]
    - name: order_code
      tests:
        - not_null
    - name: adjustment_amount
      tests: [not_null]
    - name: adjustment_completed_at
      tests: [not_null]
```

### Step 8: Dagster upstream key

**File:** `orchestration/assets/dbt.py` — thêm `src_shopee_order_adjustments` vào upstream key mapping cho `shopee_income_file_drop_asset`.

## File manifest

```
ingestion/src/shopee/income-parser.py              EDIT (+Adjustment parse logic)
transformation/models/sources.yml                   EDIT (+order_adjustments entity)
transformation/models/staging/
  src_shopee_order_adjustments.sql                  NEW
  stg_shopee_order_adjustments.sql                  NEW
transformation/models/intermediate/shopee/
  int_shopee_order_adjustments.sql                  NEW
  int_shopee_order_fees.sql                         EDIT (+adjustment LEFT JOIN)
  schema.yml                                        EDIT (+adjustment tests)
orchestration/assets/dbt.py                         EDIT (+upstream key)
```

## Risks

| Risk | Mitigation |
|---|---|
| Some files have 0 adjustment rows → empty parquet | Parser skips write if df is empty; `src_` view handles empty gracefully |
| Multiple adjustments same order+date+type (duplicate) | Dedup by `ingested_at DESC` in src_ |
| Adjustment without matching order in Doanh thu | `int_shopee_order_adjustments` is standalone; LEFT JOIN in `int_shopee_order_fees` means unmatched adjustments don't break fees table (but won't appear in `net_settlement_adjusted` — acceptable, flag in Phase 6 verification) |
| `adjustment_type` has pipe character in header (`Loại điều chỉnh \| Mô tả`) | Rename dict handles exact string match; test header assertion |

## Success criteria

- `SELECT COUNT(*) FROM int_shopee_order_adjustments` = 1 (from sample file)
- `SELECT SUM(adjustment_amount) FROM int_shopee_order_adjustments` = -54724
- `int_shopee_order_fees` gains `total_adjustment_amount` and `net_settlement_adjusted` columns
- All dbt tests pass
- Idempotent: re-ingest same file → no duplicates
