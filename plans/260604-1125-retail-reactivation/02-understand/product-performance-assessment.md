---
title: "Đánh giá: Product-performance data & có cần pipeline không"
stage: 2
status: resolved
source: 4 sonnet agents assessment 2026-06-10
lens: L1/L2/L5
---

# Đánh giá: Product-performance data & quyết định pipeline

**Trạng thái:** ✅ RESOLVED. Câu hỏi: *có cần build pipeline tính product-performance không?* → **KHÔNG cần pipeline lớn; data đã đủ.**

---

## 0. 🔴 Reframe cốt lõi — đây KHÔNG phải brand collagen làm đẹp

Hero SKU thật (doanh thu 2026): **Cordyceps (đông trùng) #1 · Shark Cartilage (khớp) · Fucoidan (miễn dịch) · Natto Kinase (tim mạch) · Gaba (huyết áp) · Chondroitin (khớp) · Reishi (linh chi)**. Collagen chỉ tầm giữa.

→ **Portfolio thực phẩm sức khỏe cho người LỚN TUỔI / có bệnh nền**, KHÔNG phải mỹ phẩm collagen cho phụ nữ trẻ.

**Hệ quả:**
- Giả định "kết quả da đẹp, selfie before/after tuần 4–6" (L1, product-customer-journey) **SAI cho phần lớn hero SKU** — kết quả cordyceps/tim mạch/khớp *vô hình hơn da* (không soi gương thấy huyết áp). Bằng chứng L1 phải là: **cảm nhận năng lượng/giấc ngủ · chỉ số xét nghiệm · tái khám · chứng thực người cùng độ tuổi**, không phải ảnh da.
- **Củng cố mạnh L5** (quà biếu sức khỏe bố mẹ) + giải thích luồng US-gift (gửi đồ sức khỏe cho người nhà lớn tuổi ở VN).
- VOC + product-knowledge phải hỏi theo từng dòng công dụng, không gộp "collagen".

---

## 1. Quyết định: KHÔNG cần pipeline lớn

Data product đã tồn tại đủ rộng. Phân tầng việc cần làm:

| Tier | Việc | Lý do |
|---|---|---|
| **Tier 0 — dùng ngay (0 build)** | Trích insight: hero SKU · retention-theo-sản-phẩm · gateway · reorder cycle · OOS alert → đẩy thẳng vào bán-ế | Đã tính xong ở §3. Use-case (b) KHÔNG cần build. |
| **Tier 1 — fix nhỏ (giờ–ngày, ROI cao)** | (1) ✅ **Fix bug margin DONE** (seed mult=1 cho 5 SKU H010 + cột `realized_margin_pct`, materialized 2026-06-10); (2) seed `product_group`/`function` (gộp variant `(*)` + nhóm công dụng); (3) bắt buộc `return_reason` + fix `int_return_sku_lines` mapping; (4) mở rộng `inventory_health` ra ngoài 8 SKU Cordyceps | Sửa lỗi & mở khóa phân tích theo brand/dòng |
| **Tier 2 — mart nhỏ (chỉ nếu dashboard cần) — HOÃN** | product-cohort mart (first_product × cohort → retention_N) · cross-product-path · market-basket model | Phục vụ use-case (a) dashboard sâu. KHÔNG phải tiền đề để bán. YAGNI tới khi dashboard thật sự dùng để ra quyết định. |

**Trả lời 2 use-case:**
- **(b) Insight để bán NGAY:** không cần pipeline — insight đã có (§3). Nút thắt là *hành động* + product-truth + VOC, không phải hạ tầng data.
- **(a) Dashboard chuyên sâu:** chỉ cần Tier 1 fix + tối đa 1–2 mart nhỏ (Tier 2), làm SAU khi insight Tier 0 chứng minh hướng. Bug margin (Tier 1.1) phải fix bất kể gì.

---

## 2. Data có gì (đã đánh giá)

| Nguồn | Grain / coverage | Dùng được |
|---|---|---|
| `mart_sku_economics_monthly` | product × tháng; 42 SKU, 24 tháng (2024-06→2026-05) | revenue, units, velocity, COGS, return_rate, top channel, slow-mover |
| `fact_sales` | dòng-đơn (order×product); 6.550 dòng rolling, join `dim_products` (brand/category) | repeat-by-product, basket, new-product, channel mix |
| `dim_products` | 685 variant / 558 product / 87 brand (Fine Japan 135) | brand+category có; **KHÔNG có tags / functional taxonomy** |
| `mart_inventory_health` | variant×location×tuần; lịch sử 679 SKU **nhưng snapshot mới chỉ 8 SKU Cordyceps** | OOS/dead/slow + DoS (coverage hẹp) |
| returns (`fact_order_returns`/`int_return_sku_lines`) | 10 đơn 2026; `rl` chỉ map 2/10 | **return_reason 90% trống → chưa dùng được làm proxy lỗi SP** |

---

## 3. Insight retail-actionable (Tier 0 — dùng ngay)

### 3a. Retention LÀ chuyện theo SẢN PHẨM (không đồng đều) — cầu nối tới bán-ế
Retail repeat tổng 25.2% (931 one-time / 1.244). Nhưng tách theo sản phẩm:

| Sản phẩm (Fine Japan) | Repeat% | Gateway→retention% | Reorder median | Nhận định |
|---|---|---|---|---|
| **Cordyceps** | **25.5%** | 28.3% (198 khách) | **31 ngày** | ⭐ Cỗ máy giữ chân — xây subscription quanh nó |
| Hyaluron&Collagen+Swallow's Nest | 25.0% | 35.3% | 21 ngày | Dính tốt, volume nhỏ |
| **Gaba (huyết áp)** | — | **47.2%** | 73 ngày | 🥇 Gateway vàng ẩn (niche, ít đẩy) |
| **Chondroitin (khớp)** | 15.4% | **36.4%** | — | 🥇 Gateway vàng ẩn |
| Hyaluron&Collagen Plus | 19.8% | 20.5% | — | Trung bình |
| Natto Kinase | 11.3% | 23.0% | 37 ngày | Volume cao, dính kém |
| **Fucoidan** | **10.9%** | 24.1% (170 khách) | 56–84 ngày | ⚠️ Bẫy volume — acquisition cao, không dính |
| **Shark Cartilage Extract (cũ)** | **4.9%** | 14.9% | — | ❌ One-and-done (cả acquisition lẫn retention kém) |

→ Bán-ế KHÔNG phải 1 cỗ máy retention chung. Mà: (a) **double-down sản phẩm dính** (Cordyceps) + **gateway vàng** (Gaba/Chondroitin → segment người lớn tuổi/bệnh nền); (b) **chẩn đoán/sửa hoặc hạ ưu tiên bẫy volume** (Fucoidan — VOC hỏi riêng "vì sao không mua lại Fucoidan?"); (c) reorder cadence **per-product**.

### 3b. Chu kỳ reorder 21–85 ngày tùy sản phẩm
Cordyceps/Cordyceps Plus ~31 ngày · Natto 37 · Fucoidan/Reishi/Gaba 56–85. **Giả định 45–60 đồng loạt là SAI** → 3-touchpoint + subscribe cadence phải theo sản phẩm.

### 3c. ✅ ĐÃ FIX 2026-06-10 — H010 KHÔNG bán dưới giá vốn (artifact COGS ×10)

> ✅ ĐÃ FIX 2026-06-10 (seed `misa_qty_multiplier=1` cho 5 SKU H010 + thêm cột `realized_margin_pct`); pipeline đã materialize lúc 03:xx ICT cùng ngày. **KHÔNG cần rebuild serving thủ công.**

**Nguyên nhân bug:** `misa_qty_multiplier=10` cũ trong `seed_sku_alias_manual.csv` — MISA ghi Hyaluron&Collagen / Cordyceps Plus / Swallow Nest theo **Hộp** (không phải Chai), nên multiplier=10 làm COGS bị nhân ×10 SAI.

**Biên thực (sau fix, từ parquet 2026-05-01):**

| SKU | net_rev (tr.đ) | cogs_before (×10) | cogs_after (×1) | realized_margin_before | realized_margin_after |
|---|---|---|---|---|---|
| VCSL19001H010 | 33.5M | 134.9M | 13.5M | −302% | **+59.8%** |
| VCSL21002H010 | 32.8M | 91.2M | 9.1M | −178% | **+72.2%** |
| VTSL24009H010 | 91.1M | 162.1M | 16.2M | −78% | **+82.2%** |
| VTSL24010H010 | 1.1M | 3.9M | 0.4M | −243% | **+65.7%** |
| VTSL21001H010 | avg 24M | — | — | — | **+79.8% avg** |
| VTSC20001L001 (control) | 65.7M | — | 17.8M | — | **+73.0% (không đổi)** |

→ **H010 KHÔNG bán dưới giá vốn.** "Lỗ 440M" là artifact hoàn toàn do bug multiplier. Biên thực +59→83% — hợp lý, khỏe mạnh. Không cần điều chỉnh giá hay ngừng bán format này.

### 3d. OOS hero-SKU
Cordyceps VTSC20001L001: DoS **3.9 ngày** (kho 16 Trương Định), velocity 5.5/ngày, ~15M/tuần rủi ro. Hậu Giang + MM An Phú đã OOS. → **nhập gấp / điều chuyển kho**.

### 3e. Cô đặc & tăng trưởng
Top-5 SKU = **71.8%** doanh thu, top-10 = 88.8%. Tăng mạnh YoY: Fucoidan +475%, Shark Cartilage +281% (kiểm xem nhờ chương trình/kênh nào để nhân rộng). Basket: Cordyceps Plus + Hyaluron&Collagen (lift 10.2) = cặp cross-sell thật để bundle.

---

## 4. Lỗ hổng / caveat data
- **~~Bug margin (§3c)~~** — ✅ ĐÃ FIX 2026-06-10. H010 biên thực +59→83%. `realized_margin_pct` có sẵn trong mart.
- **return_reason 90% trống + rl map 2/10** → returns chưa dùng được làm proxy lỗi SP (cần fix quy trình Sapo).
- **inventory_health chỉ track 8 SKU Cordyceps** — mù tồn kho các hero khác (Shark/Fucoidan...).
- **Không có functional taxonomy** (`product_type` = inventory metadata) → cần seed `product_group`.
- **Retail definition mềm:** `scope_retail` (860 đơn) vs `customer_type='RETAIL'` (1.864 đơn, nhưng [customer_type migration incomplete] → lẫn wholesale). Repeat-rate tuyệt đối hơi mềm; xếp hạng tương đối (Cordyceps > Fucoidan) vẫn tin được.

---

## 5. Hệ quả cho path
- **Product-truth (một phần):** portfolio reframe đã đóng phần lớn — nhưng *timeline kết quả per-dòng* vẫn cần owner (gate).
- **Sửa lens:** product-customer-journey + retail-lenses §L1 phải bỏ khung "da đẹp collagen" cho hero SKU → bằng chứng theo công dụng sức khỏe.
- **VOC sắc hơn:** phỏng vấn theo sản phẩm (Fucoidan one-timer vs Cordyceps repeater).
- **data-backlog:** cập nhật Tier (margin-bug 🔴, product_group, return_reason, inventory coverage = justified; product-cohort/basket = hoãn).
- **Mũi nhọn retail rõ hơn:** xây quanh **Cordyceps** + khai thác **Gaba/Chondroitin gateway** cho segment người lớn tuổi.
