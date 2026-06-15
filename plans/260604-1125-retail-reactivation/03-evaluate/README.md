---
title: "STAGE-03 — Evaluate: Decision & Priority Board"
stage: 3
status: living
updated: 2026-06-15
---

# STAGE-03 — Evaluate: Decision & Priority Board

> **Luồng:** ← [02-understand](../02-understand/) findings · → [04-opportunities](../04-opportunities/) candidate actions / [05-action-plans](../05-action-plans/) committed plans.

Stage này là mặt ra quyết định giữa hiểu vấn đề và hành động. Đọc file này trước; decision detail nằm ở [DEC-001](./DEC-001-decision-register.md), rubric nằm ở [RUBRIC-001](./RUBRIC-001-evaluation-framework.md).

## Current Evaluation State

| Chủ đề | Trạng thái hiện tại | Source |
|---|---|---|
| Focus chính | B2C/retail đã chốt; B2B-first gác lại | [DEC-001](./DEC-001-decision-register.md) |
| "Ế" cấp tính | Nhiều khả năng là cashflow/AR hoặc data gap, không phải mất cầu | [INV-001](../02-understand/INV-001-cashflow-collection-ar.md) |
| B2B collapse | Resolved: B2B không sụp thật; số cũ là artifact completed-only + COD lag | [FIND-004](../02-understand/FIND-004-b2b-collapse-root-cause.md) |
| Bottleneck retail | VOC, contactability/Zalo, CSKH capacity, catalog/channel fixes | [FIND-000](../02-understand/FIND-000-current-diagnosis.md) |
| Evaluation output | Ưu tiên hiện tại là priority board; chỉ promote sang 05 khi blocker rõ | [RUBRIC-001](./RUBRIC-001-evaluation-framework.md) |

## Decisions At A Glance

| Decision | Status | Current answer | Blocks / unlocks | Detail |
|---|---|---|---|---|
| "Ế" đau nhất là dòng tiền tháng này hay tăng trưởng bền vững? | resolved | Focus = bán lẻ/B2C; cashflow track riêng | Unlock retail priority board; B2B-first không còn là default | [DEC-001 D1](./DEC-001-decision-register.md#decision-1-focus) |
| Đã biết nhóm sỉ 2025 vỡ vì gì chưa? | open / lower urgency | B2B không sụp theo số đặt đơn; câu hỏi định tính chỉ cần nếu quay lại B2B | Không chặn retail; vẫn liên quan cashflow/margin | [DEC-001 D2](./DEC-001-decision-register.md#decision-2-b2b-2025) |
| Công suất CSKH: một mũi nhọn hay chạy song song? | open | Chưa biết đội chạy được bao nhiêu cuộc/ngày | Chặn scope stage 05/06 | [DEC-001 D3](./DEC-001-decision-register.md#decision-3-cskh-capacity) |
| Ads / messaging | resolved | Ads gác lại; message đi qua Message Core; ưu tiên listing + telesales | Chặn việc đổ ads trước product-truth + VOC | [DEC-001](./DEC-001-decision-register.md#audit-trail) |
| Product-performance pipeline lớn | resolved | Không build pipeline lớn ngay; dùng insight Tier 0 + Tier 1 fixes | Redirect effort sang action/product-truth/VOC | [FIND-005](../02-understand/FIND-005-product-performance-assessment.md) |

## Priority Board

| # | Việc | Impact | Effort | Prize / định lượng | Prereq | Moves to |
|---|---|---|---|---|---|---|
| 1 | Shopee→Zalo QR capture (O2) + lập Zalo OA (O3) | 5 | M | Bắt ~1.925 khách Shopee vô danh; mở flywheel | Zalo OA trước | 04→05 |
| 2 | Gift engine: "quà sức khỏe biếu bố mẹ" (O10) | 5 | M-H | Dòng doanh thu mới lớn nhất; buyer ≠ user + mùa vụ | catalog + Zalo OA | 04→05 |
| 3 | Lái acquisition về gateway SKU + nạp 21 gateway lên web (O1+O9) | 5 | M | +450tr LTV + 1.08 tỷ rev exposure | verify SKU pack | 04→05 |
| 4 | Subscribe & Save 30/45 + onboarding 3-touch | 4 | M | LTV subscriber 2.5-12× | Zalo OA | 04→05 |
| 5 | Gọi action queue 116 khách / 1.17 tỷ (O5) | 4 | L | Tiền ngay, 0-build | owner/CSKH capacity | 05/06 |
| 6 | Thu nợ B2B (cashflow ring-fence) | 5 | L | 605tr unpaid 2026 + AR ~3.9 tỷ | owner/accounting + payment data | 02/03 track riêng |
| 7 | Fix web: bestseller hết hàng + hợp nhất giá 2 site (O8) | 3 | L | Đang mất đơn trực tiếp và tự cắt giá | owner web/catalog | 04→05/06 |
| 8 | Joint liệu trình 90 ngày + testimonial/QR (O11) | 4 | M | Sửa category khớp, episodic→replenish | VOC khớp | 04→05 |
| 9 | VOC phỏng vấn khách | 4 | L | Giải "tại sao" cho churn/kỳ vọng | owner/CSKH | 02→03 |
| 10 | Offline pop-up pocket repeat-cao | 3 | M-H | Đà Nẵng/Cần Thơ/Tây Nguyên repeat 25-33% | venue/owner | 04 |
| 11 | Kênh nhà thuốc chuỗi Long Châu/An Khang | 3 | H | Kênh niềm tin người già | đàm phán | 04 |
| 12 | Verify data gỡ chặn | 2 | L | Reishi margin, `fact_payments`, gift %, SKU pack | data owner | 02/04 |

## Lane Tuần Này

| Lane | Việc | Vì sao làm ngay | Output cần có |
|---|---|---|---|
| Cashflow | Thu nợ B2B / xác nhận AR thật | Nghi phạm cấp tính thật | Cập nhật [INV-001](../02-understand/INV-001-cashflow-collection-ar.md) |
| Revenue now | Gọi 116 khách / 1.17 tỷ từ dashboard 103 | Có tiền gần, 0-build | Execution log + yield |
| Web/channel hygiene | Fix web hết hàng + hợp nhất giá | Đang mất đơn trực tiếp | OPP/PLAN rõ |
| Learning | Bắt đầu 5-10 VOC | Data không trả lời "tại sao" | Pattern đầu tiên feed lại 02/03/04 |
| Infrastructure | Khởi động Zalo OA | Mở QR capture, Subscribe&Save, onboarding | Zalo OA readiness / blocker |

## Blocked / Needs Answer

| Blocker | Blocks | Needed from | Where to update |
|---|---|---|---|
| `fact_payments` rỗng + owner/accounting chưa xác nhận AR | Cashflow ring-fence, thu nợ B2B | Chủ/kế toán + data fix | [INV-001](../02-understand/INV-001-cashflow-collection-ar.md), [Q-001](../02-understand/Q-001-open-questions.md) |
| CSKH capacity chưa rõ | Scope action queue, VOC, one wedge vs parallel | Owner/CSKH lead | [DEC-001 D3](./DEC-001-decision-register.md#decision-3-cskh-capacity) |
| Reishi margin âm chưa rõ artifact hay thật | Gateway SKU / Reishi | Data verification | [Q-001](../02-understand/Q-001-open-questions.md), [OPP-004](../04-opportunities/OPP-004-data-backlog.md) |
| % con-mua-cho-bố-mẹ chưa biết | Gift engine + Subscribe&Save framing | Data/VOC | [Q-001](../02-understand/Q-001-open-questions.md) |
| CAC theo kênh chưa có | Dồn ngân sách acquisition | Marketing/data | [Q-001](../02-understand/Q-001-open-questions.md) |

<a id="resolved-sequencing-note"></a>

## Resolved Sequencing Note

Sequencing cũ đặt câu hỏi **B2B-first vs B2C-first** để hết bế tắc dòng tiền nhanh. Premise đã được cập nhật bởi [FIND-004](../02-understand/FIND-004-b2b-collapse-root-cause.md) và [DEC-001](./DEC-001-decision-register.md): B2B không sụp theo tháng đặt đơn; chủ đã chốt focus retail/B2C; cashflow/B2B track riêng.

## Reference Files

| File | Vai trò |
|---|---|
| [DEC-001-decision-register.md](./DEC-001-decision-register.md) | Register + detail + audit trail của quyết định |
| [RUBRIC-001-evaluation-framework.md](./RUBRIC-001-evaluation-framework.md) | Rubric chấm điểm reusable |

## Cách Cập Nhật Stage 03

1. Finding mới từ 02 làm đổi diagnosis → cập nhật `Current Evaluation State`.
2. Quyết định mới → ghi detail vào [DEC-001](./DEC-001-decision-register.md), rồi cập nhật `Decisions At A Glance`.
3. Opportunity mới từ 04 → chấm bằng [RUBRIC-001](./RUBRIC-001-evaluation-framework.md), rồi thêm vào `Priority Board` nếu active.
4. Item đủ điều kiện sang plan → promote sang [05-action-plans](../05-action-plans/).
5. Execution tạo learning mới → quay lại 02 trước, rồi cập nhật stage 03 nếu priority/decision đổi.
