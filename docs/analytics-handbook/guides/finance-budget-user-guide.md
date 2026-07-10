# Hướng dẫn vận hành: Finance Budget vs Actual

**Dashboard:** http://bi.lan.fwg.vn/dashboard/114  
**Cập nhật:** hàng tháng (đầu tháng mới)  
**Nguồn dữ liệu:** Google Sheet Budget → dbt seed → DuckDB → Metabase

> **Cấu trúc sheet:** nguồn sự thật là `scripts/budget/validate-budget-sheet.gs` — nếu guide này và file đó không khớp, tin file đó.

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
Bước 1: Cập nhật số kế hoạch tháng mới trong Google Sheet (cột Budget)
Bước 2: Không cần làm gì thêm — sync tự chạy 02:30 hàng đêm
Bước 3: (tuỳ chọn) Muốn thấy số NGAY thay vì chờ qua đêm → trigger sync thủ công
Bước 4: Verify trên dashboard
```

Google Sheet: `https://docs.google.com/spreadsheets/d/15hba6bzrTRXUDXBeUg5_DhefrETX9kLGG8SnPJZzTfA/edit`

---

### Bước 1 — Cập nhật Google Sheet

Mở Google Sheet ngân sách → tab **BUDGET_ITEMS**. Đây là sheet dạng **matrix** (không phải danh sách dòng dài) — mỗi dòng là 1 khoản mục, mỗi tháng là 1 cặp cột.

**Cột A–G (cố định, không đổi theo tháng):**

| Cột | Tên | Ví dụ | Ghi chú |
|-----|-----|-------|---------|
| A | Dòng Tiền | Chi lương | `recurring` → chọn từ dropdown tab `__REF` (dạng `<mã account>  <tên account>`, vd `"  3341  Phải trả người lao động - lương"`). `one_off`/`reserve` → tên mô tả tự do, ví dụ "Mua máy tính cho dev team" |
| B | Ghi chú | Internet | Tự do, không ảnh hưởng logic sync — dùng để phân biệt nhiều dòng cùng chọn 1 account (vd "Internet" và "Cloud Hosting" đều map `642282 Chi phí dịch vụ mua ngoài`) |
| C | Chiều | Chi | `Thu` hoặc `Chi` |
| D | Type | recurring | `recurring` / `one_off` / `reserve` |
| E | Tháng Cần | _(để trống)_ | Hạn đạt mục tiêu — chỉ dùng cho `reserve` có deadline |
| F | Tuần TT | 1 | Tuần thanh toán trong tháng: `1`/`2`/`3`/`4`/`spread` |
| G | Tổng Cần | _(để trống)_ | Mục tiêu tích lũy (VND) — bắt buộc phải có nếu điền cột E |

**Từ cột H trở đi — cặp cột theo từng tháng, THÁNG GẦN NHẤT Ở BÊN TRÁI** (giảm dần sang phải, vd H-I=2026-08, J-K=2026-07, L-M=2026-06...) — đổi từ 2026-07-09, trước đó tháng cũ ở bên trái. Mỗi tháng chiếm 2 cột liền nhau, header row 1 ghi tháng (`2026-08`):

| Cột | Ý nghĩa |
|-----|---------|
| **Gợi Ý** (ví dụ cột H) | Số gợi ý — hiện tại nhập tay hoặc để trống, KHÔNG được sync đọc. Tự động tính gợi ý (rolling avg thực tế 3 tháng) đã được xây dựng và lên lịch chạy ngày 1 hàng tháng, 08:00 ICT, nhưng **CHƯA kích hoạt** — cần kỹ thuật cấu hình quyền ghi Google Sheet (service account) trước. Trước khi đó, cột Gợi Ý vẫn cần finance tự ước lượng hoặc để trống. |
| **Budget** (ví dụ cột I) | Số kế hoạch thật — **đây là cột duy nhất sync đọc**. Nhập số VND vào đây (có thể có dấu phẩy/₫, sync tự parse). |

**Cập nhật số kế hoạch tháng mới:**

1. Kiểm tra sheet đã có sẵn cặp cột `[Gợi Ý][Budget]` cho tháng cần nhập chưa — nếu chưa có, **chèn 1 cặp cột mới ngay sau cột G (Tổng Cần)**, TRƯỚC cặp cột của tháng hiện có gần nhất (không phải thêm ở cuối — tháng mới luôn ở bên trái nhất trong nhóm cột tháng), header row 1 ghi đúng định dạng `YYYY-MM` (ví dụ `2026-09`)
2. Với mỗi dòng khoản mục, điền số VND vào cột **Budget** của tháng đó (bỏ qua cột Gợi Ý)
3. Nếu có chi phí một lần phát sinh (one_off) → thêm dòng riêng với `Type=one_off`, điền tên mô tả ở cột A

---

### Bước 2 — Không cần export gì cả

Không còn bước "Download CSV → lưu đè seed". Sau khi finance sửa số trong sheet, sync tự động chạy:

- **02:30 ICT mỗi đêm**: Dagster đọc sheet → validate → ghi lại 2 file seed (`seed_cashflow_budget.csv`, `seed_cash_allocation_policy.csv`)
- **03:00 ICT**: `dbt build` chạy nightly, tự pick up seed mới, refresh toàn bộ mart
- Nếu validate lỗi (ví dụ Dòng Tiền không khớp `__REF`) → sync **không ghi đè** seed cũ, dashboard giữ nguyên số hôm trước, không có gì bị mất

**Muốn refresh ngay lập tức** (không đợi qua đêm) — 1 trong 2 cách:
- Dagster UI (http://localhost:3000) → tìm asset **`sheets/budget_sheet_sync_asset`** → nút **Materialize**
- Hoặc nhờ kỹ thuật chạy lệnh trong container: `python -m ingestion.src.gsheet_budget_sync` (thêm `--dry-run` để xem trước kết quả mà không ghi file)

> Nếu có thay đổi chính sách phân bổ (tab ALLOCATION_POLICY) → cùng 1 lần sync xử lý luôn, không cần thao tác riêng.

---

### Bước 3 — Muốn thấy số ngay thay vì chờ qua đêm

Nightly build (03:00 ICT) đã tự động lo phần dbt — finance **không cần chạy lệnh dbt nào**. Bước này chỉ dành cho trường hợp cần thấy số NGAY trong ngày (ví dụ đang họp, cần demo):

```bash
# Nhờ kỹ thuật chạy trong container data_platform
docker exec -it data_platform bash
dbt build --select +fact_cashflow_budget+ +mart_cashflow_budget_vs_actual+ +mart_cashflow_forecast+ +mart_cashflow_reserve_status+ +mart_cash_surplus_allocation+
```

Điều kiện: phải chạy sync sheet (Bước 2, cách "refresh ngay") **trước** thì seed mới có số mới để `dbt build` đọc.

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

Áp dụng cho khoản **`recurring`** (khoản định kỳ join với sổ cái MISA). Lưu ý: tab `__REF` KHÔNG phải chỗ được tự do thêm tên mới — nó là danh sách `cashflow_line` lấy từ taxonomy sổ cái MISA (`dim_gl_account`). Nếu thêm 1 tên mà MISA không biết, **sync sẽ reject toàn bộ budget sheet** (không chỉ dòng đó) — vì sync validate `recurring` phải khớp chính xác `__REF` để join actual.

Quy trình đúng:

1. Kiểm tra tên dòng tiền mới (ví dụ "Thuê văn phòng") đã tồn tại trong `dim_gl_account.cashflow_line` chưa — nếu chưa chắc, báo kỹ thuật/data team kiểm tra trước
2. Nếu chưa có trong taxonomy MISA → nhờ kỹ thuật xác nhận/thêm vào `dim_gl_account` trước (đây là taxonomy MISA, không sửa được trực tiếp từ Google Sheet)
3. Sau khi taxonomy đã có tên này → thêm dòng mới vào tab **`__REF`**: cột A = Chiều (Thu/Chi), cột B = tên dòng tiền (đúng chính tả taxonomy)
4. Tab **BUDGET_ITEMS** → thêm dòng mới, cột A (Dòng Tiền) chọn đúng tên vừa thêm (dropdown), điền số vào cột Budget tháng cần
5. Không cần chạy dbt thủ công — sync đêm 02:30 sẽ tự nhặt (hoặc trigger thủ công như §2 Bước 2 nếu cần thấy ngay)

> Nếu chỉ là khoản chi một lần/để dành (không phải định kỳ trừ sổ MISA) → dùng `Type=one_off` hoặc `reserve` thay vì `recurring` — không cần đụng tới `__REF`, tên ở cột A là tự do (xem FAQ "Chi phí phát sinh đột ngột").

---

### Q: Chi phí phát sinh đột ngột (mua thiết bị, sửa chữa, v.v.)?

Thêm 1 dòng mới trong tab **BUDGET_ITEMS** với `Type=one_off` (cột D), ví dụ:

| Cột | Giá trị |
|-----|---------|
| A — Dòng Tiền | Mua máy tính cho dev team |
| C — Chiều | Chi |
| D — Type | one_off |
| F — Tuần TT | 2 |
| cột Budget của tháng phát sinh | 85000000 |

Dòng `one_off` chỉ điền số vào cột Budget của đúng tháng phát sinh, các tháng khác để trống — dashboard sẽ hiển thị riêng trong bảng chi tiết. Sync tự nhặt vào lần chạy đêm kế tiếp (hoặc trigger thủ công như Bước 2).

---

### Q: Dòng tiền thực tế vượt kế hoạch lớn (ví dụ đơn hàng lớn bất ngờ)?

Dashboard sẽ tự hiện chênh lệch dương ở cột **Chênh lệch** và tỷ lệ > 100%.  
Nếu muốn ghi nhận vào kế hoạch (để forecast chính xác hơn tháng sau):

- Cập nhật số ở cột **Budget** của tháng đó lên gần với thực tế
- Hoặc để nguyên — chênh lệch là thông tin quản lý hữu ích

---

### Q: Dòng tiền thiếu hụt nghiêm trọng trong tháng — phải làm gì?

1. Dashboard Tab A → xem bảng chênh lệch → xác định dòng hụt nhiều nhất
2. Tab B → xem **Tiền mặt tự do** → đủ bù không?
3. Nếu cần điều chỉnh kế hoạch tháng sau: cập nhật số ở cột **Budget** của dòng bị ảnh hưởng
4. Nếu cần tạm thời hoãn một khoản outflow: đổi cột **E — Tuần TT** sang tuần sau hoặc tháng sau

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
3. Sync sheet đêm qua có chạy thành công không? → Dagster UI kiểm tra asset `sheets/budget_sheet_sync_asset` — nếu FAILED (thường do validate lỗi), số cũ vẫn còn, sửa lỗi trên sheet rồi trigger lại (xem §2 Bước 2)
4. Nếu vẫn trống → kiểm tra Dagster UI: http://localhost:3000 (hoặc nhờ kỹ thuật kiểm tra pipeline)

---

### Q: Muốn xem chi tiết tháng cụ thể?

Dashboard → filter **Kỳ (Period Month)** → chọn tháng → tất cả cards lọc theo tháng đó.  
Bỏ filter để xem tổng lũy kế từ đầu năm (hoặc từ T7/2026 nếu budget bắt đầu từ T7).

---

## 4. Lịch vận hành đề xuất

| Thời điểm | Việc cần làm |
|-----------|-------------|
| **Ngày 1–3 hàng tháng** | Cập nhật budget tháng mới vào Google Sheet (cột Budget) — sửa lúc nào cũng được, không có deadline export |
| **Mỗi đêm 02:30 → 03:00 ICT** | Tự động: sync sheet → seed → `dbt build`. Không cần finance làm gì — số mới nhất xuất hiện trên dashboard sáng hôm sau (T+1) |
| **Ngày 5–10** | Sổ MISA của tháng trước thường chốt xong trong khoảng này → thực tế đầy đủ hơn, ít bị thiếu giao dịch cuối tháng → nên review dashboard sau mốc này để tránh nhìn số thực tế "còn thiếu" |
| **Cuối tháng** | Review chênh lệch, điều chỉnh kế hoạch tháng tới nếu cần (sửa trực tiếp trên sheet, sync tự lo phần còn lại) |

---

**Liên hệ kỹ thuật:** xem log Dagster tại http://localhost:3000 — pipeline `pipeline_sapo_v2_incremental_job` và `pipeline_misa_*`
