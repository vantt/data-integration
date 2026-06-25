# Bake-off v1 — Scorecard & Quy ước đặt tên

Vòng bake-off đầu (template v1). 3 writer × 5 ca = 15 output → judge → chọn LLM + lỗi template.

---

## 1. Cấu trúc thư mục

```
bake-off-v1/
├── scorecard.md                  ← file này (bảng điểm + blind map)
├── outputs/                      ← 15 output writer (BẠN thả vào)
│   ├── gpt-01.json … gpt-05.json
│   ├── gemini-01.json … gemini-05.json
│   └── deepseek-01.json … deepseek-05.json
├── judge/                        ← 5 kết quả chấm (TÔI tạo)
│   └── judge-01.json … judge-05.json
└── template-improvements/        ← bản meta-prompt đề xuất (optional)
    ├── gpt.md  ·  gemini.md  ·  deepseek.md
```

## 2. Quy ước đặt tên — `{writer}-{NN}.json`

| Thành phần | Giá trị | Ghi chú |
|---|---|---|
| `{writer}` | `gpt` · `gemini` · `deepseek` | chữ thường, không dấu cách |
| `{NN}` | `01`…`05` | **khớp số prompt** (`prompt-01` → `gpt-01.json`) |
| đuôi | `.json` | output là JSON |

**Ví dụ:** output của Gemini chạy `prompt-03-churned_highvalue_winback.txt` → lưu `outputs/gemini-03.json`.

> Vì sao kiểu này: sắp xếp gọn, map 1:1 với `assembled-prompts/prompt-NN`, gom theo writer dễ đối chiếu.

## 3. Hai cách nộp output (chọn 1)

- **Cách A — lưu file:** đặt 15 file vào `outputs/` theo tên trên. Tôi đọc từ đó.
- **Cách B — dán vào chat:** dán thẳng, ghi nhãn `gpt-01: {…}`. Nhanh, không cần lưu file.

Cả hai đều được. Lưu file → có hồ sơ; dán chat → nhanh hơn.

## 4. Blind map

⚠️ Blind KHÔNG giữ được vòng này — file đặt tên theo model (`cgp/dpsk/gem/qwn`). Judge chấm theo nội dung + nêu bằng chứng để minh bạch. Vòng v2 nên đổi tên ẩn danh (A/B/C/D) trước khi chấm.

Writer: `cgp`=GPT · `qwn`=Qwen · `dpsk`=DeepSeek · `gem`=Gemini.

## 5. Bảng điểm — 4 writer × 5 ca (/12 mỗi ô)

```
          C1   C2   C3🪤  C4🪤  C5🪤 │ Σ/60 │ ghi chú
cgp(GPT)  11   11    8    11   12  │  53  │ ổn định nhất, kỷ luật margin
qwn(Qwen) 11   11    6    10   11  │  49  │ đều tay, C3 generic
dpsk(DSk) 11   12    6     8   10  │  47  │ margin-aware; C4 bịa "khách hài lòng"
gem(Gem)  10    8    8     9   11  │  46  │ DUY NHẤT bắt Leflair=B2B; giảm-giá-mạnh + overconfident
```

## 6. Kết luận

- **Writer thắng:** 🏆 **cgp (GPT)** 53/60 — ổn định, bắt mâu thuẫn margin C3, xử lý bẫy NEW + FULL_PRICE tốt nhất. Á quân: qwn (Qwen) 49.
- **Lỗi template chung (đọc DỌC):** 🔴 **C3 — cả 4 đều `recommended=true` win-back cá nhân cho Leflair** (nghi B2B + margin âm −150% + chết 3 năm). Template chưa có GATE cứng `recommended=false` cho tài khoản nghi-B2B / margin-mâu-thuẫn / chết-sâu-margin-âm.
- **Template ĐÃ tốt (đọc DỌC):** 🟢 bẫy NEW ngủ đông (C4/C5) + FULL_PRICE (C5) — cả 4 đều xử lý đúng → luật recency>lifecycle & discount_sensitivity hoạt động.
- **Lỗi LẺ (điểm yếu model, không sửa template):** gem giảm-giá-mạnh VIP margin mỏng + overconfident; dpsk bịa cảm nhận khách (C4).
- **Quyết định:** ⏭️ **sửa template → v2** (thêm gate B2B/margin-conflict). Sau v2 chạy lại để xác nhận C3 được vá.

## Bản vá đề xuất cho template v2
1. **[CHÍNH] Gate `recommended=false`:** tên giống tổ chức/sàn (Leflair, Shop, Co, TNHH…) **HOẶC** `is_margin_negative=false` mâu thuẫn `avg_order_contribution_margin_pct<0` **HOẶC** (recency cực lớn + margin âm) → `recommended=false`, hoãn, chuyển xác minh loại tài khoản. Không soạn win-back cá nhân.
2. **Chống bịa cảm nhận:** cấm tự chế đánh giá/trải nghiệm của khách nếu `recent_notes` trống.
3. **Kỷ luật margin mỏng (ĐÃ ÁP 2026-06-25):** `avg_order_contribution_margin_pct < 0.35` → ưu đãi vừa phải, không giảm sâu dù PROMO_DEPENDENT.

→ Cả 3 đã áp vào template v2. Re-test cả 5 ca bằng `assembled-prompts-v2/`.

---

## Trạng thái
- [ ] gpt-01..05
- [ ] gemini-01..05
- [ ] deepseek-01..05
- [ ] judge 5 ca (tôi làm)
- [ ] bảng 15 ô (tôi làm)
- [ ] meta-prompt → template v2 (tôi làm)
