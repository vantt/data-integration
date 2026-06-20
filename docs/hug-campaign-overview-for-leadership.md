# Hug — Chiến lược khai thác tệp khách (cho Ban lãnh đạo & Marketing)

> Giải thích **toàn bộ chiến dịch Hug** + **kịch bản khai thác từng tập khách** bằng ngôn ngữ kinh doanh.
> Số liệu trong tài liệu lấy **trực tiếp từ dữ liệu sống** (`mart_customer_tier`), cập nhật 2026-06-20. Tổng ~7.565 khách.

---

## TL;DR (đọc 60 giây)

- Ta có **3.428 khách "ẩn danh" (masked)** — mua qua Shopee/Tiki nên **bị che liên hệ**, **0 người gọi/nhắn được**. Tổng lợi nhuận gộp lifetime của nhóm này ≈ **2,09 tỷ VND**.
- Đáng giá nhất: **433 khách "mua-lặp ẩn danh" (MASKED_REPEAT)** — trung bình **6,8 đơn, ~3,3 triệu/đơn, ~1,56 tỷ CM lifetime**. Đây là khách thân thiết nhưng ta **không có cách liên hệ trực tiếp**.
- **Vấn đề lõi (đúng như lo ngại):** với khách masked, ta **chỉ chạm được khi họ đặt hàng** (nhét QR vào kiện). Mà **76% nhóm này đã >180 ngày không mua** (median **508 ngày**) → họ đang ngủ đông → **không có kiện để chạm** → vòng luẩn quẩn.
- **Lời giải = 2 kênh bổ trợ nhau:**
  1. **Hug (nhét tem vào kiện)** — bắt định danh khi khách *còn mua*. Hiệu quả cho nhóm **active**.
  2. **Kênh nội sàn (Shopee/Tiki seller tools)** — kênh **DUY NHẤT chủ động** chạm khách masked ngủ đông để **kích họ mua lại** → khi mua → Hug bắt định danh → **thoát mask vĩnh viễn**.
- **Tư duy lại "phần thưởng":** mỗi lần capture = biến 1 khách masked thành **tài sản liên hệ trực tiếp suốt đời**. Voucher 50K = **chi phí thoát-mask**, không phải khuyến mãi.

> ⚠️ Đối soát số: plan cũ ghi "~364 khách / 683M". Dữ liệu sống = **433 khách / 1,56 tỷ CM lifetime**. Hai con số định nghĩa khác nhau (683M có thể là ước tính forward/sub-set) — **cần chốt lại định nghĩa** trước khi báo cáo ra ngoài.

---

## 1. Bản đồ tệp khách — 2 trục: **Liên hệ được?** × **Giá trị/hành vi**

| Tier | Liên hệ? | Số khách | Ý nghĩa | Hướng khai thác |
|---|---|---|---|---|
| **MASKED_REPEAT** | ❌ masked | **433** | Mua lặp ẩn danh, giá trị cao (1,56 tỷ CM) | 🎯 **Hug + nội sàn** (trọng tâm) |
| masked NONBUYER | ❌ masked | 1.192 | Ẩn danh, chưa chứng minh mua-lặp | Thấp — bắt cơ hội nếu có kiện |
| masked GRAVEYARD | ❌ masked | 1.803 | Ẩn danh, gần như chết | Bỏ qua / 1 lần thử nội sàn |
| LIVE_CORE | ✅ real | 56 | Khách lõi đang hoạt động | Giữ chân + upsell + loyalty |
| SECOND_ORDER | ✅ real | 27 | Vừa mua đơn thứ 2 | Nudge lên đơn 3 (ngày 7–10) |
| DORMANT_VALUABLE | ✅ real | 122 | Từng tốt, lặng, **có liên hệ** | Win-back trực tiếp (ưu tiên) |
| LAPSED_VALUABLE | ✅ real | 1.144 | Lặng lâu, **có liên hệ** | Win-back theo lô: thử → đo → suppress |
| (real) NONBUYER/GRAVEYARD | ✅ real | ~2.789 | Lead chưa mua / đã chết | Activation rẻ / bỏ qua |

**Đọc bản đồ này:**
- Cột "❌ masked" (3.428 khách) = **chỉ Hug + nội sàn chạm được**.
- Cột "✅ real" (4.137 khách) = **marketing trực tiếp được ngay** (M1 win-back, không cần Hug).

---

## 2. Vì sao masked khó — và khó đến mức nào (đào sâu)

### Cơ chế: chỉ chạm được khi khách mua
Sàn giấu SĐT. Điểm chạm vật lý duy nhất ta kiểm soát là **kiện hàng** — chỉ tồn tại khi khách **đã đặt một đơn**. Nên việc bắt định danh **bắt buộc bám theo một giao dịch**: phải đợi họ mua → mới có kiện → mới dán tem → mới quét → mới lấy được liên hệ.

### Dữ liệu phơi bày: phần lớn masked-repeat đang ngủ đông
| Lần mua gần nhất (recency) | Số khách MASKED_REPEAT |
|---|---|
| ≤ 30 ngày | 36 |
| 31–60 ngày | 20 |
| 61–90 ngày | 13 |
| 91–180 ngày | 33 |
| **> 180 ngày** | **331 (76%)** |

→ Chỉ **~69 khách (16%) còn active** (≤90 ngày). **331 khách (76%) đã ngủ đông >6 tháng** (median 508 ngày).

### Vòng luẩn quẩn (đúng câu hỏi đặt ra)
```
Khách masked ngủ đông
   │  (không có SĐT → không nhắn/gọi được)
   ▼
Không đánh thức được  ──► Không đặt đơn mới ──► Không có kiện hàng
   ▲                                                    │
   └──────────  Không có tem để bắt định danh  ◄────────┘
```
**Với 331 khách ngủ đông, nếu CHỈ dựa vào Hug-nhét-kiện thì gần như không bắt được** — vì sẽ không có kiện nào tới. Đây là điểm plan cũ bỏ sót: A2 thuần Hug **chỉ hiệu quả với ~69 khách active**, không phải cả 433.

→ **Phải chia masked-repeat làm 2 và đánh khác nhau:**
- **Active (~69):** Hug-nhét-kiện ăn ngay (họ sắp mua lại).
- **Dormant (~331):** cần **kênh nội sàn đánh thức trước** → mới có đơn → mới Hug bắt được.

---

## 3. Tư duy lại: capture là gì, voucher là gì

- **Capture KHÔNG phải để bán 1 voucher.** Capture = **chuyển 1 khách masked → khách liên hệ trực tiếp**. Sau khi có Zalo/SĐT, ta mở được **mọi kênh chủ động suốt đời** (Zalo OA, ZNS, gọi, ưu đãi riêng, gợi ý mua lại). Đó mới là tài sản.
- **Voucher 50K = chi phí "thoát mask" (CAC), không phải khuyến mãi.** ROI nên tính theo **giá trị remarketing trọn đời** của liên hệ bắt được, không phải theo 1 lần redeem.
- **Cảnh báo kinh tế — 50K quá nhỏ với tệp này:** AOV ~3,3 triệu/đơn. 50K ≈ **1,5%** giá trị đơn → **không đủ làm đòn bẩy reactivation** cho khách giá trị cao. ⇒ Coi 50K là **token để khách chịu opt-in**, KHÔNG kỳ vọng nó kéo khách ngủ đông quay lại. Muốn đánh thức khách giá trị cao cần **đòn bẩy mạnh hơn** (ưu đãi theo %, quà theo bậc, nhắc đúng sản phẩm/chu kỳ restock).
- **Đo lượng tăng thực (incrementality):** một phần khách masked-repeat **dù sao cũng quay lại** — tặng voucher cho họ = mất tiền vô ích (cannibalization). ⇒ Phải chạy **nhóm đối chứng (holdout)**: tặng cho nửa, giữ lại nửa, đo chênh lệch → biết offer thực sự "nhấc" được bao nhiêu.

---

## 4. Chiến lược tiếp cận masked — 3 kênh, theo trình tự

### Kênh 1 — Hug nhét tem vào kiện (đã xây xong)
- **Bản chất:** phản ứng (reactive) — bắt định danh trên đơn khách *đang* mua.
- **Phủ:** dán tem **mọi đơn masked ship ra từ giờ** (tem in ~0đ; chi phí thật chỉ phát sinh khi có redeem). Không bỏ lỡ cửa sổ bắt.
- **Tốt cho:** ~69 active masked-repeat + mọi khách masked phát sinh đơn mới.
- **Giới hạn:** không chạm được 331 khách ngủ đông (không có kiện).

### Kênh 2 — Nội sàn Shopee/Tiki (kênh DUY NHẤT chủ động tới masked) — *cần kiểm chứng năng lực*
- **Bản chất:** dùng công cụ seller của sàn để chạm khách cũ **mà không cần SĐT**: chat broadcast sau mua, **shop voucher đẩy cho người theo dõi shop**, ưu đãi follow-shop, livestream. Đây là **cách duy nhất chủ động "đánh thức" khách masked ngủ đông**.
- **Vai trò chiến lược:** Shopee đánh thức → khách đặt đơn mới → **kiện hàng → Hug bắt định danh → thoát mask**. Hai kênh **bổ trợ và nối tiếp**, không thay thế nhau.
- **Đòn bẩy:** với khách AOV 3,3 triệu, nên đẩy **shop voucher giá trị thực** (vd theo %) qua sàn, không phải 50K.
- ⚠️ **Cần validate:** chính sách Shopee/Tiki VN về broadcast/chat/voucher tới khách cũ thay đổi và bị giới hạn. **Phải xác nhận năng lực thực tế** trước khi cược chiến lược vào kênh này.

### Kênh 3 — Định danh "bóng" (identity resolution)
- Một số khách masked có thể **trùng với khách đã có liên hệ** (nếu họ từng mua website/POS bằng cùng SĐT/tên). Hệ thống CRM đã có cơ chế dedup.
- **Thực tế hiện tại: 0/3.428 masked có liên hệ** → kênh này gần như không có gì để khai thác ngay, nhưng nên chạy 1 lượt dedup để chắc.

### Trình tự khai thác masked-repeat
```
[Dormant 331] ──Shopee/Tiki đánh thức──► đặt đơn mới ──► [kiện] ──► Hug bắt định danh ──┐
[Active   69] ──────────────────────────► đơn kế tiếp ──► [kiện] ──► Hug bắt định danh ──┤
                                                                                         ▼
                                                          Khách thoát mask = liên hệ trực tiếp
                                                                                         ▼
                                              CRM lifecycle: Zalo/ZNS · win-back · upsell · loyalty
```

---

## 5. Playbook theo từng tập

| Tập | Trạng thái | Đòn đánh | Kênh | Vì sao / Rủi ro |
|---|---|---|---|---|
| **MASKED_REPEAT — active (~69)** | masked, còn mua | Hug A2: tem + opt-in (token bắt liên hệ) | Kiện hàng | ROI cao, nhanh. Rủi ro: cannibalization → cần holdout |
| **MASKED_REPEAT — dormant (~331)** | masked, ngủ đông | Đánh thức nội sàn (voucher/% qua Shopee) → reorder → Hug bắt | Shopee/Tiki → kiện | Đây là khối giá trị lớn nhưng khó nhất. Rủi ro: sàn chặn broadcast → kẹt |
| masked NONBUYER/GRAVEYARD (~3.000) | masked, yếu | Bắt cơ hội nếu phát sinh đơn; 1 lần thử nội sàn rồi suppress | Kiện / nội sàn | Giá trị chưa chứng minh → không đổ ngân sách |
| LIVE_CORE (56) | real, active | Giữ chân + upsell/cross-sell + loyalty (Hug làm điểm chạm thẻ/review) | Trực tiếp + Hug loyalty | Khách lõi — bảo vệ là ưu tiên |
| SECOND_ORDER (27) | real | Nudge lên đơn 3 (ngày 7–10) | Trực tiếp | Cửa sổ tạo thói quen mua; đòn bẩy cao dù số nhỏ |
| DORMANT_VALUABLE (122) | real | Win-back trực tiếp, ưu đãi theo value | Trực tiếp (M1) | Có liên hệ → đánh ngay, không cần Hug |
| LAPSED_VALUABLE (1.144) | real | Win-back theo lô: **thử → đo → suppress** | Trực tiếp (M1) | Đừng đốt cả list; tìm sub-segment phản hồi |
| real NONBUYER/GRAVEYARD | real | Activation rẻ 1 lần / bỏ qua | Trực tiếp | Acquisition motion, ROI thấp |

---

## 6. Kịch bản (thận trọng → lạc quan)

| Kịch bản | Giả định | Kết quả masked-repeat (433) |
|---|---|---|
| **Xấu** | Sàn chặn broadcast; chỉ bắt qua đơn tự nhiên | Bắt dần ~69 active qua vài chu kỳ; 331 dormant **gần như mất**; trickle chậm |
| **Thực tế** | Hug phủ tốt + 1 chiến dịch nội sàn đánh thức | Bắt ~69 active nhanh; đánh thức + bắt một phần (vd 20–30%) của 331; phần deep-dormant rơi rụng |
| **Tốt** | Opt-in cao + nội sàn hiệu quả + offer đúng tầm | Bắt phần lớn 433 qua 2–3 chu kỳ → mở khóa marketing trực tiếp toàn tệp giá trị cao |

**Chốt tư duy:** đừng hứa "mở khóa 433 ngay". Hứa: **chặn rò rỉ (phủ tem mọi đơn) + thử nghiệm đánh thức nội sàn có đo lường**, rồi mở rộng theo dữ liệu.

---

## 7. Đo lường & cổng quyết định

Theo dõi theo từng nấc của phễu:
1. **Phủ tem** = % đơn masked có dán tem (mục tiêu ~100%).
2. **Tỷ lệ quét** = quét / tem phát.
3. **Tỷ lệ opt-in** = để lại liên hệ / quét → **đây là "tỷ lệ thoát mask"**.
4. **Đánh thức nội sàn** = reorder / số khách dormant được chạm (đo riêng từng kênh sàn).
5. **Redeem & margin tăng thực** = so với **holdout** → ROI thật.

Màn hình ROI voucher sẵn có tại **`/hug/vouchers`** (đã phát / đã dùng / % quy đổi theo chiến dịch).

**Cổng quyết định:** sau lô đầu, nếu opt-in < ngưỡng → chỉnh offer/landing; nếu nội sàn không đánh thức được → coi 331 dormant là chi phí chìm, dồn lực vào active + khách "real".

---

## 8. Trạng thái xây dựng + Go-live

### ✅ Đã xong (xây + chạy thử thông suốt)
Hạ tầng QR (Cloudflare, `hug.fjp.vn`) · sinh & in tem cuộn · trạm gắn tem vào đơn ở kho · trang opt-in (Zalo + SĐT + hiện mã) · bắt định danh tự động + hàng đợi CS · sổ phát hành & đối soát voucher · **màn quản trị chiến dịch tự phục vụ** (`/hug/campaigns`: dropdown, xem trước số khách, cảnh báo chồng lấp) · màn ROI (`/hug/vouchers`).

### 🚦 Sắp go-live A2 (thao tác nghiệp vụ ~30–45')
1. Tạo mã **HUG50** trong Sapo (50K / đơn ≥300K / 1 lần/khách).
2. Set link **Zalo OA** + deploy bản landing mới.
3. Tạo **chiến dịch A2** qua `/hug/campaigns` (nhắm package_insert × MASKED_REPEAT).
4. Quét thử 1 tem → nghiệm thu luồng.
5. Brief kho dán tem đơn MASKED_REPEAT.

---

## 9. Lộ trình mở rộng

| Hạng mục | Ghi chú |
|---|---|
| **Đánh thức nội sàn** (Shopee/Tiki tools) | **Việc chiến lược kế tiếp** — mở khóa 331 dormant; cần validate năng lực sàn |
| Win-back khách "real" (~1.180) | Doanh thu sớm, **không cần Hug** — v1 xuất list CS nhắn tay |
| ZNS (nhắn Zalo tự động) | Sau khi bắt được liên hệ → nhắc opt-in-chưa-mua; cần verify OA + duyệt template |
| A/B testing offer + holdout | Đo lượng tăng thực; tối ưu mức ưu đãi (50K vs %/quà bậc) |
| Điểm chạm Hug khác (thẻ TV, hóa đơn, tờ rơi) | Nền tảng đã hỗ trợ; mở rộng khi A2 ổn |
| Mã riêng từng khách (thay mã chung) | Attribution mạnh hơn; cần spike API ghi của Sapo |

---

## 10. Con số tóm tắt (đã verify từ dữ liệu sống)

| Chỉ số | Giá trị |
|---|---|
| Tổng khách | ~7.565 |
| **Masked (khóa cứng, 0 liên hệ được)** | **3.428** · CM lifetime ~**2,09 tỷ** |
| **MASKED_REPEAT (trọng tâm)** | **433** · CM ~**1,56 tỷ** · avg 6,8 đơn · AOV ~3,3 triệu |
| — trong đó **active (≤90 ngày)** | ~69 (16%) → Hug ăn ngay |
| — trong đó **ngủ đông (>180 ngày)** | ~331 (76%) → cần nội sàn đánh thức |
| Khách "real" liên hệ được ngay | ~4.137 (gồm ~1.180 dormant đáng win-back) |
| Ưu đãi A2 hiện tại | 50K / đơn ≥300K / 1 lần (lưu ý: nhỏ so với AOV) |
| Chi phí hạ tầng Hug | ≈ $0 (tái dùng Cloudflare) |

---

## 11. Cần gì từ Marketing & Câu hỏi mở

**Hành động:**
1. Chốt **thể lệ & mức ưu đãi** — và quyết: 50K có đủ không, hay cần offer mạnh hơn cho khách giá trị cao?
2. **Xác minh năng lực nội sàn Shopee/Tiki** (broadcast/chat/shop-voucher tới khách cũ) — đây là chìa khóa mở 331 khách ngủ đông.
3. Phối hợp kho **phủ tem mọi đơn masked** từ go-live.
4. Theo dõi ROI ở `/hug/vouchers` + quyết mở rộng theo dữ liệu.

**Câu hỏi mở:**
- **Đối soát "683M (plan) vs 1,56 tỷ CM lifetime (live)"** — chốt định nghĩa con số báo cáo (lifetime đã có vs cơ hội forward).
- Mức offer cho khách AOV 3,3 triệu: 50K (token) hay %/quà bậc (đòn bẩy thật)?
- Ngưỡng cắt "deep-dormant" (>bao nhiêu ngày thì coi là chi phí chìm, ngừng đầu tư)?
- Triển khai **holdout** đo incrementality ngay từ lô đầu?
- Khi nào bật ZNS để khép vòng nhắc lại?
</content>
