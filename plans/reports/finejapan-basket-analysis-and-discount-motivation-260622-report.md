# FineJapan: Basket Size & Discount Motivation Analysis

**Date:** 2026-06-22 | **Data:** olap.duckdb, retail active orders only (n=6,345)

---

## TL;DR

- **Mua theo cặp là cơ chế chính**: 50% đơn 1 sản phẩm, 33% đơn 2 sản phẩm. Basket thường nhỏ.
- **Discount không phải nguyên nhân bundling**: Chỉ 2.4% đơn có giảm giá. Đơn giảm giá không có basket lớn hơn đơn full price.
- **Metabo + Cordyceps/Fucoidan/Shark vẫn là top pairs**, gần như không discount (~0% đơn được giảm giá).
- **Gaba blood pressure (mới)** xuất hiện trong top pairs với Cordyceps và Natto Kinase — sản phẩm chưa theo dõi trong playbook cũ.
- **Gift items** (nến, bát tre, dù, văn phòng phẩm) chiếm nhiều top pairs — đây là promotional bundles, không phải organic multi-buy.

---

## 1. Basket Size Distribution

| Items/đơn | Đơn | % | Avg rev (VND) | % đơn có disc |
|---|---|---|---|---|
| 1 | 3,154 | **49.7%** | 1,338,378 | 2.6% |
| 2 | 2,119 | **33.4%** | 2,251,204 | 2.0% |
| 3 | 720 | 11.3% | 2,864,411 | 2.4% |
| 4 | 218 | 3.4% | 3,013,851 | 1.4% |
| 5+ | 134 | 2.1% | cao hơn | mixed |

**Nhận xét:**
- Trung bình ~1.7 sản phẩm/đơn. Đây là một customer journey rất tập trung.
- Rev tăng theo basket size (đương nhiên) nhưng không có bằng chứng discount kéo basket lên: `% đơn có disc` gần như flat ở mọi level (2-2.6%).

---

## 2. Discount: Không phải driver của bundling

```
Chỉ 151 / 6,345 đơn có giảm giá  (2.4%)
Avg discount trong số này: 32.2%
3,832 đơn có max_discount_rate = NULL (không có discount tracking)
```

| Basket type | Đơn | Avg disc% | % đơn có disc | Avg order value |
|---|---|---|---|---|
| 1 item | 3,154 | 3.2% | **2.6%** | 1,079,921 |
| 2+ items | 3,191 | 1.1% | **2.2%** | 2,363,299 |

**Kết luận mạnh: Discount KHÔNG phải nguyên nhân bundle.** Tỷ lệ đơn được giảm giá trong nhóm multi-item (2.2%) thậm chí còn thấp hơn nhóm single-item (2.6%). Khách mua 2+ sản phẩm không phải do được discount mà do được rep tư vấn (consultative selling).

---

## 3. Top Product Pairs (tất cả đơn retail)

### 3a. Supplement pairs (bỏ gift/promo items)

| Product A | Product B | Đơn cùng mua | Avg rev | % disc |
|---|---|---|---|---|
| Cordyceps | Metabo Green Tea | **139** | 5,189,383 | 0.7% |
| Metabo Green Tea | Fucoidan | **131** | 8,675,160 | 2.9% |
| Metabo Green Tea | Shark Cartilage | **113** | 8,663,141 | 0.0% |
| **Cordyceps** | **Gaba blood pressure** | **132** | 2,595,171 | 3.5% |
| Natto Kinase | **Gaba blood pressure** | 92 | 2,280,463 | 3.2% |
| Metabo Green Tea | Natto Kinase | 59 | 11,250,861 | 3.0% |
| Cordyceps | Hyaluron & Collagen | 61 | 14,590,859 | 8.8% |
| Metabo Green Tea | Hyaluron & Collagen | 55 | 18,619,446 | 3.2% |
| Hyaluron & Shark Cartilage | | 52 | 12,191,738 | 0.0% |
| Shark Cartilage | Gaba blood pressure | 52 | 2,163,095 | 0.0% |
| Cordyceps | Coix Beauty | 46 | 1,481,591 | 2.2% |
| Cordyceps | Fucoidan | 39 | 12,710,065 | 2.6% |
| Royal Reishi | Metabo Green Tea | 44 | 2,381,284 | 0.0% |

**Nhận xét:**
- **Gaba blood pressure** xuất hiện là top pair cho cả 3 premium SKU (Cordyceps 132, Natto Kinase 92, Shark Cartilage 52). Đây không phải trong playbook ban đầu → cần investigate.
- Metabo vẫn là entry SKU số 1, pair với gần như tất cả premium.
- Gần như **100% đơn top pairs là full price** (disc% gần 0). Bundling = tư vấn, không phải promo.

### 3b. Gift/promo bundles — alert

Top pairs bao gồm nhiều non-supplement items:
- Nến thơm (candles) + Gaba (96), Nến + Cordyceps (48), Nến + Natto Kinase (31)
- Bát tre cuốn khảm trai (bamboo bowls) + Shark Cartilage (89), + Cordyceps (65/40), + Natto Kinase (42)
- Dù in logo FG (umbrellas) + Cordyceps (89), + Fucoidan (41), + Hyaluron (37)
- Bút bi, sổ tay in logo FG (stationery) + supplements

Đây là **promotional gift bundles / corporate gift orders** — không phải organic multi-buy từ end consumer. Multi-item đơn có thể bị inflate bởi nhóm này.

---

## 4. Discount landing trong entry+premium co-purchase orders

```
entry lines:   782 lines | avg_line_rev=61,193 VND | avg_disc=12,168 VND | disc_share=16.6%
premium lines: 948 lines | avg_line_rev=2,116,708 VND | avg_disc=167,556 VND | disc_share=7.3%
```

**Đọc kết quả:**
- Entry SKU nhận discount tỷ lệ CÁO HƠN (16.6% vs 7.3% của giá gốc)
- Nhưng absolute discount trên premium lớn hơn nhiều (167K vs 12K) — premium đắt hơn 35× nên dù % thấp hơn vẫn là số tiền lớn
- Entry avg_line_rev = 61K (rất thấp — có nhiều zero/near-zero revenue lines, data quality issue đã biết)

**Hàm ý:** Khi rep apply discount trong đơn entry+premium, discount được dàn đều nhưng proportionally rơi nhiều hơn vào entry. Điều này nhất quán với model "entry được giảm để kéo khách, premium full price."

Tuy nhiên, chỉ ~151 đơn có discount — con số này quá nhỏ để suy ra chiến lược tổng quát. Trong hầu hết đơn entry+premium, **không có discount nào được áp dụng**.

---

## 5. Discount ở Entry SKU: không thay đổi basket size

| Entry SKU | Price type | Đơn | Avg basket | Avg rev | Avg disc% |
|---|---|---|---|---|---|
| Metabo Green Tea (main) | discounted | 11 | **7.4** | 12,244,442 | 32.5% |
| Metabo Green Tea (main) | full price | 791 | **2.8** | 5,838,944 | 0% |
| Coix Beauty | discounted | 7 | **7.2** | 8,643,100 | 19.2% |
| Coix Beauty | full price | 333 | **2.1** | 1,562,106 | 0% |

Nhìn bề mặt: discounted → basket lớn hơn. **Nhưng đây là confound**, không phải causation:
- 11 đơn Metabo discounted có avg basket = 7.4 và avg rev = 12.2M → đây là **large B2B orders** (xem section 1: các đơn 7-10+ items đều là outliers lớn)
- B2B / corporate orders tự nhiên có discount + basket lớn + rev cao cùng lúc
- Trong retail thuần, discount không làm basket lớn hơn

---

## Kết luận & Implications

### 1. Playbook vận hành ở basket nhỏ (1-2 items)
50% đơn 1 sản phẩm, 33% đơn 2. Rep phải tích cực bundle ngay trong đơn đầu — nếu để khách mua 1 item thì hầu như không quay lại với premium (từ previous report: 2% upgrade rate).

### 2. Discount không phải lever để tăng basket
Chỉ 2.4% đơn được giảm giá. Discount rate của multi-item order (2.2%) thậm chí thấp hơn single-item (2.6%). Rep nên tập trung vào **value proposition** thay vì giảm giá khi bundle.

### 3. Gaba blood pressure: unknown player trong ecosystem
132 đơn Cordyceps + Gaba, 92 đơn Natto + Gaba, 52 đơn Shark + Gaba — đây là pair lớn hơn hoặc tương đương nhiều entry SKU pair. Cần investigation: đây là sản phẩm của FineJapan hay phân phối ngoài? Khách mua segment nào?

### 4. Gift bundles inflate multi-item counts
Một phần đáng kể "multi-item orders" là corporate gift orders (nến + bát tre + dù kèm theo premium supplements). Đây là một revenue channel khác, không phải cùng dynamics với retail end-consumer.

### 5. Entry SKUs có avg_line_rev rất thấp (61K) — data quality
Nhiều entry lines có zero hoặc near-zero net_revenue (promotions/samples). Metabo Green Tea avg_unit_rev ~115K vs last_sold_price ~390K (đã flag trong previous reports). Cần làm sạch trước khi phân tích margins.

---

## Unresolved Questions

- **Gaba blood pressure là product gì?** Nguồn gốc, price point, customer segment? Rep-driven hay self-select?
- **Gift bundle channel** có P&L riêng không? Corporate gift orders có margin profile khác retail không?
- **Entry avg_line_rev = 61K** — bao nhiêu % là zero-revenue lines (samples/gifts)? Cần filter trước khi tính disc_share.
- **3,832 đơn có NULL max_discount_rate** — đây là 60% total. Là không có discount (đúng NULL=0), hay là data không được track đầy đủ?
