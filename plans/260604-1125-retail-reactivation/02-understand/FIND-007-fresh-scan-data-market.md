---
title: "FIND-007 - Fresh Scan Data And Market"
stage: 2
status: resolved
source: "6 sub-agent (4 data nội bộ DuckDB standalone + 2 research thị trường) — 2026-06-13"
---

# FIND-007 - Fresh Scan Data And Market

**Registry:** [FIND-007](../REGISTRY.md#find-007)

> Quét lại data tươi (standalone DB 2026-06-13 03:10) + research ngoài. Mục tiêu: tìm góc nhìn/insight
> plan CHƯA có. 6 phát hiện lớn dưới đây, kèm 4 chỗ MÂU THUẪN với giả định cũ cần chốt lại.

---

## A. "Ế" THẬT SỰ LÀ GÌ — chốt bằng số (order-date)

**Không phải mất cầu. Là (1) base khách co lại + (2) dòng tiền.**

- Doanh thu net theo **order-date** (đúng), retail T1-T5: 2025 = 775tr → 2026 = 715tr (**−8%, gần phẳng**).
  Jun 1-13: **2026 = 220tr vs 2025 = 119tr (+85%)**. June KHÔNG phải đáy mùa vụ (+2% so trung bình).
- **Ảo giác completed-only:** T5/2026 completed-only = 107tr vs all-order = 295tr; T6 = 50 vs 220. Phóng đại "ế" 3-4×.
- **Tín hiệu thật bị che:** số đơn retail **−55%** (479-539/quý đỉnh 2024 → ~200/quý 2025-26) nhưng
  **AOV +57%** (1.27tr → 2.0tr). ⇒ ít người mua hơn, mỗi người mua to hơn → **base đang co về lõi trung thành**.
  Đây là vấn đề **ACQUISITION/xói mòn base**, KHÁC với "rò retention" — bị AOV tăng che mất.
- **Cashflow cấp tính:** T5-T6/2026 **64-77% doanh thu UNPAID** (B2B credit). Tổng AR chưa thu toàn lịch sử ≈ **3.9 tỷ**.
  → Cảm giác "ế" của chủ nhiều khả năng = **nhìn tài khoản ngân hàng**, không phải sổ đơn.

→ Việc #1 vẫn đúng: hỏi chủ/kế toán nợ thật + fix `fact_payments`. Nhưng thêm việc mới: **vì sao base đơn co 55%?**

---

## B. ĐÒN BẨY MỚI LỚN NHẤT — Sản phẩm-cổng-vào (entry SKU → retention)

Plan đã hoãn câu này (Tier 2). Data trả lời rồi, và nó **đổi cách hiểu "72% one-time"**: không phải lỗi cỗ-máy-nhắc,
mà là **mix sản phẩm đầu vào sai**.

| Entry SKU/nhóm | #khách vào | Repeat | LTV | Phán |
|---|---|---|---|---|
| **UV Care Plus (kem chống nắng)** | **400 (lớn NHẤT)** | **10.3%** | **380K** | 🔴 RÒ RỈ acquisition #1 |
| Bone's Calcium Kids | 262 | 14% | 410K | 🔴 ngõ cụt |
| Metabo Green Tea | 211 | 12% | 450K | 🔴 ngõ cụt |
| Cordyceps standard | 196 | 31% | 3.07tr | 🟢 gateway volume |
| Fucoidan | 258 | 29.5% | 4.51tr | 🟢 gateway volume |
| Hyaluron&Collagen+Swallow | 54 | 37% | 9.9tr | 🟢 gateway giá trị |
| Cordyceps Plus | 68 | 35% | 14.8tr | 🟢 gateway giá trị |
| Đông trùng nước (CORP.H) | 26 | 50% | 16.6tr | 🟢 niche cực dính |

**Insight:** ~900 khách (UV Care + Kids + Metabo) vào bằng SP ngõ-cụt 10-14% repeat — kéo tụt one-time-rate toàn brand.
Đây là cohort lớn nhất, và nó chưa từng nằm trong plan. **Lái acquisition về cordyceps/collagen/fucoidan ≈ +450tr LTV** (ước thô).
Đông trùng nước + Reishi (undermarketed) = gateway ẩn đáng đẩy.

### B+ Product-scan bổ sung 2026-06-13 (cắt theo CÔNG DỤNG + THƯƠNG HIỆU + cross-sell)

> `category` quá thô (chỉ "Dietary Supplement") nhưng `product_name` mã hóa công dụng → parse tên ra nhóm.

**Repeat theo CÔNG DỤNG (entry, n≥20) — sạch hơn cắt theo SKU:**

| Công dụng | n khách vào | Repeat |
|---|---|---|
| Tiểu đường | 62 | 29.0% 🟢 (niche dính) |
| **Đông trùng/Miễn dịch** | **1.238 (lớn nhất)** | 28.3% 🟢 gateway volume |
| Collagen/Làm đẹp | 463 | 27.4% 🟢 |
| Tim mạch/Đột quỵ | 533 | 23.1% 🟡 |
| Giảm cân/Trà | 269 | 14.9% 🔴 |
| **Khớp/Xương sụn** | 323 | **14.9% 🔴 BẤT NGỜ** |
| Chống nắng/Da liễu | 427 | 10.1% 🔴 ngõ cụt |
| Não/Thần kinh | 25 | 8.0% 🔴 |

🔻 **BẤT NGỜ: Khớp/Xương sụn chỉ 15% repeat** — dù "khớp" là nhu cầu hero của người già. Khách vào bằng sụn vi cá/canxi KHÔNG quay lại. Mâu thuẫn với khung "hero = sức khỏe người già". (→ câu hỏi mới Q17)

**Repeat theo THƯƠNG HIỆU — đây là nhà phân phối ĐA-BRAND, không chỉ Fine Japan:**

| Brand | n entry | Repeat |
|---|---|---|
| Fine Japan Vietnam | **3.199 (78%)** | 21.9% |
| Genki Fami | 100 | 26.0% 🟢 |
| Fujina | 184 | 19.0% |
| Kirkland | 23 | 8.7% 🔴 |
| Jpanwell | 34 | **0% 🔴 (chết)** |

→ Fine Japan vẫn áp đảo volume; brand ngoài (Jpanwell 0%, Kirkland 8.7%) yếu — ứng viên dừng nhập.

**Cross-sell UV Care (giải Q13):** 409 khách vào UV Care, chỉ 42 quay lại; khi quay lại **72% lại mua UV Care**, gần như 0 bắc cầu sang cordyceps/collagen/tim mạch. ⇒ **UV Care là ngõ cụt da liễu tự-đóng, KHÔNG phải tripwire nuôi phễu hero** → cắt acquisition an toàn. Q13 ✅ RESOLVED.

**Kết luận product-scan:** không cần data thô thêm — dùng `product_name` để build seed `product_function`; phân tích/dashboard nên cắt theo công dụng + brand (không chỉ SKU). Khớp/Xương sụn 15% là red flag cần điều tra (efficacy? quà 1 lần? sai SKU?).

---

## C. CHÊNH LỆCH CHẤT LƯỢNG KÊNH — định lượng, và đòn bẩy đảo ngược

L2 đã nêu định tính; giờ có số cứng:

| Kênh | #khách | Repeat | Contactable | LTV/khách |
|---|---|---|---|---|
| **Shopee** | **2.873 (70% lẻ)** | 19% | **32.6%** | 1.76tr |
| Zalo | 147 | 35% | 98% | **9.36tr (5.3× Shopee)** |
| Facebook | 198 | 32% | 96.5% | 5.99tr |
| Offline-POS | 151 | 39% | 93% | 4.84tr |
| Lazada | 203 | 38% | 96.6% | 3.15tr |
| **Tiki** | 111 | 14% | **1.8%** | 1.92tr |

**Đòn bẩy đảo ngược:** gap LTV Shopee↔Zalo ~21.8 tỷ nhưng **phần lớn KHÔNG cứu được vì 67% khách Shopee vô danh**.
⇒ Lever cao nhất KHÔNG phải "tăng retention Shopee" mà là **bắt liên hệ Shopee tại điểm bán** (thẻ/QR → Zalo OA).
Tiki = ngõ cụt thuần (mang tiền, 1.8% liên-hệ-được — bỏ effort reactivation).

---

## D. ĐỊA LÝ — pocket chưa ai chạm (góc nhìn HOÀN TOÀN MỚI)

- **HCM = 51.7% doanh thu** (rủi ro tập trung). HCM+HN = 58%.
- **Repeat cao bất ngờ ở tỉnh nhỏ, base nhỏ, Shopee-acquired, 0 offline:**
  Bà Rịa-Vũng Tàu 33%, Gia Lai 32%, Quảng Ngãi 32%, Vĩnh Long 27%, An Giang 26%, Đắk Lắk 26%, Đà Nẵng 25%.
- **Cụm ĐBSCL** (An Giang+Bến Tre+Vĩnh Long+Long An): 208 khách, 797tr — đáng mở event/POS hub ở Cần Thơ.
- **Tây Nguyên** (Đắk Lắk+Gia Lai): LTV cao, repeat 26-32%, 0 POS.
- **Hà Nội repeat thấp dị thường 12.7%** (thấp nhất big city) — cần drill kênh.

---

## E. MÙA VỤ — settle tranh luận quà biếu bằng data

| Đỉnh | Tháng | Ghi chú |
|---|---|---|
| #1 | **T3 (8-3)** | đỉnh lẻ lớn nhất MỌI NĂM (688 đơn) |
| #2 | T6 | đỉnh, lý do chưa rõ |
| #3 | T11 | cuối năm |
| — | T1 (trước Tết) | mạnh, AOV cao |
| Đáy | T2, T4, T7 | cắt acquisition, chuyển reactivation |

- **T8 spike = B2B restocking (3.6×), KHÔNG phải gifting.**
- Timing gửi tin: **Thứ 2 + Thứ 5, 8h30-9h30 sáng**. Giữa tháng AOV cao nhất.

---

## F. CHU KỲ TÁI MUA + DISCOUNT — calibrate lại

- **Chu kỳ thực: median 63 ngày; cụm lớn nhất ~30 ngày (n=53), kế ~45 ngày (n=41).**
  ⇒ Subscribe&Save nên có nhịp **30 ngày** (không chỉ 45). Nhắc tái mua: gửi **ngày ~20-23**.
- **Discount KHÔNG phá retention** (ngược lo ngại "promo-dependent"): nhóm discount sâu repeat ≥ full-price
  (nhưng sample nhỏ + lẫn B2B/bulk → không kết luận nhân quả, cần A/B test).
  Rò lãi thật = **45 khách >25% discount nhận 504tr discount trên 410tr revenue (âm gross)**.
- **Census mép cứu-được tuần này: 15 khách contactable 31-90 ngày = 80tr LTV** (cửa sổ đang đóng, gọi ngay).
- **Action queue refresh 2026-06-13: 116 khách / 1.17 tỷ** (giảm từ 1.76 tỷ — một phần do khách đã mua).

---

## G. THỊ TRƯỜNG / RESEARCH — 5 insight ngoài data

1. **BUYER ≠ USER:** SKU sức khỏe người-lớn-tuổi nhưng **người mua là con 25-45 tuổi** (hiếu thảo/Vu Lan/Tết) —
   nhóm này ở NGAY trên TikTok/Shopee. ⇒ message + retention nhắm **người con** (về kết quả của bố/mẹ), không nhắm người dùng cuối.
   Đây là mắt xích plan reframe sản phẩm còn thiếu.
2. **"Cầu dịch sang TikTok" chỉ đúng NỬA:** TikTok Shop dẫn đầu TPCN nhưng phần migrate = **collagen/NMN anti-aging Gen-Z**,
   KHÔNG phải đông trùng/khớp/tim mạch người già. Hero SKU của brand ÍT bị TikTok đe dọa. Brand **chưa có official TikTok store = khoảng trắng**.
3. **Trên sàn giá-rẻ, seller không-ủy-quyền THẮNG official store** (Metric Q1-2025). ⇒ đua giá Shopee = thua chắc.
   Đòn bẩy "chính hãng chống giả" chỉ phát huy ở kênh verify được: **D2C web, nhà thuốc chuỗi, Shopee/TikTok Mall**.
4. **Nhà thuốc chuỗi (Long Châu/An Khang) = kênh niềm tin #1 cho TPCN người già** — Fine Japan có thể đang VẮNG MẶT (gap lớn).
   Orihiro có showroom vật lý; Fine Japan chỉ online.
5. **Giá VN ≈ 2× giá Fine Japan USA/viên** — nghi vấn nguyên nhân "ế" + lỗ hổng bị hàng xách-tay Mỹ undercut.
   **Không đối thủ nào chạy subscription/loyalty ở VN = first-mover white space.**

---

## H. BENCHMARK ĐẶT CƯỢC (research retention)

- **Kênh #1 cho VN = Zalo ZNS** (open 60-90% vs email 15-25%). **Prerequisite hạ tầng: Zalo OA verified** — làm trước mọi automation.
- Subscribe&Save: LTV 2.5-12×; **flexibility (skip/pause) quan trọng hơn discount sâu** (pause cứu 25% would-be-churn).
- Onboarding 3-touch: +30-45% second-purchase (case Vitaminstore 26% vs 20%). "Hướng dẫn dùng đúng" = đòn bẩy cảm-nhận-hiệu-quả.
- Win-back: SMS+email **+54% vs email-only**; ROI 7:1; trigger tối ưu 30-45 ngày sau đơn cuối.
- Referral health-category: **7.23% conversion** (top ngành); non-cash reward tốt hơn cash 25%; "tặng người thân hộp dùng thử" hợp gift-health.

---

## I. AUDIT KÊNH NHÀ (crawl 2 site D2C của chính mình — 2026-06-13)

> Crawl `finejapanvietnam.com` (15 SKU) + `jpcshop.vn` (8 SKU) — **CẢ HAI đều là kênh của mình**.
> Raw cache: [research/website-crawl/](../research/website-crawl/). 8 phát hiện (cross-ref data nội bộ):

1. **🟠 Kênh nhà phủ ~70% doanh thu, nhưng VẮNG 21 SKU gateway** (sửa: KHÔNG "bỏ đói" như nói ban đầu). Web phủ **8.95 tỷ / 12.83 tỷ = 69.8%** retail rev — bestseller CÓ trên web. Phần thiếu = 30.2% (3.88 tỷ) ở long-tail, trong đó **21 SKU entry-repeat ≥20% vắng hẳn** (top: Cordyceps VTSC20001L001 817M@28%, Gaba Blood, Chondroitin, Insuna/Tiểu đường, Calorie Burn — top-5 = 1.08 tỷ). → nạp các SKU giữ-khách này lên web (O9), không phải "nạp hàng trăm SKU".
2. **🔴 Xung đột kênh + tự cắt giá** (vì cả hai là của mình): cùng SKU, giá lệch tới **38%** (Hatomugi 99k ở FJV vs 136.5k ở JPC); Shark Cartilage JPC rẻ hơn FJV 11%. Hai kênh nhà cạnh tranh giá lẫn nhau → loãng định vị (O8).
3. **🟡 Giảm giá sâu KHÔNG phá margin** (sửa: KHÔNG phải clearance/ế như nói ban đầu). Sau khi lọc compare_at rác, các SKU giảm 50-75% vẫn **realized margin 52-73%** — discount tính từ giá-gốc-tham-chiếu cao (có thể giá US), KHÔNG ăn vào lãi, KHÔNG bán dưới giá vốn. Là chiêu neo giá, không phải xả hàng. Lưu ý: vài `compare_at` là data rác (11.25M thay vì 2.25M) → %off hiển thị một phần ảo.
4. **🔴 Bestseller HẾT HÀNG vẫn hiển thị (price=0):** Cordyceps Plus VCSL21002H010 (rev 1.2 tỷ, repeat 34%) + Natto VCST21003L001 (rev 765M) đang sold-out trên web nhưng vẫn show → mất đơn trực tiếp. Cùng 2 phantom listing zero-rev (PVN148/149).
5. **🔴 Margin âm cần kiểm:** Royal Reishi VTSC21006L001 (gateway, repeat 31%) margin **-35.9%**, VCSL19001C001 -283% — nghi artifact COGS/pack-SKU chưa fix (kiểu H010). Verify trước khi đẩy Reishi.
6. **🟠 Không có gift bundle** trên cả 2 site (chỉ "combo 2 hộp cùng SKU") — dù 8-3/Tết là đỉnh quà đã xác nhận. Cơ hội gifting còn nguyên.
7. **🟠 Định vị Khớp/Xương sụn = manh mối Q17:** Shark Cartilage claim mạnh "điều trị viêm/thoái hóa khớp/thoát vị" NHƯNG **không timeline/liệu trình/testimonial/chứng nhận** → khách kỳ vọng khỏi nhanh, uống vài tuần không thấy → bỏ (khớp repeat chỉ 15%). Lỗi quản-lý-kỳ-vọng, đúng lý thuyết L1.
8. **🟠 Đòn bẩy "chính hãng chống giả" CHƯA thực thi:** không tem QR, không nhà thuốc, không bảo hành, không chứng nhận — chỉ tag "chính hãng". Trong khi research nói đây là moat duy nhất ở kênh verify được.

---

## 🔻 4 MÂU THUẪN VỚI GIẢ ĐỊNH CŨ — cần chốt lại

1. **L5 "gift 2 dịp: Tết + tháng 10":** data nói **T10 (20-10) KHÔNG spike**. Lịch quà đúng = **Tết(T1) + 8-3(T3) + T11**. → sửa L5.
2. **demand-migration "cầu dịch sang TikTok":** đúng cho anti-aging, SAI cho hero SKU người già. → hạ mức báo động, đổi sang "thiếu official TikTok presence".
3. **Lo "promo-dependent phá loyalty":** data chưa thấy discount phá repeat. Rò lãi thật là **âm-gross 45 khách deep-discount**, không phải "phụ thuộc KM". → đổi trọng tâm.
4. **"72% one-time = cần cỗ máy nhắc":** thực chất phần lớn do **entry-SKU ngõ-cụt (UV Care/Kids/Metabo)**. Sửa mix đầu vào > xây thêm reminder.

---

## Câu hỏi chưa giải đáp (mới)

1. Vì sao base đơn retail co 55% từ đỉnh 2024? (event/promo/kênh gì tạo đỉnh 2024 rồi tắt?) — thiếu acquisition-source log.
2. 96 đơn UNPAID 2026 = credit term B2B bình thường hay bad-debt? — thiếu due_date.
3. ~~UV Care role gì~~ ✅ RESOLVED 2026-06-13: ngõ cụt tự-đóng (72% repeat lại mua UV Care, 0 bắc cầu hero) — cắt an toàn.
7. **Q17 (mới):** Vì sao **Khớp/Xương sụn entry chỉ 15% repeat** dù là nhu cầu hero người già? efficacy thấp / quà 1-lần / sai SKU? → có thể là lỗ hổng sản phẩm hoặc cảm-nhận-hiệu-quả, đáng đưa vào VOC.
8. **Q18 (mới):** Brand ngoài Fine Japan (Jpanwell 0%, Kirkland 8.7% repeat) — dừng nhập hay chỉ là noise volume nhỏ?
4. Fine Japan có trên Long Châu/An Khang không? (gap kênh niềm tin) — cần verify thực địa.
5. % đơn "con-mua-cho-bố-mẹ" là bao nhiêu? Nếu >40% → thiết kế lại toàn bộ retention theo buyer≠user.
6. CAC theo kênh không có → chưa tính được LTV/CAC thật (Zalo LTV cao nhưng CAC?).
