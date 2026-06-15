---
id: "INV-###"
title: "Điều tra: <tên giả thuyết / vấn đề>"
stage: 2
status: open
type: investigation
source: "<file/lens/playbook/report tạo ra điều tra này>"
from:
  - "<LENS/FIND/Q/source-id hoặc path>"
moves_to:
  - "<DEC/OPP/PLAN/stage tiếp theo hoặc pending>"
canonical_anchor: "inv-..."
lens: "<optional: L1/A3/...>"
related_lens: "<optional: ../01-perspectives/...>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: "<optional: ai chịu trách nhiệm điều tra / xác nhận>"
blocker: "<optional: data gap / cần chủ xác nhận / cần field audit>"
---

<a id="inv-..."></a>

# INV-### — Điều tra: <tên giả thuyết / vấn đề>

> **Template intent:** Đây là scaffold mở. Giữ phần identity + lineage rõ ràng, nhưng được quyền thêm, đổi tên, gộp, hoặc xóa các section tùy chọn nếu điều đó làm investigation sắc hơn. Không điền máy móc cho đủ form.

**Registry:** `INV-### -> ../REGISTRY.md#inv-...` *(chỉ bật link thật khi registry row đã tồn tại)*  
**Trạng thái:** `open` — <1 câu mô tả trạng thái hiện tại: đang điều tra, blocked, mostly-resolved, resolved>.  
**Vai trò trong path:** <lens/finding/execution nào sinh ra nghi vấn này> → 02 điều tra → <03 decision / 04 opportunity / 05 plan nào có thể bị ảnh hưởng>.

---

## Required Contract

Phần này là tối thiểu để investigation không bị rời rạc:

| Field | Nội dung |
|---|---|
| Core question | <câu hỏi chính investigation phải trả lời> |
| Why it matters | <vì sao câu hỏi này quan trọng với bài toán "bán ế"> |
| From | <source/lens/finding/question tạo ra investigation> |
| Moves to | <decision/opportunity/plan/stage sẽ nhận kết quả> |
| Evidence needed | <data, phỏng vấn, audit, owner confirmation cần có> |
| Current confidence | `high / medium / low / mixed` + 1 câu lý do |

---

## Kết Luận Tạm Thời — TL;DR

> <Kết luận ngắn nhất hiện tại. Nếu chưa có kết luận, ghi rõ "Chưa có kết luận — đang kiểm giả thuyết".>

**Điều đang tin hiện tại:**  
Viết tự nhiên theo số lượng finding thật sự có. Không bắt buộc đúng 3 ý.

- <finding / inference / uncertainty>
- <finding / inference / uncertainty>

**Việc cần làm ngay / ngã rẽ quyết định:**

- <hỏi ai / chạy query gì / audit gì / quyết định gì>

---

## Giả Thuyết / Vấn Đề

<Mô tả giả thuyết hoặc vấn đề cần hiểu. Nêu rõ nếu đây là direct fact, operational inference, hay open question.>

**Nếu giả thuyết đúng thì...**

- <hệ quả chiến lược / hành động sẽ đổi thế nào>

**Nếu giả thuyết sai thì...**

- <điều gì bị loại bỏ / nên dừng làm gì>

---

## Câu Hỏi Cần Trả Lời

Liệt kê bao nhiêu câu hỏi tùy investigation. Ít nhưng sắc tốt hơn nhiều câu hỏi loãng.

1. <câu hỏi cần trả lời>
2. <câu hỏi cần trả lời>

---

## Cách Điều Tra

Chọn format phù hợp: bảng, checklist, query plan, interview plan, crawl plan, hoặc mixed-method. Không cần giữ đúng 3 bước.

| Bước | Làm gì | Nguồn / tool | Output |
|---|---|---|---|
| 1 | <query / phỏng vấn / crawl / audit / đối chiếu> | <DuckDB / Metabase / owner / website / market scan> | <bảng / note / ảnh / quyết định> |

**Ngoài phạm vi hiện tại:**

- <những việc cố ý chưa làm để tránh phình scope>

---

## Nguồn Dữ Liệu & Caveat

| Nguồn | Grain / phạm vi | Dùng để trả lời | Caveat |
|---|---|---|---|
| <fact/mart/report/interview/source> | <order/customer/SKU/month/...> | <câu hỏi nào> | <thiếu gì / bias gì / độ tin cậy> |

**Độ tin cậy hiện tại:** `high / medium / low / mixed`

Lý do:

- <vì sao tin được>
- <vì sao còn mềm / cần xác nhận>

---

## Bằng Chứng / Findings

> Chỉ dùng số lượng finding thật sự có. Có thể đổi thành narrative, table, timeline, hoặc contradiction map nếu phù hợp hơn.

### 1. <Finding chính>

<Diễn giải ngắn, ưu tiên bảng/số cụ thể. Nếu có số cũ bị bác bỏ, giữ provenance và nói rõ vì sao sai.>

| Chỉ số / nhóm | Giá trị | Nhận định |
|---|---:|---|
| <metric> | <value> | <ý nghĩa> |

### 2. <Finding chính khác nếu có>

<Nội dung.>

---

## Mâu Thuẫn / Caveat / Rủi Ro

| Điểm cần cẩn trọng | Vì sao quan trọng | Cần làm gì để chốt |
|---|---|---|
| <mâu thuẫn / caveat> | <ảnh hưởng nếu hiểu sai> | <query / hỏi chủ / field audit> |

---

## Hệ Quả Cho Path

Điền stage nào bị ảnh hưởng; xóa dòng không liên quan.

| Stage | Ảnh hưởng |
|---|---|
| 01-perspectives | <lens nào được củng cố/bác bỏ/sửa> |
| 03-evaluate | <decision/priority nào bị mở/chốt/lật lại> |
| 04-opportunities | <opportunity nào được spawn / drop / đổi ưu tiên> |
| 05-action-plans | <plan nào cần sửa / chưa được promote> |
| 06-execute | <KPI/log/dashboard nào cần theo dõi> |

**Links cần cập nhật nếu kết luận đổi:**

- [ ] [`current-diagnosis.md`](./FIND-000-current-diagnosis.md)
- [ ] [`../03-evaluate/README.md`](../03-evaluate/README.md)
- [ ] [`../03-evaluate/DEC-001-decision-register.md`](../03-evaluate/DEC-001-decision-register.md)
- [ ] [`../04-opportunities/README.md`](../04-opportunities/README.md) hoặc opportunity liên quan
- [ ] [`../05-action-plans/README.md`](../05-action-plans/README.md) nếu đã thành committed plan

---

## Hành Động Đề Xuất / Next Steps

Viết theo số việc thật sự cần làm. Nếu chưa biết next step, nói rõ điều kiện để biết.

1. <việc cần làm đầu tiên, owner nếu biết>
2. <điều kiện để đổi status sang resolved / blocked / dropped>

---

## Optional Deepening Sections

Dùng các section dưới chỉ khi chúng làm investigation tốt hơn. Xóa nếu không cần.

### Counterfactual / Alternative Explanations

<Những cách giải thích khác có thể đúng.>

### Field Notes / Interview Notes

<Tóm tắt VOC/audit/mystery shopping không chứa PII.>

### Query Notes

<SQL/query path/snapshot/timezone đủ để tái kiểm.>

### Decision Notes

<Điều kiện nào sẽ khiến stage 03 phải đổi quyết định hoặc priority.>

---

## Thread Còn Mở

- <câu hỏi còn mở> → link sang [`open-questions.md`](./Q-001-open-questions.md) nếu cần.

---

## Phụ Lục — Phương Pháp / Raw Notes

<Ghi query, cách lọc, snapshot date, timezone, report nguồn, hoặc checklist field audit. Đủ để người sau tái kiểm tra nhưng không làm phần chính bị nặng.>
