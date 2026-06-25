# Pilot Run 1 — 31 kịch bản thật cho sale

Template **v2** (đã khóa) + writer **GPT** + 31 khách cohort (`retail-cohort-payloads.json`).
Consent: **allowed** (chính sách: không có dữ liệu consent → mặc định liên hệ được).

## Cấu trúc
```
pilot-run-1/
├── prompts/    script-{NN}-{customer_id}.txt   ← 31 prompt ráp sẵn (NN theo run_priority)
└── scripts/    script-{NN}-{customer_id}.json  ← BẠN thả 31 output GPT vào đây (cùng base name, đổi .txt→.json)
```

## Quy trình Giai đoạn B
1. **Sinh script:** chạy 31 file `prompts/script-*.txt` trên **GPT** (theo thứ tự NN — ưu tiên cao trước) → lưu `scripts/` cùng tên, đổi đuôi `.txt`→`.json`.
2. **Sale QA:** sale đọc từng script, đánh dấu `dùng ngay` / `sửa nhẹ` / `bỏ`. **Đạt nếu ≥70% dùng ngay/sửa nhẹ.**
3. **Chạy thật + đo:** gọi/nhắn theo script. Đo: liên hệ được · phản hồi tích cực · quay lại mua trong 30 ngày.

## Khi xong bước 1 → đưa tôi
Tôi spot-check vài script (gate có bắn nhầm không, số có khớp data không, FULL_PRICE/margin có đúng không) trước khi sale QA hàng loạt.

## Câu hỏi mở (bước 3)
- Đo theo **nhóm đối chứng** (1 nhóm có script vs 1 nhóm không) hay **trước-sau** (so cùng nhóm)? — quyết khi tới đo.
