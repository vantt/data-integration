# Hướng dẫn Phân loại Khách hàng (Customer Segmentation)

> **Dành cho:** Sales, Marketing, Data Team
> **Cập nhật:** 2026-04-18
> **Bảo trì:** Data Team

## Tài liệu này trả lời những câu hỏi nào?

1. Có những cách nào để phân loại khách hàng?
2. Chiều nào dùng cho mục đích gì?
3. Làm sao để triển khai trong Sapo?
4. Khi nào dùng Manual vs Auto group?

---

## TL;DR

- **8 chiều phân loại độc lập** — customer_type, value_group, lifecycle_stage, channel_preference, product_affinity, payment_behavior, geo_region, acquisition_source
- **Mỗi chiều trả lời 1 câu hỏi riêng** — Có thể kết hợp để phân tích sâu
- **Manual vs Auto** — customer_type/acquisition_source dùng manual; còn lại auto theo điều kiện
- **customer_type vs value_group** — customer_type là bản chất quan hệ (RETAIL, WHOLESALE); value_group là giá trị đóng góp (VALUE_VIP, VALUE_GOLD)

---

## Tổng quan Ma trận Phân loại

```
┌──────────────────────────────────────────────────────────────────┐
│                    CUSTOMER SEGMENTATION MATRIX                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  NHÓM 1: COMMERCIAL (Ảnh hưởng giá/chính sách)                  │
│  ════════════════════════════════════════════                    │
│  • customer_type      Manual  Bản chất quan hệ với công ty       │
│  • payment_behavior   Auto    Hành vi thanh toán, quản lý công nợ│
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  NHÓM 2: BEHAVIORAL (Hiểu hành vi khách)                        │
│  ═══════════════════════════════════════                         │
│  • value_group        Auto    Giá trị đóng góp (RFM-based)       │
│  • lifecycle_stage    Auto    Trạng thái trong vòng đời          │
│  • channel_preference Auto    Kênh mua hàng ưa thích             │
│  • product_affinity   Auto    Thương hiệu/danh mục ưa thích      │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  NHÓM 3: DEMOGRAPHIC (Thông tin khách)                          │
│  ═════════════════════════════════════                           │
│  • geo_region         Auto    Vị trí địa lý                      │
│  • acquisition_source Manual  Nguồn khách hàng                   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phân biệt customer_type vs value_group

```
customer_type = Bản chất quan hệ         value_group = Giá trị đóng góp
       │                                        │
       ▼                                        ▼
  RETAIL, WHOLESALE,                      VALUE_VIP, VALUE_GOLD,
  PARTNER, STAFF, KOL                     VALUE_SILVER, VALUE_BRONZE

→ Khách lẻ chi 50M+ = customer_type=RETAIL + value_group=VALUE_VIP
→ Đại lý mới = customer_type=WHOLESALE + value_group=VALUE_BRONZE
→ KOL = customer_type=KOL (bất kể doanh số)
```

**Quy tắc:** customer_type KHÔNG thay đổi theo doanh số, chỉ thay đổi khi quan hệ thay đổi (vd: từ RETAIL → WHOLESALE khi ký hợp đồng đại lý).

---

## Chi tiết từng chiều phân loại

### 1. customer_type — "Khách là ai? Quan hệ gì với công ty?"

**Mục đích:** Xác định bản chất quan hệ với công ty — ảnh hưởng pricing, communication, chính sách.

**Loại:** Manual (Sales team quyết định)

**Tính chất:** Mutually exclusive — 1 khách chỉ thuộc 1 type

| Type | Code | Mô tả | Chính sách giá |
|------|------|-------|----------------|
| Retail | `RETAIL` | Khách lẻ mua qua các kênh B2C | Giá niêm yết |
| Wholesale | `WHOLESALE` | Khách sỉ, đại lý, mua số lượng lớn | Giá sỉ (chiết khấu cố định ~40-50%) |
| Partner | `PARTNER` | CTV, đại lý nhỏ, đối tác | Giá đối tác (theo thỏa thuận) |
| Staff | `STAFF` | Nhân viên công ty | Giá ưu đãi nhân viên |
| KOL | `KOL` | Influencer, người có ảnh hưởng | Giá ưu đãi + hỗ trợ content |

**Cách xác định:**
- Default: `RETAIL`
- Sales team cập nhật thủ công khi ký hợp đồng sỉ/đối tác
- HR cập nhật cho nhân viên
- Marketing cập nhật cho KOL

**Lưu ý quan trọng:**
- Discount của khách `WHOLESALE` là **giá sỉ cố định**, không phải promotion
- Khi phân tích hiệu quả promotion, **phải filter** `customer_type = 'RETAIL'` only
- `KOL` khác với `SOURCE_KOL` (acquisition source): customer_type=KOL là chính KOL, SOURCE_KOL là khách đến từ KOL

---

### 2. value_group — "Khách có giá trị đóng góp thế nào?"

**Mục đích:** Phân loại khách theo tổng giá trị đóng góp (Customer Lifetime Value proxy).

**Loại:** Auto (theo điều kiện mua hàng)

**Tính chất:** Mutually exclusive — 1 khách chỉ thuộc 1 tier. **Độc lập với customer_type.**

| Tier | Code | Điều kiện | Ưu tiên |
|------|------|-----------|---------|
| VIP | `VALUE_VIP` | Tổng chi tiêu ≥ 50M **HOẶC** số đơn ≥ 20 | Cao nhất |
| Gold | `VALUE_GOLD` | Tổng chi tiêu ≥ 20M | Cao |
| Silver | `VALUE_SILVER` | Tổng chi tiêu ≥ 5M | Trung bình |
| Bronze | `VALUE_BRONZE` | Còn lại | Cơ bản |

**Phân biệt với customer_type:**
- Khách `WHOLESALE` mua nhiều → vẫn có thể là `VALUE_VIP`
- Khách `RETAIL` chi 50M → là `VALUE_VIP` (không phải VIP customer type)
- `VALUE_VIP` là tier doanh số, KHÔNG phải loại khách hàng

**Logic đánh giá (thứ tự ưu tiên):**
```sql
CASE
  WHEN total_spend >= 50000000 OR order_count >= 20 THEN 'VALUE_VIP'
  WHEN total_spend >= 20000000 THEN 'VALUE_GOLD'
  WHEN total_spend >= 5000000 THEN 'VALUE_SILVER'
  ELSE 'VALUE_BRONZE'
END
```

**Use cases:**
- Ưu tiên chăm sóc khách VIP
- Phân bổ resource telesale theo value tier
- Tặng quà/ưu đãi theo tier

---

### 3. lifecycle_stage — "Khách đang ở giai đoạn nào?"

**Mục đích:** Xác định trạng thái hoạt động của khách trong vòng đời.

**Loại:** Auto (theo thời gian mua hàng)

**Tính chất:** Mutually exclusive, thay đổi theo thời gian

| Stage | Code | Điều kiện | Hành động |
|-------|------|-----------|-----------|
| New | `LIFECYCLE_NEW` | Khách mới ≤ 30 ngày **VÀ** ≤ 2 đơn | Onboarding, welcome flow |
| Active | `LIFECYCLE_ACTIVE` | Mua trong 90 ngày gần nhất | Maintain, upsell |
| At Risk | `LIFECYCLE_AT_RISK` | Không mua 90-180 ngày | Win-back campaign |
| Churned | `LIFECYCLE_CHURNED` | Không mua > 180 ngày | Re-activation campaign |

**Logic đánh giá:**
```sql
CASE
  WHEN days_since_first_order <= 30 AND order_count <= 2 THEN 'LIFECYCLE_NEW'
  WHEN days_since_last_order <= 90 THEN 'LIFECYCLE_ACTIVE'
  WHEN days_since_last_order <= 180 THEN 'LIFECYCLE_AT_RISK'
  ELSE 'LIFECYCLE_CHURNED'
END
```

**Use cases:**
- Gửi email win-back cho `AT_RISK`
- Đo tỷ lệ churn rate
- Phân tích cohort retention

---

### 4. channel_preference — "Khách thích mua ở đâu?"

**Mục đích:** Xác định kênh mua hàng chính của khách.

**Loại:** Auto (theo lịch sử đơn hàng)

**Tính chất:** Dựa trên kênh có nhiều đơn nhất (mode)

| Preference | Code | Kênh thuộc nhóm |
|------------|------|-----------------|
| Social | `CHANNEL_SOCIAL` | Zalo, Facebook, Instagram |
| Marketplace | `CHANNEL_MARKETPLACE` | Shopee, Lazada, Tiki, TikTok |
| Direct | `CHANNEL_DIRECT` | Web, Telesale, CS |
| Offline | `CHANNEL_OFFLINE` | POS các chi nhánh |

**Logic đánh giá:**
```sql
-- Lấy channel_format có nhiều đơn nhất của khách
SELECT customer_id,
  CASE mode(channel_format)
    WHEN 'Social' THEN 'CHANNEL_SOCIAL'
    WHEN 'Marketplace' THEN 'CHANNEL_MARKETPLACE'
    WHEN 'Web' THEN 'CHANNEL_DIRECT'
    WHEN 'Direct' THEN 'CHANNEL_DIRECT'
    WHEN 'Retail' THEN 'CHANNEL_OFFLINE'
    ELSE 'CHANNEL_OTHER'
  END as channel_preference
FROM orders
GROUP BY customer_id
```

**Use cases:**
- Target quảng cáo theo kênh ưa thích
- Phân bổ budget marketing theo channel preference
- Hiểu hành vi cross-channel

---

### 5. product_affinity — "Khách thích mua brand/category nào?"

**Mục đích:** Xác định thương hiệu sản phẩm khách mua nhiều nhất.

**Loại:** Auto (theo lịch sử mua hàng)

**Tính chất:** Dựa trên brand có doanh thu cao nhất

| Affinity | Code | Điều kiện |
|----------|------|-----------|
| Fine Japan | `PRODUCT_FINE_JAPAN` | Mua Fine Japan > 60% doanh thu |
| FG Care | `PRODUCT_FG_CARE` | Mua FG Care > 60% doanh thu |
| Fine Care | `PRODUCT_FINE_CARE` | Mua Fine Care > 60% doanh thu |
| Multi-brand | `PRODUCT_MULTI` | Không brand nào > 60% |

**Logic đánh giá:**
```sql
WITH brand_share AS (
  SELECT customer_id, brand_name,
    SUM(revenue) / SUM(SUM(revenue)) OVER (PARTITION BY customer_id) as share
  FROM sales
  GROUP BY customer_id, brand_name
)
SELECT customer_id,
  CASE
    WHEN MAX(share) FILTER (WHERE brand_name = 'Fine Japan Vietnam') > 0.6 
      THEN 'PRODUCT_FINE_JAPAN'
    WHEN MAX(share) FILTER (WHERE brand_name = 'FG Care') > 0.6 
      THEN 'PRODUCT_FG_CARE'
    WHEN MAX(share) FILTER (WHERE brand_name = 'Fine Care') > 0.6 
      THEN 'PRODUCT_FINE_CARE'
    ELSE 'PRODUCT_MULTI'
  END
FROM brand_share
GROUP BY customer_id
```

**Use cases:**
- Cross-sell recommendation (khách Fine Japan → giới thiệu FG Care)
- Phân tích brand loyalty
- Target campaign theo brand affinity

---

### 6. payment_behavior — "Khách thanh toán thế nào?"

**Mục đích:** Phân loại theo hành vi thanh toán, đặc biệt quan trọng cho B2B.

**Loại:** Auto (theo lịch sử thanh toán)

**Tính chất:** Mutually exclusive

| Behavior | Code | Điều kiện |
|----------|------|-----------|
| Prepaid | `PAYMENT_PREPAID` | Luôn thanh toán trước khi giao |
| COD | `PAYMENT_COD` | Chủ yếu thanh toán khi nhận hàng |
| Credit | `PAYMENT_CREDIT` | Có hạn mức công nợ (B2B) |
| Delinquent | `PAYMENT_DELINQUENT` | Có khoản nợ quá hạn > 30 ngày |

**Logic đánh giá:**
```sql
CASE
  WHEN debt > 0 AND days_overdue > 30 THEN 'PAYMENT_DELINQUENT'
  WHEN has_credit_term = true THEN 'PAYMENT_CREDIT'
  WHEN pct_cod_orders > 0.7 THEN 'PAYMENT_COD'
  ELSE 'PAYMENT_PREPAID'
END
```

**Use cases:**
- Cảnh báo khách `DELINQUENT` cho Finance
- Chính sách credit limit cho `CREDIT`
- Ưu tiên giao hàng cho `PREPAID`

---

### 7. geo_region — "Khách ở đâu?"

**Mục đích:** Phân loại theo vị trí địa lý.

**Loại:** Auto (theo địa chỉ giao hàng)

| Region | Code | Tỉnh/Thành |
|--------|------|------------|
| HCMC | `GEO_HCMC` | TP. Hồ Chí Minh |
| Hanoi | `GEO_HANOI` | Hà Nội |
| Mekong | `GEO_MEKONG` | Các tỉnh miền Tây |
| Central | `GEO_CENTRAL` | Các tỉnh miền Trung |
| Other | `GEO_OTHER` | Còn lại |

**Use cases:**
- Tối ưu logistics theo vùng
- Regional marketing campaigns
- Phân tích penetration theo địa lý

---

### 8. acquisition_source — "Khách đến từ đâu?"

**Mục đích:** Tracking nguồn acquisition để đo marketing ROI.

**Loại:** Manual (Sales/Marketing tag khi tạo khách)

| Source | Code | Mô tả |
|--------|------|-------|
| Organic | `SOURCE_ORGANIC` | Tự tìm đến (search, direct) |
| Ads | `SOURCE_ADS` | Từ quảng cáo (FB Ads, Google Ads) |
| Referral | `SOURCE_REFERRAL` | Được giới thiệu bởi khách khác |
| KOL | `SOURCE_KOL` | Từ influencer/KOL |
| Event | `SOURCE_EVENT` | Từ sự kiện, hội chợ |

**Use cases:**
- Đo CAC (Customer Acquisition Cost) theo source
- So sánh LTV theo source
- Tối ưu marketing budget

---

## Bảng tổng hợp

| Chiều | Field | Loại | Câu hỏi | Ảnh hưởng |
|-------|-------|------|---------|-----------|
| Customer Type | `customer_type` | Manual | Khách là ai? | Pricing, Policy |
| Value | `value_group` | Auto | Giá trị đóng góp? | Service level |
| Lifecycle | `lifecycle_stage` | Auto | Giai đoạn? | Marketing action |
| Channel | `channel_preference` | Auto | Kênh nào? | Channel strategy |
| Product | `product_affinity` | Auto | Brand nào? | Cross-sell |
| Payment | `payment_behavior` | Auto | Thanh toán? | Finance, Risk |
| Geo | `geo_region` | Auto | Ở đâu? | Logistics |
| Source | `acquisition_source` | Manual | Từ đâu? | Marketing ROI |

---

## Hướng dẫn triển khai trong Sapo

### Bước 1: Đổi tên groups hiện tại

```
Hiện tại          →  Chuẩn hóa
─────────────────────────────────
RETAIL (BANLE)    →  RETAIL
WHOLESALE (BANBUON) → WHOLESALE
```

### Bước 2: Tạo thêm customer_type (Manual)

| Group Name | Code | Note |
|------------|------|------|
| Partner | PARTNER | CTV, đại lý nhỏ |
| Staff | STAFF | Nhân viên |
| KOL | KOL | Influencer, người có ảnh hưởng |

### Bước 3: Tạo VALUE tiers (Auto)

Sapo hỗ trợ auto-group theo `total_expense`:

| Group Name | Code | Condition |
|------------|------|-----------|
| VIP Customer | VALUE_VIP | total_expense >= 50,000,000 |
| Gold Customer | VALUE_GOLD | total_expense >= 20,000,000 |
| Silver Customer | VALUE_SILVER | total_expense >= 5,000,000 |
| Bronze Customer | VALUE_BRONZE | (default) |

### Bước 4: Tạo LIFECYCLE stages (Auto)

Sapo hỗ trợ auto-group theo `last_order_date`:

| Group Name | Code | Condition |
|------------|------|-----------|
| New Customer | LIFECYCLE_NEW | first_order <= 30 days AND orders <= 2 |
| Active Customer | LIFECYCLE_ACTIVE | last_order <= 90 days |
| At Risk Customer | LIFECYCLE_AT_RISK | last_order 90-180 days |
| Churned Customer | LIFECYCLE_CHURNED | last_order > 180 days |

---

## Ví dụ phân tích kết hợp nhiều chiều

| Câu hỏi | Segments kết hợp | Insight |
|---------|------------------|---------|
| Khách VIP nào đang có nguy cơ mất? | `value_group=VALUE_VIP` + `lifecycle_stage=AT_RISK` | Danh sách ưu tiên win-back |
| Khách sỉ hay mua qua kênh nào? | `customer_type=WHOLESALE` + `channel_preference=*` | Tối ưu kênh B2B |
| Khách Fine Japan có mua FG Care không? | `product_affinity=FINE_JAPAN` → cross-buy analysis | Cơ hội cross-sell |
| Khách B2B nào đang nợ quá hạn? | `customer_type=WHOLESALE` + `payment_behavior=DELINQUENT` | Cảnh báo công nợ |
| Khách mới từ KOL có giá trị cao không? | `acquisition_source=KOL` + `lifecycle_stage=NEW` → value trend | Đánh giá KOL ROI |
| Vùng nào có nhiều khách churned? | `lifecycle_stage=CHURNED` + `geo_region=*` | Regional retention issue |
| KOL có value cao không? | `customer_type=KOL` → `value_group` distribution | Đánh giá KOL performance |

---

## Ưu tiên triển khai

| Phase | Chiều | Timeline | Owner |
|-------|-------|----------|-------|
| P0 | customer_type | Tuần 1 | Sales + Data |
| P1 | value_group, lifecycle_stage | Tuần 2-3 | Data |
| P2 | channel_preference, product_affinity | Tuần 4-5 | Data |
| P3 | payment_behavior, geo_region, acquisition_source | Khi cần | Data + Finance |

---

## Checklist triển khai

**P0 - customer_type (Manual)**
- [ ] Chuẩn hóa RETAIL, WHOLESALE trong Sapo
- [ ] Tạo PARTNER, STAFF, KOL groups
- [ ] Cập nhật **36 khách sỉ ẩn** → WHOLESALE/PARTNER (chờ Sales xác nhận)
- [ ] Document policy: ai được approve chuyển customer_type?

> **Scan 2026-05-26:** Data team đã scan 14,640 đơn và tìm được 36 khách đang label RETAIL nhưng có pattern sỉ (D% 40–73%, AOV ≥2M, ≥3 đơn). Chia 3 nhóm:
> - **Nhóm 1 (10 khách):** D% ≥55% — chắc sỉ, suggest `WHOLESALE`
> - **Nhóm 2 (21 khách):** D% 40–55% — cần Sales xác nhận, suggest `WHOLESALE`
> - **Nhóm 3 (5 khách):** Tên business (shop/nhà thuốc) — suggest `PARTNER`
>
> File xác nhận: `plans/reports/wholesale-customers-review-260526.csv`
> Chi tiết danh sách: `docs/context/channel-grouping-analysis.md` — Vấn đề 5

**P1 - value_group & lifecycle_stage (Auto)**
- [ ] Kiểm tra Sapo plan có hỗ trợ auto-group không
- [ ] Tạo 4 value_group tiers với điều kiện
- [ ] Tạo 4 lifecycle_stage với điều kiện
- [ ] Test auto-assignment

**P2+ - Các chiều còn lại**
- [ ] Đánh giá nhu cầu thực tế trước khi triển khai
- [ ] Ưu tiên chiều nào có use case rõ ràng

---

## Câu hỏi thường gặp

**Q: Một khách có thể thuộc nhiều group không?**

A: Có. Mỗi chiều độc lập. Ví dụ: Khách A có thể là `customer_type=WHOLESALE` + `value_group=VALUE_VIP` + `lifecycle_stage=ACTIVE` + `channel_preference=SOCIAL`.

**Q: Khi nào dùng Manual vs Auto group?**

A: 
- **Manual:** Khi cần con người quyết định (customer_type, acquisition_source) hoặc không có data tự động
- **Auto:** Khi có thể derive từ data (value, lifecycle, channel, product)

**Q: Làm sao để discount analysis không bị sai?**

A: Luôn filter `customer_type = 'RETAIL'` khi phân tích promotion discount. Khách `WHOLESALE` có discount 40-50% là giá sỉ, không phải KM.

**Q: customer_type và value_group khác nhau thế nào?**

A:
- **customer_type**: Bản chất quan hệ (RETAIL, WHOLESALE, PARTNER, STAFF, KOL) — manual, ít thay đổi
- **value_group**: Giá trị đóng góp (VALUE_VIP, VALUE_GOLD...) — auto theo doanh số, thay đổi theo thời gian
- Khách RETAIL chi 50M+ → `customer_type=RETAIL` + `value_group=VALUE_VIP` (vẫn là khách lẻ, nhưng VIP tier)

**Q: VIP là customer_type hay value_group?**

A: **value_group**. "VIP" là tier doanh số (VALUE_VIP), không phải loại khách hàng. Đừng nhầm với customer_type.

**Q: Auto group có update real-time không?**

A: Tùy Sapo plan. Thường là daily hoặc khi có đơn hàng mới.

---

## Liên kết tài liệu

- [Data Model Overview](./data-model-overview.md) — Tổng quan data model (entry point)
- [Sales Segmentation Guide](./sales-segmentation-guide.md) — Gom nhóm doanh thu (kênh, sản phẩm, team, nhân viên)
- [Team Management](./team-management.md) — Quản lý team và attribution
- [Channel Grouping Analysis](./channel-grouping-analysis.md) — Phân tích gom nhóm kênh
