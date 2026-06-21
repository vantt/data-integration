# Data Probe: Dead-stock → Customer Targeting + Match Granularity

**Date:** 2026-06-20 · **DB:** `app_data/data_lake/export/marts/rolling/` parquet (read-only, latest snapshot per mart) · **Engine:** DuckDB 1.5.1

Mục đích: trả lời "thoát bán ế" — nên ghép SKU ế ↔ khách ở granularity nào (SKU / category / brand), và quy mô cơ hội thực tế.

---

## 1. Khung khái niệm

"Thoát bán ế" = bài toán **phía CUNG** (trạng thái tồn kho), nhưng plan resell/activation hiện thuần **phía CẦU** (trạng thái khách). Cây cầu product→customer đang thiếu.

- **Tier** (`mart_customer_tier`) = STATE biến đổi → "đáng chạm không".
- **Cohort** (entry DNA, `mart_cohort_retention` 8 trục) = MEMBERSHIP bất biến → analytical, không actionable per-khách.
- **Demand-match** (affinity × SKU ế) = quan hệ (khách × sản phẩm) = LÕI thoát bán ế → **chưa có**.

`mart_product_action_queue` đã tính sẵn trigger phía cung (`CLEAR_DEADSTOCK`) nhưng (a) nhiễu, (b) chưa bao giờ join sang khách.

## 2. Tập "ế" thực tế (nhỏ + nhiễu)

`CLEAR_DEADSTOCK` thô = **17 SKU / 42.1M VND**. Nhưng **12/17 là hàng vận hành/nội bộ** (category `Vận Hành` + `Uncategorized`: UMBRELLA, `VFJDEMOH001` demo, mã VB23/VB24) — không bán, không resell.

| Nhóm | SKU | Vốn kẹt |
|---|---|---|
| CLEAR_DEADSTOCK thô | 17 | 42.1M |
| − noise Vận Hành/Uncategorized | −12 | −36.6M |
| **= Dead-stock bán-được thật** | **5** | **5.5M** |

5 SKU thật: `VCMC21010H001` (Medicine, 2.73M) · `VTSL21005C001` (Dietary Supplement/Fine Japan, 2.06M) · `VTSL22120C001` (DS/hepalyse, 0.52M) · `VCSC24007G001` (DS, 0.13M) · `VCST24006G001` (DS, 0.05M).

**Mở rộng slow-mover** (`mart_product_health`, ~104 SKU active tracked): DOG=3 (~37M stock), QUESTION=3 (~42M). Sellable slow (DOG/QUESTION/overstock) = **6 SKU / ~79M**. Thực sự kẹt vốn đáng campaign ≈ 2 SKU: `VCST21003L001` (DOG DECELERATING, 35.2M, last-sale 10d) + `VTST23023L001` (QUESTION, 41.5M nhưng bán 1d trước = vẫn chạy).

## 3. Affinity coverage (input cho match)

| Cột | Coverage /7563 | Ghi chú |
|---|---|---|
| `top_affinity_sku` | 5114 (68%) | actionable tier 81–100% |
| `product_affinity` (brand) | 5965 (79%) | **chỉ 2 giá trị**: PRODUCT_FINE_JAPAN (4114), PRODUCT_MULTI (1851) → vô dụng cho brand-match |

Pool reachable = tier LIVE_CORE 56 + SECOND_ORDER 27 + DORMANT_VALUABLE 122 + LAPSED_VALUABLE 1144 + MASKED_REPEAT 433 = **1,782**.

## 4. Test granularity — audience cho dead-stock hiện tại (pool 1,782)

| Mức ghép | Audience | Phán quyết |
|---|---|---|
| **SKU — past-buyer** (`fact_sales`, từng mua đúng SKU) | **8** (per-SKU 3/3/2/0/0) | Chính xác, **gần rỗng** |
| packsize-root past-buyer | 0 | Không data |
| brand (`product_affinity`) | 0 | **Hỏng** (taxonomy 2-giá-trị) |
| SKU-affinity (`top_affinity_sku`) | 4 | Gần rỗng |
| category (Medicine+DS) | 1,233–1,677 (~70–94%) | = cả base = **blast, không phân biệt** |

2/5 SKU dead có **0 người từng mua** (`VCSC24007G001`, `VCST24006G001`) → failed-launch, quyết định merchandising (bundle/markdown/delist), không phải nhắm khách.

## 5. Phán quyết granularity (data-backed)

- **Chỉ SKU-level past-purchase (tái mua) có độ chính xác.** Category = spam (dead-cat ≈ toàn catalog FineJapan). Brand = hỏng. Affinity-columns = quá thưa.
- **Tier × demand-match = segmentation**; KHÔNG cần đẻ cohort khách mới (state-cohort trên base nhỏ = YAGNI).
- Quy mô hiện tại nhỏ: ~8 khách / 5.5M dead thật; ~40–77M nếu gộp slow-mover.

## 6. Hệ quả thiết kế (cho build plan)

1. **Dọn tín hiệu trước:** `mart_product_action_queue.CLEAR_DEADSTOCK` phải loại category không-bán-được (`Vận Hành`, `Uncategorized`) — hiện 70% noise.
2. **Match key = SKU past-purchase** (join `fact_sales.product_key`), bổ sung replenishment-due (`next_purchase_signal`, `predicted_next_purchase_date`) + discount-sensitivity gate. KHÔNG dùng category/brand/affinity-col làm match chính.
3. **2 kênh:** Hug (voucher) cho contactable; Shopee-native cho MASKED_REPEAT (433, không DM trực tiếp được).
4. **Track riêng** khỏi NBA customer-state (trigger khác bản chất: inventory vs customer).
5. **Thiết kế cho scale + ngưỡng kích hoạt** (quyết định user 2026-06-20: build full engine bất chấp quy mô vốn hiện nhỏ).

---

## Unresolved Questions

1. `mart_product_health` chỉ track ~104 SKU — có phải toàn bộ catalog active, hay đang lọc mất phần ế khác? Cần xác minh phủ.
2. Shopee seller messaging API / campaign-list export có sẵn để chạm 433 masked-repeat in-channel không?
3. Ngưỡng kích hoạt cụ thể (vốn-kẹt-bán-được ≥ ? / SKU có ≥ ? past-buyer) để engine "đáng chạy" — chờ user chốt con số.
4. `product_affinity` 2-giá-trị: có kế hoạch làm brand taxonomy thật không (ảnh hưởng khả năng brand-match tương lai)?
