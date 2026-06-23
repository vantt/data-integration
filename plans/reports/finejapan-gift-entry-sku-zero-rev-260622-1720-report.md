# FineJapan: Entry SKU là Quà Tặng trong Multi-SKU Orders

**Date:** 2026-06-22 | **Data:** olap.duckdb, fact_sales line-level analysis | **Updates:** basket-analysis report, purchase-trigger report, growth-diagnosis onepager

---

## TL;DR

- Trong multi-SKU orders: **75% Metabo, 78% Gaba, 67% Coix** có `net_revenue = 0` → rep tặng, không phải khách mua.
- **Premium SKU là trigger thực sự** — Shark/Natto/Cordyceps/Fucoidan (avg 1.9–4.3M) xuất hiện cùng gifted entry trong 179–209 đơn.
- Solo entry orders: 90% Metabo + 89% Coix có revenue thật → pool khách entry hợp lệ để upsell.
- Báo cáo purchase-trigger trước đó (mô hình "Metabo = anchor") bị lật ngược. Chiều nhân quả là ngược lại.

---

## 1. Dữ liệu

### Zero-revenue rate theo basket type

| Sản phẩm | Solo orders (n) | Solo zero-rev% | Multi-SKU orders (n) | Multi zero-rev% |
|---|---|---|---|---|
| Metabo Green Tea | 371 | **10%** | 1,034 | **75%** |
| Gaba blood pressure | 208 | **32%** | 751 | **78%** |
| Coix Beauty | 259 | **11%** | 386 | **67%** |
| Metabo (*) alt-name | 85 | **16.5%** | 165 | **58.8%** |

Nguồn: `unit_rev = net_revenue / quantity` per line, `COUNT(*) OVER (PARTITION BY order_id)` làm basket_size.

### Products xuất hiện cùng gifted entry SKUs

| Product (cùng đơn khi Metabo/Gaba là gift) | Appearances | Avg order rev |
|---|---|---|
| Shark Cartilage | 209 | 3,255,840 |
| Natto Kinase | 207 | 1,874,482 |
| Cordyceps | 203 + 175 | 3,141,206 – 4,336,208 |
| Fucoidan | 179 | 3,012,716 |
| Hyaluron & Collagen | 97 | 3,027,900 |

Tất cả đều là premium SKUs. Không có entry SKU nào trong top 15.

---

## 2. Mô hình đúng vs mô hình cũ

| | Mô hình cũ (sai) | Mô hình đúng |
|---|---|---|
| **Trigger** | Metabo = entry anchor | Premium SKU (Shark/Natto/Cordyceps) |
| **Metabo trong multi-SKU** | Sản phẩm khách chọn | Quà tặng rep kèm theo |
| **Chiều nhân quả** | Metabo → premium upsell | Premium → rep tặng Metabo |
| **Solo entry orders** | N/A | Real purchases → future upsell pool |

---

## 3. Implications cho vận hành

### Rep behavior hiện tại (observed từ data)
Rep đang tặng Metabo/Gaba như promotional gift trong đơn premium — đây là chiến lược **rep tự phát** (không rõ có playbook chính thức không).

### Điều cần làm rõ
1. **Gift có chủ đích không?** Rep tặng để tăng giá trị đơn cho khách hay để giải phóng hàng?
2. **Cost tracking:** Zero-rev gift lines không được tính vào revenue nhưng có COGS thật. Hiện tại không có cost allocation cho gift lines — ảnh hưởng đến gross margin thực của đơn.
3. **Upsell từ solo entry pool:** 371 đơn Metabo solo + 259 Coix solo (90% revenue thật) = ~580 khách entry thực sự. Đây là target cho upsell premium trong follow-up. Hiệu quả chưa được đo.

### Điều KHÔNG thay đổi
- Acquisition concept "mồi nhử rẻ → kéo khách vào → bán premium" vẫn đúng ở **kênh level** (Shopee/Selly/TikTok). Đây là channel acquisition playbook.
- Co-purchase rate vẫn cao hơn sequential upgrade (554 vs 20).
- Discount không phải lever (2.4% đơn, không tương quan với basket size).

---

## Unresolved Questions

- **Gaba solo zero-rev = 32%** (cao hơn Metabo 10%) → Gaba còn được gửi sample độc lập? Hay có segment khách đặc thù không?
- **Gift cost allocation:** Tổng COGS của gift Metabo/Gaba là bao nhiêu? Có đang được tính vào P&L không?
- **Rep consistency:** Tất cả rep đều tặng gift hay chỉ một số? Rep tặng nhiều hơn có conversion premium cao hơn không?
- **Solo entry → premium conversion rate:** Trong 580 khách solo entry, bao nhiêu % chuyển sang premium trong 6 tháng tiếp theo?
