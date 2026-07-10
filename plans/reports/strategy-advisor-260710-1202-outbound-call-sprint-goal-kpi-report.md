# Sprint Gọi Ra 45 Ngày — Goal, KPI, Việc Cần Làm

> 2026-07-10. Bối cảnh: tem QR chưa sản xuất được → dồn toàn lực vào GỌI RA. Cuộc gọi kiêm luôn vai trò capture (kết bạn Zalo = tem không cần in). Nguồn số: action-queue report 260611, FIND-003/006/007, masked-repeat report, phân tích strategy-advisor 260710-1143.

---

## GOAL (1 câu)

**Trong 45 ngày, gọi 100% ~200 khách giá-trị-cao có SĐT, đưa họ vào lại chu kỳ mua, kết bạn Zalo ≥50% người bắt máy, và trả lời được câu "tại sao khách không quay lại" (10 VOC).**

3 mục tiêu con:
1. **Phủ gọi:** 203 khách ưu tiên (142 OVERDUE/DUE_SOON = 653,8M LTV + 61 SILVER/GOLD/VIP at-risk/churned = 992M LTV) — mỗi khách ≥1 cuộc trong 30 ngày làm việc.
2. **Capture:** Zalo connect ≥50% khách reached — tài sản liên hệ vĩnh viễn, thay tem.
3. **Học:** 10 VOC hoàn thành + bản đồ reach-rate/objection theo segment → nạp ngược vào approach scripts.

Kỳ vọng doanh thu (thực tế, KHÔNG phải target tuần đầu): win-back conversion ngành 5–15% → 10–30 đơn ≈ 20–60M trong 60–90 ngày + pipeline hứa-mua. Giá trị lớn hơn nằm ở khách quay lại chu kỳ + Zalo asset.

---

## TỆP GỌI & THỨ TỰ (đã có sẵn trong worklist, chỉ cần claim)

| Lô | Tuần | Tệp | Lý do |
|---|---|---|---|
| 1 | 1–2 | **142 OVERDUE/DUE_SOON** (653,8M) | Cửa sổ đang đóng; cuộc gọi dễ nhất: "sắp hết sản phẩm chưa anh/chị" — nhắc restock, không phải chào hàng |
| 2 | 3–4 | **61 SILVER/GOLD/VIP at-risk/churned** (992M) | Mỏ reactivation giá trị nhất; cá nhân hóa theo lịch sử mua (script sẵn) |
| 3 | 5–6 | DORMANT_VALUABLE còn lại + SECOND_ORDER có SĐT | SECOND_ORDER gọi cửa sổ ngày 7–10 sau đơn để tạo thói quen |
| ❌ KHÔNG gọi | — | LAPSED_VALUABLE 1.144, masked, >720d | Đợi học xong lô 1–2 mới mở theo sub-segment phản hồi tốt |

- **Giờ vàng:** Thứ 2 + Thứ 5, 8h30–9h30 (data FIND-007). Retry tối đa 2 lần khung giờ khác → chuyển nhắn Zalo/SMS rồi đóng.
- Ưu tiên trong ngày: theo priority_rank của action queue (đã tính value_at_stake).

---

## KPI TUẦN (review Thứ 2, 30 phút, trên operating-board)

**Hành động (tuần 1 bật ngay):**
| KPI | Target |
|---|---|
| Cuộc gọi/tuần/người | **50** (10/ngày — 1 người là đủ khởi động) |
| Reach rate (bắt máy) | **≥40%** |
| Outcome log/cuộc | **100%** — không log = không xảy ra |

**Chất lượng (tuần 1 theo dõi, tuần 3 thành target):**
| KPI | Target |
|---|---|
| Conversation rate (nói chuyện thật, không chỉ alo-cúp) | ≥60% reached |
| **Zalo connect / reached** | **≥50%** ← thay tem |
| VOC hoàn thành | 2/tuần, tích lũy 10 |
| SĐT xác nhận đúng/sai (data enrichment) | log mỗi cuộc |

**Chuyển đổi (theo dõi từ đầu, KHÔNG ép target trước tuần 3):**
- Hứa mua / đồng ý nhận tư vấn tiếp
- Đơn đặt trong 7 ngày sau cuộc gọi (+ giá trị)
- Follow-up được đặt lịch theo chu kỳ SKU (action queue tự tính ngày cạn)

**Cổng điều chỉnh tuần 3:** reach <25% → đổi khung giờ + thử SMS-báo-trước-gọi, KHÔNG tăng volume. Conversation thấp mà reach cao → sửa 15 giây mở đầu của script.

---

## KẾT QUẢ CẦN LÀM (checklist khởi động — thứ tự)

1. **Hôm nay — chốt D3:** ai gọi, cam kết 10 cuộc/ngày. (Quyết định người, không phải hạ tầng. Đây là nút đang chặn tất cả.)
2. **Freeze danh sách 203** + thứ tự lô trong worklist (dữ liệu đã có; chỉ cần claim + không thêm bớt giữa sprint).
3. **Script:** dùng approach script autogen sẵn có + chèn 3 câu VOC (vì sao ngừng mua / cảm nhận sản phẩm / mua ở đâu khác) + **câu chốt bắt buộc:** "em kết bạn Zalo để gửi hướng dẫn dùng & nhắc lịch nhé".
4. **Quy trình log:** mỗi cuộc kết thúc = chọn outcome trong CRM (enum đã có) + đặt follow-up nếu hứa mua. Không có ngoại lệ.
5. **Bảng số tuần:** kích hoạt Track A outreach-effort (extend `mart_staff_performance_weekly` — plan 260709-1638 đã draft sẵn) → 1 dashboard 6 con số: gọi / reach / conversation / Zalo connect / hứa mua / đơn 7-ngày.
6. **Nhịp:** review Thứ 2 hằng tuần; ghi số vào execution log của operating-board (hiện đang là template rỗng).

---

## ĐỊNH NGHĨA THÀNH CÔNG SAU 6 TUẦN

- 100% tệp 203 được gọi ≥1 lần; reach ≥40% (~80+ cuộc nói chuyện thật)
- ≥40 Zalo connects (tài sản capture mới, thay tem)
- 10 VOC được ghi chép → 1 trang insight "vì sao one-time"
- ≥15 hứa-mua; đơn 7-ngày bắt đầu xuất hiện từ tuần 3–4
- Bảng số tuần chạy tự động; execution log có 6 dòng dữ liệu thật đầu tiên

Đạt → mở lô LAPSED 1.144 theo sub-segment phản hồi tốt nhất + quay lại tem khi sản xuất được (khách đã Zalo-connect thì không cần tem nữa).
Không đạt reach/conversation → vấn đề là danh sách/giờ gọi/script — sửa từng biến một, vẫn KHÔNG tăng volume.

---

## Câu hỏi chưa giải đáp
1. Ai là người gọi (CSKH nào), và 10 cuộc/ngày có khả thi với ca làm hiện tại? (D3)
2. SĐT tệp OVERDUE bao nhiêu % còn sống? (log enrichment 2 tuần đầu sẽ trả lời)
3. Có cần kịch bản ưu đãi nhỏ cho lô 2 (VIP churned) không, hay tư vấn thuần? — đề nghị: tuần 1–2 gọi thuần không ưu đãi để đo baseline, rồi mới quyết.
