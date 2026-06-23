# FineJapan — Chẩn đoán "bán ế" & hướng khai thông

> **One-page cho Leadership.** Mọi con số từ dữ liệu sống (DuckDB warehouse, 2021→2026). Tự-chứa, đọc 1 mạch. Cập nhật 2026-06-21.
> Báo cáo kỹ thuật chi tiết (phụ lục) liệt kê cuối trang — **không cần mở để ra quyết định**.

---

## Kết luận 1 dòng
Sản phẩm **không** mắc, **không** kém tác dụng, **không** cần đổi. Vấn đề thật: **mất cánh cửa khách-mới giá-rẻ + không giữ chân khách cũ** → xô thủng, vòi teo. Khai thông = **dựng lại "mồi nhử" giá rẻ đa kênh + bật giữ-chân (Hug)**, KHÔNG cần vốn mới.

---

## 1. Dữ liệu bác bỏ 3 nỗi lo
| Nỗi lo | Dữ liệu nói |
|---|---|
| "Sản phẩm quá mắc" | Sai. **8 SKU lõi** (Đông trùng/miễn dịch + xương khớp) biên LN thực **60–82%**, gánh **60,5% doanh thu B2C** — từ khách mua-lặp. Mắc mà vẫn lặp = đúng tệp. |
| "TPCN không thấy tác dụng → không ai mua lại" | Sai. First→second order **~22–25% ổn định** suốt 2024, 2026-Q1 = **29,9%**. Ai mua thì vẫn quay lại. |
| "Phải đổi sản phẩm / không biết ngách" | Ngách đã rõ trong data = 8 SKU lõi. Dead-stock thật chỉ là **quà tặng + dòng ngừng KD (~42M)** — 0 SKU lõi nào ế. |

→ **Đừng đổi sản phẩm. Đừng cần vốn mới.**

## 2. Chẩn đoán gốc — HAI lỗ rò, không phải lỗi sản phẩm

**Lỗ A — Vòi nước teo 75%: phễu khách-mới sụp, do MẤT "cửa giá rẻ".**
- Khách-mới B2C: đỉnh **~365/quý (2024-Q3)** → còn **~115/quý** nay. **Shopee** là thủ phạm: **325 → 61** (2024-Q3→2025-Q3, **−81%**), vực gãy **2025-Q2** (−51% trong 1 quý).
- **Phụ thuộc 1 kênh chết người:** Shopee từ 68% → **87%** khách-mới. Kênh đa dạng cũ (Selly 25% một quý 2022, Lazada, Tiki, POS) **biến mất sạch** — không có kênh dự phòng.
- **Insight then chốt:** cú bùng 2022 do **SKU mồi giá rẻ** (kem chống nắng ~300K, canxi ~200K) qua Selly + Shopee promo → bắt khách → bán lên TPCN premium tiền-triệu. **"Cửa giá rẻ" chết → acquisition sụp.** 2026-Q2 SKU mồi mới (Coix Beauty ~230K, 48 khách) tự xuất hiện lại = playbook cũ vẫn chạy được.

**Lỗ B — Xô thủng: khách cũ già đi vì không ai chăm.**
- **59%** khách mua-lặp đã mất (>720d). Base lặp-active đỉnh 2024 (378) → 264 (2025, **−30%**). Lý do: masked + **0 nurture** → trôi mất.
- Nhịp mua lại: **median 49 ngày**, P75 157 ngày → cửa sổ nhắc rõ ràng (chạm ngày 14 + refill ngày ~45).

> **Tóm gốc:** Premium là sản phẩm **kiếm tiền (back-end)**, không phải sản phẩm **bắt khách (front-end)**. 2022 thắng nhờ **mồi rẻ → khách → premium lặp**. Khi mất mồi rẻ + dồn hết vào 1 sàn + không giữ chân → vừa hết khách mới vừa rụng khách cũ. Cảm giác "mắc, khốc liệt" = **đặt sản phẩm sai chỗ trong phễu**, không phải sản phẩm tồi.

**Cơ chế order đã được xác nhận + cập nhật (2026-06-22):**
- Bundle xảy ra **đồng đơn (co-purchase)**, không phải trình tự đơn 1 → đơn 2. 554 khách mua entry+premium cùng đơn đầu vs chỉ 20 khách upgrade qua đơn kế (tỷ lệ 27:1). → **Rep phải bundle ngay trong đơn, không thể chờ khách tự upgrade**.
- **Đảo ngược quan trọng:** Trong multi-SKU orders, **75% dòng Metabo và 78% dòng Gaba có net_revenue = 0** → là quà tặng rep tặng kèm, không phải sản phẩm khách tự chọn. **Premium SKU là trigger thực sự** (Shark/Natto/Cordyceps/Fucoidan, avg revenue 1.9–4.3M/đơn); rep TẶNG Metabo/Gaba như gift để tăng giá trị đơn hàng.
- Solo entry orders (Metabo 90% có revenue thật, Coix 89%) = pool khách entry mới — upsell premium về sau khi rep follow-up.
- 50% đơn retail là single-item — basket nhỏ là norm. Entry-only buyer chỉ có 2% quay lại với premium nếu không có rep bundle.
- **Discount không phải lever**: chỉ 2.4% đơn có giảm giá; multi-item orders không được discount nhiều hơn single-item.

## 3. Hướng khai thông (ưu tiên theo ROI / vốn)
1. **Dựng lại "mồi nhử" giá rẻ, ĐA KÊNH** *(gốc của tăng trưởng)*: SKU rẻ (kem chống nắng/canxi/Coix) làm cửa bắt khách → upsell premium. **Trải nhiều kênh** (affiliate/Selly-like, TikTok Shop, Tiki) — gỡ phụ thuộc 87% Shopee. Vốn thấp (SKU mồi rẻ, đã có sẵn).
2. **Bật giữ-chân ngay (Hug + nurture Zalo)** *(rẻ nhất, đã build gần xong)*: nhắc refill theo nhịp 49 ngày, ngừng để 59% base trôi. Biến khách-mồi → khách-premium-lặp.
3. **Gỡ rủi ro 1-kênh**: đa dạng kênh acquisition song song với việc cứu thứ hạng Shopee.

## 4. Quick win — 0 đồng
SKU `VTST23042L001` (Natto Kinase) biên **−32,7%**, doanh thu 112M → **đang đốt lợi nhuận**. Sửa giá/COGS hoặc bỏ ngay = thu lại GP.

## 5. Câu hỏi CHỈ leadership trả lời được (dữ liệu chỉ ra "khi nào/ở đâu", không ra "vì sao")
- **Vì sao Shopee sụp 2025-Q2?** Cắt ngân sách ads? Tụt hạng/listing? Đổi thuật toán sàn? Đối thủ?
- **Vì sao kênh Selly (25% khách 2022) đóng?** Chủ động bỏ hay bị mất?
- Có chủ ý ngừng "SKU mồi giá rẻ" không, hay rơi rớt tự nhiên?
- Coix Beauty 2026-Q2 là chiến dịch có chủ đích hay tình cờ? (nếu có chủ đích → nhân rộng đúng công thức cũ).
- **"Viên uống Gaba huyết áp" là sản phẩm gì?** Data cho thấy 132 đơn Cordyceps+Gaba, 92 đơn Natto Kinase+Gaba, 52 đơn Shark Cartilage+Gaba — top-3 pair cho nhiều premium SKU. Gaba của FineJapan hay phân phối ngoài? Khách segment nào? Nếu là sản phẩm nội bộ → cần đưa vào playbook upsell.

---

## Nguồn chi tiết (phụ lục kỹ thuật — tùy chọn)
- Cohort & retention: `plans/reports/cohort-retention-diagnostic-260621-2121-report.md`
- SKU repeat × margin: `plans/reports/sku-repeat-margin-triage-260621-2121-report.md`
- Acquisition collapse theo kênh: `plans/reports/acquisition-collapse-channel-localization-260621-2139-report.md`
- Entry → premium upgrade paths (Path A/B, 554 vs 20): `plans/reports/finejapan-entry-to-premium-upgrade-path-260622-1241-report.md`
- Basket size & discount motivation: `plans/reports/finejapan-basket-analysis-and-discount-motivation-260622-report.md`
- Entry SKU = gift in multi-SKU orders (zero-rev analysis): `plans/reports/finejapan-gift-entry-sku-zero-rev-260622-1720-report.md`
- Triển khai giữ-chân (Hug A2): `docs/finejapan-growth-strategy/hug-a2-campaign-onepager.md`
