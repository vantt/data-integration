---
title: "STAGE-02 — Understand: Khám phá & điều tra"
stage: 2
status: living
---

# STAGE-02 — Understand: Khám Phá & Điều Tra

> **Luồng:** ← [01-perspectives](../01-perspectives/) · → [03-evaluate](../03-evaluate/) khi finding đủ rõ để đánh giá hoặc chốt quyết định.

Mục đích: hiểu vấn đề bằng số thật, field evidence, caveat và open question. Đọc [FIND-000-current-diagnosis](./FIND-000-current-diagnosis.md) trước.

## Template

| File | Dùng để |
|---|---|
| [_TEMPLATE-INV-investigation.md](./_TEMPLATE-INV-investigation.md) | Mở investigation/data scan/field audit mới trong stage 02 |

## Findings Đã Chốt

| ID | File | Nội dung |
|---|---|---|
| FIND-000 | [current diagnosis](./FIND-000-current-diagnosis.md) | Tóm tắt hiện trạng mới nhất: focus B2C/retail, B2B artifact, cashflow blocked, retention leak, VOC priority |
| FIND-001 | [channel mix illusion](./FIND-001-channel-mix-illusion.md) | Marketplace che lõi; B2B completed-only nhìn như sụp nhưng cần hiệu chỉnh |
| FIND-002 | [retention leak](./FIND-002-retention-leak.md) | M1 repeat thấp; waterfall point-in-time; model cũ sai 9× |
| FIND-003 | [customer segments](./FIND-003-customer-segments.md) | Tệp 1.082 khách lẻ, Active/At-Risk/Churned, Shopee contactability, US gift asset |
| FIND-004 | [b2b collapse root cause](./FIND-004-b2b-collapse-root-cause.md) | Resolved: B2B không sụp; artifact completed-only + COD lag + OPEN orders |
| FIND-005 | [product performance assessment](./FIND-005-product-performance-assessment.md) | Không cần pipeline product lớn; portfolio là sức khỏe người lớn tuổi; retention theo sản phẩm |
| FIND-006 | [margin activation signals](./FIND-006-margin-activation-signals.md) | Margin thật, delivery, activation signals refresh 2026-06-11 |
| FIND-007 | [fresh scan data market](./FIND-007-fresh-scan-data-market.md) | Fresh scan 2026-06-13: data nội bộ + thị trường + 4 mâu thuẫn cần chốt |
| FIND-008 | [dead-stock customer targeting granularity](./FIND-008-deadstock-customer-targeting-granularity.md) | Probe 2026-06-20: chỉ SKU past-purchase có precision; cây cầu product→customer đang thiếu → OPP-005 |

## Investigations / Questions Đang Mở

| ID | File | Giả thuyết / câu hỏi |
|---|---|---|
| INV-001 | [cashflow collection AR](./INV-001-cashflow-collection-ar.md) | Nghi phạm thật của "ế": AR/COD, dòng tiền thực vs doanh thu kế toán; blocked bởi payment data |
| INV-002 | [demand migration recon](./INV-002-demand-migration-recon.md) | Cầu dịch sang TikTok Shop/livestream thay vì mất hoàn toàn |
| INV-003 | [VOC customer interviews](./INV-003-voc-customer-interviews.md) | Tại sao 72% one-timer không quay lại? |
| INV-004 | [unboxing experience audit](./INV-004-unboxing-experience-audit.md) | Hộp lẻ có card/QR/hướng dẫn không? Follow-up sau mua ra sao? |
| Q-001 | [open questions](./Q-001-open-questions.md) | Câu hỏi dữ liệu/vận hành còn mở |

## Companion

| ID | File | Parent |
|---|---|---|
| COMP-001 | [VOC interview script](./COMP-001-voc-interview-script.md) | [INV-003](./INV-003-voc-customer-interviews.md) |

## Mở Điều Tra Mới

1. Copy [_TEMPLATE-INV-investigation.md](./_TEMPLATE-INV-investigation.md).
2. Dùng prefix `INV-###` nếu đang điều tra, `FIND-###` nếu đã là kết luận evidence-backed, `Q-###` nếu chỉ là câu hỏi mở.
3. Viết TL;DR ở đầu file, kể cả khi kết luận là "chưa biết".
4. Cập nhật README này, [REGISTRY.md](../REGISTRY.md), và [FIND-000](./FIND-000-current-diagnosis.md) nếu diagnosis tổng thay đổi.
5. Nếu có quyết định chiến lược, cập nhật [DEC-001](../03-evaluate/DEC-001-decision-register.md).
