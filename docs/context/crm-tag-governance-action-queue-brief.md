# Tag CRM giờ đã "có tác dụng thật" — Governance + Đồng bộ Sapo + Ảnh hưởng đến ưu tiên gọi

> **Dành cho:** Quản lý Sales/CSKH, Ops — không cần biết kỹ thuật để đọc tài liệu này
> **Trạng thái:** Đã triển khai phần lớn (2026-07-07) — 1 phần nhỏ dời lại có chủ đích
> **Liên quan:** `plans/260619-0830-crm-tag-acl-sync/`, `plans/260706-0833-crm-health-profile-tag-governance/`, `plans/260706-1738-crm-tag-signal-action-queue-consumer/`

---

## TL;DR

Trước đây NV gắn tag (VD: "risk", "vip_tier", ghi chú sức khỏe) cho khách trong CRM, nhưng tag đó **không ảnh hưởng gì** đến việc ai được ưu tiên gọi — dữ liệu NV nhập vào "biến mất" trong hệ thống. Đồng thời tag từ Sapo (nhóm khách sỉ/lẻ) không tự động chảy vào CRM, và không có nơi nào dọn dẹp tag trùng/rác khi nó phình ra. Ba việc đã làm: (1) tự động đồng bộ tag nhóm khách từ Sapo vào CRM mà không phụ thuộc cách Sapo đặt tên, (2) cho NV gõ tag mới ngay lúc gọi điện thay vì phải chờ admin tạo trước, kèm màn hình cho ops dọn dẹp/duyệt tag, và (3) làm cho tag risk/vip_tier NV gắn tay **thật sự** đẩy khách lên/xuống trong hàng đợi ưu tiên gọi. Kết quả: NV nhập tag giờ thấy nó tạo ra khác biệt thật, thay vì nhập vào khoảng không.

---

## 1. Vấn đề & Bối cảnh

### Ba vấn đề riêng biệt nhưng cùng một gốc: dữ liệu NV nhập vào không "sống" được

| Vấn đề | Ví dụ cụ thể |
|---|---|
| **Tag từ Sapo không vào CRM** | Khách được xếp nhóm "Bán buôn" (khách sỉ) bên Sapo, nhưng trong CRM không có cách nào biết điều đó trừ khi NV tự gõ tay tag "KH Sỉ" — dễ quên, dễ sai. |
| **Tag phình không kiểm soát** | Rep gõ "huyết áp cao", "huyet ap cao", "cao huyết áp" — 3 tag khác nhau cho cùng 1 ý, vì không có cơ chế chuẩn hoá. NV muốn tạo tag mới cũng phải thoát ra màn hình Settings tạo trước, mất mạch khi đang gọi khách. |
| **Tag không ảnh hưởng gì đến hệ thống gợi ý** | NV đánh giá khách là "risk" (rủi ro), nhưng hệ thống gợi ý ai cần gọi hôm nay **hoàn toàn không biết** đánh giá đó tồn tại — khách vẫn xếp hàng bình thường như chưa từng được đánh giá. |

### Hậu quả kinh doanh nếu để nguyên

Đây là một **vòng lặp chết** (theo thiết kế UX gốc `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §5):

```
NV nhập tag/ghi chú → CRM lưu lại → KHÔNG ai/hệ thống nào dùng đến
    → NV thấy "nhập không ai dùng" → NV bỏ nhập
    → càng ít dữ liệu → hệ thống gợi ý càng kém chính xác
    → (lặp lại, ngày càng tệ hơn)
```

Vấn đề "tag không tự động từ Sapo" cũng không mới — đã được phát hiện từ tháng 4/2026 khi phân tích dữ liệu Sapo cho thấy nhóm khách (`customer_group`) là một khối JSON lộn xộn, không có bảng ánh xạ rõ ràng sang khái niệm CRM. Vấn đề này nằm im 3 tháng vì chưa ai cần dùng đến, cho tới khi việc gộp 3 sáng kiến này biến nó thành yêu cầu bắt buộc.

---

## 2. Giải pháp

Ba mảnh ghép, triển khai theo đúng thứ tự phụ thuộc (cái sau cần cái trước):

### A. Đồng bộ tự động từ Sapo (Anti-Corruption Layer)

CRM không còn phụ thuộc trực tiếp vào cách Sapo đặt tên nhóm khách. Có một "lớp phiên dịch" ở giữa: Sapo nói "nhóm 1812239 mã BANBUON", lớp phiên dịch dịch thành "KH Sỉ" cho CRM hiểu — nếu sau này đổi sang phần mềm bán hàng khác (Haravan...), chỉ cần dạy lại lớp phiên dịch, CRM không cần đổi gì. Tag đồng bộ tự động cập nhật khi khách đổi nhóm bên Sapo, và **không bao giờ ghi đè tag NV đã tự gán tay**.

> **Không có màn hình riêng cho phần này** — tag "KH Sỉ" tự động xuất hiện trên hồ sơ khách y hệt một tag NV tự gõ, NV không thấy khác biệt gì trên giao diện, chỉ khác ở chỗ NV không phải tự nhập nữa.

### B. NV gõ tag mới ngay lúc gọi + màn hình dọn dẹp cho Ops

NV không cần thoát ra Settings để tạo tag trước nữa — gõ tag mới ngay trong màn hình gọi điện (VD: nhập lĩnh vực sức khỏe, ghi chú tự do). Tag mới vào "hàng chờ duyệt" thay vì lên thẳng danh sách chính thức. Ops có màn hình riêng (`/settings/tags`) để duyệt, đổi tên, gộp tag trùng, hoặc lưu trữ tag không dùng nữa — tránh tình trạng phình tag như trước.

**Màn hình gọi khách — NV chọn/gõ tag ngay tại đây (không rời màn hình):**

```
• Lĩnh vực sức khỏe
  [Tim mạch] [Hô hấp] [Miễn dịch] [Xương khớp]
  [Tiêu hóa] [Thần kinh/Ngủ] [Năng lượng] [Da]
                                          [Lưu ✓]

• Ghi chú sức khỏe  [huyết áp cao, hay mệt...    ] [+]
```

**Màn hình Ops dọn dẹp tag (`/settings/tags`) — mỗi lĩnh vực 1 tab, cộng 2 hàng chờ duyệt riêng:**

```
[Sức khỏe] [Rủi ro] [Phân khúc] ...                    [+ Tag mới]
──────────────────────────────────────────────────────────────────
⚠ Chờ duyệt — đã biết lĩnh vực (8 tag)
  "huyết áp cao" · sức khỏe · 8 khách
    → [Xác nhận]  [Đổi tên]  [Gộp vào tag có sẵn]  [Xoá]

⚠ Chờ duyệt — chưa rõ lĩnh vực (5 tag)
  "khách hay hỏi combo" · 3 khách
    → Gán lĩnh vực: [chọn ▼]   [Xác nhận]  [Xoá]
```

### C. Tag risk/vip_tier giờ ảnh hưởng thật đến ai được gọi trước

Khách được NV gắn tag "risk" giờ xuất hiện ưu tiên cao trong danh sách gọi với nhãn riêng "Cần xác minh" — tách biệt với cảnh báo rủi ro tự động của hệ thống, vì đây là đánh giá của con người, không phải máy tính. Khách được NV gắn tag "vip_tier" được xử lý ưu tiên như khách VIP thật, ngay cả khi hệ thống tự động (dựa trên lịch sử mua hàng) chưa kịp cập nhật khách đó là VIP.

**Danh sách gọi việc hôm nay — 1 dòng khách mang tag "risk":**

```
[Cần xác minh]  Nguyễn Văn A
Lý do: NV đánh giá rủi ro: Cần follow-up — cần xác minh trước khi tiếp cận
```

### Trước và sau

| | Trước | Sau |
|---|---|---|
| Tag nhóm khách từ Sapo | Không có — NV tự gõ tay nếu nhớ | Tự động đồng bộ, tự cập nhật khi đổi nhóm |
| Tạo tag mới | Phải vào Settings tạo trước | Gõ ngay lúc gọi, ops duyệt sau |
| Tag trùng/rác | Không ai dọn, phình dần | Có màn hình gộp/lưu trữ cho Ops |
| Tag risk/vip_tier (NV gắn tay) | Chỉ hiển thị trên hồ sơ, không tác dụng gì thêm | Ảnh hưởng thật thứ tự ưu tiên gọi trong worklist |

---

## 3. Tại sao chọn cách này

| Quyết định | Vì sao |
|---|---|
| Dùng "lớp phiên dịch" (ACL) thay vì map thẳng Sapo → CRM | Nếu map thẳng, đổi phần mềm bán hàng sau này phải viết lại toàn bộ. Mẫu thiết kế này đã có tiền lệ trong hệ thống (dùng cho việc liên kết định danh khách hàng), tái sử dụng thay vì phát minh lại. |
| Cho phép NV tạo tag "chưa duyệt" thay vì chặn NV tạo tag mới | Nếu chặn (bắt phải vào Settings tạo trước), NV sẽ bỏ qua việc nhập vì mất mạch khi đang gọi khách — chấp nhận có "rác tạm thời" trong hàng chờ duyệt, đổi lấy việc NV không bị cản trở. |
| Chỉ tin tag do **con người** gán (không tin tag tự động đồng bộ) khi tính ưu tiên gọi | Nếu tính cả tag tự động, khách "KH Sỉ" (tự động từ Sapo) sẽ bị hệ thống hiểu nhầm thành "NV đã đánh giá thủ công" — sai lệch lý do hiển thị cho NV, mất niềm tin vào worklist. |
| Tag đồng bộ từ Sapo tự "biến mất" khi khách đổi nhóm (không giữ lại tag cũ) | Nếu giữ lại (append-only), CRM sẽ dần "trôi" khỏi sự thật hiện tại bên Sapo — một khách đã chuyển từ sỉ sang lẻ vẫn còn tag "KH Sỉ" treo mãi. |

---

## 4. Cách hoạt động (chi tiết)

### Hình dạng dữ liệu — mỗi tag "mang theo" gì

Không cần biết tên bảng/cột, chỉ cần hình dung mỗi lần một tag được gắn cho khách, hệ thống nhớ 4 thứ:

| Thông tin | Ý nghĩa | Ví dụ |
|---|---|---|
| Tên tag | Nội dung tag | "risk", "KH Sỉ", "tim-mach" |
| Ai gắn | Người (NV cụ thể) hay hệ thống tự động | NV Lan / tự động từ Sapo |
| Nguồn (nếu tự động) | Tag tự động lấy dữ liệu từ đâu | Nhóm khách Sapo "Bán buôn" |
| Trạng thái duyệt | Đã chính thức hay đang chờ Ops duyệt | Chính thức / Chờ duyệt |

Nhờ nhớ "ai gắn", hệ thống mới phân biệt được tag NV tự đánh giá (dùng để đổi ưu tiên gọi) với tag tự động đồng bộ (không dùng để đổi ưu tiên gọi — xem lý do ở mục 3).

**Luồng tag mới do NV tạo:**

```
NV gõ tag mới lúc gọi khách
    → CRM lưu tag ở trạng thái "chờ duyệt"
       (2 cấp: đã biết lĩnh vực / chưa biết lĩnh vực)
    → Ops vào /settings/tags xem hàng chờ
    → Ops: [Xác nhận] / [Đổi tên] / [Gộp vào tag có sẵn] / [Xoá]
    → Tag chính thức xuất hiện trong danh sách chọn nhanh (chip) cho NV lần sau
```

**Luồng tag ảnh hưởng đến ưu tiên gọi:**

```
NV gắn tag "risk" hoặc "vip_tier" cho khách
    → Dữ liệu này được đưa vào bảng tính ưu tiên gọi (chỉ tính tag do NV gán tay)
    → Khách "risk" → xuất hiện mục riêng "Cần xác minh" trong worklist
    → Khách "vip_tier" → được xử lý ưu tiên như VIP, dù hệ thống tự động chưa kịp cập nhật
    → NV thấy ngay: "tag mình gắn hôm qua đã đổi thứ tự gọi hôm nay"
```

---

## 5. Kết quả & trạng thái

### Đã thay đổi thật (đo được)

- Đồng bộ tag từ Sapo: 939 khách đã có tag tự động, xác nhận chạy đúng và không ghi đè tag NV tự gán.
- Màn hình quản lý tag cho Ops: đã dùng thật, kiểm chứng trực tiếp trên dữ liệu sống (gộp tag, lưu trữ tag, hàng chờ duyệt 2 cấp).
- Ưu tiên gọi theo tag: đã lên môi trường thật — hiện có khách mang nhãn "Cần xác minh" xuất hiện đúng vị trí ưu tiên trong danh sách gọi việc.

### Còn dang dở / cố ý dời lại

| Phần còn lại | Lý do dời | Theo dõi ở đâu |
|---|---|---|
| Ghi ngược tag CRM → Sapo (2 chiều) | Cần hạ tầng hàng đợi đồng bộ dùng chung cho nhiều thay đổi khác, chưa xây riêng cho việc này | Phase 04, `crm-tag-acl-sync` |
| Đưa tag sức khỏe vào kịch bản gợi ý gọi cho NV (script) | Cần refactor bộ sinh kịch bản trước, việc riêng | Phase 04, `crm-health-profile-tag-governance` |

---

## Câu hỏi thường gặp

1. **NV gắn tag "risk" nhầm thì sao?** — Ops sửa/xoá được trong màn hình quản lý tag (`/settings/tags`), không cần sửa trực tiếp trong database.
2. **Tag Sapo đồng bộ có ghi đè tag NV đã gán tay không?** — Không. Tag do NV gán luôn thắng; đồng bộ chỉ điền vào chỗ NV chưa gán.
3. **Vì sao tag mới không hiện ngay mà phải chờ ops duyệt?** — Để tránh tình trạng cùng một ý nhưng có 3-4 tag viết khác nhau (VD: "huyết áp cao" / "huyet ap cao" / "cao huyết áp") làm dữ liệu phân mảnh, khó lọc/báo cáo sau này.

---

## Kết luận

> Tag NV gắn tay giờ không còn là ghi chú tĩnh trên hồ sơ — nó thật sự đẩy khách lên/xuống trong hàng đợi ưu tiên gọi hôm nay.
