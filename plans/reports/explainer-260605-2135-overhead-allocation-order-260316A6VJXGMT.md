# Giải thích chi phí Overhead phân bổ — Đơn `260316A6VJXGMT`

> Mục tiêu: giải thích **vì sao** đơn này gánh **2.133.775 ₫** chi phí vận hành chung (overhead),
> liệt kê đầy đủ **công thức** và **giá trị thật** dùng để ra con số đó.
> Dữ liệu lấy từ tháng **03/2026** (đơn hoàn thành 16/03/2026).

---

## 0. Tóm tắt 1 dòng

> Đơn này **chiếm 1,6286% doanh thu thuần** của tháng 03/2026, nên nó gánh **1,6286%** mỗi pool overhead tính theo doanh thu — cộng thêm **1/154** phần của pool tính theo số đơn. Tổng cộng = **2.133.775 ₫**.

| Chỉ tiêu | Giá trị |
|---|---:|
| Doanh thu thuần đơn (net_revenue) | **7.361.111 ₫** |
| Lãi đóng góp kênh (channel net profit) | 4.161.775 ₫ |
| **− Overhead phân bổ** | **−2.133.775 ₫** |
| **= Lãi ròng đầy đủ (fully-loaded)** | **2.028.000 ₫** (27,55%) |
| Loại phân bổ | **ACTUAL** (số thật từ MISA, không phải ước tính) |

---

## 1. Hai khái niệm nền

**Overhead** = chi phí vận hành chung của cả công ty (thuê nhà, lương quản lý, internet, marketing chung…) — *không* gắn riêng vào một đơn nào. Để biết một đơn lãi/lỗ thật sau khi gánh cả bộ máy, ta phải **phân bổ (allocate)** phần overhead chung này xuống từng đơn.

**Cách phân bổ — pro-rata (chia theo tỷ lệ):** mỗi đơn gánh một phần overhead **tỷ lệ thuận với "mức đóng góp"** của nó. Hệ thống dùng 2 thước đo (base metric):

| Base metric | Ý nghĩa | "Phần" của đơn này |
|---|---|---:|
| `net_revenue` | Chia theo doanh thu thuần | 7.361.111 / 451.983.189 = **1,6286%** |
| `order_count` | Chia đều mỗi đơn 1 suất | 1 / 154 = **0,6494%** |

> 451.983.189 ₫ = tổng doanh thu thuần **154 đơn hoàn thành** trong tháng 03/2026.
> 154 = tổng số đơn hoàn thành tháng 03/2026.

---

## 2. Quy trình tính (2 bước)

```
Sổ cái MISA (tài khoản 642x)
        │   gộp các tài khoản cùng nhóm theo bảng phân loại
        ▼
[Bước 1] POOL — gom chi phí thành 4 "hồ" overhead, mỗi hồ có 1 base metric
        │   pool_net = Σ net_cost các tài khoản keep_* trong pool
        ▼
[Bước 2] ALLOCATE — rải pool_net xuống từng đơn theo tỷ lệ base metric
        │   allocated = pool_net × (phần của đơn)
        ▼
   Overhead của đơn = Σ 4 pool
```

Vì đơn thuộc tháng **03/2026 < tháng hiện tại (06/2026)** nên dùng **nhánh ACTUAL**: lấy thẳng `pool_net` thật của MISA tháng đó (không dùng ước tính trailing).

---

## 3. Bước 1 — Bốn pool overhead tháng 03/2026

Mỗi pool gom 1 hoặc nhiều tài khoản MISA (chỉ những tài khoản gắn nhãn `keep_*`; các tài khoản `drop_*` là chi phí truy được trực tiếp hoặc hàng khuyến mãi đã đếm 1 lần ở chỗ khác → **không** vào pool).

### Pool `admin` — base `net_revenue` — **116.108.474 ₫**
| Tài khoản | Nội dung | net_cost (₫) |
|---|---|---:|
| 6422 | G&A (cước internet, chi phí quản lý chung…) | 107.357.324 |
| 642178 | Hỗ trợ kinh doanh (Zalo Business…) | 5.014.850 |
| 64213 | Phân bổ chi phí trả trước | 1.936.300 |
| 642177 | Phí duy trì tài khoản quản trị | 1.800.000 |
| | **Tổng pool admin** | **116.108.474** |

### Pool `handling` — base `order_count` — **1.050.000 ₫**
| Tài khoản | Nội dung | net_cost (₫) |
|---|---|---:|
| 64211 | Bao bì / đóng gói (màng PE Foam…) | 1.050.000 |

### Pool `marketing` — base `net_revenue` — **11.343.410 ₫**
| Tài khoản | Nội dung | net_cost (₫) |
|---|---|---:|
| 642172 | Quảng cáo Facebook (chung, không truy được về đơn) | 11.343.410 |

### Pool `selling` — base `net_revenue` — **3.146.451 ₫**
| Tài khoản | Nội dung | net_cost (₫) |
|---|---|---:|
| 642175 | Hỗ trợ quảng cáo + phí web EDI | 3.146.451 |

> **net_cost = Nợ − Có (loại trừ bút toán kết chuyển 911).** Tháng 03/2026 các tài khoản này không có phát sinh Có (hoàn nhập) nên net_cost = đúng số Nợ.

---

## 4. Bước 2 — Công thức phân bổ xuống đơn

### Công thức tổng quát (nhánh ACTUAL)

```
allocated_pool = pool_net × order_base / tot_base
```

- `order_base` = giá trị base của đơn (doanh thu thuần đơn, hoặc 1 nếu đếm theo số đơn)
- `tot_base`   = tổng base của toàn bộ đơn hoàn thành trong tháng

### Áp số thật cho từng pool

| Pool | base | pool_net (A) | order_base (B) | tot_base (C) | Phân bổ = A×B/C |
|---|---|---:|---:|---:|---:|
| admin | net_revenue | 116.108.474 | 7.361.111 | 451.983.189 | **1.890.971,58** |
| handling | order_count | 1.050.000 | 1 | 154 | **6.818,18** |
| marketing | net_revenue | 11.343.410 | 7.361.111 | 451.983.189 | **184.741,61** |
| selling | net_revenue | 3.146.451 | 7.361.111 | 451.983.189 | **51.243,89** |
| | | | | **TỔNG** | **2.133.775,26** |

### Cách hiểu nhanh hơn (dùng "phần %")

Ba pool theo doanh thu → đơn gánh đúng **1,6286%** mỗi pool:

```
admin     = 116.108.474 × 1,6286% = 1.890.972 ₫
marketing =  11.343.410 × 1,6286% =   184.742 ₫
selling   =   3.146.451 × 1,6286% =    51.244 ₫
```

Pool handling theo số đơn → chia đều **1.050.000 / 154 đơn**:

```
handling  = 1.050.000 ÷ 154 = 6.818 ₫
```

> 💡 **Vì sao handling chia đều mà không theo doanh thu?** Vì chi phí bao bì/đóng gói gắn với **việc xử lý một đơn**, không phụ thuộc đơn to hay nhỏ — nên mỗi đơn gánh 1 suất bằng nhau là hợp lý hơn.

---

## 5. Kết quả & dòng chảy vào P&L

```
   Σ 4 pool  =  1.890.971,58 + 6.818,18 + 184.741,61 + 51.243,89
             =  2.133.775,26 ₫   ← "Allocated overhead" trên tab Financial

Channel net profit   4.161.775,63 ₫
      − Overhead    −2.133.775,25 ₫
   ─────────────────────────────────
   Fully-loaded net profit  2.028.000,38 ₫   (margin 27,55%)
```

Đây chính là 4 dòng `OVERHEAD` trong bảng **Cost breakdown** (`overhead_admin`, `overhead_handling`, `overhead_marketing`, `overhead_selling`) và dòng **Fully-loaded net profit** ở footer P&L.

---

## 6. Đối chiếu (reconciliation) — số khớp 100%

| Kiểm tra | Kết quả |
|---|---|
| Σ 4 pool phân bổ = `allocated_overhead` trong `fact_order_economics` | 2.133.775,25 ✓ |
| `channel_net_profit − allocated_overhead = fully_loaded_net_profit` | 4.161.775,63 − 2.133.775,25 = 2.028.000,38 ✓ |
| `fully_loaded_net_profit / net_revenue = fully_loaded_margin_pct` | 2.028.000 / 7.361.111 = 27,55% ✓ |
| Mỗi `pool_net` = Σ net_cost tài khoản keep_* (bước 1) | admin 4 tk = 116.108.474 ✓ |

---

## 7. Ghi chú quan trọng

- **ACTUAL vs ESTIMATED:** Đơn này là **ACTUAL** (`is_overhead_estimated = FALSE`) vì tháng 03/2026 đã đóng sổ. Đơn của **tháng hiện tại** sẽ dùng **ước tính** = đơn giá overhead trung bình **3 tháng đã đóng gần nhất** (vì MISA tháng hiện tại chưa chốt) → khi đó badge `estimated` sẽ hiện.
- **Overhead là chi phí PHÂN BỔ, không phải hóa đơn của riêng đơn này.** Nó là ước lượng "phần đóng góp công bằng" của đơn vào chi phí bộ máy → dùng cho **báo cáo lãi/lỗ đầy đủ**, không dùng để quyết định giá/khuyến mãi cho từng đơn (việc đó nhìn **Channel net profit** — trước overhead).
- **Tài khoản `drop_*` bị loại khỏi pool:** ví dụ 64214 (hàng khuyến mãi — đã đếm 1 lần toàn cục), 642174 / 642176 (chi phí truy được trực tiếp về đơn) → tránh đếm trùng.
- **Bảng phân loại tài khoản là SCD2 (có hiệu lực theo thời gian):** hiện tất cả hiệu lực từ 2025-12-01. Nếu sau này một tài khoản đổi pool, hệ thống tự khớp theo tháng phát sinh.

---

## Nguồn dữ liệu (truy vết)

| Số liệu | Model / file |
|---|---|
| net_revenue đơn, số đơn/doanh thu tháng | `fact_orders` |
| pool_net mỗi pool × tháng | `int_overhead_pool_monthly` |
| phân bổ mỗi (đơn × pool) | `int_order_overhead_allocation` |
| 4 dòng OVERHEAD trong ledger | `fact_order_costs` |
| allocated_overhead, fully_loaded_* | `fact_order_economics` |
| net_cost từng tài khoản | `std_misa_account_ledger` ← `misa_raw/account_ledger` (03/2026) |
| account → pool, base, treatment | bảng phân loại gsheet `overhead_account_classification` |

*Công thức tham chiếu: `transformation/models/intermediate/overhead/int_order_overhead_allocation.sql` (nhánh ACTUAL) + `int_overhead_pool_monthly.sql` (định nghĩa pool).*
