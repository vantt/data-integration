# Phase 1: đổi model dbt và thêm đối soát

**Effort:** 1d · **Phụ thuộc:** phase 0 xong; QĐ-TK-01 đến 05 đã chốt · **Gate trong phase:** pytest, `scripts/checks/run-all.sh` · **Đụng prod:** không

Phần dưới đây viết theo các lựa chọn **đề xuất** ở [definition-decisions.md](definition-decisions.md). Nếu user chọn khác thì chỉ sửa đúng mục tương ứng.

## Luồng dữ liệu sau khi đổi

```text
sapo_v2_raw/product_daily_snapshot (plan lịch sử)
  └► fact_inventory_position_daily (core, plan lịch sử)
        └► fact_inventory_snapshot (core)  ◄── dim_products (thuộc tính SP)
              ▲                              ◄── fact_inventory_movements (sổ kho, số dư tại captured_at)
              └► mart_inventory_health  ◄── int_sku_sales_monthly (không đổi)
                    └► mart_product_health (ngày chụp mới nhất chung)
                          ├► mart_product_action_queue ─► Metabase
                          └► mart_deadstock_target_queue ─► CRM wh_deadstock_target
                    mart_product_health ─► CRM product_insight (oos_risk)
int_sapo_inventories: giữ nguyên, không còn ai đọc trong dbt, đánh dấu deprecated
```

| Thành phần | Vào | Biến đổi | Ra |
|---|---|---|---|
| `fact_inventory_snapshot` | `fact_inventory_position_daily`, `dim_products`, `fact_inventory_movements` | `snapshot_date = as_of_date`; cast về kiểu cũ; `stock_value_at_mac`/`committed_value_at_mac` giữ công thức cũ; `source_timestamp = captured_at`; số dư sổ kho tại `captured_at` bằng ASOF JOIN; gán `on_hand_recon_status` | Cột cũ đúng thứ tự, cộng `captured_at`, `ledger_on_hand`, `on_hand_recon_status` ở cuối |
| `mart_inventory_health` | như cũ | Không đổi logic; chuyển tiếp `captured_at` ở cuối | Cột cũ, cộng `captured_at` |
| `mart_product_health` | `mart_inventory_health` | `latest_inv` lọc `snapshot_date = MAX(snapshot_date)` thay cho `ROW_NUMBER` theo cặp; nếu QĐ-TK-05 = (b) thì `is_oos` = tổng `on_hand` ≤ 0 | Cột không đổi |

## Yêu cầu

### `fact_inventory_snapshot` (`transformation/models/core/marts/sales/fact_inventory_snapshot.sql`)

1. Đọc `ref('fact_inventory_position_daily')` thay cho `ref('int_sapo_inventories')` (dòng 57). Bỏ khối `is_incremental()` (dòng 30-34, 58-61): model là external, build lại toàn bộ, và việc khử trùng trong ngày đã làm ở `fact_inventory_position_daily`.
2. Giữ nguyên **tên, thứ tự và kiểu** của mọi cột ở dòng 89-149. Cast theo bảng kiểu đo ở phase 0.
   - `inventory_snapshot_key`: cùng công thức (dòng 91-95), trên `as_of_date`.
   - `snapshot_date = as_of_date`.
   - `source_timestamp = captured_at` (cast về kiểu cũ).
   - `inventory_modified_at`: `CAST(NULL AS <kiểu cũ>)`. Cột này trước đây cũng luôn NULL (`int_sapo_inventories.sql:74-75`).
   - `bin_location`, `wait_to_pack`: lấy từ `fact_inventory_position_daily`. Nếu bảng đó chưa có hai cột này, thêm vào cuối của `stg_sapo_v2_inventory_position_captures`, `std_inventory_position_captures` và `fact_inventory_position_daily` (theo phase 0, bước 3).
3. Thêm **ở cuối** đúng ba cột:
   - `captured_at` (TIMESTAMPTZ): thời điểm chụp.
   - `ledger_on_hand` (cùng kiểu với `on_hand`): `onhand` của giao dịch cuối cùng trong `fact_inventory_movements` có `issued_at ≤ captured_at`, cùng (`variant_id`, `location_id`). Dùng `ASOF LEFT JOIN`. Cast `variant_id`/`location_id` cho khớp kiểu hai bên (sổ kho dùng `location_id` số, ảnh chụp dùng chuỗi).
   - `on_hand_recon_status` (VARCHAR):
     - `no_ledger_history` khi `ledger_on_hand IS NULL`;
     - `match` khi `ledger_on_hand = on_hand`;
     - ngược lại là `mismatch`.
4. Nếu QĐ-TK-02 = (a): không còn dòng nào trước ngày chụp đầu tiên. Điều này tự đúng, vì nguồn chỉ có ngày đã chụp.
5. Viết lại comment đầu file cho đúng: nguồn, ý nghĩa của `snapshot_date` (ngày ICT mà ảnh chụp đại diện, theo `history_day_cutoff_hour`), quy tắc đối soát, và "dashboard dùng `on_hand` của ảnh chụp, sổ kho chỉ để đối soát". Không ghi plan ID.

### `mart_inventory_health` (`transformation/models/core/marts/sales/mart_inventory_health.sql`)

1. Thêm `captured_at` vào CTE `snapshot` (dòng 35-65) và vào cuối danh sách SELECT, sau `source_timestamp` (dòng 205).
2. Thêm vào CAVEATS (dòng 23-33) một dòng: các cờ hàng chậm/tồn chết dùng tốc độ bán của tháng gần nhất cho mọi `snapshot_date` (QĐ-TK-06).

### `mart_product_health` (`transformation/models/core/marts/mart_product_health.sql`)

1. `latest_inv` (dòng 95-115): thay `ROW_NUMBER() ... WHERE rn = 1` bằng `WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM {{ ref('mart_inventory_health') }})`. Sửa comment dòng 88-94 (bỏ câu "daily inventory snapshots are sparse").
2. Nếu QĐ-TK-05 = (b): `is_oos` lấy là `SUM(on_hand) <= 0` thay cho `MAX(is_oos::INT)::BOOL` (dòng 102). Cập nhật CAVEATS dòng 26-27.

### Đối soát (asset check)

1. Tạo `transformation/tests/assert_inventory_snapshot_onhand_matches_ledger.sql`:
   - `config(severity='warn', warn_if='>' ~ var('inventory_recon_warn_pairs'))`;
   - trả về các cặp `mismatch` ở `snapshot_date = MAX(snapshot_date)`;
   - chỉ `ref('fact_inventory_snapshot')`, để Dagster gắn check vào đúng asset (đã xác nhận ở phase 0, bước 7; nếu không gắn được thì dùng generic test trong YAML).
2. Biến `inventory_recon_warn_pairs` trong `transformation/dbt_project.yml`, giá trị theo QĐ-TK-07.
3. Severity **warn**: test lỗi không được chặn các model phía sau trong `dbt build`.

### YAML và test

- `transformation/models/core/marts/sales/_core__models.yml`:
  - Sửa mô tả `fact_inventory_snapshot` (dòng 71-77, hiện ghi sai "incremental… never deletes") và `mart_inventory_health` (dòng 532-537).
  - Mô tả ba cột mới, kèm `accepted_values` cho `on_hand_recon_status` và `not_null` cho `captured_at`.
  - Ghi `inventory_modified_at` là deprecated (luôn NULL, giữ cho tương thích).
  - Giữ test `unique_combination_of_columns` (dòng 78-81).
- `transformation/models/core/intermediate/sapo/_core__models.yml` (mục `int_sapo_inventories`, dòng 42): ghi deprecated, "không còn model dbt nào đọc; giữ cho người dùng ngoài; gỡ ở một thay đổi riêng".
- dbt unit test (YAML `unit_tests:`, cùng mẫu với các unit test đã có):
  - `fact_inventory_snapshot`:
    1. Sổ kho bằng ảnh chụp thì ra `match`.
    2. Sổ kho khác thì ra `mismatch`.
    3. Không có giao dịch thì ra `no_ledger_history`.
    4. Giao dịch có `issued_at` **sau** `captured_at` không được tính.
    5. Hai kho cùng variant thì đối soát riêng từng kho.
  - `mart_product_health`: một cặp có ở ngày D−1 nhưng không có ở ngày D thì không vào `latest_inv`. Nếu QĐ-TK-05 = (b), thêm ca: hai kho, một kho 0 và một kho 5, thì `is_oos = false`.
- Sinh lại `scripts/checks/public_models.yaml` bằng `golden_snapshot.py init`. Khoá của `fact_inventory_snapshot` vẫn là (`variant_id`, `location_id`, `snapshot_date`) (`public_models.yaml:132-138`).

## Các bước

1. Tạo worktree `feat/inventory-on-daily-snapshots` từ `main` (đã có model của plan lịch sử).
2. Viết unit test trước (chúng sẽ đỏ), rồi sửa ba model, YAML, test đối soát và biến.
3. Chạy `dbt build --select fact_inventory_snapshot+ fact_inventory_position_daily` trên shadow, rồi `scripts/checks/run-all.sh`, rồi `pytest crm/sync`.
4. Kiểm nhanh trên lake shadow:
   - Số cặp ở `MAX(snapshot_date)` bằng số cặp của `fact_inventory_position_daily` cùng ngày.
   - `DESCRIBE` cho thấy cột cũ giữ nguyên kiểu và thứ tự, ba cột mới ở cuối.

## Ma trận test

| Mức | Nội dung |
|---|---|
| dbt unit | 5 ca đối soát; `latest_inv` theo ngày chung; `is_oos` mức sản phẩm (nếu chọn) |
| dbt data | Unique theo grain; `inventory_snapshot_key` unique, not_null; `accepted_values` cho `on_hand_recon_status`; singular đối soát (warn) |
| pytest | `crm/sync` (cột ghim không đổi), `orchestration` (inventory Dagster) |
| Shadow nhanh | Số cặp ngày mới nhất; schema; thời gian build `fact_inventory_snapshot` và `mart_inventory_health` |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| ASOF JOIN sai kiểu khoá làm mọi dòng thành `no_ledger_history` | Trung bình × Trung bình | Unit test ca 1–2; trên shadow tỉ lệ `no_ledger_history` phải gần mức phase 0 (khoảng 71 trên khoảng 2.000 cặp có hàng) |
| `as_of_date` lệch múi giờ so với ngày người dùng hiểu | Thấp × Cao | Dùng nguyên `as_of_date` của plan lịch sử (đã có unit test giờ chốt); không tính lại |
| Test warn bị coi là error trong một profile nào đó | Thấp × Cao | Kiểm `dbt build` trên shadow với mismatch nhân tạo: build vẫn xanh, có cảnh báo |

## Rollback

Chưa deploy, nên chỉ cần bỏ nhánh. Sau deploy, xem phase 4.
