# Bake-off v2 — Phán quyết (judge: Claude, 2026-06-25)

Re-test template v2 (3 vá) trên 4 writer × 5 ca. **Mục tiêu: xác nhận C3 được vá + không regression.**

## Kết quả theo từng vá

| Vá | Ca kiểm | Trước (v1) | Sau (v2) | Kết luận |
|---|---|---|---|---|
| **#1 Gate B2B/margin** | C3 Leflair | cả 4 `recommended=true` win-back cá nhân 🔴 | **cả 4 `recommended=false`** + nêu nghi B2B/mâu thuẫn margin + hoãn xác minh 🟢 | ✅ VÁ THÀNH CÔNG |
| **#3 Margin mỏng** | C2 VIP 33% | gem giảm-giá-sâu + overconfident 🔴 | cả 4 "không giảm sâu vì biên mỏng", chỉ quà nhỏ; **gem chuyển risk=margin** 🟢 | ✅ VÁ THÀNH CÔNG |
| **#2 Chống bịa** | mọi ca | dpsk bịa "khách khen" (C4) 🔴 | cgp/dpsk/qwn thêm do_not "không nói khách từng khen" 🟢 | ✅ VÁ THÀNH CÔNG |

## Regression (chỗ đã tốt — phải giữ)

| Ca | Kiểm | Kết quả |
|---|---|---|
| C1 active | gate KHÔNG bắn nhầm | 🟢 cả 4 `recommended=true`, promo hợp lý (margin khỏe) |
| C4 NEW-dormant | chặn giọng khách-mới | 🟢 cả 4 guard + win-back |
| C5 FULL_PRICE + NEW | không dẫn bằng giảm giá + chặn khách-mới | 🟢 cả 4 mở thoại bằng chăm sóc/giá trị, guard FULL_PRICE |

→ **Không regression.**

## Kết luận

- ✅ **Template v2 ĐẠT** — bẫy C3 vá triệt để, không hồi quy. Tiêu chí acceptance (0 writer sa bẫy) đạt.
- 🏆 **Writer sản xuất: GPT (cgp)** — vẫn ổn định/kỷ luật nhất (giữ ngôi từ v1). Cả 4 giờ đều xử lý bẫy đúng; chênh lệch thu hẹp.
- ⏭️ **KHÓA:** template **v2** + writer **GPT** → chuyển **Giai đoạn B (pilot 31 khách)**.

## Câu hỏi mở cho Giai đoạn B
1. Bảng/endpoint CRM nào chứa `consent_contact` để join (loại `denied` trước khi gọi)?
2. Đo kết quả pilot theo nhóm đối chứng hay trước-sau?
