# {Document Title}

> **Dành cho:** {audience}
> **Cập nhật:** {date}
> **Bảo trì:** {owner}

## Tài liệu này trả lời những câu hỏi nào?

1. {question — phrased as a real question a business user would ask}
2. {question}
3. {question}

---

## TL;DR — Minimal Correct Mental Model

- {bullet 1 — the most important correction to common assumption}
- {bullet 2 — key distinction most people get wrong}
- {bullet 3 — how the system is organized}
- {bullet 4 — the biggest trap to avoid}
- {bullet 5 — where the source of truth lives}

---

## PHẦN A: HƯỚNG DẪN CHO NGƯỜI TẠO BÁO CÁO

---

## 1. Bảng tham chiếu nhanh

| Tôi muốn xem... | Gom nhóm theo | Ví dụ kết quả |
|---|---|---|
| {use case — phrased as user's question} | {dimension name} | {example output} |

---

## 2. Khái niệm chính

### 2.1. {Concept A}

{Explanation — lead with where the reader's intuition is likely wrong, then define correctly}

### 2.2. {Concept B}

{Explanation}

---

## 3. {Highest-Impact Domain Tension — give it a descriptive title}

{This section exists because confusing these two concepts causes the largest financial error.}

### {Side A} vs {Side B}

{Clear definition of each side}

{Visual: tree, table, or diagram showing the difference}

| Câu hỏi | Cách hiểu | Filter cần dùng |
|---|---|---|
| {ambiguous question 1} | {interpretation A} | {exact filter} |
| {ambiguous question 1} | {interpretation B} | {exact filter} |

---

## 4. Những hiểu nhầm thường gặp

1. **"{Concept X} ≠ {Concept Y}"** — {Difference}. {Operational consequence: what goes wrong in reports if confused.}

2. **"{Concept M} ≠ {Concept N}"** — {Difference}. {Consequence.}

3. **"{Concept P} ≠ {Concept Q}"** — {Difference}. {Consequence.}

---

## 5. Ví dụ thực tế

### Ví dụ 1: "{Real question from a business user}"

> {Step-by-step: which dimension to use, which filter to apply, expected result}

### Ví dụ 2: "{Another real question}"

> {Step-by-step}

---

## 6. Cheat Sheet

| Thuật ngữ báo cáo | Bảng | Tên cột | Giá trị mẫu |
|---|---|---|---|
| {business term} | {table_name} | {column_name} | {example values} |

---

## PHẦN B: TÀI LIỆU KỸ THUẬT

---

## 7. Kiến trúc dữ liệu

{Mermaid ER diagram showing how concepts map to tables}

---

## 8. Dữ liệu tham chiếu (Seed Files)

### 8.1. {seed_file_name}

> **File:** `{path}`

| Cột | Kiểu | Bắt buộc | Mô tả | Ví dụ |
|---|---|---|---|---|
| {col} | {type} | {yes/no} | {desc} | {example} |

---

## 9. Logic xây dựng Model

{Step-by-step derivation logic, not just "see the SQL"}

---

## 10. Quy trình vận hành

### Khi {trigger event — e.g., "thêm nguồn đơn hàng mới"}

1. {step}
2. {step}
3. {step — include verification}

### Khi {trigger event 2}

1. {step}
2. {step}

---

## 11. Chất lượng dữ liệu

| Rủi ro | Ảnh hưởng | Cách phát hiện | Cách xử lý |
|---|---|---|---|
| {risk} | {impact} | {detection query or method} | {remediation steps} |

---

## Decision Log

| Quyết định | Trạng thái | Ngày | Xác nhận bởi | Ghi chú |
|---|---|---|---|---|
| {decision} | ĐÃ XÁC NHẬN | {date} | {who} | {note} |
| {decision} | ĐỀ XUẤT | — | — | {note} |

---

## Câu hỏi mở

| Câu hỏi | Trạng thái | Ghi chú |
|---|---|---|
| {question} | CẦN XÁC NHẬN | {context} |

---

## Kết luận

> "{One sentence, under 200 characters — the single most important mental model shift this document teaches.}"
