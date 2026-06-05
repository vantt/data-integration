# Overhead — Hướng dẫn file phân loại (gsheet) + công thức phân bổ

> Doc tra cứu gộp: cách điền **gsheet `overhead_account_classification`** + **công thức phân bổ overhead** xuống từng đơn → `fully_loaded_net_profit`. Quyết định gốc: `overhead-cost-allocation-design.md` §Quyết định Q1–Q5 (TT133). Nguồn data pool: `overhead-account-ledger-ingestion-design.md` (`std_misa_account_ledger`).

## Bức tranh tổng (3 mảnh ghép)
```
std_misa_account_ledger        gsheet overhead_account_classification
(net_cost theo account×tháng)  (account → treatment/pool/base)
            └────────── JOIN theo account ──────────┘
                              ↓
        Pool từng tháng = Σ net_cost các account 'keep_*' theo pool_id
                              ↓  chia theo base_metric (pro-rata)
        allocated_overhead mỗi đơn  →  fully_loaded_net_profit
```

---

# PHẦN 1 — File phân loại (gsheet `overhead_account_classification`)

Mỗi dòng = 1 tài khoản con (leaf) trong Sổ chi tiết MISA + cách xử lý nó.

| Cột | Là gì | Cách điền |
|---|---|---|
| `account` | Mã TK con (leaf) đúng từ MISA (64211, 642172, 6422…). **KHÓA NỐI** với data ledger. | Khớp **chính xác** mã trong file |
| `account_group` | Nhóm cha: `6421` (bán hàng) / `6422` (QLDN). Chỉ để gom/báo cáo. | Suy từ prefix |
| `treatment` ⭐ | **Quyết định chính** — account làm gì trong P&L (6 giá trị, xem dưới). | Chọn 1 |
| `pool_id` | Tên "túi" gom account cùng loại → cộng thành 1 pool, chia theo cùng base. | Chỉ khi `keep_*` (vd `admin`/`handling`/`marketing`) |
| `base_metric` | **Cách chia** pool xuống đơn. | Chỉ khi `keep_*`: `net_revenue` \| `order_count` \| `gross_profit` |
| `channel` | Gán pool vào 1 kênh cụ thể (cho ads-theo-sàn). | **v1 để TRỐNG** (chia chung); v2 mới dùng |
| `effective_from` | Ngày bắt đầu áp dụng dòng này (YYYY-MM-DD) — để có lịch sử. | vd `2025-12-01` |
| `effective_to` | Ngày hết hiệu lực. **TRỐNG = còn áp dụng.** | Đổi phân loại → điền `effective_to` dòng cũ + thêm dòng mới |
| `note` | Ghi chú tự do (mô tả/lý do/"cần review"). | Tùy ý |

## `treatment` — 6 giá trị
| Giá trị | Nghĩa | Vào pool? |
|---|---|---|
| `keep_admin` | Chi phí quản lý chung (G&A) | ✅ pool Admin → `net_revenue` |
| `keep_handling` | Chi phí xử lý đơn (bao bì…) | ✅ pool Handling → `order_count` |
| `keep_marketing` | Quảng cáo | ✅ pool Marketing → `net_revenue` (dedup vs `gsheet_marketing_spend`) |
| `keep_selling` | Chi phí bán hàng chung khác | ✅ pool Selling |
| `drop_traceable` | **LOẠI** — đã tính tier-2 (phí sàn/ship/payment từ Shopee) → tránh đếm 2 lần | ❌ |
| `drop_promo_count_once` | **LOẠI** — hàng tặng đã tính ở `promo_goods_cost` (Sapo-MAC) → count-once | ❌ |

## Map sơ bộ (từ file mẫu — CHỐT cuối sau reconcile phase-04)
| account | treatment | pool / base | ghi chú |
|---|---|---|---|
| 64211 | keep_handling | handling / order_count | bao bì (màng PE, carton) |
| 64213 | keep_admin | admin / net_revenue | khấu hao trả-trước (offset 2421/2422), G&A — ✅ chốt |
| 64214 | drop_promo_count_once | — | hàng tặng (100% offset 156/kho, XK; đã ở tier-2a Sapo-MAC) — ✅ chốt |
| 642172 | keep_marketing | marketing / net_revenue | quảng cáo FB (dedup gsheet) |
| 642174 | drop_traceable | — | hoa hồng + phí xử lý GD (tier-2) |
| 642175 | keep_selling | selling / net_revenue | bundled (loyalty KHTT 49% + ad co-op/WAON 42% + EDI 9%) — ✅ chốt keep_selling (không marketing: né mislabel + dedup thừa) |
| 642176 | drop_traceable | — | phí vận chuyển (tier-2) |
| 642177 | keep_admin | admin / net_revenue | duy trì TK quản trị |
| 642178 | keep_admin | admin / net_revenue | hỗ trợ KD (Zalo Biz, in card) |
| 6422 | keep_admin | admin / net_revenue | G&A (internet, thuê bao) |

## Quy tắc bảo trì
- **Account mới xuất hiện trong data mà CHƯA có trong gsheet** → pipeline cảnh báo "chưa phân loại" + KHÔNG tự đưa vào/ra pool. → bạn thêm dòng.
- **Đổi phân loại 1 account** → đừng sửa đè: điền `effective_to` dòng cũ + thêm dòng mới (`effective_from` mới). Giữ lịch sử.

---

# PHẦN 2 — Công thức phân bổ

## Bước 1 — Dựng POOL từng tháng
Với mỗi `(pool_id, tháng)`:
```
pool(pool_id, month) = Σ std_misa_account_ledger.net_cost
                       WHERE account ∈ (các account 'keep_*' có pool_id đó, theo effective dates)
                         AND period_month = month
```
(net_cost = `Nợ − Có-loại-911`, xem ingestion doc §5.)

## Bước 2 — Chia pool xuống đơn (pro-rata theo base)
```
allocated_overhead(đơn) = Σ_qua_các_pool [ pool(pool_id, month_của_đơn)
                            × ( base_metric_của_đơn / Σ base_metric_toàn_bộ_đơn_trong_month ) ]
```
- Mẫu số = tổng base của **đơn ĐÃ FULFILLED** trong tháng đó (Q5: đơn hủy-trước-giao không vào mẫu số).
- Mỗi pool dùng `base_metric` của nó (admin→net_revenue, handling→order_count…).
- 1 đơn nhận tổng từ **nhiều pool** cộng lại.

## Bước 3 — Closure (kiểm tra bắt buộc)
```
Σ allocated_overhead (mọi đơn trong tháng) == Σ pool(các pool, tháng)   ← dbt test
```
Lệch = sai (không được tạo thêm / làm mất tiền).

## Ví dụ cụ thể (tháng 3)
Pool Admin = **100,000,000₫**; Pool Handling = **600,000₫**. Toàn bộ đơn T3: tổng doanh thu = **2,000,000,000₫**, số đơn = **1,000**.
→ rate Admin = 100M/2,000M = **5% doanh thu**; rate Handling = 600,000/1,000 = **600₫/đơn**.

| Đơn | Doanh thu | Admin (5%×DT) | Handling (chia đều) | Σ overhead |
|---|---|---|---|---|
| A (to) | 10,000,000 | 500,000 | 600 | 500,600 |
| B (nhỏ) | 100,000 | 5,000 | 600 | 5,600 |

→ Admin: đơn to gánh gấp 100× đơn nhỏ (theo doanh thu). Handling: **bằng nhau** (đóng gói tốn như nhau). **Đó là lý do tách 2 pool 2 base** (Q3) — tránh đơn nhỏ bị tính thiếu chi phí xử lý.

## Kết quả waterfall
```
channel_net_profit  − allocated_overhead  =  fully_loaded_net_profit
```

---

# PHẦN 3 — Ước tính trong tháng (provisional, Q4-B)

**Vấn đề:** pool THẬT tháng M chỉ có đầu tháng M+1 (sau MISA chốt sổ + export). Trong tháng M phải hiện gì?

**Giải pháp = ước tính theo rate THÁNG TRƯỚC, rồi ghi đè khi số thật về:**
- **Trong tháng M:** mỗi pool dùng **rate thực của 1–3 tháng đã chốt gần nhất** áp cho đơn tháng M. Cờ `is_overhead_estimated = true`.
  - rate Admin = pool_admin(tháng trước) / doanh-thu(tháng trước); rate Handling = pool_handling(tháng trước) / số-đơn(tháng trước).
- **Đầu tháng M+1 (export về):** tính lại bằng pool THẬT → **GHI ĐÈ** tháng M; cờ → `false`. **KHÔNG** book variance, **KHÔNG** sửa tháng đã chốt trước đó.
- **Tháng đầu tiên (chưa có lịch sử):** dùng `budgeted_rate` nhập tay, hoặc để trống (chỉ hiện `channel_net_profit`).

**Vì sao ổn:** `fully_loaded` là số **báo cáo**, KHÔNG dùng quyết định nhận/đẩy đơn (quyết định dùng `channel_net_profit`, đã chính xác realtime). Ước tính có **cờ rõ** + tự cập nhật → ~1.2× phức tạp, không phải true-up đầy đủ.

---

## Việc còn phải làm (phase-04)
1. Chốt 3 dòng treatment treo: `64213` (phân bổ gì), `642175` (mixed), `64214` (đúng hàng tặng?).
2. **Reconcile** 64214 (103M) vs sales-ledger-642 (1.08B) vs Sapo-MAC promo — tie-out count-once.
3. Dedup marketing 642172/642175 vs `gsheet_marketing_spend`.
4. Build model `int_order_overhead_allocation` (pool + pro-rata + provisional) + closure test + `fully_loaded_net_profit`. Verify Dagster.
