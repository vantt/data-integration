# Customer Insight & Approach-Script — Hướng dẫn dùng bộ file

Mục tiêu dự án: từ dữ liệu khách (customer360) → AI sinh **chân dung + kịch bản tiếp cận cá nhân hóa** cho sale.
Giai đoạn hiện tại: **(a)** làm + kiểm thử template prompt trước khi đầu tư hạ tầng.

---

## 0. Bản đồ nhanh — file nào, lúc nào

```
THIẾT KẾ        customer-insight-prompt-template.md   ← nguồn chân lý (template + contract + meta-review)
                          │
CHỌN KHÁCH      retail-ai-outreach-cohort.sql         ← lọc tập retail đáng chạy
                          │
DỮ LIỆU TEST    *-payloads.json                       ← khách thật (đã mask phone) để nạp prompt
                          │
LẮP SẴN         assembled-prompts/*.txt               ← template + 1 khách, dán-một-phát
                          │
CHẠY & CHẤM     pilot-runbook.md                      ← quy trình bake-off + rubric + pilot
                judge-prompt.md                       ← prompt chấm chéo 3 kịch bản/ca
                          │
THAM CHIẾU      baselines/*.json                       ← output mẫu của Claude để so sánh
```

Thứ tự đọc lần đầu: **`master-flow.md` (toàn cảnh) → README (file này) → template.md → pilot-runbook.md**. Còn lại tra khi cần.

> 📌 `master-flow.md` = tài liệu cái-nhìn-tổng: gộp toàn bộ quy trình 3 giai đoạn, 3 prompt, bảng 15 ô đọc 2 chiều, luật vàng. Đọc trước hết.

---

## 1. `customer-insight-prompt-template.md` — NGUỒN CHÂN LÝ

Trái tim của dự án. Gồm 3 phần:

| Phần | Là gì | Dùng khi nào |
|---|---|---|
| **PHẦN 1 — Prompt Template** | Khối `[SYSTEM]/[DATA]/[TASK]/[OUTPUT SCHEMA]` chạy thật | Mỗi lần sinh kịch bản cho 1 khách |
| **PHẦN 2 — Input Contract** | Từ điển field + ví dụ payload | Khi cần hiểu trường dữ liệu nào nghĩa gì |
| **PHẦN 3 — Meta-prompt Review** | Prompt nhờ LLM khác chấm + cải template | Khi muốn nâng cấp template (bake-off) |

**Cách dùng PHẦN 1 (thủ công):** copy nguyên khối ```text``` → thay 5 placeholder `{{...}}` bằng dữ liệu 1 khách → dán vào LLM → nhận JSON.
> Đỡ phải thay tay: dùng file trong `assembled-prompts/` (xem mục 4).

**Cách dùng PHẦN 3:** copy PHẦN 3 + PHẦN 1 → dán vào GPT/Gemini/... → nó trả bảng điểm + bản template cải thiện.

⚠️ Đây là file **được sửa nhiều lần** (v1 → v2...). Mọi thay đổi quy tắc/schema sửa Ở ĐÂY, các file khác bám theo.

---

## 2. `retail-ai-outreach-cohort.sql` — LỌC KHÁCH ĐÁNG CHẠY

Query chọn khách RETAIL **đáng** để AI viết kịch bản (loại data bẩn + không đáng công).

**Lọc gì:** liên hệ được · không phải đại lý · margin lành · ≥2 đơn + có sản phẩm neo · còn cứu được (recency ≤270 ngày) · giá trị cao hoặc đang trong cửa sổ mua. Có cột `run_priority` để xếp hàng đợi gọi.

**Dùng khi nào:** mỗi đợt muốn tạo danh sách khách mới để chạy (cohort động theo thời gian).
**Chạy ở đâu:** Metabase / pipeline dùng `FROM main_marts.dim_customers`. Chạy local trên host thì đổi FROM sang `read_parquet('app_data/.../dim_customers/*.parquet')` (ghi chú có sẵn đầu file).
**Chỉnh:** muốn nhiều khách hơn → nới `recency_days` (≤365=41, ≤540=60 khách).

---

## 3. `*-payloads.json` — DỮ LIỆU KHÁCH (đã mask phone)

Ba file, ba mục đích khác nhau:

| File | Nội dung | Dùng để |
|---|---|---|
| `retail-cohort-payloads.json` | **31 khách pilot** (≤270 ngày), sắp theo `run_priority` | Chạy **pilot thật** — sinh script cho sale |
| `retail-customer-test-payloads.json` | **5 khách đa trạng thái** (active/at-risk/churned/new/full-price) | **Bake-off** — test template trên đủ tình huống |
| `real-customer-test-payloads.json` | 3 khách hỗn hợp (gồm 1 sỉ) | Tham khảo ban đầu (không dùng cho pilot retail) |

**Cấu trúc mỗi phần tử:**
```
{ "data_as_of": "...", "run_priority": 73,   ← chỉ để xếp hàng, KHÔNG nạp vào prompt
  "customer_json": { ...toàn bộ field khách... },  ← phần nạp vào [DATA]
  "recent_notes": [], "recent_conversations": [], "tags": [] }
```
**Lưu ý:** phone đã mask (`0984****39`) để không lộ PII; không ảnh hưởng chất lượng test. `consent_contact="unknown"` vì warehouse chưa có — phải join CRM trước khi gọi thật.

---

## 4. `assembled-prompts/*.txt` — PROMPT DÁN-MỘT-PHÁT

5 file = **PHẦN 1 template + 1 khách đã ráp sẵn**. Không cần đụng template, **mở file → copy hết → dán vào LLM → chạy**.

| File | Khách | Test điều gì |
|---|---|---|
| `prompt-01-active_due_soon.txt` | Hoàng Thức | ca chuẩn (nhắc mua lại) |
| `prompt-02-at_risk.txt` | VIP 121M, rớt nhịp | cứu khách giá trị cao |
| `prompt-03-churned_highvalue_winback.txt` | "Leflair" | **bẫy data bẩn** |
| `prompt-04-new.txt` | NEW ngủ đông 3 năm | **bẫy nhãn sai** |
| `prompt-05-full_price_nonpromo.txt` | FULL_PRICE | bán không khuyến mãi |

Dùng cho **bake-off**: chạy 5 file này trên từng LLM rồi chấm điểm.
> File này **sinh ra từ template + payload**. Khi có template v2, ráp lại bằng script đã dùng (mục "Tạo lại" cuối file).

---

## 5. `baselines/*.json` — OUTPUT MẪU CỦA CLAUDE

5 output Claude tạo từ 5 prompt bake-off — **cột tham chiếu** trong bảng so sánh LLM.

**Dùng khi nào:** khi chạy GPT/Gemini/... cho cùng 5 ca, so output của chúng với Claude để xem ai viết tốt hơn.
**Điểm nhấn:** xem `output-claude-03` và `04` — cách Claude **không sa 2 bẫy** (Leflair → `recommended=false`; NEW ngủ đông → win-back không chào-mừng).
⚠️ Đừng để Claude tự chấm điểm mình — sale chấm mù cả cột Claude lẫn các LLM khác.

---

## 6. `pilot-runbook.md` — QUY TRÌNH CHẠY

Hướng dẫn từng bước, chia 2 hoạt động:
- **A — Bake-off:** ít khách × nhiều LLM → chọn LLM tốt nhất + cải template (làm TRƯỚC). Có rubric chấm 6 tiêu chí.
- **B — Pilot thật:** 31 khách × 1 LLM → sinh script cho sale (làm SAU khi có v2). Có bước join consent + QA + đo kết quả.

Đây là file **mở ra làm theo** khi bắt đầu chạy.

---

## Luồng end-to-end (gộp lại)

```
1. (đã xong) Thiết kế template v1            → template.md
2. (đã xong) Lọc cohort + export payload     → cohort.sql + *-payloads.json
3. ►BẠN: Bake-off                            → assembled-prompts/ + pilot-runbook §A
        chạy 5 prompt × 3-4 LLM, chấm rubric,
        chạy meta-prompt (PHẦN 3) lấy bản cải thiện
4. ►GỬI TÔI: bảng điểm + bản cải thiện        → tôi hợp nhất → template v2
5. Pilot thật v2                             → retail-cohort-payloads.json + runbook §B
        join consent → sinh 31 script → sale QA → chạy → đo
6. Nếu đạt: productionize                     → wire vào CacheInsight (plan riêng)
```

**Việc tiếp theo của bạn = bước 3** (Bake-off). Mọi thứ cần đã nằm trong `assembled-prompts/` và `pilot-runbook.md`.

---

## Tạo lại assembled-prompts khi có template v2
Sau khi template.md cập nhật, chạy lại script ráp prompt (đã dùng ở phiên trước): đọc khối ```text``` trong PHẦN 1 + từng payload → ghi đè `assembled-prompts/*.txt`. Báo tôi, tôi chạy lại giúp.
