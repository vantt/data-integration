# Phase A3 — Second-Order Activation

> Stage A · Status: 🟢 thiết kế xong · Phụ thuộc: A1 (tier) · chạy trên [Hug](./phase-hug-dynamic-touchpoint-platform.md) · Context: [`discussion.md`](./discussion.md) §16 + research/economics report

## Mục tiêu

Biến khách **mua-1-lần → mua-lần-2** trong cửa sổ vàng. Lực tăng trưởng thật cho "bán ế". Target = tier **SECOND_ORDER** (~27 giờ, lớn dần khi A2 feed contactable mới).

## Chốt

- **Cửa sổ:** nudge **ngày 7–10** (probe: median tới đơn-2 = 33d, P25=9d → đón trước khi đóng).
- **Ưu đãi:** voucher **50–75K hoặc free-ship**, valid 30–45d, min-order + loại SKU margin-âm (ride Sapo coupon). An toàn (đơn-2 ≈ 1.26M, CM đơn-đầu 62.6%).
- **Cơ chế:** sequence tự động qua Hug lifecycle / Zalo; **CS task riêng cho value≥SILVER**. Volume nhỏ → nhẹ.

## Related code

- Đọc tier SECOND_ORDER (cache.db) · trigger sequence (Hug campaign lifecycle / Zalo ZNS) · CS task (crm).

## Success criteria

- Second-order rate đo được; nudge đúng cửa sổ 7–10d; voucher an toàn margin.

## Open

- Tự động hoá mức nào khi volume tăng (full sequence vs CS-assist).
