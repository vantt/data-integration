---
title: Phân bổ Chi phí Quản lý DN vào Lãi/Lỗ theo Đơn (Overhead Allocation)
status: draft
last_modified: 2026-06-03
domain_refs: [domains/finance.md]
related_designs: [order-pl-schema-design.md, discount-classification.md]
---

# Phân bổ Chi phí Quản lý DN vào Lãi/Lỗ theo Đơn

## Mục tiêu

Mở rộng P&L theo đơn từ **lãi đóng góp cấp kênh** (`channel_net_profit`, đang có) xuống
**lãi ròng đầy đủ** (`fully_loaded_net_profit`) bằng cách phân bổ chi phí quản lý DN
(TK 642, có thể gồm 635 và phần 641 chung) xuống từng đơn — để mỗi đơn "gánh chung" bộ máy.

> Đây là bài toán *cost absorption / phân bổ chi phí gián tiếp*. Nổi tiếng dễ làm sai.
> Tài liệu này ghi nhận **các bẫy phải tránh**, **cách phân bổ**, **nguồn dữ liệu**, và
> **cách gắn vào pipeline hiện có** trước khi lên plan triển khai.

---

## 0. Cảnh báo tư duy quan trọng nhất — GIỮ 2 TẦNG LÃI TÁCH BẠCH

Chi phí quản lý DN gần như **cố định trong kỳ** (thuê VP, lương quản lý/kế toán, phần mềm,
khấu hao). Phân bổ xuống đơn hợp lý để **báo cáo**, nhưng **nguy hiểm nếu dùng để ra quyết định**
vận hành. Hai bẫy kinh điển:

- **Bẫy "đơn lỗ nên bỏ":** từ chối một đơn "lỗ sau phân bổ" → chi phí quản lý **không giảm**,
  chỉ **dồn sang đơn khác**. Quyết định nhận/từ chối/đẩy kênh phải dựa trên
  **lãi đóng góp (contribution > 0)**, không phải lãi ròng sau phân bổ.
- **Death spiral:** rải overhead theo doanh thu → cắt sản phẩm "lỗ" → overhead dồn sang phần
  còn lại → chúng thành "lỗ" → cắt tiếp → vô tận.

**Ràng buộc thiết kế bắt buộc:** giữ `channel_net_profit` (contribution) làm **cột riêng,
KHÔNG ghi đè**; chỉ **thêm** cột `fully_loaded_net_profit` bên dưới. Báo cáo phải hiển thị cả hai.

---

## 1. Waterfall mục tiêu

```
net_revenue (đã bóc VAT — Sapo VAT-inclusive: net = total − total_tax)
  − COGS (TK632, MISA)                          → gross_profit            [ĐÃ CÓ]
  − phí sàn / ship / payment (TK641 trực tiếp)
  − chiết khấu shop gánh                          → channel_net_profit      [ĐÃ CÓ] ★ MỐC QUYẾT ĐỊNH
  ────────────────────────────────────────────────
  − overhead phân bổ (TK642 + 635 + 641 chung)   → fully_loaded_net_profit [MỚI]   ★ MỐC BÁO CÁO
```

Trạng thái hiện tại (xem [order-pl-schema-design.md](order-pl-schema-design.md)):
- `fact_order_economics` dừng ở `channel_net_profit` / `channel_net_margin_pct`.
- `fact_order_costs` là sổ long-format: 1 dòng / (order_id, cost_type),
  `cost_category` ∈ {COGS, PLATFORM_FEE, TAX, SHIPPING, DISCOUNT}, amount luôn dương.

---

## 2. Những vấn đề phải lưu tâm

| # | Vấn đề | Hệ quả & cách xử lý |
|---|--------|---------------------|
| 1 | **Cố định vs biến đổi** | Giữ contribution tách bạch; đừng quyết định trên số đã phân bổ (xem §0). |
| 2 | **Chi phí kỳ vs giao dịch** | 642 là số **tháng**, chốt trễ (đầu tháng sau). Realtime phải dùng **rate dự toán (budgeted)**; sau khi MISA chốt sổ thì **true-up** về thực tế. Cần cờ `is_estimated`. |
| 3 | **Phải khớp MISA (closure)** | Tổng overhead phân bổ cho **mọi đơn trong kỳ = đúng số TK642 thực tế** của kỳ. ⇒ phân bổ **theo tỷ trọng** (`base_đơn / tổng_base_kỳ × pool`) để **tự động khớp**. Cách "rate cố định × số đơn" **không tự khớp** → cần dòng chênh lệch. |
| 4 | **Mẫu số biến động** | `642_tháng / số_đơn_tháng`: tháng ít đơn → mỗi đơn gánh nặng oan. Dùng **rate trượt 3–6 tháng** hoặc **dự toán năm** để mượt. |
| 5 | **VAT** | Doanh thu Sapo **VAT-inclusive**; chi phí 642 trên MISA thường ghi **net** (VAT vào TK133). So sánh **cùng cơ sở**: `net_revenue` (đã bóc VAT) đối với overhead net. Đừng trộn gross/net. |
| 6 | **Double-count** | Pool overhead **không** chứa cái đã nằm trong COGS (632) hay phí trực tiếp (641 ship/sàn). Pool = 642 thuần + phần 641 **không trace được** + 635 (nếu chọn). Map TK rõ ràng. |
| 7 | **Trace trước, allocate sau** (vàng) | Gán trực tiếp cái gì gán được (ads Shopee → Shopee; lương kho → theo số kiện). **Chỉ rải** phần G&A thực sự chung (giám đốc, kế toán, thuê VP). |
| 8 | **Đơn hủy/hoàn** | Chốt rõ base: chỉ đơn `completed` gánh, hay gồm đơn hủy? Khuyến nghị base = đơn hợp lệ. |
| 9 | **Làm tròn (residual)** | Tổng sau làm tròn phải = pool. Gán phần dư vào đơn lớn nhất hoặc 1 dòng điều chỉnh. |
| 10 | **Quản trị config** | Quy tắc phân bổ phải có **version/lịch sử** để tái lập báo cáo cũ. |

---

## 3. Cách phân bổ — chọn base nào?

| Base | Hợp khi overhead chủ yếu do… | Nhược |
|------|------------------------------|-------|
| **Doanh thu thuần** | (mặc định SME VN, đơn giản nhất) | Đơn giá trị cao gánh nhiều dù ít công |
| **Lãi gộp (gross_profit)** | "ai khỏe gánh nhiều" — công bằng theo khả năng chịu | Đơn margin mỏng nhẹ gánh (đôi khi đúng ý) |
| **Số đơn (flat/đơn)** | xử lý giao dịch: kế toán, CSKH, đóng gói cơ bản | Đơn nhỏ và lớn gánh như nhau |
| **Số lượng món/kiện** | kho, soạn hàng, đóng gói (cần line-item — đã có) | Phức tạp hơn |

**Khuyến nghị (ABC-lite):** tách 642 thành vài **sub-pool theo cost driver**, mỗi pool một base:

- Pool **kho/vận hành** → theo **số lượng món/kiện**
- Pool **văn phòng/G&A** (giám đốc, kế toán, thuê VP, phần mềm) → theo **doanh thu** hoặc **lãi gộp**
- Pool **tài chính** (635 lãi vay, phí NH) → theo **tiền thu** (`total_collected`)

**KISS cho v1:** bắt đầu **1 pool, base = lãi gộp hoặc doanh thu, closure-based**; thiết kế bảng
config cho phép **tách pool sau** mà không sửa model. Việc duy nhất bắt buộc ngay từ đầu là
**tách `channel_net_profit` (contribution) khỏi `fully_loaded_net_profit`**.

### Công thức (closure-based)

Với mỗi `(kỳ_tháng × pool)`:

```
overhead_đơn = base_đơn / SUM(base_đơn trong kỳ) × pool_kỳ_thực_tế
```

Tự động khớp closure: `SUM(overhead_đơn) = pool_kỳ`. Xử lý residual làm tròn (§2.9).

---

## 4. Nguồn dữ liệu — MISA hay Google Sheet? → **Cả hai, mỗi cái một vai**

| | **MISA** | **Google Sheet** |
|---|---|---|
| Vai trò | **Nguồn chân lý số THỰC** + mỏ neo đối soát (closure) + true-up | **Tầng cấu hình & giả định** do người nhập |
| Cấp | TK642/641/635 theo **tháng**, theo TK | Quy tắc phân bổ, rate dự toán, chi phí MISA chưa ghi |
| Ưu | Chính xác, khớp BCTC, có kiểm toán | Linh hoạt, realtime, dễ sửa |
| Nhược | Chốt trễ, chi tiết tháng, cần API/export | Thủ công, dễ sai, cần version |

**Mô hình lai:**
- **MISA → `overhead_costs_monthly`** (seed/source): số thực 642/635/641-chung theo tháng × TK.
  MISA AMIS có API; nếu không → export Sổ cái / Bảng cân đối phát sinh TK642 theo tháng rồi ingest.
  Dùng để **đối soát closure** + **true-up**.
- **Google Sheet → `overhead_allocation_config`** (seed): (a) **rate dự toán** tháng hiện tại chưa
  chốt sổ, (b) **quy tắc phân bổ** (pool → base, trọng số kênh), (c) chi phí nội bộ MISA chưa kịp ghi.

---

## 5. Gắn vào pipeline hiện có

Kiến trúc đã sẵn chỗ — thay đổi gọn:

### 5.1 `fact_order_costs` (mở rộng)
Thêm rows:
- `cost_category = 'OVERHEAD'`
- `cost_type ∈ {overhead_admin, overhead_logistics, overhead_finance}`
- `source_system ∈ {misa, gsheet}`
- `fee_source = 'allocated'` (**giá trị mới**, phân biệt với `'actual'`)
- thêm cờ `is_estimated` (budgeted vs đã true-up)

Đúng pattern long-format amount-dương sẵn có — không phá schema.

### 5.2 `fact_order_economics` (mở rộng)
Thêm cột (giữ nguyên cột cũ):
- `allocated_overhead`
- `fully_loaded_net_profit = channel_net_profit − allocated_overhead`
- `fully_loaded_margin_pct`
- `is_overhead_estimated`

### 5.3 Model mới
- `int_order_overhead_allocation` — với mỗi `(tháng × pool)` tính
  `base_đơn / tổng_base_kỳ × pool_kỳ`; phát ra rows OVERHEAD.
- Seeds/sources: `overhead_costs_monthly` (MISA), `overhead_allocation_config` (Google Sheet).
- Test đối soát: `SUM(allocated_overhead theo kỳ) == pool_kỳ` (closure assertion).

### 5.4 Sơ đồ luồng

```
MISA (642/635/641-chung, tháng × TK)  ─┐
                                       ├─→ int_order_overhead_allocation ─→ fact_order_costs (rows OVERHEAD)
Google Sheet (config + budgeted rate) ─┘                                 └─→ fact_order_economics (fully_loaded_*)
            ▲                                                                         │
            └──────────────────  closure / true-up đối soát theo kỳ  ────────────────┘
```

---

## 6. Vietnamese chart-of-accounts mapping (tham chiếu)

| TK | Tên | Vai trò trong P&L đơn |
|----|-----|------------------------|
| 511 | Doanh thu | `gross_revenue` / `net_revenue` (Sapo, VAT-inclusive) |
| 632 | Giá vốn hàng bán | COGS — **đã có** (MISA) |
| 641 | Chi phí bán hàng | ship/sàn/payment **trace được** → trực tiếp; phần chung → pool overhead |
| 642 | Chi phí quản lý DN | **pool overhead chính** (phân bổ) |
| 635 | Chi phí tài chính | lãi vay, phí NH → pool finance (nếu chọn) |
| 133 | Thuế GTGT đầu vào | giải thích vì sao chi phí MISA ghi net |

---

## Câu hỏi còn mở (cần chốt trước khi lên plan)

1. **MISA**: có API (AMIS) hay export thủ công? Chốt sổ 642 trễ bao lâu sau cuối tháng?
2. **Phạm vi pool**: chỉ TK642, hay gồm 635 (lãi vay) + phần 641 chung không trace được?
3. **Base ưu tiên**: 1 pool theo doanh thu (đơn giản) / theo lãi gộp / ABC-lite nhiều pool ngay?
4. **Realtime hay không**: cần số ngay trong tháng (budgeted + true-up) hay chỉ báo cáo
   **sau khi chốt sổ** là đủ? (Quyết định độ phức tạp ~gấp đôi.)
5. **Đơn hủy/hoàn** có gánh overhead không?

## Phase-01 — chốt schema ingestion (pre-work cho phase-04, CHƯA implement)

Std-gate đã xong (`std_misa_sales_lines` live, verified Dagster 2026-06-04). Hai nguồn overhead dưới đây đã chốt **schema**, nhưng **ingestion hoãn tới phase-04** (chờ trả lời Q1: MISA AMIS API hay export thủ công).

**`overhead_costs_monthly`** (pool số tiền overhead theo tháng — nguồn MISA):
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `period_month` | DATE | ngày đầu tháng |
| `account` | VARCHAR | TK642 / 635 / 641-chung |
| `amount` | BIGINT | VND, **net VAT** |
| `source` | VARCHAR | `'misa_amis'` (API) \| `'misa_export'` (thủ công) |
| `ingested_at` | TIMESTAMPTZ | |
- Partition `year=YYYY/month=M`. **COUNT-ONCE:** pool này PHẢI loại phần 642 promo đã nằm ở sales-ledger (tier-2 `promo_goods_cost`) — xem CONTRACT plan §4.

**`overhead_allocation_config`** (GSheet — pattern `gsheet_marketing_spend.py`):
| Cột | Kiểu |
|---|---|
| `pool_id` / `pool_name` | VARCHAR |
| `account_pattern` | VARCHAR (vd `'642%'`) |
| `base_metric` | VARCHAR (`net_revenue`\|`gross_profit`\|`order_count`) |
| `channel_weight` / `budgeted_rate` | DECIMAL |
| `effective_from` / `effective_to` | DATE |
| `version` | INTEGER |
- Env `SOURCES__SPREADSHEET_URL__OVERHEAD_CONFIG` → parquet → `src_overhead_allocation_config`. Giữ `version`/`effective_*` cho lịch sử config.

**Chặn (blocker phase-04):** Q1 (API vs export) + Q2-Q5 ở trên phải chốt với user trước khi build ingestion + `int_order_overhead_allocation`.
