# FineJapan: Entry SKU → Premium Upgrade Path Analysis

**Date:** 2026-06-22 | **Data:** olap.duckdb, retail active orders only

---

## TL;DR

Playbook "mồi rẻ → upsell premium" hoạt động theo **cơ chế đồng đơn (Path A)**, không phải theo trình tự đơn 1 → đơn 2 (Path B).

- **554 khách** mua entry + premium **cùng một đơn đầu** (rep-driven bundle)  
- Chỉ **20 khách** có chuỗi: đơn 1 entry-only → đơn 2 premium  
- 1099 khách mua entry-only đơn đầu → chỉ **2% ever upgraded** tự phát về sau  

---

## Path A — Co-purchase trong đơn đầu (entry + premium cùng giỏ)

**554 khách** | Dominant pattern: Metabo Green Tea là entry SKU chủ lực

| Entry SKU | Premium SKU | Khách |
|---|---|---|
| Metabo Green Tea | Cordyceps | 96 |
| Metabo Green Tea | Shark Cartilage | 89 |
| Metabo Green Tea | Fucoidan | 83 |
| Metabo Green Tea | Natto Kinase | 40 |
| Metabo Green Tea | Hyaluron & Collagen | 25 |
| Metabo Green Tea | Royal Reishi | 24 |
| **Coix Beauty** | Cordyceps | 21 |
| Metabo Green Tea | Hyaluron & Collagen (low-price) | 21 |
| **Calcium** | Shark Cartilage | 19 |
| Metabo Green Tea | Shark Cartilage (*) | 17 |
| **UV Care Plus** | Cordyceps (*) | 11 |
| **Coix Beauty** | Natto Kinase | 10 |
| UV Care Plus | Shark Cartilage | 8 |
| Coix Beauty | Shark Cartilage | 6 |

**Nhận xét:**
- Metabo Green Tea chiếm ~70% tổng co-purchase — đây là entry SKU thực sự của playbook cũ
- Coix Beauty (mới 2026-Q2) đã xuất hiện trong top pairs → playbook đang hồi sinh
- Calcium và UV Care Plus đóng góp ít trong co-purchase

---

## Path B — Consecutive upgrade: đơn 1 entry-only → đơn 2 premium

**20 khách tổng** (rất nhỏ)

| Entry (đơn 1) | Premium (đơn 2) | Khách | Avg ngày |
|---|---|---|---|
| Coix Beauty | Hyaluron & Collagen | 3 | 68 ngày |
| Metabo Green Tea | Hyaluron & Collagen | 3 | 58 ngày |
| Metabo Green Tea | Cordyceps | 2 | 34 ngày |
| Metabo Green Tea | Shark Cartilage | 2 | ~0* |
| Coix Beauty | Cordyceps | 1 | 10 ngày |
| UV Care Plus | Natto Kinase | 1 | 197 ngày |

*avg_days=0 có thể là split-order cùng ngày, không phải true upgrade.

**Nhận xét:** Path B yếu đến mức thống kê. 20/1099 entry buyers = ~1.8%. Khách không tự navigate từ entry → premium — họ cần rep dẫn dắt.

---

## Funnel: Entry-only first-order buyers

```
1,099  mua entry-only đơn đầu
  ↓ 14%
  154  quay lại mua đơn 2
    ↓ 12%
     18  đơn 2 có premium  (= 1.6% của entry buyers)
 
   24  ever mua premium (any order sau đơn 1) = 2.2% of entry buyers
```

---

## Entry SKU performance (standalone upgrade rate)

| Entry SKU | Buyers (entry-only first) | Ever upgraded | Rate |
|---|---|---|---|
| Metabo Green Tea | 207 | 15 | **7%** |
| Coix Beauty | 154 | 5 | **3%** |
| UV Care Plus | 407 | 2 | **0%** |
| Calcium (Kids) | 272 | 0 | **0%** |

**Critical:** UV Care Plus và Calcium có 0% standalone upgrade. Họ bring traffic nhưng không dẫn đến premium nếu không có rep trong cùng đơn.

---

## Kết luận & Implications

### 1. Cơ chế thực: Rep-bundled, không phải self-serve sequential
Playbook "mồi rẻ" hoạt động khi rep/tư vấn đưa premium vào giỏ cùng lúc với entry SKU. 554 co-purchase vs 20 sequential = tỷ lệ 27:1. Đây là **consultative selling**, không phải self-upgrade funnel.

### 2. Metabo Green Tea là entry SKU #1 (không phải UV Care hay Calcium)
- 802 đơn tổng (cao nhất toàn catalog)
- 7% standalone upgrade rate (tốt nhất trong entry group)
- Dẫn đến Cordyceps, Shark Cartilage, Fucoidan trong cùng đơn

### 3. UV Care Plus và Calcium = pure acquisition, zero upgrade path
Hai SKU này chỉ có giá trị nếu rep kết hợp premium cùng đơn. Nếu khách mua standalone, 0% quay lại với premium. Cần xem xét có nên invest vào 2 SKU này nếu không có consultative channel hay không.

### 4. Coix Beauty (2026-Q2) đang tái hiện đúng playbook
21 co-purchase Coix + Cordyceps trong đơn đầu → dấu hiệu rep đang bundle lại. Đây là signal quan trọng.

### 5. Return rate từ entry-only buyers cực thấp: 14%
Vs 22-26% overall first→second repeat rate (cohort report). Entry-only buyers không gắn bó — họ cần premium anchor để trở thành repeaters.

---

## Unresolved Questions

- Kênh nào (Shopee vs Sapo-direct vs Selly) produce nhiều co-purchase nhất? Có thể Sapo-direct (rep-assisted) dominate Path A, còn Shopee = standalone với 0% upgrade.
- Metabo Green Tea: 802 orders nhưng avg_unit_rev chỉ 115K (rất thấp vs last_price 390K) — có nhiều order zero-revenue (quà tặng/sample)? Cần làm sạch.
- Liệu có window thời gian tốt hơn để retarget entry-only buyers? (14 ngày? 30 ngày?)
