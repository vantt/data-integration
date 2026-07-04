# Hướng dẫn vận hành: Finance Budget vs Actual

**Dashboard:** http://bi.lan.fwg.vn/dashboard/114  
**Cập nhật:** hàng tháng (đầu tháng mới)  
**Nguồn dữ liệu:** Google Sheet Budget → dbt seed → DuckDB → Metabase

---

## 1. Xem report

### Tab A — Budget vs Actual

Truy cập dashboard → chọn tab **"Budget vs Actual"**

| Card | Hiển thị gì | Đọc như thế nào |
|------|-------------|-----------------|
| **Tổng kế hoạch** | Tổng VND đã plan (filter theo kỳ) | Tổng inflow + outflow theo kỳ đang chọn |
| **Tổng thực tế** | Số tiền thực tế từ MISA | So sánh với Kế hoạch để thấy mức thực hiện |
| **Chênh lệch** | Thực tế − Kế hoạch (VND) | Dương = vượt kế hoạch, Âm = hụt kế hoạch |
| **Tỷ lệ thực hiện** | Thực tế / Kế hoạch (%) | ≥ 100% = đạt, < 80% = cần xem lại |
| **Bar chart** | Kế hoạch vs Thực tế theo từng Dòng Tiền | Thanh nào lệch nhiều = dòng cần chú ý |
| **Bảng chênh lệch** | Chi tiết từng dòng, từng tháng | Chênh lệch tuyệt đối + % |
| **Biểu đồ dự báo** | Số dư thực tế (xanh đậm) + Dự báo (xanh nhạt) | Đường nhạt = dự báo nếu giữ nguyên kế hoạch |

**Cách dùng filter:**
- **Kỳ (Period Month):** chọn tháng cần xem — để trống = xem tất cả
- **Cashflow Line:** lọc theo dòng tiền cụ thể (lương, NCC, v.v.)

### Tab B — Reserve & Allocation

| Card | Hiển thị gì |
|------|-------------|
| **Tiền mặt tự do** | Thặng dư sau khi trừ hết reserve bucket tháng mới nhất |
| **Bảng dự phòng** | Tiến độ tích lũy từng quỹ: mục tiêu, đã tích lũy, còn thiếu, % hoàn thành |
| **Phân bổ theo tháng** | Stacked bar: mỗi tháng thặng dư được chia vào bucket nào |
| **Chính sách phân bổ** | Bảng log các rule waterfall đang áp dụng |

---

## 2. Duy trì budget hàng tháng

### Quy trình chuẩn (đầu mỗi tháng)

```
Bước 1: Cập nhật số kế hoạch tháng mới trong Google Sheet
Bước 2: Xuất sheet → tải file CSV → thay file seed
Bước 3: Chạy dbt seed + dbt build để refresh mart
Bước 4: Verify trên dashboard
```

---

### Bước 1 — Cập nhật Google Sheet

Mở Google Sheet ngân sách → tab **BUDGET_ITEMS**

Cấu trúc mỗi dòng:

| Cột | Ví dụ | Ghi chú |
|-----|-------|---------|
| `cashflow_line` | Chi lương | Phải khớp với danh sách trong tab `__REF` |
| `period_month` | 2026-08-01 | Ngày đầu tháng, format YYYY-MM-01 |
| `direction` | outflow | `inflow` hoặc `outflow` |
| `planned_amount` | 240000000 | VND, không có dấu phẩy |
| `payment_week` | 1 | Tuần thanh toán trong tháng (1–4) hoặc `spread` |
| `item_type` | recurring | `recurring` / `one_off` / `reserve` |
| `item_label` | _(để trống)_ | Chỉ cần nếu `item_type=reserve` |
| `item_target` | _(để trống)_ | Mục tiêu tích lũy reserve (VND) |
| `target_month` | _(để trống)_ | Hạn đạt mục tiêu reserve |
| `notes` | Tăng lương tháng 8 | Ghi chú tùy ý |

**Thao tác thêm tháng mới (ví dụ T8/2026):**

1. Copy 5 dòng recurring từ tháng trước (T7)
2. Đổi cột `period_month` → `2026-08-01`
3. Cập nhật `planned_amount` nếu có thay đổi
4. Xóa `notes` không còn liên quan
5. Nếu có chi phí một lần (one_off) → thêm dòng riêng với `item_type=one_off`

---

### Bước 2 — Xuất CSV

Trong Google Sheet:
- **File → Download → Comma Separated Values (.csv)** (chỉ tab BUDGET_ITEMS)
- Lưu đè vào: `transformation/seeds/seed_cashflow_budget.csv`

> Nếu có thay đổi chính sách phân bổ → làm tương tự với tab ALLOCATION_POLICY → lưu vào `transformation/seeds/seed_cash_allocation_policy.csv`

---

### Bước 3 — Chạy dbt

```bash
# Vào container data_platform
docker exec -it data_platform bash

# Chạy seed + toàn bộ finance mart
dbt seed --select seed_cashflow_budget seed_cash_allocation_policy
dbt build --select +fact_cashflow_budget+ +mart_cashflow_budget_vs_actual+ +mart_cashflow_forecast+ +mart_cashflow_reserve_status+ +mart_cash_surplus_allocation+
```

Nếu thêm cột mới vào seed (hiếm gặp), cần full-refresh:
```bash
dbt seed --full-refresh --select seed_cashflow_budget
dbt build --full-refresh --select fact_cashflow_budget+
```

---

### Bước 4 — Verify

- Mở dashboard → chọn tháng vừa thêm → số liệu Kế hoạch xuất hiện
- Cột Thực tế sẽ có data khi Dagster đã pull đủ giao dịch MISA của tháng đó

---

## 3. FAQ

### Q: Làm sao biết khi nào data MISA đã cập nhật?

Tab A → card **"Độ tuổi dữ liệu"** (góc phải dưới) hiển thị tháng gần nhất có dữ liệu thực tế. Nếu hiện `⚠️ DỮ LIỆU CÓ THỂ CŨ` → MISA chưa sync hoặc Dagster pipeline bị lỗi.

---

### Q: Thêm dòng tiền mới (ví dụ "Thuê văn phòng") thì làm thế nào?

1. Trong Google Sheet → tab **`__REF`** → thêm dòng mới ở cột B (Dòng Tiền), cột A (Chiều: Thu/Chi)
2. Tab **BUDGET_ITEMS** → thêm dòng với `cashflow_line` = tên vừa tạo trong `__REF`
3. Apps Script sẽ tự validate khi nhập — nếu tên không có trong `__REF` sẽ báo lỗi đỏ
4. Chạy dbt như Bước 3

---

### Q: Chi phí phát sinh đột ngột (mua thiết bị, sửa chữa, v.v.)?

Thêm dòng `item_type=one_off` vào đúng tháng phát sinh:

```
cashflow_line:  Thanh toán nhà cung cấp
period_month:   2026-08-01
direction:      outflow
planned_amount: 85000000
payment_week:   2
item_type:      one_off
notes:          Mua máy tính cho dev team
```

Dòng `one_off` chỉ xuất hiện 1 tháng, không lặp lại — dashboard sẽ hiển thị riêng trong bảng chi tiết.

---

### Q: Dòng tiền thực tế vượt kế hoạch lớn (ví dụ đơn hàng lớn bất ngờ)?

Dashboard sẽ tự hiện chênh lệch dương ở cột **Chênh lệch** và tỷ lệ > 100%.  
Nếu muốn ghi nhận vào kế hoạch (để forecast chính xác hơn tháng sau):

- Cập nhật `planned_amount` của tháng đó lên gần với thực tế
- Hoặc để nguyên — chênh lệch là thông tin quản lý hữu ích

---

### Q: Dòng tiền thiếu hụt nghiêm trọng trong tháng — phải làm gì?

1. Dashboard Tab A → xem bảng chênh lệch → xác định dòng hụt nhiều nhất
2. Tab B → xem **Tiền mặt tự do** → đủ bù không?
3. Nếu cần điều chỉnh kế hoạch tháng sau: cập nhật `planned_amount` của dòng bị ảnh hưởng
4. Nếu cần tạm thời hoãn một khoản outflow: đổi `payment_week` sang tuần sau hoặc tháng sau

---

### Q: Muốn thay đổi chính sách phân bổ waterfall (tăng/giảm reserve)?

Tab **ALLOCATION_POLICY** trong Google Sheet:

| Cột | Ý nghĩa |
|-----|---------|
| `priority` | Thứ tự ưu tiên (1 = cao nhất) |
| `bucket` | Tên quỹ |
| `rule_type` | `fill_to_target` / `fixed` / `remainder` |
| `value` | Số VND (với fill_to_target/fixed) hoặc để trống (remainder) |
| `effective_from` | Ngày bắt đầu áp dụng |
| `effective_to` | Ngày kết thúc (để trống = còn hiệu lực mãi) |

Để thay đổi: **không xóa dòng cũ** — thêm dòng mới với `effective_from` mới và đặt `effective_to` của dòng cũ = ngày cuối tháng trước.

---

### Q: Dashboard hiển thị trống / không có data?

Kiểm tra theo thứ tự:
1. Filter **Kỳ** đang chọn có data không? → bỏ filter, xem tất cả
2. Card "Độ tuổi dữ liệu" → data MISA có tháng đó chưa?
3. `dbt seed` đã chạy chưa? → chạy lại Bước 3
4. Nếu vẫn trống → kiểm tra Dagster UI: http://localhost:3000 (hoặc nhờ kỹ thuật kiểm tra pipeline)

---

### Q: Muốn xem chi tiết tháng cụ thể?

Dashboard → filter **Kỳ (Period Month)** → chọn tháng → tất cả cards lọc theo tháng đó.  
Bỏ filter để xem tổng lũy kế từ đầu năm (hoặc từ T7/2026 nếu budget bắt đầu từ T7).

---

## 4. Lịch vận hành đề xuất

| Thời điểm | Việc cần làm |
|-----------|-------------|
| **Ngày 1–3 hàng tháng** | Cập nhật budget tháng mới vào Google Sheet |
| **Ngày 3–5** | Xuất CSV → chạy dbt seed + build |
| **Ngày 5–10** | MISA sync xong → thực tế tháng trước đầy đủ → review dashboard |
| **Cuối tháng** | Review chênh lệch, điều chỉnh kế hoạch tháng tới nếu cần |

---

**Liên hệ kỹ thuật:** xem log Dagster tại http://localhost:3000 — pipeline `pipeline_sapo_v2_incremental_job` và `pipeline_misa_*`
