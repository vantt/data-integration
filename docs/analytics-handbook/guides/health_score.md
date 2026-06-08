# Health Score — Chỉ số Sức khỏe Kinh doanh

> **Đối tượng:** CEO, Store Manager, Sales Ops
> **Cập nhật:** 2026-04-01
> **Hiển thị tại:** Daily Sales Dashboard, Yesterday's Sales Dashboard (tab Tổng quan)

## Mục đích

Health Score là **một con số duy nhất (0-100)** cho biết tình hình kinh doanh đang khỏe hay đang có vấn đề. Mở dashboard lên, nhìn 2 giây là biết.

Không cần đọc 10 biểu đồ. Không cần so sánh từng con số. Health Score tổng hợp 4 chiều quan trọng nhất thành 1 điểm.

---

## Cách đọc

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   75 – 100    Khỏe mạnh                            │
│               Các chỉ số đều tăng hoặc ổn định.    │
│               Tiếp tục vận hành bình thường.        │
│                                                     │
│   50 – 74     Cần chú ý                            │
│               Có chỉ số đang giảm.                  │
│               Xem bảng Health Breakdown để biết      │
│               vấn đề nằm ở đâu.                     │
│                                                     │
│    0 – 49     Báo động                              │
│               Nhiều chỉ số sụt nghiêm trọng.        │
│               Cần hành động ngay.                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 4 thành phần

Health Score = tổng 4 thành phần, mỗi thành phần tối đa **25 điểm**.

### 1. Doanh thu (Revenue Momentum) — max 25đ

So sánh tổng doanh thu thuần (Net Revenue) **7 ngày gần nhất** vs **7 ngày trước đó** (Week-over-Week).

| WoW Change | Điểm | Ý nghĩa |
|------------|-------|---------|
| >= +5% | 25 | Doanh thu tăng trưởng tốt |
| 0% đến +5% | 20 | Ổn định, nhích nhẹ |
| -10% đến 0% | 15 | Giảm nhẹ, cần theo dõi |
| -25% đến -10% | 8 | Giảm đáng kể |
| < -25% | 0 | Sụt nghiêm trọng |

**Tại sao quan trọng:** Doanh thu là chỉ số sống còn. Giảm 1 tuần có thể là dao động bình thường, nhưng giảm liên tục nhiều tuần là tín hiệu cần hành động.

### 2. Đơn hàng (Order Momentum) — max 25đ

So sánh số lượng đơn hàng **7 ngày gần nhất** vs **7 ngày trước đó**.

| WoW Change | Điểm | Ý nghĩa |
|------------|-------|---------|
| >= +5% | 25 | Đơn hàng tăng |
| 0% đến +5% | 20 | Ổn định |
| -10% đến 0% | 15 | Giảm nhẹ |
| -25% đến -10% | 8 | Giảm đáng kể |
| < -25% | 0 | Sụt nghiêm trọng |

**Tại sao tách riêng doanh thu và đơn hàng:** Doanh thu tăng nhưng đơn hàng giảm = bạn đang bán được đơn lớn nhưng mất khách nhỏ. Đơn hàng tăng nhưng doanh thu giảm = bạn đang bán nhiều đơn rẻ hơn. Hai tín hiệu rất khác nhau.

### 3. Khách quay lại (Customer Loyalty) — max 25đ

Tỷ lệ khách hàng quay lại mua trong 7 ngày gần nhất (khách đã từng mua trước đó / tổng khách mua).

| Returning Rate | Điểm | Ý nghĩa |
|---------------|-------|---------|
| >= 50% | 25 | Khách trung thành, nền tảng vững |
| 35% – 50% | 20 | Bình thường |
| 20% – 35% | 12 | Khách mới nhiều nhưng ít quay lại |
| < 20% | 5 | Hầu như toàn khách mới, rất ít quay lại |

**Tại sao quan trọng nhất cho "bán ế":** Nếu doanh thu giảm nhưng khách cũ vẫn quay lại, vấn đề có thể chỉ là mùa thấp điểm hoặc marketing yếu. Nhưng nếu khách cũ cũng không quay lại, đó là vấn đề nền tảng — sản phẩm, dịch vụ, hoặc giá cả có gì đó sai.

### 4. Giá trị đơn hàng (AOV Stability) — max 25đ

So sánh AOV (Average Order Value) **7 ngày gần nhất** vs **7 ngày trước đó**.

| AOV Change | Điểm | Ý nghĩa |
|-----------|-------|---------|
| -5% đến +15% | 25 | Ổn định hoặc tăng nhẹ — tốt |
| > +15% | 20 | Tăng mạnh — có thể do mất khách mua đơn nhỏ |
| -15% đến -5% | 15 | Giảm nhẹ — khách đang mua ít hơn |
| < -15% | 5 | Giảm mạnh — khách đang cắt giảm chi tiêu |

**Tại sao đo "ổn định" thay vì "càng cao càng tốt":** AOV tăng đột biến không hẳn tốt — có thể vì bạn mất hết khách mua đơn nhỏ, chỉ còn vài đơn lớn. AOV ổn định trong khi đơn hàng tăng mới là tín hiệu khỏe mạnh thật sự.

---

## Cách hành động theo Health Score

### Score 75-100: Khỏe mạnh

Không cần hành động khẩn cấp. Tập trung vào:
- Duy trì chất lượng dịch vụ
- Thử nghiệm kênh mới hoặc sản phẩm mới
- Tối ưu margin

### Score 50-74: Cần chú ý

Xem bảng **Health Breakdown** để xác định vấn đề:

| Component báo động | Hành động |
|---------------------|-----------|
| Doanh thu giảm, đơn hàng ổn | Kiểm tra AOV — khách mua ít tiền hơn? Xem tab Sản phẩm: sản phẩm giá cao có bán không? |
| Đơn hàng giảm, doanh thu ổn | Ít khách hơn nhưng chi nhiều hơn. Kiểm tra kênh: kênh nào mất traffic? |
| Khách quay lại thấp | Vấn đề retention. Kiểm tra: chất lượng sản phẩm, dịch vụ sau bán, chương trình loyalty |
| AOV giảm | Khách đang cắt giảm. Xem có promotion nào đang cannibalize doanh thu không |

### Score 0-49: Báo động

Cần hành động ngay:
1. Xác định component nào 0 điểm — đó là vấn đề cấp bách nhất
2. Mở tab **Kênh bán hàng** — kênh nào sụt nhiều nhất?
3. Mở tab **Sản phẩm** — sản phẩm nào còn bán được?
4. So sánh với tuần trước trong **CEO Weekly Pulse** — đây là tạm thời hay xu hướng dài?

---

## Ví dụ thực tế

### Ví dụ 1: Score = 50 (Cần chú ý)

```
Doanh thu (WoW):    0/25   WoW: -33.5%    Báo động
Đơn hàng (WoW):     0/25   WoW: -36.5%    Báo động
Khách quay lại:     25/25   Rate: 66.7%    OK
AOV ổn định:        25/25   WoW: +4.8%     OK
```

**Đọc:** Doanh thu và đơn hàng sụt nặng, nhưng khách cũ vẫn quay lại và giá trị đơn hàng ổn. Vấn đề không phải sản phẩm/dịch vụ (khách cũ vẫn thích), mà là **traffic/marketing** — cần thu hút thêm khách mới.

### Ví dụ 2: Score = 30 (Báo động)

```
Doanh thu (WoW):    0/25   WoW: -40%      Báo động
Đơn hàng (WoW):     8/25   WoW: -15%      Báo động
Khách quay lại:     12/25  Rate: 28%       Chú ý
AOV ổn định:        10/25  WoW: -12%       Chú ý
```

**Đọc:** Tất cả đều giảm, đặc biệt khách quay lại thấp + AOV giảm. Đây là tín hiệu **khách đang bỏ đi và những người còn lại mua ít hơn**. Cần kiểm tra ngay: sản phẩm có vấn đề? Đối thủ đang giảm giá mạnh? Có negative review nào gần đây?

### Ví dụ 3: Score = 90 (Khỏe mạnh)

```
Doanh thu (WoW):   25/25   WoW: +12%      OK
Đơn hàng (WoW):    20/25   WoW: +3%       OK
Khách quay lại:    25/25   Rate: 55%       OK
AOV ổn định:       20/25   WoW: +8%        OK
```

**Đọc:** Mọi thứ đều tốt. Doanh thu tăng mạnh, đơn hàng tăng nhẹ, khách trung thành cao, giá trị đơn hàng tăng. Đây là thời điểm để **mở rộng** — thử kênh mới, sản phẩm mới.

---

## Giới hạn

- Health Score dùng **cửa sổ 7 ngày**. Nếu có sự kiện đặc biệt (Tết, Black Friday), score có thể bị lệch tạm thời.
- Score không phân biệt được "giảm vì mùa thấp" vs "giảm vì vấn đề thật". Cần kết hợp với kinh nghiệm kinh doanh.
- Returning customer rate phụ thuộc vào data quality của `dim_customers.first_order_date`.
- Score được thiết kế cho retail/e-commerce SMB. Ngành khác có thể cần điều chỉnh trọng số.

---

## Tham chiếu kỹ thuật

- **Source tables:** `fact_orders`, `dim_customers`
- **Blueprints:** [`sales_today_operation.md`](../blueprints/sales_today_operation.md), [`sales_yesterday_operation.md`](../blueprints/sales_yesterday_operation.md)
- **SQL logic:** Xem card "Health Score" và "Health Breakdown" trong blueprint
- **Scoring formula:** 4 components × 25 points = 100 max. Thresholds calibrated cho retail SMB Vietnam.
