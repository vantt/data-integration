# Pilot Run 1 — Spot-check (Claude, 2026-06-25)

31 script GPT (template v2) đối chiếu data nguồn `retail-cohort-payloads.json`.

## Kết quả: 31/31 ĐẠT — không lỗi cứng

| Tiêu chí cứng | Kết quả |
|---|---|
| JSON parse | 🟢 31/31 hợp lệ |
| Schema đủ field (top + approach) | 🟢 31/31 |
| **Số liệu khớp data** (lifetime_value, tier) | 🟢 31/31 — **không bịa số** |
| **Gate KHÔNG bắn nhầm** | 🟢 31/31 `recommended=true` (cohort đã loại B2B/margin-âm từ SQL → gate đứng yên đúng) |
| **FULL_PRICE** không dẫn bằng giảm giá | 🟢 các ca FULL_PRICE đều có guard |
| **Margin mỏng (<35%)** không giảm sâu | 🟢 6/6 ca (#09,10,15,22,28,29) đều "không giảm giá sâu vì biên mỏng", kể cả PROMO_DEPENDENT |
| Anti-fab (không bịa cảm nhận) | 🟢 xuất hiện nhất quán ("không bịa phản hồi khách") |
| Không lộ số nội bộ | 🟢 do_not nhất quán |

## Quan sát nhỏ (không chặn)
- Vài tên ngắn/mơ hồ (#29 "BL", #22 "Petter Phạm") — gate KHÔNG bắn (đúng: chỉ bắn tên giống tổ chức rõ ràng). Sale nên để ý khi gọi, nếu phát hiện là tài khoản lạ/đại lý thì bỏ.
- Chất lượng đồng đều: mở thoại chăm sóc-trước, nhắc đúng sản phẩm affinity, multi-channel, thuần Việt.

## Kết luận
✅ **31 script đạt chất lượng production** — chuyển thẳng **Sale QA** (acceptance ≥70% "dùng ngay/sửa nhẹ"). Không cần lọc bỏ trước.

## Tiếp theo
1. Sale QA 31 script → đánh dấu dùng ngay / sửa nhẹ / bỏ.
2. Chạy thật + đo (đối chứng vs trước-sau — quyết khi tới).
