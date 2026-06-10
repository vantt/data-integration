---
title: "Cơ chế bán hàng — Retention Mechanisms"
stage: 4
status: idea
source: ../reference/sales-slowdown-diagnosis-and-action-playbook.md
---

# Cơ chế bán hàng — Retention Mechanisms

> Các cơ chế solution-level chắt từ nhóm lens B (first-principles).
> Trạng thái mặc định: **idea** (chưa triển khai).
> Lens nguồn: [first-principles-lenses.md](../perspectives/first-principles-lenses.md)

---

## Card 1 — JTBD: Bán "kết quả/sự kiện", không bán collagen

**Ý tưởng**
Phân khúc lại message theo "job to be done" thay vì theo sản phẩm: khách mua cho mình (self-care, chu kỳ đều) vs mua làm quà (mẹ, Tết — đúng pattern US-gift). Trigger acquisition bắt mùa sự kiện (Tết, hè, mùa cưới), không chỉ nhịp sinh lý reorder.

**Vì sao (first principle)**
Không ai mua collagen vì collagen — họ "thuê" nó cho một job cảm xúc/sự kiện (trẻ lại trước cưới, da đẹp để tự tin, làm quà cho mẹ). Message hiện tại tả timeline sinh lý (đúng cho reorder) nhưng bỏ qua trigger mua ban đầu là cảm xúc/sự kiện.

**Cách triển khai**
- Audit lại tệp khách: gắn tag `job_type = self_care | gift` dựa trên pattern đơn (đơn có địa chỉ khác giao/nhận, đơn dịp Tết/lễ).
- Viết 2 bộ message khác nhau: self-care (nhịp đều, kết quả dài hạn) vs gift (dịp đặc biệt, ý nghĩa trao tặng).
- Lịch campaign acquisition: lên lịch 3 đợt/năm theo mùa sự kiện lớn.

**Trạng thái:** idea

**Lens nguồn:** B4 — [first-principles-lenses.md](../perspectives/first-principles-lenses.md)

---

## Card 2 — Subscribe & Save: Biến reorder thành mặc định

**Ý tưởng**
Cung cấp tùy chọn "đăng ký giao định kỳ 45 ngày, giảm 10% + freeship". Biến quyết định reorder (dễ rớt) thành mặc định (phải chủ động hủy). Metric Bắc Đẩu đổi thành **"active replenishers"** thay vì "số đơn".

**Vì sao (first principle)**
Hàng tái mua mỗi 45–60 ngày = mô hình subscription trá hình. Tài sản thật không phải "số đơn" mà là số khách đang trong chu kỳ replenish. Đang bán từng đơn rời rạc → mỗi lần hết là "quyết định mới" → dễ rớt sang chỗ khác hoặc quên. Đòn bẩy M1-repeat mạnh hơn voucher win-back.

**Cách triển khai**
- Thiết kế flow "Subscribe & Save" trên kênh nhà (Web/Zalo OA): khách chọn chu kỳ 45 ngày, giảm 10% + freeship.
- Thêm cột `is_subscriber` + `subscription_status` vào `dim_customers` để theo dõi.
- KPI mới: đếm `active_replenishers` (khách có subscription active) hàng tháng.
- Ưu tiên pitch cho nhóm OVERDUE/AT_RISK trước — đang hết nhưng chưa đặt lại.

**Trạng thái:** idea

**Lens nguồn:** B5 — [first-principles-lenses.md](../perspectives/first-principles-lenses.md)

---

## Card 3 — Trust/Chính hãng làm con hào

**Ý tưởng**
Biến "chính hãng" thành positioning chủ lực qua tem/QR truy xuất. Tận dụng luồng US-gift làm bảo chứng trust: "người nhà gửi từ Mỹ = chính hãng 100%" → pitch mua nội địa cùng nguồn, khỏi chờ.

**Vì sao (first principle)**
Supplement VN ngập hàng giả; lý do #1 khách không mua lại / mua chỗ rẻ = sợ giả. Luồng US-gift (~824 người nhận VN) không phải "tệp chưa trả tiền" mà là tài sản trust — họ đã cầm hàng thật. Đây có thể là một nguyên nhân core collapse mà data không thấy.

**Cách triển khai**
- Gắn tem chống giả + QR truy xuất nguồn gốc lên mọi sản phẩm.
- Script US-gift xoay quanh trust transfer: *"Anh/chị đang dùng hàng người nhà gửi — chính hãng. Bên em là cùng nguồn chính hãng đó tại VN, khỏi chờ gửi từ Mỹ."*
- Đưa "chống giả" thành positioning chính trên mọi kênh (Social, Web, hộp hàng).
- Trước khi outbound call US-gift: audit hộp hàng CrossBorder có card/QR/hướng dẫn dùng chưa — nếu không có, fix trước.

**Trạng thái:** idea

**Lens nguồn:** B6 — [first-principles-lenses.md](../perspectives/first-principles-lenses.md)

---

## Card 4 — Touch "kết quả" + Referral Flywheel

**Ý tưởng**
Thêm Touch "kết quả" (~tuần 6–8 sau mua): xin review/ảnh before-after + mã giới thiệu ("giới thiệu bạn, cả hai được X"). Bổ sung vào sequence 3-touchpoint hiện có (Day 3 / Day 21 / Day 45). Vá xô thủng từ đầu vào, không chỉ giữ nước.

**Vì sao (first principle)**
Collagen cho kết quả nhìn thấy + mang tính xã hội (da đẹp → người ta hỏi). Khách hài lòng tuần 6–8 là kênh acquisition rẻ nhất (CAC ≈ 0). Touch 3 hiện tại (Day 45) chỉ nhắm reorder — bỏ lỡ cú "xin giới thiệu/UGC" đúng lúc khách thấy kết quả rõ nhất.

**Cách triển khai**
- Thêm **Touch 4** (~Day 48–56): *"[Tên], dùng được 6–7 tuần rồi — đây là lúc nhiều khách thấy rõ nhất. Anh/chị có thể chia sẻ 1 ảnh / cảm nhận không? Và nếu muốn giới thiệu bạn bè, cả hai được [X]."*
- Tạo mã referral cá nhân, track trong Sheet hoặc hệ thống đơn hàng.
- Ghi outcome: số review thu được, số referral kích hoạt, CAC từ kênh này.
- Sequence đầy đủ sau khi bổ sung: Day 3 (dùng đúng) → Day 21 (cơ thể đang thay đổi) → Day 45 (reorder) → Day 48–56 (kết quả + giới thiệu).

**Trạng thái:** idea

**Lens nguồn:** B7 — [first-principles-lenses.md](../perspectives/first-principles-lenses.md)
