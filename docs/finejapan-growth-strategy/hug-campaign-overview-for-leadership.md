# Hug — Chiến lược khai thác tệp khách (cho Ban lãnh đạo & Marketing)

> Giải thích **toàn bộ chiến dịch Hug** + **kịch bản khai thác từng tập khách** bằng ngôn ngữ kinh doanh.
> Số liệu lấy **trực tiếp từ dữ liệu sống** (`mart_customer_tier` + `fact_orders`), cập nhật 2026-06-21. Tổng ~7.565 khách.
> Dựa trên 3 nghiên cứu sâu trong `plans/reports/`: Shopee/Tiki seller reactivation · masked-repeat economics · **margin anomalies root-cause**.
> 📄 **Cần bản A2 đọc nhanh 1 trang?** → [`hug-a2-campaign-onepager.md`](./hug-a2-campaign-onepager.md) (one-pager tóm tắt chiến dịch A2; tài liệu này vẫn là chiến lược Hug đầy đủ).

---

## TL;DR (đọc 60 giây)

- Ta có **3.428 khách "ẩn danh" (masked)** — mua qua Shopee/Tiki nên **bị che liên hệ**, **0 người gọi/nhắn được**.
- Đáng giá nhất: **433 khách "mua-lặp ẩn danh" (MASKED_REPEAT)** — nhưng **~15 là tài khoản B2B/export bị phân loại nhầm** (xem cảnh báo dưới) → **~418 khách tiêu dùng thật**, lifetime CM **~2,95 tỷ** (sau khi loại artifact).
- **Vấn đề lõi:** với khách masked ta **chỉ chạm được khi họ đặt hàng** (nhét QR vào kiện). Mà chỉ **~69 khách (16%) còn active**; **~364 đã churn** → không có kiện để chạm.
- **TIN TỐT (đã kiểm chứng):** **Shopee Chat Broadcast** chạm khách đã mua **tới 720 ngày, miễn phí, không cần follow** → **kênh chủ động** đánh thức nhóm ngủ đông. Tiki yếu (chỉ ads).
- **Lời giải = 2 kênh nối tiếp:** Shopee broadcast **đánh thức** → khách mua lại → **Hug nhét-tem bắt định danh** → **thoát mask vĩnh viễn**.
- **Tư duy lại:** capture = biến khách masked thành **tài sản liên hệ suốt đời**; voucher = **chi phí thoát-mask**. **50K quá nhỏ so với AOV cao** → chỉ là token opt-in, không phải đòn bẩy reactivation.

> ⚠️ **PHÁT HIỆN DỮ LIỆU QUAN TRỌNG (lớn hơn Hug):** 2 "bất thường" trước đây **đều là ARTIFACT**, không phải lỗ thật:
> - "Bucket A lỗ −1,25 triệu/đơn" → do **15 tài khoản B2B/export/nội bộ** (đơn giảm 100%, doanh thu thu ngoài Sapo) lọt nhầm. Khách nhỏ THẬT chỉ có CM mỏng dương (~+9,9K/đơn).
> - "Khách −1,1 tỷ" = **"Fine Japan-USA"** — tài khoản export gắn nhầm RETAIL (12 đơn, gross 6,7 tỷ nhưng net=0, COGS 1,1 tỷ booked).
> - **Hệ thống:** mẫu "net=0 + COGS booked" có ở **3.544 đơn / 1.711 khách / méo ~−23,7 tỷ CM** trên TOÀN warehouse → **mọi báo cáo CM/gross-profit đang bị lệch**. Cần xác nhận nghiệp vụ (export thu ngoài Sapo?) + thêm cờ loại trừ trong mart. *(Đây là việc riêng, ảnh hưởng rộng hơn Hug.)*

---

## 1. Bản đồ tệp khách — 2 trục: **Liên hệ được?** × **Giá trị/hành vi**

| Tier | Liên hệ? | Số khách | Hướng khai thác |
|---|---|---|---|
| **MASKED_REPEAT** | ❌ masked | **433** (~418 tiêu dùng + ~15 B2B nhầm) | 🎯 **Shopee broadcast + Hug** |
| masked NONBUYER | ❌ masked | 1.192 | Thấp |
| masked GRAVEYARD | ❌ masked | 1.803 | Bỏ qua |
| LIVE_CORE | ✅ real | 56 | Giữ chân + upsell + loyalty |
| SECOND_ORDER | ✅ real | 27 | Nudge lên đơn 3 (ngày 7–10) |
| DORMANT_VALUABLE | ✅ real | 122 | Win-back trực tiếp |
| LAPSED_VALUABLE | ✅ real | 1.144 | Win-back theo lô: thử → đo → suppress |
| (real) NONBUYER/GRAVEYARD | ✅ real | ~2.789 | Activation rẻ / bỏ qua |

- "❌ masked" (3.428) = **chỉ Shopee broadcast + Hug chạm được**.
- "✅ real" (4.137) = **marketing trực tiếp được ngay** (không cần Hug).

---

## 2. Vì sao masked khó — và khó đến mức nào

### Cơ chế: chỉ chạm được khi khách mua
Sàn giấu SĐT. Điểm chạm vật lý duy nhất ta kiểm soát là **kiện hàng** — chỉ có khi khách **đã đặt đơn**.

### "Ngủ đông" thực ra là **churn**, không phải chu kỳ chậm
Khoảng cách mua-lại median chỉ **7 ngày** → khi còn active họ quay vòng rất nhanh. Recency median 508 ngày là do tệp **lưỡng cực**: nhóm nhỏ cycle nhanh + nhóm lớn **đã bỏ đi**. ⇒ Active: Hug bắt trong ~1 tháng; churn: phải đánh thức.

### Bản đồ 3 vùng theo khả năng tiếp cận (433 masked-repeat)
| Vùng | Recency | Số khách | Tiếp cận |
|---|---|---|---|
| **1 — Active** | ≤ 90 ngày | **69** | Hug bắt ngay ở đơn kế tiếp |
| **2 — Dormant tiếp cận được** | 91–720 ngày | **283** (~259 qua sàn) | **Shopee Chat Broadcast** đánh thức |
| **3 — Lost** | > 720 ngày | **81** | ❌ ngoài tầm công cụ → chi phí chìm |

→ **Vùng tiếp cận được (1+2) = ~321 khách.** Shopee broadcast giới hạn 720 ngày.

---

## 3. Tư duy lại: capture là gì, voucher là gì

- **Capture = chuyển khách masked → liên hệ trực tiếp** → mở mọi kênh chủ động suốt đời. Đó là tài sản, không phải 1 lần redeem.
- **Voucher = chi phí thoát-mask (CAC)**, ROI tính theo giá trị remarketing trọn đời.
- **50K quá nhỏ** với khách AOV cao → chỉ là token opt-in; muốn đánh thức cần đòn bẩy mạnh hơn (%, quà bậc, nhắc đúng chu kỳ restock).
- **Holdout bắt buộc:** một phần khách dù sao cũng quay lại → phải có nhóm đối chứng để đo offer thực sự "nhấc" bao nhiêu.

### Offer bậc thang (đã sửa theo root-cause)
| Nhóm | Thực chất | Offer |
|---|---|---|
| ~15 tài khoản "AOV thấp" | **B2B/export/nội bộ phân loại nhầm** (không phải khách tiêu dùng) | ❌ Loại khỏi target (và **sửa phân loại** trong dữ liệu) |
| 82 khách đơn nhỏ thật (<500K) | CM mỏng **dương** (~+9,9K/đơn) | ❌ Không tặng (50K > CM → lỗ ROI) |
| Khách AOV ≥ 1M | CM dương an toàn | ✅ 50K (hoặc % nếu cần đòn bẩy mạnh) |

---

## 4. Chiến lược tiếp cận masked — 3 kênh, theo trình tự

### Kênh 1 — Hug nhét tem vào kiện (đã xây xong)
Reactive — bắt định danh trên đơn khách *đang* mua. Tem ~0đ; chi phí thật chỉ khi redeem. **Phủ tem mọi đơn masked**. Tốt nhất cho **Vùng 1 (69 active)**.

### Kênh 2 — Shopee Chat Broadcast (đã kiểm chứng ✅) — kênh chủ động tới masked ngủ đông
- **Chat Broadcast:** chạm khách đã mua **tới 720 ngày, miễn phí, không cần follow** (cap ~1 tin/khách/ngày, ~2× follower/tuần). **Viết như nhắc restock**, không blast KM → tránh phạt spam.
- **GMV Max + Smart Voucher:** voucher **Shopee tài trợ (0đ với seller)**, thuật toán re-serve khách cũ.
- **Follow Prize:** tăng follower → nới trần broadcast.
- **Tiki:** yếu (chỉ ads).
- ⚠️ **Còn xác nhận cuối:** trần broadcast trên portal VN; Smart Voucher có ở VN không; xin xác nhận ToS cho tem-insert Zalo.

### Kênh 3 — Định danh "bóng" (dedup)
Hiện 0/3.428 masked có liên hệ → chạy 1 lượt dedup để chắc.

### Tuân thủ ToS sàn
- ✅ Được: tem/insert "**follow Zalo nhận bảo hành / ưu đãi thành viên / tư vấn**" (chào **dịch vụ**). QR Hug chỉ kích hoạt **sau khi khách đã hoàn tất đơn** → không vi phạm.
- ❌ Cấm: dùng chat sàn **rủ giao dịch ngoài sàn** → khóa shop.

### Trình tự
```
[Dormant ≤720d 283] ──Shopee broadcast──► đặt đơn ──► [kiện] ──► Hug bắt ──┐
[Active 69]         ──────────────────────► đơn kế tiếp ─► [kiện] ──► Hug bắt ─┤
[Lost >720d 81]    ── bỏ ────────────────────────────────────────────────────┘
                                                                              ▼
                                                 Thoát mask → CRM trực tiếp suốt đời
```

---

## 5. Playbook theo từng tập

| Tập | Đòn đánh | Kênh | Ghi chú |
|---|---|---|---|
| **MASKED_REPEAT Vùng 1 (69 active)** | Hug A2: tem + opt-in | Kiện | ROI cao, nhanh; cần holdout |
| **MASKED_REPEAT Vùng 2 (283 dormant ≤720d)** | Shopee broadcast đánh thức → reorder → Hug bắt | Shopee→kiện | Khối lớn nhất; phụ thuộc năng lực sàn |
| **MASKED_REPEAT Vùng 3 (81 lost >720d)** | Bỏ | — | Ngoài tầm công cụ |
| ~15 tài khoản B2B/export nhầm | **Sửa phân loại** (không phải mục tiêu marketing) | — | Đang làm méo số liệu |
| masked NONBUYER/GRAVEYARD (~3.000) | Bắt cơ hội nếu có đơn | Kiện | Không đổ ngân sách |
| LIVE_CORE (56) | Giữ chân + upsell + loyalty | Trực tiếp + Hug loyalty | Khách lõi |
| SECOND_ORDER (27) | Nudge đơn 3 (ngày 7–10) | Trực tiếp | Cửa sổ tạo thói quen |
| DORMANT_VALUABLE (122) | Win-back trực tiếp | Trực tiếp | Có liên hệ → đánh ngay |
| LAPSED_VALUABLE (1.144) | Win-back theo lô: thử→đo→suppress | Trực tiếp | Tìm sub-segment phản hồi |

---

## 6. Kịch bản (thận trọng → lạc quan)

| Kịch bản | Giả định | Kết quả |
|---|---|---|
| **Xấu** | Sàn chặn broadcast | Bắt ~69 active; 283 dormant kẹt; 81 mất |
| **Thực tế** | Hug phủ tốt + Shopee broadcast hiệu lực | Bắt 69 active nhanh; đánh thức + bắt **một phần** 283 (tùy R); 81 bỏ |
| **Tốt** | Opt-in cao + broadcast tốt + offer đúng tầm | Bắt phần lớn 321 vùng tiếp cận được |

**Chốt tư duy:** không hứa "mở khóa 433 ngay". Hứa: **phủ tem + thử Shopee broadcast có holdout đo lường**, mở rộng theo dữ liệu.

---

## 7. Đo lường & cổng quyết định

Phễu: ① **Phủ tem** (~100% đơn masked) → ② **Tỷ lệ quét** → ③ **Tỷ lệ opt-in** (= "tỷ lệ thoát mask") → ④ **Đánh thức nội sàn** (reorder/khách được broadcast) → ⑤ **Redeem & margin tăng thực** (so holdout).
- Màn ROI voucher: **`/hug/vouchers`**.
- **Holdout:** Vùng 1 (~62) đo được (đọc 60–90 ngày); Vùng 2 chỉ định hướng (mẫu nhỏ).

---

## 8. Trạng thái xây dựng + Go-live

### ✅ Đã xong
Hạ tầng QR (`hug.fjp.vn`) · sinh & in tem cuộn · trạm gắn tem · trang opt-in (Zalo + SĐT + hiện mã) · bắt định danh tự động + hàng đợi CS · sổ phát hành & đối soát voucher · **màn quản trị chiến dịch** (`/hug/campaigns`) · màn ROI (`/hug/vouchers`).

### 🚦 Go-live A2 dạng PILOT (khuyến nghị — không full-launch)
1. Tạo mã **HUG50** Sapo (chỉ áp khách AOV ≥1M).
2. Set Zalo OA + deploy landing.
3. Tạo chiến dịch A2 qua `/hug/campaigns` (package_insert × MASKED_REPEAT, **loại 15 tài khoản B2B**).
4. Quét thử nghiệm thu.
5. Brief kho phủ tem.
6. Song song: chuẩn bị Shopee Chat Broadcast đánh thức Vùng 2.

---

## 9. Lộ trình mở rộng

| Hạng mục | Ghi chú |
|---|---|
| **Sửa dữ liệu export/zero-revenue (23,7 tỷ)** | **Ưu tiên riêng** — méo mọi báo cáo CM; cần xác nhận nghiệp vụ + cờ loại trừ trong mart |
| **Shopee broadcast đánh thức Vùng 2** | Việc chiến lược kế tiếp — mở 283 dormant |
| Win-back khách "real" (~1.180) | Doanh thu sớm, không cần Hug |
| ZNS (nhắn Zalo tự động) | Sau khi bắt liên hệ; cần verify OA + duyệt template |
| A/B testing offer + holdout | Đo incrementality |
| Điểm chạm Hug khác / mã riêng từng khách | Khi A2 ổn |

---

## 10. Con số tóm tắt (verify từ dữ liệu sống)

| Chỉ số | Giá trị |
|---|---|
| Tổng khách | ~7.565 |
| Masked (0 liên hệ được) | **3.428** |
| MASKED_REPEAT | **433** (gồm ~15 B2B/export nhầm → **~418 tiêu dùng**, CM ~**2,95 tỷ** sau loại artifact) |
| — Vùng 1 active (≤90d) | **69** → Hug bắt ngay |
| — Vùng 2 dormant tiếp cận (91–720d) | **283** (~259 qua sàn) → Shopee broadcast |
| — Vùng 3 lost (>720d) | **81** → mất |
| Khách "real" liên hệ ngay | ~4.137 (gồm ~1.180 dormant đáng win-back) |
| Kênh masked-repeat | ~84% marketplace |
| ⚠️ Đơn "net=0 + COGS booked" (lỗi hệ thống) | **3.544 đơn / 1.711 khách / ~−23,7 tỷ CM méo** |
| Chi phí hạ tầng Hug | ≈ $0 |

> "683M" (plan cũ) **bỏ** — thay bằng số verify ở trên; "cơ hội forward" tính sau pilot (từ tỷ lệ reactivation thật).

---

## 11. Quyết định cần chốt & việc cần làm

**Quyết định (đã có khuyến nghị):**
1. Loại Bucket A khỏi voucher → **CÓ** (15 B2B: sửa phân loại; 82 nhỏ: 50K > CM).
2. Tỷ lệ reactivation R → **đừng đoán, đo bằng pilot** (ngân sách ở 10%).
3. Báo cáo dùng median + **loại tài khoản zero-net-revenue** → **CÓ**.
4. "683M" → **bỏ**, dùng 418 khách / ~2,95 tỷ + forward sau pilot.
5. ~52 khách giá trị cao ngoài sàn → CS chạm tay 1:1, **điều tra kênh trước**.
6. Bật holdout lô đầu → **CÓ** (chính là cách đo R).
7. *(Mới)* **Sửa vấn đề dữ liệu export/zero-revenue (23,7 tỷ)** — xác nhận nghiệp vụ rồi thêm cờ loại trừ trong mart.

**Hành động Marketing:**
1. Chốt thể lệ & mức ưu đãi (50K token vs %/quà bậc).
2. **Xác nhận cuối năng lực Shopee broadcast (portal VN)** + soạn nội dung "nhắc restock".
3. Phối hợp kho **phủ tem mọi đơn masked**.
4. Theo dõi ROI ở `/hug/vouchers`, mở rộng theo dữ liệu.

### Khuyến nghị bước đi — PILOT có holdout (~2–4 tuần) trước khi scale
| Arm | Tệp | Treat/Control | Đo gì | Cửa đọc |
|---|---|---|---|---|
| **A — Hug tem** | Vùng 1 active (AOV≥1M, loại B2B) | ~40 / ~22 | opt-in + mua-lại | 60–90 ngày |
| **B — Shopee broadcast** | Vùng 2 dormant ≤720d | ~130 / ~70 | reactivation **R** (định hướng) | 120–180 ngày |

Mỗi arm 1 mã riêng; loại tài khoản zero-net-revenue khỏi tính toán. **Cổng:** đạt ngưỡng opt-in/redeem/R → scale; không → chỉnh hoặc dừng. Mục tiêu: chi tiền nhỏ để **học con số thật** thay vì đoán.

*(Backing kỹ thuật — tùy chọn, không cần để nắm chiến lược: `plans/260620-2357-hug-a2-pilot-holdout/`, `plans/260620-1408-crm-hug-voucher-a2-golive/`, `plans/reports/`.)*
</content>
