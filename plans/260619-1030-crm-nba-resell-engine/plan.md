# Plan — CRM Re-sell: Funnel-First Roadmap

> Status: **In progress** (updated 2026-06-24: A1 tier mart implemented; Hug platform design complete; A2/A3/A4 designed; M5 voucher go-live + A2 pilot pending; Stage B deferred). Untouched by 260623 audit work.
> Thiết kế: [`discussion.md`](./discussion.md) · Probe: `plans/reports/data-probe-core-boundary-shopee-masked-identity-260619-1054-report.md`

## Chẩn đoán (data tươi, N=7563)

"Bán ế" = **activation problem**, không phải reactivation. Active base tí hon (~83 live core), 69% nghĩa địa, ~77 đơn/tháng. Shopee masked **resolves** (không vỡ) → order/value của khách masked đáng tin. → Tạo active, không phải xếp hạng active.

## Quyết định đã chốt

- ✅ **Sequencing: funnel trước, engine sau.**
- ✅ Engine boundary = **Def-B (1,263)** `contactable AND (repeat OR recency≤90)`.
- ✅ Identity capture nhắm **346 masked-repeat Shopee** đầu tiên (capture xong kế thừa full history → vào core).
- ✅ Kiến trúc hybrid+ 3 chặng vẫn đúng nhưng **deferred** thành Stage B.
- ✅ Heuristic minh bạch, KHÔNG ML (YAGNI). Không dùng `fact_payments` (rỗng), `customer_type` (dở).

## PLATFORM — Hug (dùng chung mọi campaign Stage A+)

| | Mục tiêu | Status |
|---|---|---|
| [**Hug**](./phase-hug-dynamic-touchpoint-platform.md) · [discussion](./discussion-hug.md) | Dynamic touchpoint: QR câm in 1 lần → server route campaign tốt nhất, đa-campaign, smart tracking, cầu nối định danh, voucher engine. A2/A3/loyalty/review **chạy trên Hug**. Hosting reuse CF Worker+D1 (≈$0); token opaque. | 🟢 thiết kế xong → implement |

## STAGE A — Funnel-first (NOW) · ROI nhanh

| Phase | Mục tiêu | Tập khách | Status |
|---|---|---|---|
| [A1](./phase-a1-customer-tiering-mart.md) | Tiering mart — **7 tier** (LIVE_CORE 56 / SECOND_ORDER 27 / DORMANT_VALUABLE 122 / LAPSED_VALUABLE 1.144 / MASKED_REPEAT 433 / NONBUYER 1.598 / GRAVEYARD 4.183) | 7,563 | 🟢 IMPLEMENTED (parse+validate; chờ build) |
| [A2](./phase-a2-identity-capture-funnel.md) | Identity capture (qua **Hug**) → masked thành contactable; mở khóa 683M CM | 364 masked-repeat | 🔵 ưu tiên cao nhất |
| [A3](./phase-a3-second-order-activation.md) | Đẩy đơn-2 (nudge ngày 7–10, voucher 50–75K, qua **Hug**) | SECOND_ORDER ~27↑ | 🟢 thiết kế xong |
| [A4](./phase-a4-oneshot-winback-suppress.md) | One-shot win-back: DORMANT_VALUABLE (122, ưu tiên) + LAPSED_VALUABLE (1.144, thử→đo→suppress); nghĩa địa/NONBUYER suppress | 122 + 1.144 | 🟢 thiết kế xong |

## STAGE B — NBA Engine 3 chặng (LATER) · đầu tư khi active base lớn

| Phase | Mục tiêu | Status |
|---|---|---|
| B-v1 (thin) | Next-best-action tối giản cho **live core ~83** | ⛔ sau Stage A |
| [B1–B5](./phase-01-warehouse-scoring-foundation.md) | Engine đầy đủ: warehouse scoring → CRM scoring → rule engine → CS surface → feedback. Chi tiết: phase-01..05 (Stage B reference) | ⛔ deferred |

> Stage B detail = phase-01..05 (thiết kế engine đầy đủ, giữ nguyên). Thin v1 = lát cắt tối giản của thiết kế đó cho ~83 live core.

## Quyết định mở (bàn tiếp)

- A1: định nghĩa tier cuối + ngưỡng (live core, dormant-valuable, masked-repeat, second-order, graveyard).
- A2: cơ chế capture (QR→Zalo OA flow), tracking masked→contactable, ưu đãi opt-in, ZNS sau.
- Ladder v2 (discussion §16): map tier → objective → action.
- Engine §14 (#1 trọng số, #3 contactability state): hoãn tới Stage B.

## Next

Stage A + Hug **thiết kế xong**. Triển khai theo [`build-order.md`](./build-order.md): `M0 foundation → M2 Hug skeleton → M4 capture (thin slice) → M3 token → M5 A2 go-live`; M1 (A4/A3 revenue) song song. Verify sớm: Sapo coupon API · Zalo deep-link ref.
