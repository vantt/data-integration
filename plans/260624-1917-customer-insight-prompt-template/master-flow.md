# Master Flow — Customer Insight & Approach Script

Tài liệu cái-nhìn-tổng: gộp toàn bộ quy trình từ dữ liệu khách → template prompt → kịch bản tiếp cận cá nhân hóa cho sale. Đọc file này trước, các file khác là chi tiết từng bước.

---

## 1. Mục tiêu

Từ dữ liệu khách (customer360) → AI sinh **chân dung + kịch bản tiếp cận cá nhân hóa** để sale gọi/nhắn. Nguyên tắc nền: **mart đã tính sẵn mọi con số (RFM, CLV, margin); LLM chỉ DIỄN GIẢI + VIẾT, không tính, không bịa số.**

Giai đoạn hiện tại: **kiểm thử + chốt template** trước khi đầu tư hạ tầng.

```
DATA khách ─► TEMPLATE (LLM) ─► kịch bản tiếp cận ─► sale gọi/nhắn ─► đo kết quả
              (đã tính sẵn số)   (chân dung+cơ hội+
                                  rủi ro+lời thoại)
```

---

## 2. Từ vựng (chống nhầm — đọc kỹ phần này)

| Thuật ngữ | Là gì |
|---|---|
| **Writer (thí sinh)** | LLM chạy template để **VIẾT** kịch bản. Có 3: A, B, C (vd GPT/Gemini/DeepSeek) |
| **Judge (trọng tài)** | 1 LLM **khác** 3 writer (vd Claude), chỉ **CHẤM** kịch bản |
| **Template (PHẦN 1)** | Prompt sinh kịch bản cho 1 khách |
| **Judge-prompt** | Prompt chấm 3 kịch bản cùng khách |
| **Meta-prompt (PHẦN 3)** | Prompt **sửa template** (nâng cấp v1→v2) |
| **Test set (5 ca)** | 5 khách đa trạng thái — dùng **suốt** lúc tinh chỉnh template |
| **Cohort (31 khách)** | Tập pilot thật — dùng **cuối**, sau khi template ưng ý |
| **Rubric** | Bảng 6 tiêu chí chấm kịch bản (0-2 mỗi tiêu chí, max 12) |
| **Gate (cổng bẫy)** | Lỗi nghiêm trọng (bịa số/sa bẫy/giảm giá khi margin âm) → loại thẳng |

---

## 3. Ba "prompt" — mỗi cái một việc, ĐỪNG lẫn

| Prompt | Tác động lên | Input | Output | Dùng khi |
|---|---|---|---|---|
| **Template** (PHẦN 1) | sinh **kịch bản** | template + 1 khách | JSON kịch bản | mỗi lần cần kịch bản cho 1 khách |
| **Judge-prompt** | chấm **kịch bản** | data khách + 3 kịch bản A/B/C | JSON điểm + xếp hạng | sau khi 3 writer sinh xong, mỗi ca 1 lần |
| **Meta-prompt** (PHẦN 3) | sửa **template** | template + phát hiện lỗi | template cải thiện | sau khi chấm, biết template yếu chỗ nào |

Một dòng: **Template viết · Judge chấm · Meta-prompt sửa template.**

---

## 4. Hai cỡ data — mấu chốt

| | Test set (5 ca) | Cohort (31 khách) |
|---|---|---|
| File | `retail-customer-test-payloads.json` | `retail-cohort-payloads.json` |
| Dùng khi | **suốt** lúc tinh chỉnh template | **chỉ sau** khi template ưng ý |
| Mục đích | thước đo mỗi phiên bản template | pilot thật, sinh script cho sale |

→ Ghép **data nhỏ (5 ca)** vào chạy NGAY từ đầu để đo. Chỉ **data đầy đủ (31)** mới đợi template ưng ý — đừng đốt công sinh 31 script khi template còn sửa.

---

## 5. FLOW LỚN — toàn cảnh 3 giai đoạn

```
┌─────────────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN A — BAKE-OFF + TỐI ƯU TEMPLATE   (data: 5 ca test)         │
│                                                                     │
│   ┌───────────────────────── VÒNG LẶP ──────────────────────────┐   │
│   │ 1. Template vN chạy trên 3 writer × 5 ca → 15 kịch bản       │   │
│   │ 2. Judge chấm: 5 lượt (mỗi ca so 3 bản) → BẢNG 15 Ô          │   │
│   │ 3. Đọc bảng 2 chiều:                                         │   │
│   │      • NGANG → xếp hạng 3 writer (chọn LLM)                  │   │
│   │      • DỌC  → lỗi chung của 3 = lỗi TEMPLATE                 │   │
│   │ 4. Meta-prompt + template vN + lỗi chung → template v(N+1)   │   │
│   │ 5. Chưa đạt ngưỡng? ──► quay lại bước 1 với v(N+1) ──────────┤   │
│   └──────────────────────────┬──────────────────────────────────┘   │
│                       đạt ngưỡng (vd ≥70% sale duyệt, 0 sa bẫy)      │
└──────────────────────────────┼──────────────────────────────────────┘
                               ▼  KHÓA: template ưng ý + LLM thắng
┌─────────────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN B — PILOT THẬT   (data: 31 cohort)                         │
│   1. Join CRM lấy consent → loại 'denied'                           │
│   2. Template-khóa + LLM-thắng → sinh 31 kịch bản                    │
│   3. Sale QA: ≥70% "dùng được" thì đạt                              │
│   4. Gọi/nhắn thật → đo (liên hệ được / phản hồi / quay lại mua 30d) │
└──────────────────────────────┼──────────────────────────────────────┘
                               ▼  nếu kết quả tốt
┌─────────────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN C — PRODUCTIONIZE                                          │
│   Wire vào CacheInsight: batch sinh + cache + hiện trong Customer360 │
│   UI; re-generate khi có đơn/hội thoại mới. (Plan riêng khi tới.)    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. GIAI ĐOẠN A — chi tiết (Bake-off + tối ưu template)

### A1. Sinh kịch bản (3 writer)
Mở `assembled-prompts/*.txt` (template+khách ráp sẵn). Mỗi writer chạy cả 5 file → mỗi writer 5 kịch bản. Tổng **3 × 5 = 15**. Lưu `output-{writer}-{ca}.json`.

### A2. Chấm (judge, chấm chéo)
Dùng **judge-prompt.md** + **1 LLM khác** 3 writer. Chạy **5 lượt** — mỗi lượt 1 ca, dán 3 bản **A/B/C giấu tên** (ngẫu nhiên). Ghi bí mật A/B/C = writer nào.

### A3. Lập BẢNG 15 Ô (số /12 minh họa)
```
         C1    C2    C3🪤   C4🪤   C5  │ Tổng/60 │ sa bẫy
  A      10    9     11     8     9   │   47    │  0
  B       8   11    FAIL   10     7   │  ~36    │  1 (bẫy C3)
  C       9    8     10    FAIL    8   │  ~35    │  1 (bẫy C4)
```

### A4. Đọc bảng theo 2 CHIỀU (đây là chỗ "kết hợp cả 3")
| Chiều | Đọc gì | Để |
|---|---|---|
| **NGANG** (1 writer × 5 ca) | cộng hàng + đếm sa bẫy | **chọn writer thắng** (A) |
| **DỌC** (1 ca × 3 writer) | cột cả-3-đều-thấp = lỗi **template**; chỉ-1-ô-thấp = **writer đó yếu** | **biết sửa template ở đâu** |

> Cùng một bảng. Ngang để chọn LLM, dọc để sửa template. KHÔNG trộn 3 LLM thành một.

### A5. Sửa template (meta-prompt)
Lấy **lỗi CHUNG** (đọc dọc) → đưa cho **meta-prompt (PHẦN 3)** cùng template hiện tại → nhận template cải thiện. Có thể chạy meta-prompt trên **cả 3 writer** rồi gộp ý hay nhất (tùy chọn).
> Chỉ sửa template cho lỗi cả-3-cùng-sai. Lỗi chỉ-1-writer-sai = trừ điểm writer đó, KHÔNG sửa template (tránh khít 1 model).

### A6. Lặp đến khi đạt ngưỡng
Chạy lại template mới trên đúng 5 ca → chấm lại → điểm tăng? Lặp đến khi: sale duyệt ≥70% "dùng được" **và** không writer nào sa bẫy → **khóa template + writer thắng**.

---

## 7. GIAI ĐOẠN B — chi tiết (Pilot thật)

1. **Consent:** join CRM lấy `consent_contact`, loại `denied`. (Cohort hiện `unknown`.)
2. **Sinh 31 kịch bản:** template-khóa + writer-thắng, chạy `retail-cohort-payloads.json` theo thứ tự `run_priority`.
3. **Sale QA** (bắt buộc): đánh dấu `dùng ngay`/`sửa nhẹ`/`bỏ`. Đạt nếu ≥70% "dùng ngay/sửa nhẹ".
4. **Chạy thật + đo:** tỷ lệ liên hệ được, phản hồi tích cực, quay lại mua trong 30 ngày. So nhóm có-script vs đối chứng (nếu tách được).

---

## 8. GIAI ĐOẠN C — Productionize (tóm tắt)

Nếu B đạt → wire vào `CacheInsight`: batch sinh insight + cache + hiển thị trong Customer 360 UI, re-generate khi có đơn/hội thoại mới. Lập plan riêng khi tới đây.

---

## 9. Luật vàng (nguyên tắc xuyên suốt)

1. **Số do DATA, LLM không tính** — chống bịa số tài chính.
2. **Một template chung** — không làm riêng cho từng LLM; phải bền trên nhiều model.
3. **Đọc matrix 2 chiều** — ngang chọn LLM, dọc sửa template.
4. **Lỗi-chung = template; lỗi-lẻ = model.** Chỉ sửa template cho lỗi cả-3-cùng-sai.
5. **Chấm chéo + giấu tên + cổng bẫy** — judge ≠ writer; A/B/C ẩn danh; sa bẫy = loại thẳng.
6. **Đổi 1 biến/lúc** — khóa template thì đổi LLM; khóa LLM thì đổi template. Đừng vặn cả hai.
7. **Sale là trọng tài cuối** — LLM-judge chỉ sàng trước; sale biết khách + giọng VN.
8. **Data nhỏ liên tục, data đầy đủ cuối** — 5 ca đo mỗi vòng; 31 cohort chỉ ở pilot.

---

## 10. Bảng tra: file nào ở bước nào

| Bước | File |
|---|---|
| Hiểu trường dữ liệu | `customer-insight-prompt-template.md` §PHẦN 2 |
| Sinh kịch bản | `assembled-prompts/*.txt` (hoặc §PHẦN 1 + payload) |
| Chấm kịch bản | `judge-prompt.md` |
| Sửa template | `customer-insight-prompt-template.md` §PHẦN 3 |
| Tham chiếu output mẫu | `baselines/*.json` |
| Quy trình + bảng tổng | `pilot-runbook.md` |
| Lọc khách pilot | `retail-ai-outreach-cohort.sql` |
| Data 5 ca test | `retail-customer-test-payloads.json` |
| Data 31 pilot | `retail-cohort-payloads.json` |

---

## 11. Trạng thái hiện tại & việc kế tiếp

**Đã xong:** template v1 (đã vá) · cohort gating + 31 payload · 5 ca test + 5 prompt ráp sẵn · 5 baseline Claude · judge-prompt · runbook · master-flow (file này).

**Việc kế tiếp = GIAI ĐOẠN A:**
1. Chọn 3 writer (GPT/Gemini/DeepSeek) + 1 judge (Claude).
2. Chạy 5 prompt × 3 writer → 15 kịch bản.
3. Judge-prompt chấm 5 lượt → bảng 15 ô.
4. Đọc 2 chiều → chọn writer + gửi tôi lỗi chung → meta-prompt → template v2.
5. Lặp đến khi đạt → khóa → Giai đoạn B.

## Câu hỏi mở (giải khi tới Giai đoạn B)
- Bảng/endpoint CRM nào chứa `consent_contact` để join?
- Đo kết quả B theo nhóm đối chứng hay trước-sau?
