---
id: "OPP-005"
title: "Dead-stock → Customer Targeting Engine"
stage: 4
status: built
type: opportunity
source: "../02-understand/FIND-008-deadstock-customer-targeting-granularity.md"
from:
  - "FIND-008"
moves_to:
  - "PLAN-004 (P0/P1/P2 data path deployed 2026-06-21)"
canonical_anchor: "opp-005"
depends_on:
  - "dọn noise mart_product_action_queue.CLEAR_DEADSTOCK (loại Vận Hành/Uncategorized)"
created: 2026-06-20
updated: 2026-06-20
---

<a id="opp-005"></a>

# OPP-005 — Dead-stock → Customer Targeting Engine

**Registry:** [OPP-005](../REGISTRY.md#opp-005)

**Status:** `built` / in-execution — engine core LIVE 2026-06-21; activation Hug/Shopee pending.
**From:** [FIND-008](../02-understand/FIND-008-deadstock-customer-targeting-granularity.md) — granularity probe.
**Moves to:** PLAN-004 (P0/P1/P2 data path DEPLOYED 2026-06-21).

---

## Required Contract

| Field | Nội dung |
|---|---|
| User / segment | Khách từng mua đúng SKU ế/slow + đang replenishment-due, trong pool reachable 1,782 (LIVE_CORE / SECOND_ORDER / DORMANT_VALUABLE / LAPSED_VALUABLE / MASKED_REPEAT) |
| Job / pain / leverage | Thoát vốn-kẹt phía cung bằng cách ghép SKU ế → danh sách khách xếp hạng; lấp mắt xích product→customer mà plan hiện thiếu |
| Source evidence | [FIND-008](../02-understand/FIND-008-deadstock-customer-targeting-granularity.md): chỉ SKU past-purchase có precision; category/brand/affinity-col không dùng được |
| Proposed move | Engine ghép SKU ế/slow ↔ khách qua match key = SKU past-purchase + replenishment-due + discount-sensitivity gate; output 2 kênh (Hug voucher + Shopee-native) |
| Success signal | Vốn-kẹt-bán-được giảm; conversion rate của past-buyer được chạm > baseline blast |
| Main risk / blocker | Quy mô vốn hiện nhỏ (5.5–77M); `product_affinity` hỏng; Shopee messaging API chưa rõ; cần dọn noise `mart_product_action_queue` trước |

---

## Ý Tưởng

Engine ghép **SKU ế/slow → danh sách khách xếp hạng**. Match key:

- **SKU past-purchase** (`fact_sales.product_key` — từng mua đúng SKU) → trục precision duy nhất.
- **+ replenishment-due** (`next_purchase_signal`, `predicted_next_purchase_date`) → khách đến nhịp tái mua.
- **+ discount-sensitivity gate** → chỉ tung voucher cho nhóm cần, tránh ăn lãi nhóm full-price.

Output 2 kênh phân phối:

1. **Hug (voucher)** — cho khách contactable.
2. **Shopee-native** — cho MASKED_REPEAT (433 khách, KHÔNG DM trực tiếp được) qua campaign-list / seller messaging in-channel.

**Track RIÊNG** khỏi NBA customer-state: trigger khác bản chất (inventory-driven vs customer-state-driven).

---

## Vì Sao Cơ Hội Này Tồn Tại

Plan resell/activation hiện thuần phía **CẦU** (trạng thái khách). "Thoát bán ế" là bài toán phía **CUNG** → thiếu hẳn cây cầu product→customer. `mart_product_action_queue.CLEAR_DEADSTOCK` đã tính trigger phía cung nhưng chưa bao giờ join sang khách. FIND-008 chứng minh chỉ SKU past-purchase ghép được chính xác — nên engine khả thi nhưng phải build đúng match key, không dùng category (blast) / brand (hỏng) / affinity-col (thưa).

---

## Cách Có Thể Triển Khai

- **Dọn tín hiệu nguồn trước:** loại category không-bán-được (`Vận Hành`, `Uncategorized`) khỏi `CLEAR_DEADSTOCK` (~70% noise hiện tại).
- **Match layer:** join SKU ế/slow ↔ `fact_sales` past-buyer; rank theo replenishment-due + value.
- **Gate:** discount-sensitivity trước khi gắn voucher.
- **Distribute:** route Hug (contactable) vs Shopee-native (masked).
- **Merchandising fallback:** SKU 0-lifetime-buyer (failed-launch) → bundle/markdown/delist, KHÔNG đưa vào engine nhắm khách.

---

## Nguồn & Lineage

| Loại | Link / ID | Ghi chú |
|---|---|---|
| Finding | [FIND-008](../02-understand/FIND-008-deadstock-customer-targeting-granularity.md) | Bằng chứng granularity: SKU past-purchase = precision duy nhất |
| Data backlog | [OPP-004](./OPP-004-data-backlog.md) | Market-basket / inventory_health ↔ affinity (liên quan, nhưng OPP-005 chốt match key đúng) |

---

## Chấm Điểm Sơ Bộ

| Tiêu chí | Điểm (1-5) | Ghi chú |
|---|---|---|
| **Impact** | — | not scored yet — quy mô vốn hiện nhỏ nhưng owner muốn build cho scale |
| **Effort** | — | |
| **Confidence** | — | |
| **Time-to-cash** | — | |

**Tổng / Quyết định:** `built` — engine core LIVE 2026-06-21 (P0/P1/P2 data path GREEN, verified); activation Hug/Shopee pending.

**Điều kiện để promote — tất cả ĐÃ giải quyết (2026-06-20):**

- ✅ Dọn noise `mart_product_action_queue.CLEAR_DEADSTOCK` — **code DONE** (chưa deploy): filter `category NOT IN ('Vận Hành','Uncategorized')`, validate 17→5 SKU/5.5M.
- ✅ Xác minh Shopee messaging API cho MASKED_REPEAT — **RESOLVED**: KHÔNG có API messaging Shopee ([report](../../reports/researcher-260620-2217-shopee-seller-messaging-masked-buyers-re-engagement-report.md)) → manual workflow Seller Center.
- ✅ User chốt ngưỡng kích hoạt — **CHỐT**: ≥30M VND HOẶC ≥3 SKU mỗi cái ≥20 past-buyer (khởi điểm).

---

## Decision Note — Owner Call 2026-06-20

> **Quyết định user (2026-06-20): BUILD FULL ENGINE** — thiết kế cho scale + ngưỡng kích hoạt, **bất chấp quy mô vốn-ế hiện nhỏ (5.5–77M)**.
>
> Đây là **business call của owner**, KHÔNG phải YAGNI auto-cut. Probe FIND-008 cho thấy cơ hội hiện nhỏ; bình thường rubric sẽ hoãn. Owner chủ động chọn build sẵn hạ tầng + ngưỡng kích hoạt để engine tự bật khi vốn-ế tích đủ lớn. Không được tự cắt scope này theo logic minimalism mà không hỏi lại owner.

### 4 Quyết Định Chốt 2026-06-20 (đóng open questions)

1. **P0 noise-clean — code DONE, chưa deploy.** Filter `category NOT IN ('Vận Hành','Uncategorized')` (NULL→coalesce 'Uncategorized'→loại) vào nhánh CLEAR_DEADSTOCK `mart_product_action_queue.sql`. Validate live: 17 → 5 SKU / 5.5M. Còn lại: `dbt run` + rebuild serving view.
2. **Ngưỡng kích hoạt (open Q #1) — CHỐT khởi điểm:** ≥30M VND HOẶC ≥3 SKU mỗi cái ≥20 past-buyer eligible. Probe đã vượt → chạy ngay.
3. **Shopee leg (open Q #2) — RESOLVED bằng research** ([report](../../reports/researcher-260620-2217-shopee-seller-messaging-masked-buyers-re-engagement-report.md)): KHÔNG có API messaging Shopee → engine chỉ sinh danh sách masked-repeat (433), ops chạm thủ công Seller Center (Chat Broadcast 2 msg/buyer/tuần ~280–350/433 + Repeat Buyer Voucher auto + Follow Prize; ~25 phút/đợt, $0, ~99% phủ qua 2 tuần). Caveat: quota VN chưa verify.
4. **Scope sản phẩm P1 (open Q #3) — CHỐT:** own-brand Fine Japan Vietnam, filter chính `brand_code='FJV'`. Own-brand FJV slow/dead = 20 SKU / 81.1M (2 SKU vốn lớn `VTST23023L001` QUESTION 41.5M + `VCST21003L001` DOG 35.2M); giữ ~97% vốn + ~342/426 past-buyer. Caveat data-quality: vài SKU FJV brand_name NULL (prefix VCMC/VCSC/VCST) → dùng `brand_code` (đầy đủ hơn); coverage-check trong P1 rà SKU FJV NULL-brand_code vốn lớn.

---

## Anti-Patterns

- Dùng category-match → spam cả base (dead-cat ≈ toàn catalog FineJapan).
- Dùng `product_affinity` brand-match → hỏng (taxonomy 2-giá-trị).
- Đưa SKU 0-lifetime-buyer vào engine nhắm khách → đó là merchandising, không phải targeting.
- Gộp chung trigger với NBA customer-state → lẫn bản chất inventory vs customer.
