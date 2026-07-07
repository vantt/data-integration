---
name: doc-decision-brief
description: "Write a business-facing brief explaining a completed initiative — the problem it solved, the context behind it, what was built, why this approach was chosen over alternatives, and how it works in enough depth to satisfy a curious reader. Use when a plan/project is done and stakeholders need the story behind it, not just a concept definition (that's doc-domain-knowledge), an operational workflow (that's doc-workflow), or an engineer-only ADR (that's docs/decisions/). Trigger on requests like: 'viết tài liệu giải thích cho biz-user tại sao mình làm feature X', 'viết brief giải thích initiative đã xong cho stakeholder không rành kỹ thuật', 'explain why we built this the way we did', 'viết retrospective cho plan đã hoàn thành'."
---

# Decision Brief Documentation

Explain **why an initiative existed and why it was solved this way** — for a reader who isn't an engineer but needs enough of the "why" to trust the outcome and speak about it credibly.

Reuse [`assets/template.md`](assets/template.md) as scaffold unless the user asks for a different format.

## When this differs from other doc skills

| Skill | Explains | Audience |
|---|---|---|
| `doc-domain-knowledge` | A concept's meaning in the data (static) | Business + technical, dual layer |
| `doc-workflow` | How a process runs end-to-end (ops) | Technical/operational |
| `docs/decisions/` (ADR) | Engineering trade-off record | Engineers only |
| **`doc-decision-brief`** (this) | Why an initiative was built: problem → solution → rationale | Business-first, technical-curious |

Use this skill only when there is a **completed (or near-complete) initiative** with a real problem behind it — not for documenting a static concept or a routine process.

## Core Principle

Every brief must let a business reader answer, unprompted, three questions:

1. What was actually broken/missing before this? (concrete, not abstract — a real case, a real number)
2. What changed?
3. Why this fix and not an easier/cheaper one? (the trade-off that was accepted)

If the reader can't answer these after reading, the brief failed regardless of how accurate it is.

## Structure

1. **TL;DR** (3-5 câu) — vấn đề, giải pháp, tác động. Phải đứng độc lập, đọc xong đủ hiểu 80% cho người bận, copy-paste được vào Slack.
2. **Vấn đề & Bối cảnh** — pain cụ thể (ai gặp, gặp khi nào, hậu quả gì nếu không sửa). Dùng ví dụ thật, không mô tả trừu tượng. VD: không viết "hệ thống thiếu liên kết dữ liệu" mà viết "NV gắn tag risk cho khách B, nhưng khách B vẫn được ưu tiên gọi vì action queue không đọc tag risk".
3. **Giải pháp** — mô tả bằng ngôn ngữ nghiệp vụ trước; thuật ngữ kỹ thuật (nếu cần) giải thích ngay tại chỗ dùng, không dồn vào bảng chú giải cuối bài. **Nếu giải pháp có màn hình/UI thật, vẽ 1 mockup đơn giản ngay trong phần này** (ASCII, nhãn tiếng Việt/nghiệp vụ thật lấy từ phase doc hoặc implementation report — KHÔNG chụp HTML/code thật). "Không code" ≠ "không hình ảnh" — thiếu mockup, reader hiểu khái niệm nhưng không hình dung được giải pháp trông như thế nào khi dùng.
4. **Tại sao chọn cách này** — nêu ít nhất 1 phương án khác đã bị cân nhắc và lý do loại (chi phí, rủi ro, thời gian, giới hạn dữ liệu...). Nếu không có phương án khác thực sự được cân nhắc, đừng bịa ra để có mục này — nói thẳng "đây là cách duy nhất khả thi vì X".
5. **Cách hoạt động (chi tiết)** — dành cho người tò mò hơn, gồm những phần sau khi áp dụng được (bỏ qua phần nào không liên quan, đừng ép):
   - **Luồng dữ liệu/logic** ở mức khái niệm (không code) — chuyện gì xảy ra theo thứ tự.
   - **Hình dạng dữ liệu** bằng khái niệm nghiệp vụ, không phải tên cột/kiểu SQL. VD: "mỗi tag mang theo: tên, ai gắn (người hay tự động), nếu tự động thì từ nguồn nào, đã duyệt hay đang chờ duyệt" — KHÔNG viết "crm_party_tag.source VARCHAR".
   - Nếu chưa có mockup UI ở phần Giải pháp (mục 3), đây là chỗ bù lại — ít nhất 1 UI mockup cho phần phức tạp nhất.
6. **Kết quả & trạng thái** — cái gì đã thay đổi thật (đo được nếu có số), cái gì còn dang dở/deferred và tại sao.

## Gathering Source Material

Khi nguồn là plan(s) đã thực thi trong repo này:

1. **Đọc `plan.md` trước tiên, không phải phase files.** Convention của repo này đặt sẵn bảng "Vấn đề" và sơ đồ "Giải pháp" ngay trong `plan.md` — đó gần như là bản nháp thô của mục 1-2 trong brief, chỉ cần dịch sang ngôn ngữ nghiệp vụ. Đừng tự suy diễn lại từ đầu khi tài liệu nguồn đã có sẵn.
2. **Lấy bằng chứng/con số từ implementation report (`reports/phase-XX-implementation-report.md`), không phải phase spec.** Phase spec là kế hoạch (có thể đổi lúc làm); report có dòng `Summary:` cuối file với số liệu/kết quả xác nhận thật (VD: "939 synced tags", "MANUAL_RISK_REVIEW=1").
3. **Trạng thái ở header `plan.md` có thể cũ (stale).** Nếu `plan.md` ghi "Status: TODO" nhưng thư mục `reports/` đã có report với `Status: DONE`, tin report — không tin header.
4. **Xác minh tài liệu tham khảo THẬT SỰ nói về cùng initiative, không chỉ trùng từ khoá.** VD thực tế: khi viết brief về CRM party tags (risk/vip_tier NV gán), 2 report cũ tên có chữ "tags" hoá ra nói về Sapo order/customer tags (marketing attribution) — một hệ thống tag hoàn toàn khác. Chỉ dùng được 1 chi tiết liên quan thật (root cause `customer_group` JSON blob). Đọc lướt qua trước khi coi là "chất liệu" — đừng ép nội dung không liên quan vào brief chỉ vì tên file khớp.
5. **Khi nhiều plan gộp thành 1 initiative, tìm sợi chỉ xuyên suốt trước khi viết.** Đừng liệt kê 3 plan cạnh nhau như 3 câu chuyện riêng — tìm tài liệu/thiết kế gốc giải thích TẠI SAO chúng thuộc về nhau (thường là 1 note thiết kế UX/kiến trúc được cả 3 plan tham chiếu tới). Dùng đó làm khung TL;DR, rồi mới chia 3 plan thành 3 phần của MỘT giải pháp.

## Anti-patterns

- **Kể lịch sử triển khai thay vì giải thích rationale** — liệt kê "Phase 1 làm X, Phase 2 làm Y" là project history, không phải lý do. Người đọc business không cần biết thứ tự phase, cần biết tại sao.
- **Vấn đề mơ hồ** — "cải thiện trải nghiệm" không phải vấn đề, đó là khẩu hiệu. Vấn đề phải cụ thể đến mức người ngoài cuộc đọc xong tự thấy khó chịu vì nó từng tồn tại.
- **Bỏ qua phương án bị loại** — nếu không giải thích tại sao KHÔNG làm theo cách khác, reader không thể đánh giá quyết định có hợp lý, chỉ có thể tin suông.
- **Trộn TL;DR với chi tiết** — TL;DR phải đứng một mình được.
- **Giải pháp không có gì để hình dung** — mô tả giải pháp chỉ bằng văn xuôi trừu tượng khi thật ra có UI/data thật có thể vẽ ra. Reader hiểu bối cảnh + rationale (vì phần đó cụ thể) nhưng vẫn không hình dung được giải pháp trông ra sao khi dùng — dấu hiệu: đọc xong mục Giải pháp mà không thể tự vẽ lại 1 màn hình hay 1 bản ghi dữ liệu, dù plan gốc có sẵn ASCII wireframe/data structure để dịch lại.

## Reuse from doc-domain-knowledge

Áp dụng nguyên tắc ngôn ngữ dùng chung: tránh jargon không giải thích, evidence-based (link tới plan/report thật thay vì diễn giải lại), một câu kết luận ở cuối mỗi phần dài.

Nếu concept nền tảng trong brief (VD: "tag" là gì, "action queue" là gì) chưa có domain-knowledge doc riêng, cân nhắc link ra thay vì giải thích lại từ đầu — brief này giả định người đọc đã biết khái niệm cơ bản, chỉ tập trung vào QUYẾT ĐỊNH đã đưa ra.
