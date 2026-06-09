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

1. **MISA**: có API (AMIS) hay export thủ công? Chốt sổ 642 trễ bao lâu sau cuối tháng? → ✅ **ĐÃ CHỐT (v1)** — xem §"Quyết định Q1" dưới.
2. **Phạm vi pool**: chỉ TK642, hay gồm 635 (lãi vay) + phần 641 chung không trace được? → ✅ **ĐÃ CHỐT (v1)** — xem §"Quyết định Q2" dưới.
3. **Base ưu tiên**: 1 pool theo doanh thu (đơn giản) / theo lãi gộp / ABC-lite nhiều pool ngay? → ✅ **ĐÃ CHỐT (v1)** — xem §"Quyết định Q3" dưới.
4. **Realtime hay không**: cần số ngay trong tháng (budgeted + true-up) hay chỉ báo cáo
   **sau khi chốt sổ** là đủ? (Quyết định độ phức tạp ~gấp đôi.) → ✅ **ĐÃ CHỐT (v1 = B)** — xem §"Quyết định Q4" dưới.
5. **Đơn hủy/hoàn** có gánh overhead không? → ✅ **ĐÃ CHỐT (v1)** — xem §"Quyết định Q5" ngay dưới.

## Quyết định Q1 — Nguồn overhead: MISA API hay export thủ công? (CHỐT v1, 2026-06-04)

### Câu hỏi
Pool TK642 (và sau này 641-common) lấy từ **MISA AMIS API** hay **export Sổ cái thủ công**?

### 🎯 Quyết định v1
> **v1 = export THỦ CÔNG.** Xuất Sổ cái TK642 từ MISA → CSV/XLSX → ingest theo pattern `gsheet_marketing_spend.py` (file-drop → `src_` → `stg_`). `source = 'misa_export'`.
> - **Cadence:** export *sau khi MISA chốt sổ* tháng → khớp tự nhiên với Q4 (closure-only).
> - **Estimate tạm:** khi chưa có export tương ứng (tháng chưa chốt / kỳ thiếu data) → dùng rate ước tính (xem Q4 — provisional) thay vì để trống.
> - **API (AMIS) = v2** nếu khối lượng/tần suất tăng — không làm v1 (YAGNI).

### Hệ quả & TODO
- Ingestion idempotent, partition `year/month`; manual drop → re-ingest an toàn.
- Manual + post-closure ⇒ **fit tự nhiên Q4 closure-only** (data vốn về theo đợt sau chốt sổ).
- 📌 **TODO (cần trước khi build phase-04):** lấy **1 export Sổ cái TK642 thật** để (a) xác nhận count-once overlap với sales-ledger-642 (~1.08B promo), (b) seed dữ liệu lịch sử + xác định độ trễ chốt sổ thực tế.

## Quyết định Q2 — Phạm vi pool overhead (CHỐT v1, 2026-06-04)

### Câu hỏi
Pool overhead phân bổ xuống đơn (tier-3) gồm những tài khoản nào: chỉ TK642, hay thêm 635 (lãi vay) + phần 641 chung?

### Nguyên tắc xương sống: COUNT-ONCE + match-to-purpose
Pool chỉ chứa chi phí **(a) thật, (b) chung/không trace được xuống đơn, (c) CHƯA bị tính ở tier-2**. Bất cứ gì đã là direct cost tier-2 (ship, phí sàn, phí thanh toán) **tuyệt đối không** vào pool — count-once, giống rule 642-promo.

| TK | Tên | Bản chất |
|---|---|---|
| **642** | Chi phí quản lý DN (G&A) | Lương quản lý, thuê VP, khấu hao admin, phần mềm, kế toán/pháp lý → **chung, không trace được** |
| **641** | Chi phí bán hàng | (a) *traceable* = ship/phí sàn/phí thanh toán → **ĐÃ ở tier-2**; (b) *common* = lương sales cứng, marketing thương hiệu, showroom |
| **635** | Chi phí tài chính | Chủ yếu **lãi vay**, lỗ tỷ giá |

### ⚠️ CẬP NHẬT TT133 (2026-06-05) — sổ công ty dùng Thông tư 133
Sổ công ty = **TT133** → **KHÔNG có TK641 riêng**; `TK642 = "Chi phí quản lý kinh doanh"` tách đúng 2 con:
- **6421 = Chi phí bán hàng** (lương sales, marketing/quảng cáo, ship khách, phí sàn, hoa hồng, bao bì, showroom…)
- **6422 = Chi phí quản lý DN / G&A** (lương admin, thuê VP, khấu hao admin, phần mềm, kế toán…)

⇒ "642-only" ban đầu **mơ hồ** (gồm cả 6421 bán hàng, có phần đã ở tier-2). Quyết định dưới **sửa theo TT133**: pool sạch = **6422**; **6421** phải deep-dive. Phần "Phán quyết 641-common" bên dưới giờ áp cho **6421**.

### Phán quyết từng tài khoản
- **TK642 → CÓ (lõi pool).** Nhưng phải là **642 tiền mặt G&A thật, đã LOẠI phần 642-promo** nằm trong sales-ledger (đã thành `promo_goods_cost` tier-2). Count-once cốt tử.
- **TK635 → KHÔNG.** Lãi vay là **quyết định tài chính** (cấu trúc vốn), không phải vận hành. Operating profit đo *trước* lãi vay; nhét vào per-order sẽ bóp méo so sánh vận hành giữa 2 DN khác mức vay. `fully_loaded` là số hiệu quả vận hành, không phải định giá DN. *Nếu* sau này cần view cost-of-capital → làm **layer riêng có nhãn** (vd "cost of capital on inventory"), KHÔNG trộn vào G&A.
- **TK641-common → CÓ về nguyên tắc, NHƯNG defer v1** vì rủi ro double-count: nếu sổ 641 MISA không tách sạch *traceable* (ship/sàn — đã ở tier-2) khỏi *common* (lương/quảng cáo) → dễ tính 2 lần phí ship/sàn.

### 🎯 Quyết định v1 (TT133)
> **Pool sạch v1 = TK6422 (G&A thuần)**, base `net_revenue`. Không trace, không ở tier-2 → zero double-count → ship ngay khi có export.
> **6421 (bán hàng) — KEEP set (đưa vào pool SAU deep-dive), LOẠI phần traceable:**

| 6421 item | Xử lý | Pool / base |
|---|---|---|
| Phí sàn / ship khách / phí thanh toán / affiliate / chiết khấu | **LOẠI** (đã tier-2, count-once) | — |
| **Bao bì / đóng gói chung** | KEEP | Handling → **`order_count`** |
| **Lương NV bán hàng** | KEEP | Selling-common → `net_revenue` (hoặc order_count) |
| **Showroom / mặt bằng bán hàng** | KEEP | `net_revenue`; hoặc gán riêng channel offline |
| **Quảng cáo / marketing** | KEEP (tách nguồn ↓) | brand → `net_revenue`; ads-theo-sàn → **gán channel đó** |

> **−635 (lãi vay): để NGOÀI** (financing; layer cost-of-capital riêng chỉ khi cần).

### ⚠️ Marketing — tách nguồn BẮT BUỘC (2 lý do)
1. **Dedup vs `gsheet_marketing_spend`:** ad spend có thể vừa ở gsheet vừa book 6421 → đếm 2 lần. Đối chiếu, chỉ lấy phần KHÔNG trùng.
2. **Ads-theo-sàn gán đúng kênh** (Shopee/Lazada/TikTok Ads → đơn của CHÍNH kênh đó, channel-weighted), KHÔNG rải đều; brand-chung → `net_revenue`.

### 📌 TODO (cần Sổ cái 6421 chi tiết để mở keep-set)
- [ ] Lấy Sổ cái/sub-account **TK6421** đủ chi tiết (diễn giải/đối tượng) → phân loại từng dòng theo bảng trên.
- [ ] **Đối chiếu marketing**: `gsheet_marketing_spend` vs phần quảng cáo trong 6421 → xác định trùng, loại phần trùng.
- [ ] Tách **ads-theo-sàn** vs **brand-chung** trong 6421.
- [ ] Xác nhận **promo-goods (hàng KM)** dưới TT133 book vào 6421 hay 6422 → cho count-once 642-promo (`int_promo_642_monthly_total`).
- [ ] (Tùy) 635 tài trợ tồn kho → layer cost-of-capital riêng (KHÔNG vào G&A).

**Trạng thái:** CHỐT v1 = **6422-only** (pool sạch, ship ngay khi có export). **6421-keep set** = lộ trình ngay-sau (cần Sổ cái 6421 chi tiết). 635 ngoài. Cột `account` trong `overhead_costs_monthly` vẫn nhận account khác để mở rộng.

---

## Implementação — Decisions Made (Phase 01–04, chốt 2026-06-09)

Phần này ghi nhận những gì **thật sự được build** so với design ở trên, phục vụ tái lập báo cáo + audit sau này.

### Schema thực tế — `stg_overhead_account_classification` (GSheet seed)

Cấu trúc **làm việc** khác design một chút vì SCD2 + flexibility config:

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `account` | VARCHAR | MISA leaf sub-account (vd `64213`, `642171`, `64214`). KHÔNG cast sang INTEGER — dùng VARCHAR để bảo toàn `_` ở composite ids. |
| `account_group` | VARCHAR | Nhóm (vd `'6421'`, `'6422'`), dùng cho reporting/grouping. |
| **`treatment`** | VARCHAR | ✅ **Enum hoạt động:** `'keep_admin'`, `'keep_handling'`, `'keep_marketing'`, `'keep_selling'`, `'drop_traceable'`, `'drop_promo_count_once'`. |
| **`pool_id`** | VARCHAR | ID tên pool — v1 = `'admin_pool'` chỉ; v2+ (6421) mở thêm `'handling_pool'`, `'selling_pool'`, `'channel_ads_pool'`. |
| **`base_metric`** | VARCHAR | ✅ `'net_revenue'` (v1) hoặc `'order_count'` (v2+). Không `'gross_profit'` — loại per design §Q3. |
| `channel` | VARCHAR | (NULL v1). Khi bật channel-ads: channel-code (vd `'shopee'`, `'tiktok'`) để weight allocation. |
| `effective_from` / `effective_to` | DATE | SCD2: config active từ `effective_from` đến `effective_to` (NULL = mở). Cho phép repoint account này sang pool khác qua thời gian. |
| `note` | VARCHAR | Diễn giải (vd "G&A thuần" vs "handling-only bao bì"). |
| `ingest_method` | VARCHAR | Provenance (vd `'gsheet_manual'`, `'misa_api'`). |

**Source:**  
Loaded từ `overhead_account_classification_raw` (Google Sheets) via `src_overhead_allocation_config` pattern. Nếu API MISA khả dụng sau này → thêm `ingest_method='misa_api'`.

### Model chain — Intermediate + Mart

**`int_overhead_pool_monthly`** (grain = 1 row per pool × month):
- **Input:** `std_misa_account_ledger` (net_cost per account-month) + `stg_overhead_account_classification` (SCD2 treatment rules)
- **Logic:** Effective-dated join — match `period_month` vào classification row active (date predicate `period_month >= effective_from AND period_month <= effective_to`)
- **Filter:** `WHERE treatment LIKE 'keep_%'` — loại `drop_*` ngay tại pool stage (đừng cộng lại sau)
- **Output columns:** `pool_id`, `base_metric`, `period_month`, **`pool_net`** (SUM net_cost), `n_accounts`
- **Closure property:** Pool_net âm/dương; SUM(pool_net) across orders = pool thực tế MISA (tự khớp bằng design).

**`int_order_overhead_allocation`** (grain = 1 row per order × pool):
- **Two branches (actual vs estimated):**
  - **ACTUAL:** `period_month < current_date (ICT)` → pro-rata từ `int_overhead_pool_monthly.pool_net` thực tế
  - **ESTIMATED:** `period_month >= current_date` → dùng trailing N=3 closed-month rate, cờ `is_overhead_estimated=TRUE`
- **Fulfilled-order rule (§Q5):** Order phải `first_shipped_at IS NOT NULL OR status = 'COMPLETED'`
- **Output columns:** `order_code`, `pool_id`, `period_month`, `base_metric`, **`allocated_amount`** (VND), **`is_overhead_estimated`** (BOOLEAN)

### Cột mới trong `fact_order_economics` — Tier-3 fully-loaded (Phase-04)

| Cột | Công thức | Ghi chú |
|---|---|---|
| **`allocated_overhead`** | `SUM(int_order_overhead_allocation.allocated_amount)` | NULL nếu không có pool matching. |
| **`is_overhead_estimated`** | `BOOL_OR(int_order_overhead_allocation.is_overhead_estimated)` | TRUE nếu bất kỳ pool nào là estimate (tháng chưa chốt). |
| **`fully_loaded_net_profit`** | `channel_net_profit − allocated_overhead` | NULL nếu allocated_overhead IS NULL. **REPORT-ONLY** — không dùng để accept/reject đơn. |
| **`fully_loaded_margin_pct`** | `fully_loaded_net_profit / net_revenue` | NULL khi net_revenue=0 hoặc allocated_overhead NULL. |

**Ví dụ:**
```
order_code | date_key | net_revenue | cogs | channel_net_profit | allocated_overhead | fully_loaded_net_profit
ABC123     | 20260601 |  1,000,000  | 600k |     350,000        |       80,000       |    270,000            [35% margin → 27%]
XYZ456     | 20260610 |     50,000  |  30k |      15,000        |       12,000       |      3,000            [30% margin → 6%] — bị under-cost đơn nhỏ
```

### COUNT-ONCE Verification — Zero Double-Count ✅

**Thực tế kiểm chứng (2026-06-09):**

- **`std_misa_account_ledger` TK64214 (G&A promo):** 103.11M VND (139 XK rows)
- **`std_misa_sales_lines` (promo lines, tied MISA→Sapo):** 62.7M VND
- **Confirmed counted-once (matched MISA→Sapo order):** 60.34M VND ✅
- **Confirmed under-counted (gifting / MISA-internal, không ở Sapo):** ~29.1M VND (accepted, documented trong promo-count-once-reconciliation.md)
- **Zero overlap / double-count verified:** Account 64214 excluded từ pool via `drop_promo_count_once` treatment; không nằm ở `int_order_cogs_reconciled.cogs_goods_misa` (632-only filter).

**Detail:**  
Phần G&A 6422 (không phải promo) không có conflict vì:
- 6422 = admin thuần, NOT ở sales-ledger MISA promo
- Overhead pool tách khỏi COGS allocation

=> **Design closure rule hoạt động:** SUM(allocated_overhead per kỳ) = pool_kỳ thực tế.

### Trạng thái v1 — Pool duy nhất, 1 base metric

**Implement:** Pool **admin_pool** (6422-only) theo `base_metric='net_revenue'`.

**Từng từ:**
- ✅ Config table (`stg_overhead_account_classification`) sẵn sàng SCD2
- ✅ `int_overhead_pool_monthly` pool net-cost per (pool, month)
- ✅ `int_order_overhead_allocation` pro-rata actual + trailing-rate estimate
- ✅ `fact_order_economics` thêm 4 cột fully-loaded, cờ estimated
- ⏳ `overhead_costs_monthly` ingest — schema chốt, thực thi = v2 (sau khi có export TK642 thật từ MISA)
- ⏳ `overhead_allocation_config` GSheet ingest — schema chốt, thực thi = v2
- ⏳ v2-afterward: mở 6421 keep-set (bao bì→order_count, lương/quảng cáo→net_revenue, ads-theo-sàn→channel-weighted) + selling/handling/channel-ads pools

**Cảnh báo:** v1 (6422-only) **under-state fully_loaded** (bỏ qua lương sales, quảng cáo, bao bì chưa ở tier-2 since 6421 chưa open). Chấp nhận cho báo cáo; bù lại v2 khi 6421 có Sổ cái chi tiết.

## Quyết định Q3 — Base phân bổ overhead (CHỐT v1, 2026-06-04)

### Câu hỏi & 3 lựa chọn
Chia pool xuống đơn theo base nào: ① 1 pool theo `net_revenue` (đơn giản) · ② theo `gross_profit` · ③ ABC-lite (nhiều pool, nhiều driver)?

### Điểm mấu chốt
> **Bóp méo lớn nhất của overhead TMĐT = chi phí scale-theo-số-đơn (pick/pack/ship/CS) lại đem chia theo doanh thu.** Đơn 5tr và đơn 50k tốn pick/pack/CS gần như nhau, nhưng revenue-base gán cho đơn lớn gấp ~100 lần → **đơn nhỏ bị under-cost hệ thống**, giấu mất sự thật đơn nhỏ/rẻ thường lỗ sau ops thật.

- **① net_revenue:** đơn giản, ai cũng hiểu, closure đương nhiên đúng — NHƯNG under-cost đơn nhỏ (sai giả định overhead scale theo doanh thu).
- **② gross_profit: LOẠI** — hồi quy ngược-đời, phạt sản phẩm tốt nhất; là phân bổ "khả năng gánh" chứ không phải "nguyên nhân". Không khuyến nghị.
- **③ ABC-lite:** match pool với cost-driver thật → lộ ra đơn nhỏ đắt đỏ; cần config + driver data (số đơn ✓, số món ✓ đều có).

### 🎯 Quyết định v1: ABC-lite (TT133 pool map)
| Pool | Chứa (TT133) | Base (driver) |
|---|---|---|
| **Admin (G&A)** | **6422** toàn bộ | **`net_revenue`** |
| **Handling** | 6421: **bao bì/đóng gói** (+ CS nếu có) | **`order_count`** (hoặc số món) |
| **Selling-common** | 6421: lương NV bán hàng, showroom, brand-marketing | **`net_revenue`** |
| **Channel-ads** | 6421: ads-theo-sàn (Shopee/Lazada/TikTok Ads) | **gán channel đó** (channel-weighted) |

- **Thực tế triển khai theo 2 nhịp:**
  - **v1 (ngay khi có export) = chỉ pool Admin (6422) theo `net_revenue`** ≈ Q3 "v0 single-pool". Pool Handling/ABC-lite **chưa kích hoạt** vì 6422 không có thành phần xử lý — handling nằm ở 6421 (bao bì).
  - **v1-sau (cần Sổ cái 6421) = bật pool Handling** (bao bì→order_count) + Selling-common + Channel-ads. Đây mới là lúc ABC-lite 2-pool có ý nghĩa.
- **Schema `overhead_allocation_config` đã hỗ trợ sẵn** (`pool_id`, `base_metric` ∈ {net_revenue, gross_profit, order_count}, `channel_weight`).
- **Tránh gross_profit base. Tránh full-ABC** (quá nhiều config cho 1 số report-only → YAGNI).
- **Cảnh báo:** v1 (6422-only) **under-state** fully_loaded (bỏ qua lương sales + ads + bao bì chưa có ở tier-2). Chấp nhận cho v1 (report-only, có cờ) — thà thiếu-mà-sạch hơn double-count; bù lại khi mở 6421-keep.

### 📌 Câu quyết định độ phức tạp (TT133)
- [x] 6422 = admin thuần → pool Admin (net_revenue), không có handling → v1 = single admin pool.
- [ ] Soi Sổ cái **6421**: tách bao bì (→handling/order_count) · lương sales/showroom/brand (→net_revenue) · ads-theo-sàn (→channel) · LOẠI traceable (ship/sàn/payment — đã tier-2).

### Liên kết Q2 ↔ Q3
Base phải khớp **cost-driver** (nguyên nhân), giữ **count-once** thiêng liêng. Doanh thu là driver tốt cho admin nhưng **tệ** cho chi phí xử lý (bao bì) → handling theo `order_count`. Vì 6422 là admin thuần, ABC-lite 2-pool chỉ thực sự kích hoạt khi mở 6421-keep.

**Trạng thái:** CHỐT — v1 = pool Admin 6422 theo `net_revenue` (single-pool); v1-sau bật Handling (6421 bao bì→order_count) + Selling-common + Channel-ads; gross_profit loại; full-ABC để sau.

## Quyết định Q4 — Realtime hay Closure-only? (CHỐT v1 = B, 2026-06-04)

### Vấn đề
MISA chốt sổ TK642 **sau** cuối tháng vài ngày–vài tuần → pool thật của tháng M chỉ biết ~M+10..15. fully_loaded nên: **chờ chốt sổ** (closure) hay **ước tính realtime + true-up**?

### Bối cảnh quyết định (vì sao nghiêng closure)
1. **fully_loaded là report-only**, KHÔNG dùng accept/reject (quyết định dùng `channel_net_profit` tier-2, đã realtime sẵn) → nhu cầu realtime của fully_loaded **rất thấp**.
2. Cadence tự nhiên của P&L đầy đủ là **hàng tháng, sau chốt sổ** → trễ mid-M+1 là chấp nhận được.
3. Budgeted + true-up làm **số tháng trước đổi sau chốt sổ** → bào mòn niềm tin cho 1 số chỉ để báo cáo.
4. **Q1 = export thủ công** → data vốn về theo đợt sau chốt sổ → closure là fit tự nhiên.

### 🎯 Quyết định v1 = **B (Closure-only nền + provisional estimate NHẸ)**
> - **Chính = closure-based actual:** export TK642 tháng M về → phân bổ pool thật → fully_loaded tháng M **FINAL**, `is_overhead_estimated = false`.
> - **Provisional (nhẹ) cho tháng CHƯA chốt:** dùng **trailing actual rate** (pool actual ÷ base của 1–3 tháng đã chốt gần nhất) áp cho đơn tháng hiện tại → hiện fully_loaded tạm, cờ `is_overhead_estimated = true`. Khi actual về → **GHI ĐÈ** (re-materialize tháng đó). KHÔNG book variance, KHÔNG restate tháng đã chốt.
> - Chưa có actual nào (DN mới) → dùng `overhead_allocation_config.budgeted_rate`, hoặc NULL + cờ "chưa có".

Đây **không phải** full true-up (~2x). Là **~1.2x** — chỉ est→actual swap trên tháng đang mở, không có máy móc variance/restatement.

### So sánh 3 mức (đã chọn B)
| Mức | Mô tả | Phức tạp |
|---|---|---|
| A. Closure-only thuần | tháng chưa chốt → fully_loaded NULL | 1.0x |
| **B. Closure + provisional nhẹ** ⭐ | actual sau chốt + ước tính trailing-rate cho tháng hiện tại, cờ estimated, est→actual swap | ~1.2x |
| C. Full realtime + true-up | budgeted + variance + restatement | ~2x (loại) |

### Khớp design hiện có
Field `is_overhead_estimated` (BOOLEAN) + `overhead_allocation_config.budgeted_rate` đã có sẵn — design anticipate đúng hướng B. Triết lý decision-first: overhead ước tính bị **làm mờ/gắn nhãn**, không cạnh tranh `channel_net_profit`.

**Trạng thái:** CHỐT v1 = B.

## Quyết định Q5 — Đơn hủy/hoàn có gánh overhead không? (CHỐT v1, 2026-06-04)

### Câu hỏi
Khi phân bổ overhead (TK642/635/641-chung) xuống từng đơn ở tier-3 (`fully_loaded_net_profit`), các **đơn hủy** (cancelled) và **đơn hoàn/trả** (returned/refunded) có được tính một phần overhead không?

### Reframe — đây là câu hỏi về MẪU SỐ, không phải đạo đức
Pool overhead tháng là **con số CỐ ĐỊNH đã chi tiền thật**, độc lập với việc đơn nào "xứng đáng". Ràng buộc closure `SUM(allocated) == pool_period` (design §6) bắt buộc toàn bộ pool **phải rơi vào đâu đó**. Vậy câu hỏi thật là: *đơn hủy/hoàn có nằm trong **tập đơn để chia pool (base)** không?*
- **Loại khỏi base** → phần overhead chúng "ăn" bị dồn ngầm sang đơn tốt → đơn tốt gánh hộ, và **mất visibility** chi phí của tỷ lệ hủy/hoàn.
- **Đưa vào base** → đơn hủy hiện một khoản overhead + "lỗ" → đơn tốt nhẹ hơn.

### Phải tách 3 trạng thái — chúng KHÁC NHAU về kinh tế (đừng gộp "hủy" với "hoàn")
| Trạng thái | Đã tiêu nguồn lực thật? | Phán quyết v1 |
|---|---|---|
| **Hủy TRƯỚC fulfill** (khách bom giỏ, hủy ngay; chưa pick/pack/ship) | ~0 | **KHÔNG gánh** — đưa vào base chỉ tạo "lỗ ảo" trên mọi giỏ bỏ → nhiễu |
| **Hoàn/trả** (đã giao rồi trả) | Gánh **NHIỀU HƠN** đơn thường (xuôi + ngược: ship về, kiểm, nhập lại, xử lý refund) | Đơn gốc **GIỮ** phần overhead đã phân bổ; **KHÔNG** cộng thêm chi phí ngược vào đơn gốc |
| **Hủy SAU fulfill / RTO** (giao không thành công) | Gánh thật (đã pick/pack/ship) | **CÓ gánh** phần ops; phần ship hỏng đã là **direct cost tier-2** |

### Nguyên tắc quyết định: số này DÙNG ĐỂ LÀM GÌ?
`fully_loaded_net_profit` được định nghĩa là **"để báo cáo, KHÔNG dùng quyết định nhận/từ chối đơn"**; overhead **không nằm** ở tier quyết định (`channel_net_profit`). ⇒ Với quyết định accept/reject, Q5 không áp dụng. Độ chính xác activity-based (ABC) cầu kỳ trên đơn hủy có **giá trị thấp** ở tier báo cáo → **YAGNI**.

### 🎯 Quy tắc v1 (KISS, closure-safe, implement được với data hiện có)
> **Base phân bổ = đơn ĐÃ FULFILL trong kỳ** (proxy: có `std_fulfillments` / có COGS / `status` ∈ {shipped, completed, returned}), trọng số theo `net_revenue` (hoặc `gross_profit`).
> - **Hủy trước fulfill → LOẠI khỏi base** (zero activity, không lỗ ảo).
> - **Hoàn/trả → đơn gốc GIỮ allocation** (nó là đơn fulfilled thật trong kỳ); **không** đẩy reverse cost về đơn gốc — reverse logistics đã là direct cost tier-2 (`shipping_fee_return_refund`, `shipping_fee_failed_delivery`) + đã có `fact_order_returns`.
> - **RTO / hủy sau fulfill → Ở TRONG base** (đã tiêu ops).

Closure vẫn đúng: pool chia trên tập fulfilled. Data đủ để implement: `fact_orders.status`, `std_fulfillments`, `fact_order_returns`.

### ⚠️ Cái bẫy phải tránh — đừng để overhead "che" chi phí churn
Nếu tỷ lệ hủy/hoàn/RTO đáng kể (TMĐT VN thường 8–15% RTO), **đừng chôn** nó vào overhead per-order — nó sẽ **biến mất khỏi tầm nhìn** và không ai hành động. Artifact đúng để quản trị = **1 KPI riêng "cost of churn / failed fulfillment"** (data có sẵn: `fact_order_returns` + `shipping_fee_failed_delivery` + `shipping_fee_return_refund`). Surface riêng → drive giảm RTO; chôn vào overhead → giấu vấn đề.

### Lộ trình nâng cấp (chỉ khi cần)
Lên activity-based (đơn hủy-sau-fulfill và hoàn gánh đúng phần tiêu thụ xuôi/ngược) **chỉ khi** có quyết định cụ thể cần độ chính xác đó (vd: định giá phí xử lý, đàm phán RTO với sàn). v1 không làm.

**Trạng thái:** CHỐT v1. ✅ **Toàn bộ Q1–Q5 đã chốt** — xem các §Quyết định ở trên. Phase-04 sẵn sàng build (chỉ còn cần 1 export Sổ cái TK642 thật để seed data + xác nhận count-once).

## Phase-01 — chốt schema ingestion (pre-work cho phase-04, CHƯA implement)

Std-gate đã xong (`std_misa_sales_lines` live, verified Dagster 2026-06-04). Hai nguồn overhead dưới đây đã chốt **schema**, ingestion implement ở phase-04 (Q1 đã chốt = **export thủ công** — xem §Quyết định Q1).

**`overhead_costs_monthly`** (pool số tiền overhead theo tháng — nguồn MISA):
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `period_month` | DATE | ngày đầu tháng |
| `account` | VARCHAR | **v1: chỉ TK6422** (G&A thuần, net 642-promo — sổ TT133). 6421-keep set mở ngay-sau (cần Sổ cái 6421); 635 để ngoài (xem Q2). Cột vẫn nhận account khác để mở rộng. |
| `amount` | BIGINT | VND, **net VAT** |
| `source` | VARCHAR | **v1 = `'misa_export'`** (thủ công, xem Q1); `'misa_amis'` (API) = v2 |
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

**Phase-04 readiness:** ✅ Q1–Q5 đã chốt (design đủ để build). Còn cần thực tế: 1 export **Sổ cái TK642** thật để seed data lịch sử + xác nhận count-once overlap với sales-ledger-642 trước khi enforce dedup.
