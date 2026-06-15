---
title: "DEC-001 - Decision Register"
stage: 3
status: living
source: sales-slowdown-diagnosis-and-action-playbook.md §0.5.2; stage-03 decision log
updated: 2026-06-15
---

# DEC-001 - Decision Register

**Registry:** [DEC-001](../REGISTRY.md#dec-001)

> File này là source of truth cho **quyết định đã chốt**, **quyết định còn mở**, và **audit trail quyết định** của stage 03. Mặt đọc nhanh của stage vẫn là [README.md](./README.md).

## Cách Đọc

| Bạn cần... | Đọc section |
|---|---|
| Biết quyết định nào đang chặn bước tiếp theo | [Open / Blocking Decisions](#open-blocking-decisions) |
| Đọc reasoning chi tiết cho D1-D3 | [Decision Details](#decision-details) |
| Biết quyết định nào đã chốt ngày nào | [Audit Trail](#audit-trail) |
| Cập nhật quyết định mới | [Cách Cập Nhật](#cach-cap-nhat) |

<a id="open-blocking-decisions"></a>

## Open / Blocking Decisions

| ID | Decision | Status | Current answer | Blocks / unlocks | Detail |
|---|---|---|---|---|---|
| D1 | "Ế" đau nhất là dòng tiền tháng này hay tăng trưởng bền vững? | resolved | Focus = bán lẻ/B2C; cashflow track riêng | Unlock retail priority board; B2B-first không còn là default | [decision-1-focus](#decision-1-focus) |
| D2 | Đã biết nhóm sỉ 2025 vỡ vì gì chưa? | open / lower urgency | B2B không sụp theo số đặt đơn; câu hỏi định tính chỉ còn cần nếu quay lại B2B | Không chặn retail; vẫn liên quan cashflow/margin | [decision-2-b2b-2025](#decision-2-b2b-2025) |
| D3 | Công suất CSKH: một mũi nhọn hay chạy song song? | open | Chưa biết đội chạy được bao nhiêu cuộc/ngày | Chặn scope stage 05/06: một wedge hay nhiều lane song song | [decision-3-cskh-capacity](#decision-3-cskh-capacity) |

<a id="decision-details"></a>

## Decision Details

Mỗi quyết định dưới đây ảnh hưởng trực tiếp đến thứ tự và nội dung của các stage tiếp theo. Khi một quyết định chuyển trạng thái, cập nhật cả detail bên dưới, [Audit Trail](#audit-trail), và bảng `Decisions At A Glance` trong [README.md](./README.md).

<a id="decision-1-focus"></a>

### D1 — "Ế" đau nhất là dòng tiền tháng này hay tăng trưởng bền vững?

**Status:** resolved  
**Resolved date:** 2026-06-09  
**Current answer:** chủ chọn focus = B2C/retail; B2B-first gác lại; cashflow track riêng.

**Bối cảnh**  
B2B collapse (T1→T5: 278tr → 2tr) gây bế tắc dòng tiền ngay. B2C retention (M1 repeat 3–17%) là bệnh mạn tính cần 2 quý để thấy kết quả. Hai hướng không loại trừ nhau; khác nhau ở **đốt gì trước**.

**Các lựa chọn**

- **B2B-first:** tuần này gọi 5–10 khách sỉ đã ngừng, hỏi nguyên nhân, reactivate ngay. Dòng tiền trong tháng. Rủi ro: B2B có thể không phục hồi được nếu nguyên nhân cấu trúc.
- **B2C-first:** theo thứ tự 0.4 (3-touchpoint → call-list lẻ → infra). Retention dài hạn. Rủi ro: không trả hóa đơn tháng tới.

**Cập nhật 2026-06-09 từ điều tra B2B**  
B2B không sụp: cầu 2026 = 2–3× 2025; "sụp" là artifact completed-only + COD lag + 491tr OPEN. Urgency B2B-first giảm mạnh → nghiêng **B2C-first + điều tra cashflow**. Xem [b2b-collapse-root-cause](../02-understand/FIND-004-b2b-collapse-root-cause.md).

**Cập nhật 2026-06-09 — đã chốt**  
Chủ chọn focus = B2C/retail. B2B-first gác lại. Trong retail, mũi nhọn tiếp theo được chọn qua priority board và các opportunity retail.

**Ảnh hưởng**

- Stage 04: thứ tự ưu tiên cơ hội thay đổi hoàn toàn.
- Stage 05: plan B2B-first không còn là default tuần đầu.
- [README.md#resolved-sequencing-note](./README.md#resolved-sequencing-note): sequencing cũ đã được merge và đánh dấu resolved/stale.

<a id="decision-2-b2b-2025"></a>

### D2 — Đã biết nhóm sỉ 2025 vỡ vì gì chưa?

**Status:** open / lower urgency  
**Current answer:** câu hỏi định lượng đã trả lời; câu hỏi định tính còn hữu ích nếu quay lại B2B.

**Bối cảnh**  
B2B T1 2025: ~42 đơn → T5 2025: đáy gần chết (8 đơn, 20tr). Data không thấy nguyên nhân; có thể là OOS hero-SKU, tăng giá, mất sales chủ chốt, công nợ đọng, đối tác đổi nguồn, hoặc sự kiện cụ thể. Xem phân tích supply-side tại [b2b-collapse-root-cause](../02-understand/FIND-004-b2b-collapse-root-cause.md).

**Các lựa chọn**

- **Đã biết:** bỏ qua bước điều tra, đi thẳng vào reactivation với context đúng.
- **Chưa biết:** hỏi chính chủ/sales lead trước khi gọi khách sỉ: "Chính xác chuyện gì xảy ra Q1–Q2 2025 khiến B2B rơi?" Câu trả lời là một sự kiện cụ thể mà model retention không thấy được.

**Cập nhật 2026-06-09 từ điều tra B2B**  
Câu hỏi định lượng ("sụp bao nhiêu?") đã trả lời: B2B không sụp thật, là artifact đo lường. Câu hỏi định tính (nguyên nhân 2025 vỡ) vẫn còn giá trị nếu cần reactivate B2B sau, nhưng không còn chặn hành động retail ngay.

**Ảnh hưởng**

- Không chặn retail.
- Vẫn liên quan cashflow/margin nếu quay lại B2B hoặc thu nợ.
- Nếu chưa biết nguyên nhân, không nên mở B2B reactivation lớn.

<a id="decision-3-cskh-capacity"></a>

### D3 — Công suất CSKH: một mũi nhọn hay chạy song song 5 luồng?

**Status:** open  
**Current answer:** chưa biết đội chạy được bao nhiêu cuộc/ngày.

**Bối cảnh**  
Plan hiện tại có 5 luồng hành động (CALL_NOW, WIN_BACK, REORDER_NUDGE, SECOND_ORDER, BULK) + 3-touchpoint sequence + US-gift outbound. Đội mỏng + CSKH giới hạn cuộc/ngày → dàn mỏng = không luồng nào đủ lực. C8 (KISS): chọn 1 wedge thắng trước — *1 segment × 1 hero-SKU × 1 message × 2 tuần*.

**Các lựa chọn**

- **Một mũi nhọn (C8):** chọn 1 luồng duy nhất cho tuần đầu, đo win, rồi mở rộng. Ví dụ: chỉ làm CALL_NOW + WIN_BACK top 35.
- **Song song có kiểm soát:** chạy 2–3 luồng nhưng phân owner rõ (Sales lead / CSKH / Marketing) và giới hạn tổng cuộc/ngày theo thực tế.

**Ảnh hưởng**

- Stage 04: số cơ hội được promote lên plan phụ thuộc quyết định này.
- Stage 05: scope tuần 1 thay đổi.
- [evaluation-framework.md](./RUBRIC-001-evaluation-framework.md): tiêu chí Effort cần phản ánh công suất thực tế.

<a id="audit-trail"></a>

## Audit Trail

| Ngày | Quyết định | Lý do | Dựa trên finding | Ảnh hưởng |
|---|---|---|---|---|
| 2026-06-09 | Hạ ưu tiên "B2B-first", nghiêng B2C-first + cashflow | Điều tra B2B resolved: cầu B2B 2026 = 2–3× 2025; "sụp" là artifact completed-only + COD lag + 491tr OPEN | [b2b-collapse-root-cause](../02-understand/FIND-004-b2b-collapse-root-cause.md) | Update priority board, spawn cashflow-collection-ar |
| 2026-06-09 | "Ế" nhiều khả năng = cash/công nợ, không phải mất cầu, nhưng chặn bởi data gap | Điều tra cashflow: 2.7 tỷ AR B2B (84% >90 ngày, 77% vào 2 VIP) nhưng `fact_payments` rỗng | [cashflow-collection-ar](../02-understand/INV-001-cashflow-collection-ar.md) | Cần hỏi chủ + fix data trước khi action |
| 2026-06-09 | Chốt focus = bán lẻ/B2C | B2B không phải đám cháy; chủ chọn retail | [b2b-collapse-root-cause](../02-understand/FIND-004-b2b-collapse-root-cause.md) + quyết định chủ | Toàn path ưu tiên retail; đòn bẩy #1 = VOC phỏng vấn khách |
| 2026-06-10 | Ads gác lại; mọi thông điệp marketing đi qua Message Core → adapter mỗi kênh; ưu tiên listing + telesales > ads | Ads đi ngược chẩn đoán leak-first + chưa đo được (ROAS disabled, `fact_payments` rỗng); telesales/ads/listing là cùng một thông điệp | [messaging-core](../04-opportunities/OPP-003-messaging-core.md) | Gom messaging về 1 lõi; ads chờ offer + đo được; build sau product-truth + VOC |
| 2026-06-10 | Không build pipeline product lớn; data đã đủ; chỉ fix Tier 1 (bug margin, product_group, return_reason, inventory coverage); Tier 2 hoãn | 4-agent assessment: `mart_sku_economics` + `fact_sales` + `inventory_health` trả lời được hầu hết; retention theo sản phẩm tính được ngay | [product-performance-assessment](../02-understand/FIND-005-product-performance-assessment.md) | Mũi nhọn retail = xây quanh Cordyceps + gateway Gaba/Chondroitin; reframe portfolio sức khỏe người lớn tuổi |
| 2026-06-10 | Fix bug margin: COGS ×10 overcount (5 SKU H010, MISA ghi theo Hộp) — seed `misa_qty_multiplier=1` + thêm cột `realized_margin_pct` | H010 không bán dưới giá vốn; "lỗ 440M" là artifact hoàn toàn; biên thực +59–83% | [product-performance-assessment](../02-understand/FIND-005-product-performance-assessment.md) | Cần materialize qua pipeline; pipeline đã chạy 2026-06-10 03:xx |

<a id="cach-cap-nhat"></a>

## Cách Cập Nhật

1. Quyết định mới nhưng chưa chốt → thêm vào [Open / Blocking Decisions](#open-blocking-decisions) và tạo detail section có anchor ổn định.
2. Khi chốt → đổi status trong detail, thêm dòng vào [Audit Trail](#audit-trail), rồi cập nhật [README.md](./README.md).
3. Nếu quyết định đổi priority hoặc scope execution → cập nhật `Priority Board`, `Ready To Move`, hoặc stage 05/06 liên quan.
4. Nếu quyết định còn thiếu evidence → link về investigation hoặc open question ở stage 02, không tự lấp bằng giả định.
