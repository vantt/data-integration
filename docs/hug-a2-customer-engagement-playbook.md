# Hug A2 — Playbook tiếp cận & bắt contact khách (masked)

> Kịch bản làm việc với khách: **vì sao, offer gì, dẫn dắt thế nào** để khách ẩn danh (Shopee/Tiki) chịu để lại liên hệ → thoát mask.
> Self-contained (đọc 1 mạch). Cập nhật 2026-06-21. Tổng quan A2: `docs/hug-a2-campaign-onepager.md`.

---

## 1. Ràng buộc cốt lõi — đọc trước khi làm gì
- Khách **masked = không có contact**; **sàn KHÔNG cho xin contact** (xin SĐT/Zalo qua chat sàn = vi phạm, khóa shop).
- ⇒ **Không thể xin contact trước.** Trình tự bắt buộc:
  **kích mua lại → khách mua (trên sàn) → kiện hàng có tem → khách quét → opt-in (cho contact).**
- Contact chỉ lấy được **trên mặt của mình** (landing, sau khi quét tem) — **sau cú mua**, **không phải trên sàn**.

## 2. Hai kênh — Hug mở "kênh quan hệ", KHÔNG dời "kênh giao dịch"
| | Giao dịch (nơi mua) | Quan hệ (cách liên lạc) |
|---|---|---|
| Là gì | Shopee/Tiki | **Zalo/SĐT (của mình)** |
| ToS | giữ trên sàn | sàn không quản |
- Khách **cứ mua trên sàn**; Hug chỉ **mở kênh để chăm sóc/nhắc** (trước đây = 0).
- **Qua công cụ sàn:** chỉ trỏ về sàn ("đặt lại trên shop"). **Qua Zalo (khách tự cho):** kênh mình, marketing được nhưng **service-first, dẫn dần**.

## 3. Trình tự theo nhóm (3 vùng)
- **Active ≤90d (~69):** đang mua đều → **KHỎI broadcast**. Chỉ **phủ tem** → đơn kế tiếp tự bắt contact. *(Quick win.)*
- **Dormant 91–720d (~283):** **broadcast đẩy mua + mồi quét tem** → mua trên Shopee → kiện → quét → opt-in.
- **Lost >720d (~81):** bỏ (ngoài tầm công cụ).

## 4. Triết lý chuyển đổi — 50K là phụ, "lý do" mới là chính
AOV tiền-triệu → 50K (~1,5% đơn) không đủ làm đòn bẩy. Bán **3 trụ lý do** (lợi ích của khách):
1. **Chính hãng** — "quét xác thực hàng thật" (nỗi lo #1 với TPCN Nhật) → lý do để quét + tạo niềm tin tức thì.
2. **Không gián đoạn liệu trình** — TPCN dùng theo đợt → "để lại SĐT, nhắc khi gần hết hộp" = dịch vụ thật, không phải marketing.
3. **Chăm sóc & ưu đãi thành viên** — bảo hành, dược sĩ tư vấn, + 50K lần sau.
→ **Lead bằng chính hãng + liệu trình; 50K chốt sau.**

## 5. Thang cam kết — mỗi bước 1 "yes" nhỏ
```
Nấc 0  QUÉT QR            (tò mò/xác thực — ma sát ~0)
Nấc 1  Nhận giá trị FREE  ("✓ Hàng chính hãng" — chưa xin gì → thiện cảm)
Nấc 2  FOLLOW ZALO        (1 chạm; nhẹ hơn SĐT) → "nhận hướng dẫn dùng + bảo hành"
Nấc 3  ĐỂ LẠI SĐT         (khung dịch vụ: nhắc tái dùng + ưu đãi)  ← bước thoát mask
Nấc 4  HIỆN MÃ 50K        (thưởng SAU cam kết)
Nấc 5  NUÔI DƯỠNG (Zalo)  tip → nhắc restock → 50K → mua lại
```
Nguyên tắc: **cho trước (xác thực) → xin sau**; **xin cái dễ trước (follow) → SĐT sau**; **lộ mã SAU khi có SĐT** (chỉ *tease* "có ưu đãi" trước).

## 6. Hai ưu đãi — ĐỪNG nhập làm một
- **Voucher reactivation** (trong broadcast): kéo khách dormant **quay lại mua lần 1**. Ưu tiên **Smart Voucher Shopee tài trợ (0đ)** / shop voucher.
- **HUG50** (trên landing, sau quét): **token để opt-in** + giảm cho lần *sau*.
→ Tránh chồng 2 cái thành giảm quá sâu.

## 7. Script cụ thể từng điểm chạm

**7.1 — Thẻ trong kiện (hook để quét):**
> 🇯🇵 *Cảm ơn bạn đã chọn FineJapan chính hãng.*
> **Quét QR để xác thực hàng thật + nhận hướng dẫn dùng đúng liệu trình.** *(Kèm ưu đãi 50K lần sau.)*

**7.2 — Landing opt-in (4 màn, theo thang §5):**
- M1 *(tin tưởng, chưa xin):* "✓ **Sản phẩm chính hãng FineJapan** — lô hợp lệ." + logo.
- M2 *(đổi giá trị lấy follow):* "**Theo dõi Zalo** nhận: hướng dẫn dùng · dược sĩ tư vấn · bảo hành." → nút Follow.
- M3 *(xin SĐT, khung dịch vụ + lý do thật):* "Bạn mua qua sàn nên shop **chưa có cách liên hệ chăm sóc**. Để lại SĐT để **được nhắc khi gần hết hộp (không gián đoạn liệu trình)** + **ưu đãi thành viên 50K**." + ☑ *đồng ý nhận chăm sóc, hủy bất kỳ lúc nào — không spam.*
- M4: "🎁 Mã **HUG50** giảm 50K đơn sau. Đã thêm vào nhóm chăm sóc ✓"

**7.3 — Zalo OA nurture (sau follow/opt-in):**
> Ngày 0: chào + xác nhận chính hãng + cách dùng SP vừa mua.
> Ngày 3–5: tip dùng đúng/kết hợp (giá trị, không bán).
> ~Hết hộp: **"Sắp hết [SP]? Đặt lại trên Shopee [link shop] — dùng HUG50."** ← mua-lại TRÊN SÀN.

**7.4 — Shopee Chat Broadcast (dormant — KHÔNG xin contact):**
> "FineJapan: bạn từng dùng [SP]. Sắp hết? Khách cũ có **mã giảm trên shop**. Đặt lại [link shop]. *Trong kiện có **tem xác thực chính hãng**, nhớ quét.*"
> *(Chỉ đẩy mua + mồi quét tem; tuyệt đối không hỏi SĐT/Zalo.)*

**7.5 — Xử lý nghi ngờ ("sao shop cần số tôi?"):**
> "Vì bạn mua qua sàn, shop **không thấy SĐT** — không thể bảo hành/nhắc liệu trình. Số **chỉ để chăm sóc đơn của bạn**, **không bán/không spam**, hủy 1 chạm."

## 8. Kinh tế — hiểu đúng để không kỳ vọng sai
- Cú **mua-lại lần 1 của khách dormant = chi phí "mua lại contact"** (trả voucher để có 1 đơn mà *chưa* giữ chân được). **Lãi thật từ đơn thứ 2** trở đi (khi đã có Zalo để nhắc).
- Phễu dormant **2 tầng** (broadcast→mua→quét→opt-in) → rơi rụng mỗi bước → **yield thấp & chậm**. **Active (69) là quick win**; đừng kỳ vọng bắt nhanh cả 283.

## 9. Đo lường & A/B (gắn vào pilot)
- Phễu: phủ tem → quét → **opt-in (= tỷ lệ thoát-mask)** → mua lại → redeem; đối chiếu **holdout**.
- **A/B chính = LÝ DO** ("xác thực chính hãng + liệu trình" vs "giảm 50K") → xem cái nào opt-in cao hơn. *(Quan trọng hơn mức giảm.)*
- Màn ROI: `/hug/vouchers`.

## 10. Tuân thủ
- **ToS sàn:** broadcast chỉ "restock/chính hãng + trỏ shop", không rủ ngoài sàn, không xin contact.
- **Nghị định 13/2023 (bảo vệ dữ liệu cá nhân):** ô **đồng ý rõ mục đích** + cho hủy → hợp pháp + tăng tin tưởng.

---

## Tóm 1 câu
**Khách masked: "mua lại trước → bắt contact sau (ở kiện)".** Broadcast chỉ đẩy mua + mồi quét tem; contact bắt ở landing sau khi hàng tới, bằng **lý do chính-hãng/liệu-trình** (không phải 50K), qua **thang micro-yes**. Active thì khỏi broadcast, cứ phủ tem.

## Còn chờ chốt (ảnh hưởng script)
- Mức offer thật (50K token vs %/quà cho khách giá trị cao).
- Voucher reactivation broadcast: Smart Voucher (Shopee tài trợ) hay shop voucher?
- Xác nhận năng lực Shopee Chat Broadcast trên portal VN.
- Nội dung A/B "lý do" cuối cùng (cần copywriter trau chuốt nhiều biến thể).
</content>
