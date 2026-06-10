---
title: "Open Decisions — Các quyết định chiến lược chưa chốt"
stage: 3
status: open
source: sales-slowdown-diagnosis-and-action-playbook.md §0.5.2
---

# Open Decisions — Các quyết định chiến lược chưa chốt

> Mỗi quyết định dưới đây ảnh hưởng trực tiếp đến thứ tự và nội dung của các stage tiếp theo.
> Khi chốt → ghi vào [decision-log.md](./decision-log.md).

---

## Quyết định 1 — "Ế" đau nhất là dòng tiền tháng này hay tăng trưởng bền vững?

**Bối cảnh**
B2B collapse (T1→T5: 278tr → 2tr) gây bế tắc dòng tiền ngay. B2C retention (M1 repeat 3–17%) là
bệnh mạn tính cần 2 quý để thấy kết quả. Hai hướng không loại trừ nhau — khác nhau ở **đốt gì trước**.

**Các lựa chọn**
- **B2B-first:** tuần này gọi 5–10 khách sỉ đã ngừng, hỏi nguyên nhân, reactivate ngay.
  Dòng tiền trong tháng. Rủi ro: B2B có thể không phục hồi được nếu nguyên nhân cấu trúc.
- **B2C-first:** theo thứ tự 0.4 (3-touchpoint → call-list lẻ → infra). Retention dài hạn.
  Rủi ro: không trả hóa đơn tháng tới.

**Cập nhật 2026-06-09 (từ điều tra B2B):** B2B không sụp (cầu 2026 = 2–3× 2025; "sụp" là artifact completed-only + COD lag + 491tr OPEN) → urgency B2B-first giảm mạnh → nghiêng **B2C-first + điều tra cashflow**. Xem [b2b-collapse-root-cause](../02-understand/b2b-collapse-root-cause.md).

**Cập nhật 2026-06-09 — ĐÃ CHỐT:** chủ chọn FOCUS = B2C/retail (cá nhân). B2B-first gác lại. Còn lại trong retail: chọn mũi nhọn nào → chấm điểm 7 card ở [retail-offline-plays](../04-opportunities/retail-offline-plays.md) bằng [evaluation-framework](./evaluation-framework.md).

**Ảnh hưởng**
- Stage 04 (opportunities): thứ tự ưu tiên cơ hội thay đổi hoàn toàn
- Stage 05 (action-plans): plan B2B-first khác plan B2C-first ở tuần đầu
- [sequencing.md](./sequencing.md): bảng thứ tự đốt lửa phụ thuộc quyết định này

**Status: RESOLVED** (2026-06-09: chủ chọn retail/B2C)

---

## Quyết định 2 — Đã biết nhóm sỉ 2025 vỡ vì gì chưa?

**Bối cảnh**
B2B T1 2025: ~42 đơn → T5 2025: đáy gần-chết (8 đơn, 20tr). Data không thấy nguyên nhân —
có thể là OOS hero-SKU, tăng giá, mất sales chủ chốt, công nợ đọng, đối tác đổi nguồn, hay
sự kiện cụ thể nào đó. Xem phân tích supply-side tại
[../02-understand/b2b-collapse-root-cause.md](../02-understand/b2b-collapse-root-cause.md).

**Các lựa chọn**
- **Đã biết:** bỏ qua bước điều tra, đi thẳng vào reactivation với context đúng.
- **Chưa biết:** phải hỏi chính chủ/sales lead trước khi gọi khách sỉ —
  *"Chính xác chuyện gì xảy ra Q1–Q2 2025 khiến B2B rơi?"*
  Câu trả lời là 1 sự kiện cụ thể mà không model retention nào thấy được.

**Cập nhật 2026-06-09 (từ điều tra B2B):** câu hỏi định lượng ("sụp bao nhiêu?") đã trả lời — B2B KHÔNG sụp thật, là artifact đo lường. Câu hỏi định tính (nguyên nhân 2025 vỡ) vẫn còn giá trị nếu cần reactivate B2B sau, nhưng không còn chặn hành động ngay. Xem [b2b-collapse-root-cause](../02-understand/b2b-collapse-root-cause.md).

**Ảnh hưởng**
- Nếu chưa biết: chặn Quyết định 1 (không thể reactivate B2B hiệu quả nếu chưa hiểu lý do vỡ)
- Stage 02 (understand): b2b-collapse-root-cause.md cần được điền trước

**Status: OPEN** (chờ chủ xác nhận hướng — cashflow/margin/B2C là nghi phạm mới)

---

## Quyết định 3 — Công suất CSKH: một mũi nhọn hay chạy song song 5 luồng?

**Bối cảnh**
Plan hiện tại có 5 luồng hành động (CALL_NOW, WIN_BACK, REORDER_NUDGE, SECOND_ORDER, BULK) +
3-touchpoint sequence + US-gift outbound. Đội mỏng + CSKH giới hạn cuộc/ngày → dàn mỏng = không
luồng nào đủ lực. C8 (KISS): chọn 1 wedge thắng trước — *1 segment × 1 hero-SKU × 1 message × 2 tuần*.

**Các lựa chọn**
- **Một mũi nhọn (C8):** chọn 1 luồng duy nhất cho tuần đầu, đo win, rồi mở rộng.
  Ví dụ: chỉ làm B2B-reactivation (nếu chọn B2B-first) hoặc chỉ làm CALL_NOW + WIN_BACK top 35.
- **Song song có kiểm soát:** chạy 2–3 luồng nhưng phân owner rõ (Sales lead / CSKH / Marketing)
  và giới hạn tổng cuộc/ngày theo thực tế.

**Ảnh hưởng**
- Stage 04 (opportunities): số cơ hội được promote lên plan phụ thuộc quyết định này
- Stage 05 (action-plans): scope tuần 1 thay đổi
- [evaluation-framework.md](./evaluation-framework.md): tiêu chí Effort cần phản ánh công suất thực tế

**Status: OPEN**
