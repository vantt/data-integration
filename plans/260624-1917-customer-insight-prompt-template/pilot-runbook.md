# Pilot Runbook — Customer Insight & Approach Script

Hướng dẫn chạy pilot từ template v1 → chọn LLM tốt nhất → cải template v2 → sinh script thật cho sale.

**Nguyên tắc:** tách 2 hoạt động. Đừng gộp.
- **Hoạt động A — Bake-off** (chọn LLM + cải template): ít khách, nhiều LLM. Làm TRƯỚC.
- **Hoạt động B — Pilot thật** (sinh script cho sale dùng): nhiều khách, 1 LLM tốt nhất. Làm SAU khi có v2.

---

## HOẠT ĐỘNG A — Bake-off chọn LLM & cải template

### A1. Chọn 3-4 LLM để so
Gợi ý: Claude (đã có baseline), GPT-4o/o-series, Gemini 2.x, DeepSeek. Càng đa dạng càng tốt.

### A2. Sinh kịch bản — dùng prompt lắp sẵn (không cần copy template)
Thư mục `assembled-prompts/` có 5 file, mỗi file = template v1 + 1 khách, **dán nguyên file vào LLM là chạy**:

| File | Trạng thái khách | Test điều gì |
|---|---|---|
| `prompt-01-active_due_soon.txt` | Active, sắp tới kỳ mua | ca chuẩn — nhắc mua lại + promo hợp lý |
| `prompt-02-at_risk.txt` | VIP 121M, 135 ngày | cứu khách giá-trị-cao trước khi rớt |
| `prompt-03-churned_highvalue_winback.txt` | "Leflair" (B2B nhầm RETAIL) | **bẫy**: LLM có nhận ra data bẩn / margin âm không |
| `prompt-04-new.txt` | NEW nhưng ngủ đông 1101 ngày | **bẫy**: có dùng nhầm giọng chào-mừng không |
| `prompt-05-full_price_nonpromo.txt` | FULL_PRICE, ngủ đông sâu | bán không-khuyến-mãi + win-back |

> 2 ca "bẫy" (03, 04) là phép thử quan trọng nhất — LLM nào sa bẫy = loại.

**Cách làm:** với mỗi LLM, chạy lần lượt 5 file → lưu output JSON. Đặt tên `output-{llm}-{case}.json` (vd `output-gpt-01.json`).

### A3. Chấm điểm mỗi output (rubric 0-2 mỗi tiêu chí)
| # | Tiêu chí | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | **Không bịa số** | bịa số không có trong data | mơ hồ | chỉ dùng số đã cho |
| 2 | **Tuân thủ rule** (consent/margin/promo) | vi phạm | thiếu sót | đúng hết |
| 3 | **Nhận diện bẫy** (data bẩn ca 03/04) | sa bẫy | nửa vời | nêu rõ trong data_gaps/risk |
| 4 | **Kịch bản dùng được** (sale đọc là gọi được) | vô dụng | cần sửa | dùng ngay |
| 5 | **Giọng đúng segment** + thuần Việt | sai | ổn | tự nhiên, đúng |
| 6 | **Schema JSON hợp lệ** (parse được) | lỗi | thiếu field | đủ, đúng |

Tối đa 12đ/ca × 5 ca = 60đ/LLM. Ghi vào bảng tổng (mục A5).

### A4. Lấy đề xuất cải template (mỗi LLM)
Mở `customer-insight-prompt-template.md` → copy **PHẦN 3 (META-PROMPT REVIEW)** + **PHẦN 1** → dán vào từng LLM. Nó trả về bảng điểm 7 tiêu chí + top 5 điểm yếu + **một bản template cải thiện**. Lưu lại các bản này.

### A5. Tổng hợp → gửi lại
Điền bảng:

| LLM | Điểm bake-off (/60) | Sa bẫy? | Điểm mạnh template-review | Ghi chú sale |
|---|---|---|---|---|
| Claude | | | | |
| GPT | | | | |
| Gemini | | | | |
| DeepSeek | | | | |

**Gửi tôi:** (a) bảng này, (b) các bản template cải thiện, (c) 2-3 output bạn thấy tốt nhất + tệ nhất.
→ Tôi hợp nhất thành **template v2** (lấy điểm mạnh mỗi bản, sửa điểm yếu chung).

---

## HOẠT ĐỘNG B — Pilot thật (sau khi có v2)

### B1. Tiền điều kiện: consent
Cohort hiện `consent_contact=unknown`. **Trước khi gọi thật**, join CRM lấy consent, loại khách `denied`. (Tôi có thể viết bước join này khi tới đó.)

### B2. Sinh 31 script
Dùng template **v2** + `retail-cohort-payloads.json` (31 khách, đã sắp `run_priority`). Chạy trên LLM thắng cuộc. Sinh theo thứ tự priority cao → thấp.

### B3. Sale QA (bắt buộc, không bỏ)
Sale đọc từng script, đánh dấu: `dùng ngay` / `sửa nhẹ` / `bỏ`. Định nghĩa **acceptance**: ≥70% script "dùng ngay hoặc sửa nhẹ" thì template đạt; dưới ngưỡng → quay lại A.

### B4. Chạy thật & đo
Gọi/nhắn theo script. Đo: tỷ lệ liên hệ được, tỷ lệ phản hồi tích cực, tỷ lệ quay lại mua trong 30 ngày. So nhóm có-script vs nhóm đối chứng (nếu tách được).

### B5. Quyết định productionize
Nếu B4 tốt → wire vào `CacheInsight`: batch generate + cache + hiển thị trong Customer 360 UI, re-generate khi có đơn/hội thoại mới. (Phase riêng, tôi lập plan khi tới.)

---

## Refresh cohort (khi cần chạy lại)
```
python -c "..."   # hoặc chạy retail-ai-outreach-cohort.sql trong Metabase
```
Cohort động theo recency → nên refresh trước mỗi đợt pilot. Nới `recency_days` trong SQL nếu cần nhiều khách hơn (≤365→41, ≤540→60).

---

## Checklist nhanh
- [ ] A2: chạy 5 prompt × 3-4 LLM
- [ ] A3: chấm rubric
- [ ] A4: chạy meta-prompt lấy bản cải thiện
- [ ] A5: gửi tôi → nhận v2
- [ ] B1: join consent
- [ ] B2: sinh 31 script (v2)
- [ ] B3: sale QA ≥70%
- [ ] B4: chạy thật + đo
- [ ] B5: productionize nếu đạt

## Unresolved
- Consent join: cần xác định bảng/endpoint CRM chứa `consent_contact` (profile layer) để map `customer_id` → consent.
- Có nhóm đối chứng cho B4 không, hay đo trước-sau?
