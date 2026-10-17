# Phase 3: gate S, số trước/sau, user duyệt danh sách đổi

**Effort:** 0.5d · **Phụ thuộc:** phase 1, 2 · **Gate:** `scripts/shadow/gate.sh S --allow-new --allow-code-change` · **Đụng prod:** không · **Cần user:** duyệt `change-list.md`

## Bối cảnh

- `gate.sh` chạy hết mọi bước rồi mới báo PASS/FAIL. Mỗi bước lỗi được in `FAILED: <tên>` (`scripts/shadow/gate.sh:38-40`). Ở bước cuối, gate xoá các lake của nhánh (`lake-B`, `lake-D`, `lake-E`, `lake-BF`) vì chúng chứa PII (dòng cuối của script). Vì vậy số card phải đo trên một lake dựng riêng.
- `golden_snapshot.py compare` in từng khác biệt: số dòng, schema, cột có giá trị khác, dấu vân tay dòng. `keyed-diff` in số dòng lệch và 5 khoá mẫu (`docs/operations/refactor-safety-harness.md` §6.1). Khoá mẫu chỉ dùng để điều tra, không đưa vào report.
- Đây là thay đổi **có chủ đích đổi số**. Vì vậy "gate đạt" nghĩa là: các bước golden chỉ báo đúng các bảng trong E-list, với đúng loại khác biệt dự kiến, và **mọi bước khác** đều `ok`. Cách làm giống đợt sửa lỗi số ngày 15/10 (`plans/reports/numfix-261015-1712-two-number-bugs-change-list.md` §3).

## E-list: khác biệt golden dự kiến

| Bảng | Khác biệt được phép | Lý do |
|---|---|---|
| `fact_inventory_snapshot` | Số dòng; schema chỉ **thêm** `captured_at`, `ledger_on_hand`, `on_hand_recon_status` ở cuối; giá trị mọi cột | Đổi nguồn (QĐ-TK-01, 02) |
| `mart_inventory_health` | Số dòng; schema chỉ thêm `captured_at` ở cuối; giá trị | Đi theo nguồn |
| `mart_product_health` | Giá trị các cột tồn (`on_hand`, `stock_value_at_mac`, `dead_stock_value_at_risk`, `days_of_supply`, `is_oos`, `is_low_stock`, `is_dead_stock`, `oos_risk`); số dòng có thể đổi (tập sản phẩm "đang giữ hàng", `mart_product_health.sql:139`) | QĐ-TK-04, 05 |
| `mart_product_action_queue` | Số dòng; giá trị | Đi theo `mart_product_health` |
| `mart_deadstock_target_queue` | Số dòng; giá trị | Đi theo `mart_product_health` |
| `fact_inventory_position_daily` | Chỉ khi phase 1 phải thêm `bin_location`/`wait_to_pack`: schema thêm hai cột ở cuối, giá trị cột cũ **không đổi** | Phase 0, bước 3 |

Mọi bảng public khác: 0 khác biệt. Cùng E-list phải đúng ở ba cặp so sánh: build thường (lake-A/lake-B), build trên lake rolling rỗng (lake-A/lake-E) và `--full-refresh` (lake-AF/lake-BF). Bước lõi trần (6b) phải build xanh.

Các bước khác phải `ok`:
- dbt inventory: chỉ có node **thêm** là test đối soát và các unit test; SQL đổi ở đúng các model của phase 1.
- Module boundaries: không có cạnh mới ngoài ma trận (core đọc core).
- Dagster inventory: chỉ có asset check **thêm** trên `fact_inventory_snapshot`; selection của mọi job không đổi.
- pytest.

## Đo số trước/sau

Lake chuẩn: `lake-A` (baseline dựng từ `main`, đã có model của plan lịch sử và ≥ 2 đêm chụp). Lake nhánh: `lake-N`, dựng riêng bằng `scripts/shadow/clone-lake.sh lake-N` rồi `scripts/shadow/build-lake.sh "$BRANCH_DIR" lake-N`. Xoá `lake-N` bằng `scripts/shadow/cleanup.sh lake-N` ngay khi đo xong.

Một script đo dùng một lần, đặt trong `reports/` của plan (không đưa vào repo code), chạy trong `run-shadow.sh`:
1. Với mỗi lake, tạo schema `main_marts` trong DuckDB in-memory, mỗi bảng là một view trên parquet rolling mới nhất của bảng đó.
2. Với mỗi card trong kiểm kê ở phase 0:
   - Chạy SQL **cũ** (bản thật lấy từ API) trên lake-A, cho ra số **trước**.
   - Chạy SQL **mới** (blueprint ở phase 2) trên lake-N, cho ra số **sau**.
   - Với card có đổi SQL (OOS, Chu kỳ báo cáo), chạy thêm SQL cũ trên lake-N, để tách phần đổi do dữ liệu khỏi phần đổi do định nghĩa.
   - Bỏ các mệnh đề `[[...]]` (không bộ lọc). Chạy thêm một lần với bộ lọc kho lần lượt từng kho cho các card scalar của tab Current Stock.
   - Card scalar: ghi giá trị. Card bảng: ghi số dòng và tổng các cột số. Không ghi dòng chi tiết.
3. Ghi lại `snapshot_date` mới nhất của lake-N (`as_of_pin`). Phase 4 dùng lại giá trị này để so với prod.
4. **CRM:** số dòng và số `product_key` khác nhau của `mart_deadstock_target_queue`; số dòng theo `action_type` của `mart_product_action_queue`; số sản phẩm `oos_risk = true` trong `mart_product_health`. Chỉ đếm, không có cột khách hàng.
5. **Đối soát:** số cặp theo `on_hand_recon_status` ở `as_of_pin`; tổng `on_hand` của ảnh chụp so với tổng `ledger_on_hand`; tổng `stock_value_at_mac` so với tổng `inventory_value` của sổ kho cùng ngày.

## `change-list.md` (đầu ra, ghi trong thư mục plan)

Theo mẫu `plans/reports/numfix-261015-1712-two-number-bugs-change-list.md`:
1. Tóm tắt: đổi gì, vì sao, QĐ nào đã chốt.
2. File đổi (phase 1, 2).
3. Bảng và cột đổi: kết quả golden ở ba cặp so sánh, đối chiếu với E-list.
4. Card đổi, mỗi card một dòng: dashboard, id, tên, trước, sau, phần do dữ liệu, phần do định nghĩa, QĐ liên quan.
5. CRM và hàng đợi hành động: số trước/sau.
6. Đối soát ở `as_of_pin`.
7. Những gì **không** đổi: bảng public còn lại, cột ghim của CRM, selection của Dagster.
8. Dòng duyệt: "User duyệt: … (ngày, giờ)".

Cập nhật [definition-decisions.md](definition-decisions.md): thay số "ước lượng" bằng số đo, và chuyển trạng thái `đã chốt` → `đã áp: <commit>` sau phase 4.

## Các bước

1. Rebase nhánh lên `main`. Làm mới baseline nếu `main` đã đổi (harness §9.2).
2. Chạy `scripts/shadow/gate.sh S --allow-new --allow-code-change`. Lưu log vào `reports/gate-s.log`, đã lọc bỏ khoá mẫu.
3. Đối chiếu từng dòng `FAILED: golden…` với E-list. Bảng nào ngoài E-list là lỗi: điều tra bằng `keyed-diff`, sửa ở phase 1, rồi chạy lại gate.
4. Dựng `lake-N`, chạy script đo, xoá `lake-N`.
5. Viết `change-list.md`, gửi user qua coordinator. Đợi duyệt.

## Tiêu chí xong

- Golden khớp đúng E-list ở cả ba cặp so sánh; mọi bước khác `ok`.
- Mọi card trong kiểm kê có số trước/sau.
- User đã duyệt `change-list.md`, có ngày giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Lake-base chỉ có 2–3 đêm chụp nên card xu hướng ở shadow ít điểm hơn prod | Chắc chắn × Thấp | Ghi rõ trong change-list; số "hôm nay" vẫn đúng nghĩa |
| Số trên shadow khác prod vì dữ liệu đã đổi khi deploy | Chắc chắn × Thấp | So ở cùng `as_of_pin` (phase 4); các ngày mới chỉ là phần thêm |
| Report vô tình chứa dữ liệu khách hàng | Thấp × Cao | Script chỉ xuất số tổng hợp; review report trước khi gửi |

## Rollback

Không có thay đổi prod. Nếu user không duyệt: quay lại phase 1 hoặc 2 theo ý kiến của user, rồi chạy lại phase 3.
