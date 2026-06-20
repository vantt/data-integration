# Hug — Chiến lược khai thác tệp khách (cho Ban lãnh đạo & Marketing)

> Giải thích **toàn bộ chiến dịch Hug** + **kịch bản khai thác từng tập khách** bằng ngôn ngữ kinh doanh.
> Số liệu lấy **trực tiếp từ dữ liệu sống** (`mart_customer_tier`), cập nhật 2026-06-20. Tổng ~7.565 khách.
> Đã bổ sung kết quả 2 nghiên cứu sâu (xem `plans/reports/…shopee-tiki-seller-reactivation…` và `…masked-repeat-economics-reachability…`).

---

## TL;DR (đọc 60 giây)

- Ta có **3.428 khách "ẩn danh" (masked)** — mua qua Shopee/Tiki nên **bị che liên hệ**, **0 người gọi/nhắn được**.
- Đáng giá nhất: **433 khách "mua-lặp ẩn danh" (MASKED_REPEAT)** — trung bình **6,8 đơn, AOV ~3,3 triệu** → khách thân thiết nhưng **không liên hệ trực tiếp được**.
- **Vấn đề lõi:** với khách masked ta **chỉ chạm được khi họ đặt hàng** (nhét QR vào kiện). Mà chỉ **~69 khách (16%) còn active**; **~364 đã churn** (không quay lại) → không có kiện để chạm.
- **TIN TỐT (đã kiểm chứng):** **Shopee Chat Broadcast** chạm được khách đã mua **tới 720 ngày, miễn phí, không cần follow** → đây là **kênh chủ động** đánh thức nhóm ngủ đông. Tiki yếu (chỉ ads).
- **Lời giải = 2 kênh nối tiếp:** Shopee broadcast **đánh thức** khách ngủ đông → họ mua lại → **Hug nhét-tem bắt định danh** → **thoát mask vĩnh viễn**.
- **Tư duy lại:** capture = biến khách masked thành **tài sản liên hệ suốt đời**; voucher = **chi phí thoát-mask**, không phải khuyến mãi. **50K quá nhỏ so với AOV 3,3 triệu** → chỉ là token opt-in, không phải đòn bẩy reactivation.

> ⚠️ **Cảnh báo số liệu:** vài "outlier" cực đoan (1 khách kênh khác −1,1 tỷ CM) làm **méo tổng CM** → dùng **median**, đừng tin số cộng dồn. Plan cũ ghi "683M" chưa khớp định nghĩa — **cần chốt lại**.

---

## 1. Bản đồ tệp khách — 2 trục: **Liên hệ được?** × **Giá trị/hành vi**

| Tier | Liên hệ? | Số khách | Ý nghĩa | Hướng khai thác |
|---|---|---|---|---|
| **MASKED_REPEAT** | ❌ masked | **433** | Mua lặp ẩn danh, giá trị cao | 🎯 **Shopee broadcast + Hug** (trọng tâm) |
| masked NONBUYER | ❌ masked | 1.192 | Ẩn danh, chưa chứng minh mua-lặp | Thấp — bắt cơ hội nếu có kiện |
| masked GRAVEYARD | ❌ masked | 1.803 | Ẩn danh, gần như chết | Bỏ qua |
| LIVE_CORE | ✅ real | 56 | Khách lõi đang hoạt động | Giữ chân + upsell + loyalty |
| SECOND_ORDER | ✅ real | 27 | Vừa mua đơn thứ 2 | Nudge lên đơn 3 (ngày 7–10) |
| DORMANT_VALUABLE | ✅ real | 122 | Từng tốt, lặng, **có liên hệ** | Win-back trực tiếp (ưu tiên) |
| LAPSED_VALUABLE | ✅ real | 1.144 | Lặng lâu, **có liên hệ** | Win-back theo lô: thử → đo → suppress |
| (real) NONBUYER/GRAVEYARD | ✅ real | ~2.789 | Lead chưa mua / đã chết | Activation rẻ / bỏ qua |

- "❌ masked" (3.428) = **chỉ Shopee broadcast + Hug chạm được**.
- "✅ real" (4.137) = **marketing trực tiếp được ngay** (M1 win-back, không cần Hug).

---

## 2. Vì sao masked khó — và khó đến mức nào (đào sâu, có dữ liệu)

### Cơ chế: chỉ chạm được khi khách mua
Sàn giấu SĐT. Điểm chạm vật lý duy nhất ta kiểm soát là **kiện hàng** — chỉ có khi khách **đã đặt đơn**. Bắt định danh **bắt buộc bám theo một giao dịch**.

### "Ngủ đông" thực ra là **churn**, không phải chu kỳ chậm
Khoảng cách mua-lại của masked-repeat có **median chỉ 7 ngày** → khi còn active họ quay vòng **rất nhanh**. Recency median 508 ngày là do tệp **lưỡng cực**: một nhóm nhỏ cycle nhanh + một nhóm lớn **đã bỏ đi hẳn**. ⇒ Với khách active, Hug bắt được **trong ~1 tháng**; với nhóm churn, **phải đánh thức mới có cửa**.

### Bản đồ 3 vùng theo khả năng tiếp cận (433 masked-repeat)
| Vùng | Recency | Số khách | Tiếp cận |
|---|---|---|---|
| **1 — Active** | ≤ 90 ngày | **69** | Hug bắt ngay ở đơn kế tiếp |
| **2 — Dormant tiếp cận được** | 91–720 ngày | **283** (~259 qua sàn) | **Shopee Chat Broadcast** đánh thức |
| **3 — Lost** | > 720 ngày | **81** | ❌ không công cụ nào chạm → chi phí chìm |

→ **Vùng tiếp cận được (1+2) = ~321 khách.** Chỉ ~81 là mất hẳn (Shopee broadcast giới hạn 720 ngày).

---

## 3. Tư duy lại: capture là gì, voucher là gì

- **Capture = chuyển 1 khách masked → khách liên hệ trực tiếp.** Sau đó mở được **mọi kênh chủ động suốt đời** (Zalo OA, ZNS, gọi, ưu đãi riêng). Đó mới là tài sản — không phải 1 lần redeem.
- **Voucher = chi phí thoát-mask (CAC), không phải khuyến mãi.** ROI tính theo giá trị remarketing trọn đời.
- **50K quá nhỏ:** AOV ~3,3 triệu → 50K ≈ 1,5% đơn → chỉ là **token opt-in**, không kéo được khách ngủ đông. Khách giá trị cao cần **đòn bẩy mạnh hơn** (%, quà bậc, nhắc đúng chu kỳ restock).
- **Đo lượng tăng thực (holdout):** một phần khách **dù sao cũng quay lại** → tặng voucher cho họ = mất tiền (cannibalization). Phải chạy nhóm đối chứng để biết offer thực sự "nhấc" bao nhiêu.

### ⚠️ Offer bậc thang (theo dữ liệu AOV) — quan trọng
| Nhóm AOV | % tệp | Lợi nhuận/đơn | Offer đề xuất |
|---|---|---|---|
| **< 500K (Bucket A)** | ~22% (97 khách) | **ÂM (~−1,25 triệu/đơn)** | ❌ **KHÔNG tặng voucher** (càng bán càng lỗ) |
| 500K – 1M (B) | — | mỏng | 25K |
| ≥ 1M (C+) | ~40%+ | dương, an toàn | 50K |

---

## 4. Chiến lược tiếp cận masked — 3 kênh, theo trình tự

### Kênh 1 — Hug nhét tem vào kiện (đã xây xong)
- Phản ứng (reactive) — bắt định danh trên đơn khách *đang* mua. Tem in ~0đ; chi phí thật chỉ khi redeem.
- **Phủ tem mọi đơn masked** từ go-live → không bỏ lỡ. Tốt nhất cho **Vùng 1 (69 active)**.

### Kênh 2 — Shopee Chat Broadcast (đã kiểm chứng ✅) — kênh chủ động tới masked ngủ đông
- **Chat Broadcast:** chạm khách đã mua **tới 720 ngày, miễn phí, không cần follow** (cap ~1 tin/khách/ngày, ~2× số follower/tuần). **Phải viết như nhắc restock/đơn**, không phải blast KM → tránh bị phạt spam.
- **GMV Max Ads + Smart Voucher:** voucher do **Shopee tài trợ (0đ với seller)**, thuật toán tự re-serve khách cũ.
- **Follow Prize:** tăng follower → nới trần broadcast.
- **Tiki:** yếu, không có công cụ broadcast tương đương → coi như kênh thụ động (chỉ ads).
- **Vai trò:** Shopee đánh thức → khách đặt đơn → **kiện → Hug bắt định danh → thoát mask**. Hai kênh **nối tiếp**, không thay thế.
- ⚠️ **Còn xác nhận cuối** (trước khi cược ngân sách): trần broadcast trên portal VN, Smart Voucher có live ở VN không, và xin xác nhận ToS cho tem-insert Zalo.

### Kênh 3 — Định danh "bóng" (identity resolution)
- Hiện **0/3.428 masked** có liên hệ → gần như không có gì khai thác ngay; chạy 1 lượt dedup để chắc.

### Tuân thủ ToS sàn (quan trọng)
- ✅ Được: tem/insert "**follow Zalo nhận bảo hành / ưu đãi thành viên / tư vấn sức khỏe**" (chào **dịch vụ**, phổ biến ở bán lẻ VN). QR Hug bắt định danh chỉ kích hoạt **sau khi khách đã hoàn tất đơn trên sàn** → không vi phạm.
- ❌ Cấm: dùng chat sàn **rủ khách giao dịch ngoài sàn** → khóa/treo shop.

### Trình tự
```
[Dormant ≤720d 283] ──Shopee broadcast/voucher──► đặt đơn ──► [kiện] ──► Hug bắt ──┐
[Active 69]         ───────────────────────────► đơn kế tiếp ─► [kiện] ──► Hug bắt ─┤
[Lost >720d 81]    ── (không chạm được — bỏ) ──────────────────────────────────────┘
                                                                                    ▼
                                                       Thoát mask → CRM trực tiếp suốt đời
```

---

## 5. Playbook theo từng tập

| Tập | Trạng thái | Đòn đánh | Kênh | Vì sao / Rủi ro |
|---|---|---|---|---|
| **MASKED_REPEAT — Vùng 1 active (69)** | masked, còn mua | Hug A2: tem + opt-in | Kiện hàng | ROI cao, nhanh. Cần holdout đo cannibalization |
| **MASKED_REPEAT — Vùng 2 dormant (283)** | masked, ngủ đông ≤720d | **Shopee broadcast/voucher đánh thức** → reorder → Hug bắt | Shopee → kiện | Khối giá trị lớn nhất. Phụ thuộc năng lực sàn |
| **MASKED_REPEAT — Vùng 3 lost (81)** | masked, >720d | Bỏ (ngoài tầm công cụ) | — | Chi phí chìm; không đầu tư |
| ~52 khách masked giá trị rất cao (kênh ngoài sàn) | masked, direct/social | **Cần chiến lược riêng** (không chạm bằng Shopee broadcast) | Chưa rõ | Giá trị/đầu người rất cao — đáng nghiên cứu riêng |
| masked NONBUYER/GRAVEYARD (~3.000) | masked, yếu | Bắt cơ hội nếu có đơn; không đổ ngân sách | Kiện | Giá trị chưa chứng minh |
| LIVE_CORE (56) | real, active | Giữ chân + upsell + loyalty | Trực tiếp + Hug loyalty | Khách lõi — bảo vệ |
| SECOND_ORDER (27) | real | Nudge lên đơn 3 (ngày 7–10) | Trực tiếp | Cửa sổ tạo thói quen |
| DORMANT_VALUABLE (122) | real | Win-back trực tiếp | Trực tiếp (M1) | Có liên hệ → đánh ngay |
| LAPSED_VALUABLE (1.144) | real | Win-back theo lô: thử → đo → suppress | Trực tiếp (M1) | Tìm sub-segment phản hồi |

---

## 6. Kịch bản (thận trọng → lạc quan)

| Kịch bản | Giả định | Kết quả masked-repeat |
|---|---|---|
| **Xấu** | Sàn chặn broadcast; chỉ bắt qua đơn tự nhiên | Bắt ~69 active; ~283 dormant kẹt; 81 lost mất |
| **Thực tế** | Hug phủ tốt + Shopee broadcast hiệu lực | Bắt 69 active nhanh; đánh thức + bắt **một phần** 283 (tùy tỷ lệ reactivation R); 81 bỏ |
| **Tốt** | Opt-in cao + broadcast tốt + offer đúng tầm | Bắt phần lớn 321 vùng tiếp cận được → mở khóa CRM trực tiếp tệp giá trị cao |

**Chốt tư duy:** không hứa "mở khóa 433 ngay". Hứa: **phủ tem mọi đơn + thử Shopee broadcast có holdout đo lường**, mở rộng theo dữ liệu.

---

## 7. Đo lường & cổng quyết định

Phễu: ① **Phủ tem** (% đơn masked dán tem, ~100%) → ② **Tỷ lệ quét** → ③ **Tỷ lệ opt-in** (= "tỷ lệ thoát mask") → ④ **Đánh thức nội sàn** (reorder / khách dormant được broadcast) → ⑤ **Redeem & margin tăng thực** (so holdout).
- Màn ROI voucher: **`/hug/vouchers`** (đã phát / đã dùng / % quy đổi).
- **Holdout:** Vùng 1 (~62 marketplace) đủ lực đo (40 treat / 22 control, đọc 60–90 ngày); Vùng 2 (~259) **chỉ định hướng** (mẫu nhỏ).
- **Cổng:** opt-in < ngưỡng → chỉnh offer/landing; broadcast không đánh thức được → coi dormant là chi phí chìm, dồn lực active + khách "real".

---

## 8. Trạng thái xây dựng + Go-live

### ✅ Đã xong (xây + chạy thử thông suốt)
Hạ tầng QR (Cloudflare, `hug.fjp.vn`) · sinh & in tem cuộn · trạm gắn tem vào đơn ở kho · trang opt-in (Zalo + SĐT + hiện mã) · bắt định danh tự động + hàng đợi CS · sổ phát hành & đối soát voucher · **màn quản trị chiến dịch tự phục vụ** (`/hug/campaigns`) · màn ROI (`/hug/vouchers`).

### 🚦 Sắp go-live A2 (thao tác nghiệp vụ ~30–45')
1. Tạo mã **HUG50** trong Sapo (50K / đơn ≥300K / 1 lần/khách) — **chỉ áp Bucket C+ (AOV ≥1M)**.
2. Set link **Zalo OA** + deploy bản landing mới.
3. Tạo **chiến dịch A2** qua `/hug/campaigns` (nhắm package_insert × MASKED_REPEAT).
4. Quét thử 1 tem → nghiệm thu luồng.
5. Brief kho dán tem đơn MASKED_REPEAT.
6. **Song song:** chuẩn bị **Shopee Chat Broadcast** đánh thức Vùng 2 (nội dung kiểu nhắc restock).

---

## 9. Lộ trình mở rộng

| Hạng mục | Ghi chú |
|---|---|
| **Shopee Chat Broadcast đánh thức Vùng 2** | **Việc chiến lược kế tiếp** — mở khóa 283 dormant |
| Chiến lược riêng cho ~52 khách giá trị cao ngoài sàn | Không chạm bằng broadcast → cần cách khác |
| Win-back khách "real" (~1.180) | Doanh thu sớm, không cần Hug — v1 xuất list CS nhắn tay |
| ZNS (nhắn Zalo tự động) | Sau khi bắt liên hệ → nhắc opt-in-chưa-mua; cần verify OA + duyệt template |
| A/B testing offer + holdout | Đo incrementality; tối ưu mức ưu đãi |
| Điểm chạm Hug khác (thẻ TV, hóa đơn, tờ rơi) | Nền tảng đã hỗ trợ |
| Mã riêng từng khách (thay mã chung) | Attribution mạnh hơn; cần spike API ghi Sapo |

---

## 10. Con số tóm tắt (verify từ dữ liệu sống)

| Chỉ số | Giá trị |
|---|---|
| Tổng khách | ~7.565 |
| **Masked (0 liên hệ được)** | **3.428** |
| **MASKED_REPEAT (trọng tâm)** | **433** · avg 6,8 đơn · AOV ~3,3 triệu · gap mua-lại median 7 ngày |
| — Vùng 1 active (≤90d) | **69** → Hug bắt ngay |
| — Vùng 2 dormant tiếp cận được (91–720d) | **283** (~259 qua sàn) → Shopee broadcast |
| — Vùng 3 lost (>720d) | **81** → mất |
| Khách "real" liên hệ được ngay | ~4.137 (gồm ~1.180 dormant đáng win-back) |
| Kênh masked-repeat | ~84% marketplace (Shopee/Tiki) |
| Chi phí hạ tầng Hug | ≈ $0 |

> Tổng CM bị **outlier làm méo** → báo cáo nên dùng median/đã-loại-outlier (xem report analytics).

---

## 11. Quyết định cần chốt & việc cần làm

**Quyết định (nghiệp vụ — chờ chốt):**
1. **Loại Bucket A** (<500K AOV, lợi nhuận âm) khỏi voucher? *(khuyến nghị: CÓ)*
2. **Tỷ lệ reactivation R%** mặc định để ước cơ hội forward (10 / 20 / 30%)?
3. **Loại outlier CM** khi báo cáo (dùng median)? *(khuyến nghị: CÓ)*
4. Đối soát **"683M (plan)"** — bỏ hay định nghĩa lại?
5. Chiến lược cho **~52 khách giá trị cao ngoài sàn**?
6. Bật **holdout** đo incrementality ngay lô đầu?

**Hành động Marketing:**
1. Chốt thể lệ & mức ưu đãi (50K token vs %/quà bậc cho khách giá trị cao).
2. **Xác nhận cuối năng lực Shopee broadcast trên portal VN** + soạn nội dung "nhắc restock".
3. Phối hợp kho **phủ tem mọi đơn masked**.
4. Theo dõi ROI ở `/hug/vouchers`, mở rộng theo dữ liệu.
</content>
