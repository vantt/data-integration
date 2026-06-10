---
title: "First-Principles Lenses"
stage: 1
status: living
source: ../reference/sales-slowdown-diagnosis-and-action-playbook.md
---

## 0.5 Góc nhìn bổ sung — first-principles (cập nhật 2026-06-09)

> Section 0 giải quyết tầng **product × customer journey** (tại sao khách lẻ không reorder).
> Section này bổ sung các lens **first-principles** mà phân tích trước chưa có — vài lens **thách thức
> chính lựa chọn "tập trung B2C"**. Mục đích: mở thêm hướng action để tháo bế tắc, không thay thế plan.

### Nhóm A — Thách thức "BÁN CÁI GÌ / CHO AI TRƯỚC" (đòn bẩy cao nhất, chiến lược)

**A1. Đám cháy thật vs đám cháy chọn — B2B trước, B2C sau.**
First principle: doanh thu sụp 95% là do **5–10 khách sỉ** ngừng mua (B2B T1 42đơn/278tr → T5 2đơn/2tr),
không phải 995 khách lẻ one-time. Nhưng plan đổ toàn lực B2C — ván retention **2 quý mới ra tiền**.
Mismatch thời gian: B2C retention không trả hóa đơn tháng sau; reactivate **1 khách sỉ ≈ 100+ đơn lẻ**.
→ **Action:** trước call-list lẻ, gọi đích danh từng khách `discount_type=negotiated_deep` đã ngừng;
hỏi gốc: *bỏ vì giá / OOS / công nợ chạm trần / đối thủ?* Cuộc gọi đáng giá nhất tuần này.
*Không phủ nhận B2C — B2C đúng về cấu trúc dài hạn; A1 chỉ đảo thứ tự đốt lửa cho dòng tiền ngắn hạn.*

**A2. Cầu đi đâu rồi? — di cư kênh, không phải mất khách.**
First principle: khách không "biến mất", họ **mua chỗ khác**; không thể reactivate vào kênh họ đã rời.
2025–2026 ở VN, mua supplement dịch mạnh sang **TikTok Shop / livestream**. Core sụp + Shopee đơn nhỏ
tăng có thể là tín hiệu cầu dịch sang nơi rẻ/tiện hơn, không phải ngừng dùng.
→ **Action:** 1 ngày recon — Fine Japan đang bán ở đâu trên TikTok Shop? Giá nào? Ai bán? Đối thủ
livestream nào? Nếu cầu đã dịch → win-back về kênh nhà thua nếu không trả lời được "tại sao mua của
mình chứ không phải livestream rẻ hơn".
→ **Spawned:** [demand-migration-recon](../02-understand/demand-migration-recon.md)

**A3. Cái gì vỡ ở phía CUNG? — blind spot lớn nhất.**
First principle: doanh thu = f(cầu, **cung**, quan hệ). Toàn bộ phân tích đang ở phía cầu/khách.
"Ế" đột ngột 2025 thường có nguyên nhân cung/vận hành: **OOS hero-SKU**, tăng giá, mất 1 sales chủ
chốt, mất quyền phân phối, đối tác sỉ đổi nguồn, công nợ đọng.
→ **Action:** hỏi chính chủ/sales lead (không hỏi data): ***"Chính xác chuyện gì xảy ra Q1–Q2 2025
khiến B2B rơi?"*** Câu trả lời có thể là 1 sự kiện cụ thể mà không model retention nào thấy được.
→ **Spawned:** [b2b-collapse-root-cause](../02-understand/b2b-collapse-root-cause.md)

### Nhóm B — Reframe "BÁN NHƯ THẾ NÀO" (cơ chế, áp dụng ngay)

**B4. JTBD — bán "kết quả/sự kiện", không bán "collagen".**
First principle: không ai mua collagen vì collagen; họ "thuê" nó cho một **job cảm xúc/sự kiện**
(trẻ lại trước cưới/Tết, hết lo lão hóa, da đẹp để tự tin). Plan mô tả sản phẩm theo timeline sinh lý
(đúng cho reorder), nhưng **trigger MUA là cảm xúc/sự kiện**.
→ **Action:** phân khúc lại theo "job": mua cho mình (self-care, chu kỳ đều) vs mua **làm quà**
(mẹ, Tết — đúng pattern US-gift). Message khác hẳn. Acquisition bắt **mùa sự kiện** (Tết, hè, mùa cưới),
không chỉ nhịp sinh lý cho reorder.
→ **Spawned:** [retention-mechanisms](../04-opportunities/retention-mechanisms.md)

**B5. Đây là business subscription trá hình.**
First principle: hàng tái mua mỗi 45–60 ngày = **mô hình subscription**. Tài sản thật không phải "số đơn"
mà là **số khách đang trong chu kỳ replenish**. Đang bán từng đơn rời rạc thay vì bán **quan hệ bổ sung định kỳ**.
→ **Action:** "Subscribe & Save" — đăng ký giao định kỳ 45 ngày, giảm 10% + freeship. Biến reorder từ
*quyết định lặp lại* (dễ rớt) thành *mặc định* (phải chủ động hủy) — đòn bẩy M1-repeat mạnh hơn voucher
win-back. Metric Bắc Đẩu đổi thành **"active replenishers"**.
→ **Spawned:** [retention-mechanisms](../04-opportunities/retention-mechanisms.md)

**B6. Trust/Chính hãng là con hào — đặc biệt với US-gift.**
First principle: supplement VN ngập hàng giả; lý do #1 khách không mua lại / mua chỗ rẻ = **sợ giả**.
Reframe luồng US-gift (mục 6): không phải "tệp chưa trả tiền" mà là **tài sản TRUST** — "người nhà gửi
từ Mỹ" = bảo chứng thật 100%.
→ **Action:** pitch US-gift xoay quanh trust transfer: *"Anh/chị đang dùng hàng người nhà gửi — chính
hãng. Bên em là **cùng nguồn chính hãng đó tại VN**, khỏi chờ gửi từ Mỹ."* Với toàn brand: "chống giả"
thành positioning chính (tem, QR truy xuất) — có thể là một nguyên nhân core collapse mà data không thấy.
→ **Spawned:** [retention-mechanisms](../04-opportunities/retention-mechanisms.md)

**B7. Flywheel giới thiệu tại khoảnh khắc KẾT QUẢ — cơ chế đang thiếu hoàn toàn.**
First principle: collagen cho kết quả **nhìn thấy + mang tính xã hội** (da đẹp → người ta hỏi). Khách hài
lòng ở **tuần 6–8 là kênh acquisition rẻ nhất** (CAC ≈ 0). Plan có Touch 3 (Day 45) chỉ để reorder —
bỏ lỡ cú "xin giới thiệu/UGC" đúng lúc khách thấy kết quả.
→ **Action:** thêm **Touch "kết quả"** (~tuần 6–8): xin review/ảnh before-after + mã giới thiệu
("giới thiệu bạn, cả hai được X"). Vá xô thủng từ **đầu vào**, không chỉ giữ nước. (Bổ sung vào sequence mục 5.7.)
→ **Spawned:** [retention-mechanisms](../04-opportunities/retention-mechanisms.md)

### Nhóm C — Meta

**C8. Một mũi nhọn (KISS chống dàn trải).**
First principle: doanh nghiệp ế thường **dàn quá mỏng** (4 kênh, nhiều SKU, 5 luồng, P0–P4) trong khi
nhân lực CSKH giới hạn (câu hỏi mở #4).
→ **Action:** chọn **1 wedge** thắng trước rồi mới mở: *1 segment × 1 hero-SKU × 1 message × 2 tuần*.
Có 1 win thật → nhân rộng. Đừng chạy song song 5 luồng với đội mỏng.

> **Sắp xếp ưu tiên & câu hỏi quyết định** → đã chuyển sang [03-evaluate](../03-evaluate/README.md).
