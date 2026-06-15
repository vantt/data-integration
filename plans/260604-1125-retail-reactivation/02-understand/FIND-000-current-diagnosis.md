---
title: "FIND-000 - Current Diagnosis"
created: 2026-06-15
status: living
stage: 2
source: ../06-execute/operating-board.md
---

# FIND-000 - Current Diagnosis

**Registry:** [FIND-000](../REGISTRY.md#find-000)

> Đây là bản tóm tắt hiện trạng mới nhất của chẩn đoán. Chi tiết bằng chứng nằm trong các investigation ở cùng folder. [EXEC-BOARD operating board](./../06-execute/operating-board.md) chỉ giữ vai trò quản lý vận hành sau khi đã hiểu hệ thống.

## Trọng Tâm Hiện Tại

**🎯 Trọng tâm (2026-06-09): BÁN LẺ/B2C.** Đòn bẩy lớn nhất nằm NGOÀI hệ thống — data nói CÁI GÌ không nói TẠI SAO. Việc #1: [VOC phỏng vấn khách](./INV-003-voc-customer-interviews.md).

**⭐ Reframe chiến lược (2026-06-13): "Cỗ máy vs Cối xay".** Bạn đang chạy 2 doanh nghiệp ngược nhau; số cái tốt bị cái dở làm nhiễu → tưởng "ế". "Ế" thật = cashflow + xói mòn base, KHÔNG mất cầu. → [tổng hợp chiến lược + 6 nước đi](./../01-perspectives/PERS-004-engine-vs-treadmill-synthesis.md).

## Bối Cảnh Số 1 Phút

- **"Sụp cấp tính" phần lớn là ẢO GIÁC ĐO LƯỜNG** (cập nhật 2026-06-09): điều tra cho thấy B2B **KHÔNG sụp** —
  cầu 2026 = **2–3× mức 2025**; "T1 278→T5 2tr" là artifact completed-only + lag hoàn tất COD ~46–78 ngày + 491tr đang chờ thu.
  → Nghi phạm "ế" thật = **cashflow** (hàng đã giao chờ thu COD) hoặc **margin**, KHÔNG phải mất cầu. [b2b](./FIND-004-b2b-collapse-root-cause.md) · [cashflow](./INV-001-cashflow-collection-ar.md)
- **Vấn đề mạn tính (THẬT, bền):** **71.8% khách lẻ mua 1 lần**, M1 repeat **3–17%** (lành mạnh 30–50%).
  → **fresh-scan 2026-06-13:** phần lớn one-time KHÔNG phải thiếu cỗ-máy-nhắc mà là **mix sản phẩm-cổng-vào sai** —
  SKU thu hút khách MỚI nhiều nhất = UV Care/Kids/Metabo (repeat 10-14%, ngõ cụt); cordyceps/collagen/fucoidan repeat 29-37%.
- **Tài sản ẩn:** ~824 người nhận quà US (76% tệp liên hệ được) đã dùng sản phẩm, chưa từng tự mua.
- **⭐ fresh-scan 2026-06-13 (6-agent: 4 data + 2 research):** "ế" = (1) **base đơn lẻ co −55%** từ đỉnh 2024 nhưng AOV +57% (ít người mua hơn, mua to hơn) + (2) **cashflow** (64-77% doanh thu T5-T6 UNPAID, AR ~3.9 tỷ). Doanh thu order-date gần phẳng; Jun 2026 **+85% vs Jun 2025**. → [fresh-scan đầy đủ + 4 mâu thuẫn cần chốt](./FIND-007-fresh-scan-data-market.md)

→ Chi tiết số thật: [`02-understand/README.md`](./README.md) · Provenance: [`archive`](../archive/2026-06-04-original-sales-slowdown-playbook.md).

## Reframe Sản Phẩm

**Reframe sản phẩm (2026-06-10):** hero SKU = đồ sức khỏe người lớn tuổi (cordyceps/khớp/tim mạch), KHÔNG phải collagen làm đẹp. Retention theo SẢN PHẨM: Cordyceps dính (25%), Fucoidan bẫy volume (11%), Gaba/Chondroitin gateway vàng. 🔴 bug margin H010 bán dưới giá vốn (~440M). [chi tiết](./FIND-005-product-performance-assessment.md).

## Nhánh Cần Nhớ

| Nhánh | Trạng thái | Source |
|---|---|---|
| B2B collapse | ✅ Resolved: B2B không sụp thật; artifact đo completed-only + COD lag | [`b2b-collapse-root-cause.md`](./FIND-004-b2b-collapse-root-cause.md) |
| Cashflow / AR | 🟠 Blocked: findings mạnh nhưng cần xác nhận chủ/kế toán + fix `fact_payments` | [`cashflow-collection-ar.md`](./INV-001-cashflow-collection-ar.md) |
| B2C retention | 🔴 Vấn đề thật, ưu tiên retail/B2C | [`retention-leak.md`](./FIND-002-retention-leak.md) |
| VOC khách lẻ | 🔴 Open, ưu tiên cao nhất vì data không trả lời "tại sao" | [`voc-customer-interviews.md`](./INV-003-voc-customer-interviews.md) |
| Demand migration | 🔴 Open: cầu có dịch sang TikTok Shop/livestream không? | [`demand-migration-recon.md`](./INV-002-demand-migration-recon.md) |

## Điều Tra Còn Mở Đáng Làm Tuần Này

- [demand-migration](./INV-002-demand-migration-recon.md): cầu dịch sang TikTok Shop/livestream?
- [cashflow-AR](./INV-001-cashflow-collection-ar.md): nghi phạm thật của "ế", nhưng cần xác nhận dữ liệu thanh toán và kế toán.
- [VOC khách hàng](./INV-003-voc-customer-interviews.md): tại sao one-timer không quay lại, ngoài những gì data transactional thấy được.
