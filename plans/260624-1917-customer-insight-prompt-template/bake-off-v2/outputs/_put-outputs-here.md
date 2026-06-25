# Bake-off v2 — thả output re-test vào đây

Nguồn prompt: `../../assembled-prompts-v2/` (template v2 — 3 vá: gate B2B/margin, chống bịa, margin mỏng).

Quy ước tên: `{writer}-{NN}.json` — writer ∈ {cgp, dpsk, gem, qwn}, NN ∈ 01..05.
Ví dụ: `cgp-03.json`, `gem-02.json`.

Chạy CẢ 5 ca × 4 writer = 20 output. Xong → báo tôi judge lại.

**Tâm điểm re-judge:**
- **C3 (Leflair):** gate có bắn không? (`recommended=false` + nêu nghi B2B/margin mâu thuẫn)
- **C2 (VIP margin 33%):** luật margin mỏng có kìm bớt giảm-giá-sâu không?
- C1/C4/C5: xác nhận không regression.
