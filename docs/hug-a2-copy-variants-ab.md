# Hug A2 — Bộ copy tiếng Việt (A/B variants)

> Viết cho chiến dịch bắt liên hệ khách mua-lặp ẩn danh (MASKED_REPEAT) qua tem QR trong kiện.
> **Ngôn điệu:** ấm, chỉn chu, cao cấp — không sến, không "sale sốc".
> **Placeholder:** `[SP]` = tên sản phẩm cụ thể | `[link-shop]` = URL shop Shopee | `[link-zalo]` = link follow Zalo OA.
> Cập nhật 2026-06-21.

---

## Bảng tổng — Khuyến nghị mặc định (chạy đầu)

| Surface | Mặc định | Lý do |
|---|---|---|
| Thẻ trong kiện | **Góc A / v1** | "Chính hãng + xác thực" là hook tự nhiên nhất khi tay cầm hộp — không cần lý do mua thêm |
| Landing M1 | **Góc A / v1** | Xác nhận tức thì → thiện cảm ngay, trước khi xin bất cứ thứ gì |
| Landing M2 | **Góc B / v1** | "Nhắc liệu trình" = giá trị thực > "bảo hành chung chung" |
| Landing M3 | **Góc B / v1** | Khung dịch vụ (không gián đoạn liệu trình) thuyết phục hơn 50K với AOV cao |
| Landing M4 | **Góc A / v1** | Ngắn, ấm, không oversell sau khi đã có cam kết |
| Zalo Ngày 0 | **Góc A / v1** | Ưu tiên xác nhận → khách vừa opt-in cần được "chốt niềm tin" ngay |
| Zalo Ngày 3–5 | **Góc B / v1** | Tip dùng đúng = giá trị thuần, không bán |
| Zalo Hết hộp | **Góc B / v1** | "Đừng ngắt liệu trình" + link → trigger mua lại tự nhiên |
| Shopee Broadcast | **Góc A / v1** | Chính hãng + mồi quét tem — an toàn ToS, không xin contact |
| FAQ | Dùng toàn bộ | FAQ không A/B, cần đủ để xử lý mọi nghi ngờ |

---

## 1. Thẻ / insert trong kiện

> Giới hạn: ~40–60 ký tự dòng chính + 1–2 dòng phụ. In 2 mặt thẻ nhỏ (85×55mm hoặc tương đương).
> Mục tiêu duy nhất: khách nhìn thấy, tò mò, quét QR.

---

### Góc A — Chính hãng / Xác thực

**Insert-A / v1** *(khuyến nghị mặc định)*
```
Xác thực hàng chính hãng FineJapan
Quét QR để kiểm tra lô hàng + nhận hướng dẫn dùng đúng liệu trình.
(Kèm ưu đãi dành riêng cho bạn.)
```

**Insert-A / v2**
```
Sản phẩm này có tem xác thực FineJapan.
Quét QR — xem ngay lô hàng có hợp lệ không + nhận tài liệu dùng chuẩn.
```

> Ghi chú: v1 dùng "chính hãng" trước, v2 dùng "tem xác thực" — test cái nào click-through cao hơn.

---

### Góc B — Liệu trình / Không gián đoạn

**Insert-B / v1**
```
Dùng đúng liệu trình — hiệu quả mới rõ.
Quét QR để nhận lịch nhắc + hướng dẫn kết hợp từ chuyên gia.
(Và một ưu đãi nhỏ cho lần sau.)
```

**Insert-B / v2**
```
[SP] cần dùng đủ liệu trình mới phát huy tác dụng.
Quét QR — nhận nhắc tái dùng + hướng dẫn cá nhân hóa cho bạn.
```

---

### Góc C — Ưu đãi (baseline/control)

**Insert-C / v1**
```
Cảm ơn bạn đã chọn FineJapan.
Quét QR để nhận mã giảm 50.000đ cho đơn sau.
```

**Insert-C / v2**
```
Ưu đãi dành riêng cho khách FineJapan.
Quét QR — nhận ngay mã HUG50 (giảm 50K đơn kế tiếp).
```

> Ghi chú: Góc C là control để đo baseline opt-in rate. Chạy song song với A hoặc B, KHÔNG chạy cùng lúc cả 3 (split nhỏ không đủ ý nghĩa thống kê).

---

## 2. Landing opt-in — 4 màn (mobile)

> Thiết kế: trắng/xanh navy/vàng gold. Font sạch. Mỗi màn = 1 action duy nhất.
> Câu body: ≤2 dòng hiển thị không cần scroll. Nút CTA: rõ, đủ lớn (tối thiểu 48px).

---

### M1 — Tin tưởng (chưa xin gì)

*Mục tiêu: xác nhận hàng thật ngay, tạo thiện cảm trước khi yêu cầu bất cứ điều gì.*

**Landing-M1 / Góc A / v1** *(khuyến nghị mặc định)*
```
[Icon check xanh lá / dấu ✓ lớn]

Sản phẩm chính hãng FineJapan
Lô hàng hợp lệ — xuất xứ Nhật Bản, nhập khẩu chính ngạch.

[Logo FineJapan]
```
> Nút: Xem hướng dẫn dùng →

**Landing-M1 / Góc A / v2**
```
[Icon tem xác thực]

Đã xác thực: hàng thật FineJapan
Tem này thuộc lô [mã lô] — nhập khẩu chính ngạch, còn hạn sử dụng.

[Logo FineJapan]
```
> Nút: Nhận hướng dẫn dùng →

**Landing-M1 / Góc B / v1**
```
[Icon lịch / nhịp tim nhẹ]

Chào bạn — bạn đang dùng [SP] FineJapan.
Để liệu trình phát huy hiệu quả, dùng đúng cách và đủ thời gian là quan trọng nhất.

[Logo FineJapan]
```
> Nút: Nhận hướng dẫn liệu trình →

**Landing-M1 / Góc C / v1**
```
[Icon quà / hộp]

Cảm ơn bạn đã chọn FineJapan.
Chúng tôi có một ưu đãi nhỏ dành riêng cho bạn — khách mua chính hãng.

[Logo FineJapan]
```
> Nút: Nhận ưu đãi →

---

### M2 — Mời follow Zalo OA

*Mục tiêu: đổi giá trị cụ thể lấy 1 chạm follow — nhẹ hơn xin SĐT.*

**Landing-M2 / Góc A / v1** *(khuyến nghị mặc định)*
```
Theo dõi FineJapan trên Zalo
để nhận:

  • Hướng dẫn dùng [SP] đúng liệu trình
  • Xác thực nhanh khi mua lần sau
  • Hỗ trợ từ dược sĩ khi cần

Miễn phí — 1 chạm theo dõi, hủy bất kỳ lúc nào.
```
> Nút: [icon Zalo] Theo dõi Zalo FineJapan

**Landing-M2 / Góc A / v2**
```
Nhận tài liệu chính hãng từ FineJapan
qua Zalo — gồm:

  • Cách dùng [SP] đúng & đủ liệu trình
  • Bảo hành sản phẩm nếu có vấn đề
  • Cập nhật hàng về kho (tránh đứt hàng)
```
> Nút: [icon Zalo] Theo dõi ngay

**Landing-M2 / Góc B / v1**
```
Liệu trình [SP] thường kéo dài [X] tuần.
Theo dõi Zalo FineJapan — chúng tôi sẽ nhắc bạn
đúng lúc cần tái dùng, kèm hướng dẫn kết hợp.

Không spam. Chỉ thông tin chăm sóc sức khỏe của bạn.
```
> Nút: [icon Zalo] Theo dõi để được nhắc

**Landing-M2 / Góc C / v1**
```
Theo dõi Zalo FineJapan
để nhận mã ưu đãi 50.000đ và thông tin hàng mới về kho.

1 chạm — hủy bất kỳ lúc nào.
```
> Nút: [icon Zalo] Theo dõi & nhận ưu đãi

---

### M3 — Xin SĐT (khung dịch vụ + consent)

*Bước thoát mask. Ngôn ngữ = dịch vụ thật, không phải marketing. Bắt buộc có dòng consent + hủy được.*
*Giới hạn: input field SĐT + 1 checkbox + 1 nút.*

**Landing-M3 / Góc B / v1** *(khuyến nghị mặc định)*
```
Để chúng tôi chăm sóc liệu trình cho bạn

Vì bạn mua qua sàn, FineJapan chưa có cách liên hệ
khi gần hết hộp hoặc khi bạn cần hỗ trợ.

Để lại số điện thoại — chúng tôi sẽ nhắc bạn
đúng thời điểm tái dùng (không gián đoạn liệu trình)
và gửi mã ưu đãi thành viên.

[Ô nhập SĐT]

☐ Tôi đồng ý nhận thông tin chăm sóc từ FineJapan qua SMS/Zalo.
  Mục đích: nhắc lịch tái dùng & ưu đãi thành viên.
  Hủy bất kỳ lúc nào bằng cách nhắn "HUY" hoặc nhấn hủy trong Zalo.
```
> Nút: Xác nhận & nhận mã ưu đãi

**Landing-M3 / Góc B / v2**
```
Nhắc liệu trình — dịch vụ miễn phí từ FineJapan

[SP] hiệu quả nhất khi dùng liên tục không ngắt quãng.
Chúng tôi sẽ nhắc bạn trước khi hết hộp khoảng [X] ngày
— để bạn kịp đặt đơn, không bị gián đoạn.

Để lại SĐT để kích hoạt dịch vụ nhắc này.

[Ô nhập SĐT]

☐ Tôi đồng ý để FineJapan liên hệ chăm sóc (nhắc tái dùng & ưu đãi).
  Không spam. Hủy bất kỳ lúc nào.
```
> Nút: Kích hoạt nhắc liệu trình

**Landing-M3 / Góc A / v1**
```
Kích hoạt bảo hành & chăm sóc chính hãng

FineJapan chỉ bảo hành và hỗ trợ trực tiếp
với khách đã đăng ký — vì qua sàn, chúng tôi không có SĐT của bạn.

Để lại số để kích hoạt:
  • Bảo hành sản phẩm nếu có vấn đề
  • Hỗ trợ dược sĩ khi cần tư vấn
  • Mã ưu đãi thành viên (50K đơn sau)

[Ô nhập SĐT]

☐ Tôi đồng ý nhận thông tin chăm sóc từ FineJapan (bảo hành, ưu đãi, nhắc tái dùng).
  Hủy bất kỳ lúc nào — nhắn "HUY" hoặc nhấn hủy trong Zalo.
```
> Nút: Kích hoạt quyền lợi thành viên

**Landing-M3 / Góc C / v1**
```
Nhận mã giảm 50.000đ

Để lại số điện thoại để nhận mã HUG50
(giảm 50K áp dụng cho đơn từ 300K trên Shopee FineJapan).

[Ô nhập SĐT]

☐ Tôi đồng ý nhận ưu đãi và thông tin chăm sóc từ FineJapan.
  Hủy bất kỳ lúc nào — nhắn "HUY".
```
> Nút: Nhận mã HUG50

---

### M4 — Hiện mã HUG50 + cảm ơn

*Sau khi có SĐT. Ngắn, ấm, không oversell. Mã phải nổi bật.*

**Landing-M4 / Góc A / v1** *(khuyến nghị mặc định)*
```
Cảm ơn bạn — đã thêm vào danh sách chăm sóc FineJapan.

Mã ưu đãi của bạn:

        HUG50

Giảm 50.000đ cho đơn từ 300K — dùng lần đặt tiếp theo trên Shopee.
Mã này chỉ dành riêng cho bạn, dùng 1 lần.

Chúng tôi sẽ nhắc bạn qua Zalo khi gần đến lúc tái dùng [SP].
```
> Nút phụ (nhỏ hơn): Đặt ngay trên Shopee → [link-shop]

**Landing-M4 / Góc B / v1**
```
Đã kích hoạt nhắc liệu trình cho bạn.

Mã ưu đãi lần sau:

        HUG50

Giảm 50.000đ — áp dụng khi đặt lại trên Shopee FineJapan.

Chúng tôi sẽ nhắn nhắc bạn trước khi hết hộp.
Giờ cứ dùng đúng liệu trình — để hiệu quả nhất.
```
> Nút phụ: Xem hướng dẫn dùng [SP]

**Landing-M4 / Góc C / v1**
```
Mã của bạn đây:

        HUG50

Giảm 50.000đ cho đơn từ 300K trên Shopee FineJapan.
Dùng lần đặt tiếp — mã 1 lần, không hết hạn trong 90 ngày.

Cảm ơn bạn đã tin tưởng FineJapan.
```
> Nút: Đặt ngay trên Shopee → [link-shop]

---

## 3. Zalo OA nurture

> Giới hạn: Zalo OA broadcast ~300 ký tự hiển thị đầy đủ không truncate. Không dùng quá nhiều icon.
> Tone: ấm, ngắn, hữu ích — không push bán ở Ngày 0 và Ngày 3–5.

---

### Ngày 0 — Chào + xác nhận chính hãng + cách dùng

**Zalo-D0 / Góc A / v1** *(khuyến nghị mặc định)*
```
Xin chào — FineJapan ở đây.

Sản phẩm [SP] bạn vừa nhận đã được xác thực chính hãng, nhập khẩu chính ngạch từ Nhật Bản.

Để dùng hiệu quả nhất:
[hướng dẫn ngắn 2–3 dòng dành riêng cho SP này — điền khi triển khai]

Nếu có bất kỳ thắc mắc nào, nhắn tin vào đây — dược sĩ của chúng tôi sẽ phản hồi trong giờ hành chính.
```

**Zalo-D0 / Góc A / v2**
```
Cảm ơn bạn đã chọn [SP] FineJapan.

Hàng bạn nhận là hàng chính hãng — tem QR bạn vừa quét đã xác nhận điều đó.

[Hướng dẫn dùng tóm tắt cho SP]

Có gì cần hỏi về sản phẩm hay liệu trình — cứ nhắn vào đây nhé.
```

**Zalo-D0 / Góc B / v1**
```
Xin chào — FineJapan đây.

[SP] sẽ phát huy tốt nhất khi dùng đủ liệu trình và đúng cách.
Dưới đây là hướng dẫn ngắn gọn cho bạn:

[hướng dẫn dùng SP — điền khi triển khai]

Chúng tôi sẽ nhắc bạn khi gần đến thời điểm tái dùng.
Giờ cứ yên tâm dùng đều nhé.
```

---

### Ngày 3–5 — Tip dùng đúng / kết hợp (không bán)

**Zalo-D3 / Góc B / v1** *(khuyến nghị mặc định)*
```
Tip nhỏ từ FineJapan:

[SP] hấp thụ tốt hơn khi uống [vào buổi sáng/sau ăn/với nước ấm — điền theo SP].
Kết hợp với [thói quen/thực phẩm phù hợp] có thể hỗ trợ thêm hiệu quả.

Nếu bạn có câu hỏi gì về cách dùng, nhắn vào đây — chúng tôi luôn ở đây.
```

**Zalo-D3 / Góc B / v2**
```
Bạn đang dùng [SP] được vài ngày rồi.

Một điều ít người biết: [insight thực tế về SP — điền khi triển khai].

Duy trì đều đặn — hiệu quả thường rõ hơn sau [X] tuần.
Có gì muốn hỏi thêm không?
```

**Zalo-D3 / Góc A / v1**
```
Từ FineJapan — một lưu ý nhỏ khi dùng [SP]:

[Tip dùng đúng — điền theo SP]

Sản phẩm chính hãng từ Nhật có thành phần chuẩn nồng độ,
nên dùng đúng liều là đủ — không cần tăng thêm.

Cần tư vấn thêm, nhắn vào đây nhé.
```

---

### Khoảng hết hộp — Nhắc restock

*Timing: tính theo vòng dùng SP (ví dụ: SP 30 ngày → gửi ngày 23–25). Gửi qua Zalo, trỏ về Shopee.*

**Zalo-Restock / Góc B / v1** *(khuyến nghị mặc định)*
```
Bạn sắp dùng hết [SP] rồi.

Để không bị gián đoạn liệu trình, nên đặt thêm trong 3–5 ngày tới.

Đặt lại trên Shopee FineJapan: [link-shop]
Nhớ nhập mã HUG50 để giảm 50.000đ.

(Hàng trong kho — ship ngay.)
```

**Zalo-Restock / Góc B / v2**
```
Nhắc nhỏ từ FineJapan:

Nếu bạn bắt đầu dùng [SP] khoảng [ngày X], giờ có lẽ còn [X] ngày nữa là hết.

Dừng giữa chừng có thể làm giảm hiệu quả của cả liệu trình.
Đặt thêm kịp để không bị hổng: [link-shop]

Mã HUG50 vẫn còn hiệu lực cho bạn — giảm 50K.
```

**Zalo-Restock / Góc A / v1**
```
Gần đến lúc tái dùng [SP] rồi.

FineJapan luôn có hàng chính hãng tại shop Shopee — đặt ngay để nhận đúng hàng, đúng lô.

[link-shop]

Dùng mã HUG50 — giảm 50.000đ, áp dụng cho đơn từ 300K.
```

---

## 4. Shopee Chat Broadcast (Dormant — ToS-safe)

> Ràng buộc cứng: KHÔNG hỏi SĐT/Zalo, KHÔNG rủ mua ngoài sàn. Chỉ: restock + trỏ shop + mồi quét tem.
> Giới hạn: ~200–250 ký tự (Shopee broadcast). Kiểm tra lại giới hạn ký tự trên portal trước khi gửi.

---

**Broadcast / Góc A / v1** *(khuyến nghị mặc định)*
```
FineJapan: bạn từng dùng [SP] — hàng vẫn có trên shop.
Đặt lại: [link-shop]

Lưu ý: trong kiện có tem QR xác thực chính hãng — nhớ quét để xem lô hàng hợp lệ nhé.
```

**Broadcast / Góc A / v2**
```
Chào bạn — [SP] FineJapan vẫn còn hàng, ship ngay.
[link-shop]

Kiện có tem xác thực chính hãng — quét QR kiểm tra nguồn gốc sau khi nhận hàng.
```

**Broadcast / Góc B / v1**
```
FineJapan nhắc nhỏ: nếu bạn đang dùng dở liệu trình [SP] mà đã dừng,
vẫn chưa muộn để tiếp tục — hàng còn tại shop.

[link-shop] (kèm hướng dẫn tái dùng trong kiện.)
```

**Broadcast / Góc B / v2**
```
Bạn từng dùng [SP] FineJapan.
Liệu trình dùng liên tục hiệu quả hơn — hàng đang có tại shop, đặt được ngay.

[link-shop]
Trong kiện có tem xác thực + hướng dẫn dùng chuẩn.
```

> Ghi chú: Không cần Góc C riêng cho Broadcast — mã giảm không được phép đề cập bên ngoài landing (tránh nhầm lẫn với voucher reactivation riêng biệt trên sàn).

---

## 5. FAQ — Xử lý nghi ngờ

> Dùng toàn bộ, không A/B. Đặt ở cuối landing hoặc trong menu Zalo OA.
> Tone: thẳng thắn, không phòng thủ.

---

**Q1: Sao shop cần số điện thoại của tôi?**

> Vì bạn mua qua Shopee, FineJapan không nhận được số điện thoại từ sàn — đó là chính sách của Shopee, không phải lỗi của shop.
> Số của bạn chỉ dùng để: nhắc khi gần hết hộp (không gián đoạn liệu trình) và gửi ưu đãi thành viên.
> Không dùng cho mục đích nào khác. Hủy bất kỳ lúc nào bằng cách nhắn "HUY".

---

**Q2: Có bị spam không?**

> Không. FineJapan chỉ nhắn khi gần đến thời điểm tái dùng sản phẩm của bạn (1–2 lần/chu kỳ hộp) và khi có ưu đãi dành riêng cho thành viên.
> Bạn có thể hủy nhận tin bất kỳ lúc nào — nhắn "HUY" vào Zalo hoặc nhấn hủy theo dõi Zalo OA.

---

**Q3: Tôi đã mua nhiều lần trên Shopee — sao bây giờ mới liên hệ?**

> Đúng vậy — trước đây Shopee không cho phép shop liên hệ trực tiếp với khách đã mua.
> Hệ thống tem xác thực này là cách FineJapan mở kênh chăm sóc trực tiếp lần đầu tiên.
> Cảm ơn bạn đã tin tưởng shop từ trước đến nay.

---

**Q4: Thông tin của tôi có được bảo mật không?**

> Có. FineJapan thu thập và lưu trữ thông tin theo Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân.
> Số điện thoại của bạn không được chia sẻ hoặc bán cho bên thứ ba.
> Bạn có quyền yêu cầu xóa thông tin bất kỳ lúc nào — nhắn "XOA" vào Zalo hoặc liên hệ shop.

---

**Q5: Mã HUG50 dùng như thế nào?**

> Nhập mã **HUG50** vào ô "Mã giảm giá" khi đặt đơn trên Shopee FineJapan.
> Điều kiện: đơn từ 300.000đ, mỗi tài khoản dùng 1 lần, hiệu lực 90 ngày kể từ ngày đăng ký.
> Nếu mã báo lỗi, nhắn vào Zalo — shop xử lý trong 24h.

---

## Ghi chú triển khai

| Hạng mục | Placeholder | Điền trước go-live |
|---|---|---|
| Tên sản phẩm | `[SP]` | Ví dụ: "Collagen EX", "Tảo Spirulina" |
| Link shop Shopee | `[link-shop]` | URL rút gọn của shop |
| Link follow Zalo OA | `[link-zalo]` | Deep link hoặc QR Zalo OA |
| Thời gian liệu trình | `[X] tuần`, `[X] ngày` | Theo từng SKU |
| Hướng dẫn dùng SP | `[hướng dẫn...]` | Copy từ nhà sản xuất / dược sĩ |
| Ngày bắt đầu dùng | `[ngày X]` | Dynamic (từ dữ liệu opt-in timestamp) |

---

*Cuối file.*
